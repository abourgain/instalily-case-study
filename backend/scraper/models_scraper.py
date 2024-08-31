"""Scraper to extract models from the PartSelect website."""

import json
import time

from tqdm import tqdm
import selenium
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from backend.scraper.config import logging, get_args
from backend.scraper.scraper import BaseScraper


# Constants
BASE_URL = "https://www.partselect.com/"
CATEGORIES = ["Dishwasher", "Refrigerator"]


class ModelsScraper(BaseScraper):
    """Class to scrape models on the PartSelect website."""

    def get_number_of_models(self):
        """Extract the total number of models from the summary element."""
        try:
            summary = self.driver.find_element(By.CLASS_NAME, "summary")
            total_models_text = summary.text.split()[-1]
            total_models = int(total_models_text.replace(',', ''))  # Convert to integer after removing commas
            return total_models
        except selenium.common.exceptions.NoSuchElementException:
            logging.error("No summary found: cannot determine the number of models.")
            return 0
        except (TimeoutException, ValueError) as e:
            if self.verbose:
                logging.error("Error finding number of models: %s", e)
            return 0  # Default to 0 models if there's an error
        except selenium.common.exceptions.StaleElementReferenceException as e:
            if self.verbose:
                logging.error("Exception raised: %s", e)
            return 0  # Default to 0 models if there's an error

    def get_number_of_models_and_pages(self, models_per_page=100):
        """Calculate the number of pages based on the total number of models."""
        n_models = self.get_number_of_models()
        n_pages = 0 if n_models == 0 else (n_models + models_per_page - 1) // models_per_page
        return n_pages, n_models

    def scrape_models_on_page(self):
        """Extract all models listed on the current page."""
        try:
            models = []
            ul_element = self.driver.find_element(By.CLASS_NAME, "nf__links")
            li_elements = ul_element.find_elements(By.TAG_NAME, "li")

            for li in li_elements:
                a_tag = li.find_element(By.TAG_NAME, "a")
                model_name = a_tag.get_attribute("title")
                model_url = a_tag.get_attribute("href")
                model_description = a_tag.text
                models.append(
                    {
                        "name": model_name,
                        "url": model_url,
                        "description": model_description,
                    }
                )

            return models
        except selenium.common.exceptions.NoSuchElementException:
            logging.error("No models found on the page.")
            return []
        except (TimeoutException, ValueError) as e:
            if self.verbose:
                logging.error("Error scraping models on page: %s", e)
            return []

    def scrape_all_models(self, n_pages: int, base_url: str = "https://www.partselect.com/Dishwasher-Models.htm", save_local=True):
        """Scrape all models across multiple pages."""
        try:
            self.driver = self._setup_driver()
            self.driver.get(base_url)
            time.sleep(self._get_random_wait_time())  # Allow page to load

            all_models = []

            # tqdm progress bar
            for i in tqdm(range(n_pages), desc="Scraping models"):
                url = f"{base_url}?start={i+1}"
                self.driver.get(url)
                time.sleep(self._get_random_wait_time())  # Allow page to load

                all_models.extend(self.scrape_models_on_page())

            if save_local:
                # Save the scraped data to a JSON file
                category = base_url.split("/")[-1].split("-")[0]
                file_path = f"./backend/scraper/data/{category}_models.json"
                if self.verbose:
                    logging.info("Saving scraped data to JSON file %s...", file_path)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(all_models, f, indent=2)

            return all_models
        except (TimeoutException, ValueError) as e:
            if self.verbose:
                logging.error("Error scraping all models: %s", e)
            return []

    def scrape_models(
        self,
        save_local: bool = True,
    ):
        """Scrape the PartSelect site for models."""
        if self.verbose:
            logging.info("\nScraping %s models...", BASE_URL)

        models_data = {}

        for category in CATEGORIES:
            self.driver = self._setup_driver()
            url = f"{BASE_URL}/{category}-Models.htm"
            if self.verbose:
                logging.info("\nScraping category: %s at URL: %s", category, url)
            self.driver.get(url)
            time.sleep(self._get_random_wait_time())  # Allow page to load

            n_pages, n_models = self.get_number_of_models_and_pages()
            if self.verbose:
                logging.info("> For category %s, found %d models across %d pages", category, n_models, n_pages)

            all_models = self.scrape_all_models(base_url=url, n_pages=n_pages, save_local=True)

            models_data[category] = all_models

        if save_local:
            file_path = "./backend/scraper/data/models.json"
            if self.verbose:
                logging.info("Saving scraped data to JSON file %s...", file_path)
            # Save the scraped data to a JSON file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(models_data, f, indent=2)


def main():
    """Run the scraper."""
    args = get_args()

    scraper = ModelsScraper(headful=args.headful, verbose=args.verbose, driver_type=args.driver, use_proxy=args.no_proxy)
    scraper.scrape_models()


if __name__ == "__main__":
    main()
