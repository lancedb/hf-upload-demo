# LanceDB Hugging Face Update Demo

This project demonstrates a simple staged workflow for to manage your Lance datasets on [Hugging Face Hub](https://huggingface.co/datasets/lancedb/magical_kingdom).

To create a repo like this, first create and upload an initial table using LanceDB on a local machine, and then upload it to the Hub via a CLI command.

As the dataset evolves, you can apply a one-time schema + data update, and upload the updated version of the data back to the Hub. Only the new data is uploaded, keeping things clean.

## Setup

Use `uv`, and export both `OPENAI_API_KEY` and `HF_TOKEN`.

```bash
uv sync
export OPENAI_API_KEY=...
export HF_TOKEN=hf_...
hf auth login --token "$HF_TOKEN"
```

The scripts look for a local file named `.env`, so to run any of them, you'll need to copy the `.env.example` to a new file named `.env` and update the respective env variables there.

## Step 1: Create the initial Lance table

Start clean, then build the Lance table locally.
This creates the `characters` table, computes embeddings in batches, and creates an FTS index.

```bash
rm -rf magical_kingdom
uv run python create_dataset.py
```

## Step 2: Upload the Initial Snapshot to the Hub

Upload the full `magical_kingdom` directory to `datasets/lancedb/magical_kingdom`.

```bash
hf upload lancedb/magical_kingdom magical_kingdom . \
  --repo-type dataset \
  --commit-message "Initial table (no category)"
```

## Step 3: Update the dataset locally

Imagine a scenario where you want to add a new `category` column and backfill its values with a single `merge_insert` operation into your existing table.

This is **both as schema update and a data update**, which Lance excels at: because Lance supports incremental data evolution, it can add, remove and alter columns _without rewriting any data files_ in the existing dataset, making them very efficient operations on large tables.

```bash
uv run python update_dataset.py
```

Over time, you can run a [compaction](https://docs.lancedb.com/lance#data-compaction) job that calls `table.optimize()` to manage the number of manifests that are recorded in the history.

## Step 4: Upload the updated version to the Hub

Upload the same local directory again (now a new version of the dataset) with a new commit message.

```bash
hf upload lancedb/magical_kingdom magical_kingdom . \
  --repo-type dataset \
  --commit-message "Add category column and backfill values"
```

## Step 5: Inspect versions and query on the Hub

`inspect_dataset.py` reads from `hf://datasets/lancedb/magical_kingdom` and prints table versions.
`query.py` also reads from the Hub and runs all five example queries.

```bash
uv run python inspect_dataset.py
uv run python query.py
```

If you run `update_dataset.py` again without resetting, it will fail at `add_columns` because `category` already exists.
That is expected for this one-time demo flow.

## Update the Dataset Card

The Hub dataset card is the repo’s root `README.md`.
This project keeps the source card text in `HF_DATASET_CARD.md`, so publish updates there and upload it as `README.md` as required:

```bash
hf upload lancedb/magical_kingdom HF_DATASET_CARD.md README.md \
  --repo-type dataset \
  --commit-message "Update dataset card"
```

## Optional: Reset the Hub Repo

If you want to replay the full demo from scratch on the Hub:

```bash
hf repos delete lancedb/magical_kingdom --repo-type dataset
hf repos create lancedb/magical_kingdom --repo-type dataset
```
