---
license: cc-by-4.0
configs:
- config_name: characters
  data_dir: "characters.lance"
task_categories:
- feature-extraction
language:
- en
tags:
- lance
---

# Querying using LanceDB On Hugging Face

This guide shows how to run LanceDB queries directly against the dataset hosted on the Hub. You can run simple filtered search queries, or vector search/FTS queries
on an index, because a Lance dataset on the Hugging Face packages not only the data
and multimodal assets, but also the *indexes* in one place.

Lance datasets are also versioned, so you can time-travel to earlier versions of the dataset as needed.

## Schema

The `characters` table uses this Lance schema:

```text
id: int32 not null
image: binary not null
name: string not null
role: string not null
description: string not null
stats: struct<strength: int8, courage: int8, magic: int8, wisdom: int8> not null
image_path: string not null
image_vector: fixed_size_list<float>[512]
text_for_embedding: string not null
text_vector: fixed_size_list<float>[1536]
category: string
```

Before running the examples below, export a Hugging Face token:

```bash
export HF_TOKEN=hf_...
```

For text query embeddings, also export:

```bash
export OPENAI_API_KEY=...
```

For this small dataset, rate limits are usually not an issue, but using `HF_TOKEN` is still recommended.

## Common Setup

```python
import lancedb
from lancedb.embeddings import get_registry

db = lancedb.connect("hf://datasets/lancedb/magical_kingdom")
table = db.open_table("characters")

registry = get_registry()
text_embedding = registry.get("openai").create(name="text-embedding-3-small")
image_embedding = registry.get("open-clip").create(
    name="ViT-B-32",
    pretrained="laion2b_s34b_b79k",
)
```

## Q1: Strongest Knight (Filtered Search)

Run simple queries with filters followed by sorting as follows:

```python
(
    table.search()
    .where("category = 'knight'")
    .select(["name", "role", "stats.strength"])
    .limit(4)
    .to_polars()
    .sort("stats.strength", descending=True)
    .head(1)
)
```
The character belonging to the `knight` category with the greatest `stats.strength`
is Sir Lancelot!

```
┌──────────────┬───────────────────────────┬────────────────┐
│ name         ┆ role                      ┆ stats.strength │
│ ---          ┆ ---                       ┆ ---            │
│ str          ┆ str                       ┆ i8             │
╞══════════════╪═══════════════════════════╪════════════════╡
│ Sir Lancelot ┆ Knight of the Round Table ┆ 5              │
└──────────────┴───────────────────────────┴────────────────┘
```

## Q2: High-Magic Characters (Filtered Search)

The `stats` column is a nested field (i.e., a struct in PyArrow). LanceDB can directly
query the struct's values with minimum IOPS.

```python
(
    table.search()
    .where("stats.magic >= 4")
    .select(["name", "role", "stats.magic", "stats.strength"])
    .limit(2)
    .to_polars()
)
```

The two characters with the most magical power are the Merlin 🧙 and Morgan Le Fay 🧙🏼.

```
┌───────────────┬────────────────────┬─────────────┬────────────────┐
│ name          ┆ role               ┆ stats.magic ┆ stats.strength │
│ ---           ┆ ---                ┆ ---         ┆ ---            │
│ str           ┆ str                ┆ i8          ┆ i8             │
╞═══════════════╪════════════════════╪═════════════╪════════════════╡
│ Merlin        ┆ Wizard and Advisor ┆ 5           ┆ 2              │
│ Morgan le Fay ┆ Sorceress          ┆ 5           ┆ 2              │
└───────────────┴────────────────────┴─────────────┴────────────────┘
```

## Q3: Text Vector Similarity Search

You can directly query the vector index on the Hub using LanceDB without needing to download the data locally. The example below shows how to query the text emnbedding for "a brave knight with magical prowess".

```python
query = "a disloyal knight"
query_vector = embed_texts([query])[0]

(
    table.search(query_vector, vector_column_name="text_vector")
    .select(["name", "role"])
    .limit(1)
    .to_polars()
)
```

Mordred is the "treacherous knight who ultimately rebels against Arthur, leading to Camelot's downfall."

```
┌─────────┬────────────────┬───────────┐
│ name    ┆ role           ┆ _distance │
│ ---     ┆ ---            ┆ ---       │
│ str     ┆ str            ┆ f32       │
╞═════════╪════════════════╪═══════════╡
│ Mordred ┆ Traitor Knight ┆ 0.865597  │
└─────────┴────────────────┴───────────┘
```

## Q4: Image Vector Similarity Search (Text-to-Image)

The dataset also comes with pre-computed image embeddings of the characters, and the image bytest are stored in this dataset alongside the embeddings themselves.

The query below shows that we want a magical character who carries a staff and has a long beard (ruling out Morgan Le Fay, a female mage).

```python
query = "a powerful mage with a staff and a long beard"
query_vector = image_embedding.compute_query_embeddings(query)[0]

(
    table.search(query_vector, vector_column_name="image_vector")
    .select(["name", "role"])
    .limit(2)
    .to_polars()
)
```

The most similar result based on the image embedding is, indeed, Merlin!

```
┌────────────┬───────────────────────────┬───────────┐
│ name       ┆ role                      ┆ _distance │
│ ---        ┆ ---                       ┆ ---       │
│ str        ┆ str                       ┆ f32       │
╞════════════╪═══════════════════════════╪═══════════╡
│ Merlin     ┆ Wizard and Advisor        ┆ 1.432212  │
│ Sir Gawain ┆ Knight of the Round Table ┆ 1.559731  │
└────────────┴───────────────────────────┴───────────┘
```

## Q5: Full-Text Search (FTS)

Run full-text search by keywords on the dataset just as easily as you run a vector search query.

The query below shows the result when searching for the keyqword 

```python
keyword = "treacherous"

(
    table.search(keyword, query_type="fts")
    .select(["name", "role", "description"])
    .limit(5)
    .to_polars()
)
```

We get the Lady of the Lake as the result, who is a "mysterious supernatural figure associated with Avalon, known for giving Arthur the sword Excalibur."
```
┌──────────────────────┬───────────────────┬─────────────────────────────────┬─────────┐
│ name                 ┆ role              ┆ description                     ┆ _score  │
│ ---                  ┆ ---               ┆ ---                             ┆ ---     │
│ str                  ┆ str               ┆ str                             ┆ f32     │
╞══════════════════════╪═══════════════════╪═════════════════════════════════╪═════════╡
│ The Lady of the Lake ┆ Mystical Guardian ┆ A mysterious supernatural figu… ┆ 2.17613 │
└──────────────────────┴───────────────────┴─────────────────────────────────┴─────────┘
```

Use this template to distribute and share other interesting multimodal Lance datasets to the Hub, and query them using LanceDB!

## Source Code

The source code to reproduce the data and the steps to upload the datasets to the Hub are in [this repo](https://github.com/lancedb/hf-upload-demo).
