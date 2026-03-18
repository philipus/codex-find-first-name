# codex-find-first-name

A CLI tool to help you find and rank first names for your baby using pairwise comparisons and Elo-style scoring.

## Overview

This project helps you discover and rank baby names by comparing them in a simple “duel” format.
Instead of browsing long lists, you repeatedly choose between two names, and the system builds a ranking based on your preferences.

## Features

* Scrape name lists from beliebte-vornamen.de
* Guided filtering to reduce large name sets
* Pairwise comparison game
* Simple scoring or Elo-based ranking
* Undo last decision
* Save and resume ranking sessions
* Autosave support

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### 1. Scrape names

```bash
python -m name_finder.scrape_beliebte_names
```

### 2. Start the game

```bash
python -m name_finder.name_duel_game \
  --data data/all_names.json \
  --gender male \
  --mode elo
```

### 3. Resume a session

```bash
python -m name_finder.name_duel_game \
  --state data/my_session.json
```

## Controls

During the game:

* `1` → choose first name
* `2` → choose second name
* `s` → skip
* `u` → undo last decision
* `q` → quit

## Project Structure

```text
src/name_finder/
  scrape_beliebte_names.py
  name_duel_game.py
tests/
data/
```

## Roadmap

* Result analysis (top N names)
* Pronunciation-based filtering
* Surname compatibility scoring

## License

MIT (or your license)
