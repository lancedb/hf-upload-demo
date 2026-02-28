"""Generate 1024x1024 character portraits into ./img from magical_kingdom.json."""

import base64
import json
import os
import re
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON = BASE_DIR / "magical_kingdom.json"
IMAGE_DIR = BASE_DIR / "img"
OPENAI_IMAGE_MODEL = "gpt-image-1.5"
FORCE_REGENERATE = True

load_dotenv()
load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR.parent / ".env", override=False)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def prompt_for(name: str, role: str, description: str) -> str:
    return "\n".join(
        [
            "Use case: illustration-story",
            "Asset type: dataset character portrait",
            f"Primary request: Create a cartoon portrait of {name}, {role}.",
            "Style/medium: consistent 2D storybook cartoon illustration, clean linework.",
            "Composition/framing: centered chest-up portrait, facing camera, readable silhouette.",
            "Lighting/mood: warm cinematic daylight, heroic but friendly mood.",
            f"Constraints: Reflect this description: {description}",
            "Avoid: photorealism, modern clothing, text, logo, watermark, extra hands.",
        ]
    )


def encode_jpeg_1024(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")
        if rgb.size != (1024, 1024):
            raise ValueError(f"Expected 1024x1024 image, got {rgb.size}")
        out = BytesIO()
        rgb.save(out, format="JPEG", quality=92)
        return out.getvalue()


def generate_one(client: OpenAI, prompt: str) -> bytes:
    response = client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        quality="high",
        output_format="jpeg",
    )
    item = response.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    if isinstance(item, dict) and item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    raise RuntimeError("OpenAI image API returned no b64 image payload")


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    rows = json.loads(INPUT_JSON.read_text())
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    for row in rows[3:]:
        filename = f"{slugify(row['name'])}.jpg"
        out_path = IMAGE_DIR / filename

        if out_path.exists() and not FORCE_REGENERATE:
            print(f"skip {out_path}")
            continue

        prompt = prompt_for(row["name"], row["role"], row["description"])
        raw = generate_one(client, prompt)
        out_path.write_bytes(encode_jpeg_1024(raw))
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
