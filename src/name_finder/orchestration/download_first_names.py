from dataclasses import dataclass

from name_finder.data.scrapers.popular_names_de import PopularNamesDEScraper
from name_finder.domain.models import FirstName


@dataclass(slots=True)
class DownloadFirstNamesUseCase:
    scraper: PopularNamesDEScraper

    def run(self, max_pages: int = 15) -> list[FirstName]:
        return self.scraper.download_names(max_pages=max_pages)
