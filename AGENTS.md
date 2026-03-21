# Agent Guidelines

## Project structure
- Application code lives under `src/name_finder/`
- Data fixtures sit in `data/`
- Tests live in `tests/`

## Entry points
- Scraper: `python -m name_finder.scrape_beliebte_names`
- Game: `python -m name_finder.name_duel_game [options]`

## Test workflow
- Run the suite with `pytest` (configured for `src` layout)
- Use fixtures for scraper parsing tests; no live HTTP calls

## Rules
- Keep changes localized and readable
- Preserve JSON schemas unless a change is requested
- Add deterministic tests for new behaviors

## Current features
- Alphabetical scraper with completeness checks
- CLI duel game supporting simple and Elo scoring
- Guided filtering & optional persistence of filtered lists
- Ranking persistence + autosave/resume
- Undo of the last duel decision

## Dependencies

- Use real external libraries (e.g. requests, beautifulsoup4)
- Do not create local replacements for external libraries (e.g. requests, bs4)
- All dependencies must be installed via pip and declared in requirements.txt
- If a dependency is missing, update requirements.txt

## Project structure

- Code lives in src/name_finder/
- Do not introduce new top-level packages without explicit instruction