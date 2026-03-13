# codex-find-first-name

An app to help parents discover first names for their child.

## Planned architecture

The project follows separation of concerns with three layers:

1. **Data**: adapters for web scraping, APIs, and storage.
2. **Orchestration**: use-cases that coordinate business workflows.
3. **Representation**: CLI / API / UI entry points.

Current focus: downloading first-name lists from [beliebte-vornamen.de](https://www.beliebte-vornamen.de/lexikon/).

## Categorization fields

Each scraped first-name record currently includes:

- `gender` (`female`, `male`, `unknown`)
- `country` (`germany`, `unknown`)
- `source` (`popular-first-names-de`, `unknown`)

The source site distinguishes between girl and boy index pages, for example:

- `https://www.beliebte-vornamen.de/lexikon/a-frau`
- `https://www.beliebte-vornamen.de/lexikon/a-mann`

The scraper uses these URLs to infer gender.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Download first names

```bash
name-finder download --max-pages 15 --output data/first_names.json
```

This command crawls index pages, extracts likely first names, enriches them with categories, deduplicates names per gender, and writes JSON output.

## Run tests

```bash
pytest
```
