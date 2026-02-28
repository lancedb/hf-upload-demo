"""
Simple filtered search and vector search LanceDB query examples.
"""

import os

import lancedb
from create_dataset import embed_clip_texts, embed_texts
from dotenv import load_dotenv

# Run on the hub directly
DB_URI = "hf://datasets/lancedb/magical_kingdom"
TABLE_NAME = "characters"

load_dotenv()
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be set in environment"


def q1_knights_filtered(table):
    """Who is the strongest of the knights? (traditional filter)"""
    return (
        table.search()
        .where("category = 'knight'")
        .select(["name", "role", "stats.strength"])
        .limit(4)
        .to_polars()
        .sort("stats.strength", descending=True)
        .head(1)
    )


def q2_high_magic_filtered(table):
    """Who are the most magical characters? (nested object filter)"""
    return (
        table.search()
        .where("stats.magic >= 4")
        .select(["name", "role", "stats.magic", "stats.strength"])
        .limit(2)
        .to_polars()
    )


def q3_text_vector_search(table):
    """Semantic search over text embeddings."""
    query = "a disloyal knight"
    query_vector = embed_texts([query])[0]
    return (
        table.search(query_vector, vector_column_name="text_vector")
        .select(["name", "role"])
        .limit(1)
        .to_polars()
    )


def q4_image_vector_search(table):
    """Text-to-image semantic search over image embeddings."""
    query = "a powerful mage with a staff and a long beard"
    query_vector = embed_clip_texts([query])[0]
    return (
        table.search(query_vector, vector_column_name="image_vector")
        .select(["name", "role"])
        .limit(2)
        .to_polars()
    )


def q5_fts_keyword_search(table):
    """Keyword search using FTS."""
    keyword = "mysterious"
    return (
        table.search(keyword, query_type="fts")
        .select(["name", "role", "description"])
        .limit(5)
        .to_polars()
    )


def main() -> None:
    db = lancedb.connect(DB_URI)
    table = db.open_table(TABLE_NAME)

    print("Q1: Who are the knights (filtered)", q1_knights_filtered(table))
    print(
        "Q2: Who are the most magical characters (filtered)",
        q2_high_magic_filtered(table),
    )
    print("Q3: Vector search (text_vector)", q3_text_vector_search(table))
    print("Q4: Vector search (image_vector)", q4_image_vector_search(table))
    print("Q5: Keyword search (FTS)", q5_fts_keyword_search(table))


if __name__ == "__main__":
    main()
