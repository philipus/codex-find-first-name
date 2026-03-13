from __future__ import annotations

import argparse
import json
from pathlib import Path

from name_finder.data.scrapers.popular_names_de import PopularNamesDEScraper
from name_finder.orchestration.download_first_names import DownloadFirstNamesUseCase


def main() -> None:
    parser = argparse.ArgumentParser(description="Find and rank first names")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download first names from web")
    download.add_argument("--max-pages", type=int, default=15)
    download.add_argument("--output", type=Path, default=Path("data/first_names.json"))

    args = parser.parse_args()

    if args.command == "download":
        scraper = PopularNamesDEScraper()
        use_case = DownloadFirstNamesUseCase(scraper=scraper)
        names = use_case.run(max_pages=args.max_pages)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = [{"name": item.value, "source_url": item.source_url, "gender": item.gender.value, "country": item.country.value, "source": item.source.value} for item in names]
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(payload)} names to {args.output}")


if __name__ == "__main__":
    main()
