"""Build the Arthurian dataset in LanceDB with app-managed embeddings.

Requires:
- OPENAI_API_KEY in environment (.env is loaded)
- open-clip package available (e.g. `uv pip install open-clip-torch`)
"""

import json
import os
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import lancedb
import open_clip
import pyarrow as pa
import torch
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be set in environment"

INPUT_JSON = Path("magical_kingdom.json")
IMAGE_DIR = Path("img")
DB_DIR = Path("magical_kingdom")
TABLE_NAME = "characters"
BATCH_SIZE = 5
TEXT_MODEL = "text-embedding-3-small"
TEXT_DIMS = 1536
IMAGE_DIMS = 512
DEVICE = "cpu"

client = OpenAI()
clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="laion2b_s34b_b79k", device=DEVICE
)
clip_model.eval()

SCHEMA = pa.schema(
    [
        pa.field("id", pa.int32(), nullable=False),
        pa.field("image", pa.binary(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("role", pa.string(), nullable=False),
        pa.field("description", pa.string(), nullable=False),
        pa.field(
            "stats",
            pa.struct(
                [
                    pa.field("strength", pa.int8()),
                    pa.field("courage", pa.int8()),
                    pa.field("magic", pa.int8()),
                    pa.field("wisdom", pa.int8()),
                ]
            ),
            nullable=False,
        ),
        pa.field("image_path", pa.string(), nullable=False),
        pa.field("image_vector", pa.list_(pa.float32(), list_size=IMAGE_DIMS)),
        pa.field("text_for_embedding", pa.string(), nullable=False),
        pa.field("text_vector", pa.list_(pa.float32(), list_size=TEXT_DIMS)),
    ]
)

def embed_texts(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=TEXT_MODEL, input=texts)
    # Response is returned in input order.
    return [item.embedding for item in response.data]


def embed_images(image_bytes: list[bytes]) -> list[list[float]]:
    images = [Image.open(BytesIO(blob)).convert("RGB") for blob in image_bytes]
    image_tensor = torch.stack([clip_preprocess(img) for img in images]).to(DEVICE)
    with torch.no_grad():
        embeddings = clip_model.encode_image(image_tensor)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
    return embeddings.cpu().to(torch.float32).tolist()


def embed_clip_texts(texts: list[str]) -> list[list[float]]:
    tokens = open_clip.tokenize(texts).to(DEVICE)
    with torch.no_grad():
        embeddings = clip_model.encode_text(tokens)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
    return embeddings.cpu().to(torch.float32).tolist()


def iter_row_batches(batch_size: int = BATCH_SIZE) -> Iterator[pa.RecordBatch]:
    records = sorted(json.loads(INPUT_JSON.read_text()), key=lambda r: r["name"])
    image_paths = sorted(IMAGE_DIR.glob("*.jpg"), key=lambda p: p.name)
    source_rows: list[dict] = []

    for row, img_path in zip(records, image_paths):
        stats = row["stats"]

        source_rows.append(
            {
                "id": row["id"],
                "name": row["name"],
                "role": row["role"],
                "description": row["description"],
                "stats": {
                    "strength": stats["strength"],
                    "courage": stats["courage"],
                    "magic": stats["magic"],
                    "wisdom": stats["wisdom"],
                },
                "image_path": f"img/{img_path.name}",
                "image": img_path.read_bytes(),
                "text_for_embedding": f"{row['role']}. {row['description']}",
            }
        )

    for start in range(0, len(source_rows), batch_size):
        chunk = source_rows[start : start + batch_size]
        text_vectors = embed_texts([row["text_for_embedding"] for row in chunk])
        image_vectors = embed_images([row["image"] for row in chunk])

        out_rows = []
        for row, txt_vec, img_vec in zip(chunk, text_vectors, image_vectors):
            out_rows.append(
                {
                    **row,
                    "text_vector": txt_vec,
                    "image_vector": img_vec,
                }
            )

        yield pa.RecordBatch.from_pylist(out_rows, schema=SCHEMA)


def main() -> None:
    db = lancedb.connect(DB_DIR)

    table = db.create_table(
        TABLE_NAME,
        data=iter_row_batches(),
        schema=SCHEMA,
        mode="create",
    )

    print(f"Created table: {TABLE_NAME} with {table.count_rows()} rows.")

    table.create_fts_index("description", replace=True)
    print("Created FTS index on: description")

    print("Finished creating LanceDB dataset with embeddings and FTS index.")

if __name__ == "__main__":
    main()
