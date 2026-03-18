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
