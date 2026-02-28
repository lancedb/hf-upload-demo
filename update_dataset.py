"""Minimal demo: add category column, then backfill with merge_insert."""

from pathlib import Path

import lancedb
import pyarrow as pa

DB_DIR = Path("magical_kingdom")
TABLE_NAME = "characters"


def classify(role: str, description: str) -> str:
    """Assign a category from role + description using simple heuristics."""
    role_l = role.lower()
    text_l = f"{role} {description}".lower()

    if "king" in role_l:
        return "king"
    if "queen" in role_l:
        return "queen"
    if "knight" in role_l:
        return "knight"
    if any(token in text_l for token in ["wizard", "sorcer", "mage", "enchant", "magic"]):
        return "mage"
    return "other"


def main() -> None:
    db = lancedb.connect(DB_DIR)
    table = db.open_table(TABLE_NAME)

    # Step 1: add the new column (schema evolution).
    table.add_columns(pa.field("category", pa.string()))
    table = db.open_table(TABLE_NAME)

    # Step 2: compute categories in Python and prepare merge input.
    n = table.count_rows()
    source = table.search().select(["id", "role", "description"]).limit(n).to_arrow()
    categories = [
        classify(role, description)
        for role, description in zip(
            source.column("role").to_pylist(),
            source.column("description").to_pylist(),
        )
    ]
    category_data = pa.table(
        {
            "id": source.column("id"),
            "category": pa.array(categories, type=pa.string()),
        }
    )

    # Step 3: one merge_insert to update category by id.
    (
        table.merge_insert("id")
        .when_matched_update_all()
        .execute(category_data)
    )

    print("Backfilled category values with merge_insert.")
    print(table.search().select(["id", "name", "category"]).limit(10).to_polars())


if __name__ == "__main__":
    main()
