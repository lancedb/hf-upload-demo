# Raw Data

This directory contains source artifacts used to build the LanceDB demo dataset:

- `magical_kingdom.json`: base character metadata.
- `img/`: generated 1024x1024 JPEG portraits for each character.
- `generate_images.py`: script that generates portraits with the OpenAI Images API.

## When to use this

Use these files when you want to regenerate or tweak the source dataset inputs before running `create_dataset.py` from the repository root.

## Generate images

From the repository root:

```bash
uv run python raw_data/generate_images.py
```

Requirements:

- `OPENAI_API_KEY` set in environment.
- `.env` file in the repo root (or in this directory) with required variables.

The script reads `raw_data/magical_kingdom.json` and writes JPEG files into `raw_data/img/`.
