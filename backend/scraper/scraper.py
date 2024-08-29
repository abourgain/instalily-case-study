"""
File to scrape the PartSelect website for models of appliances.
"""

import argparse
from io import StringIO
import json
import time
import random
import logging

import pandas as pd
import requests
from tqdm import tqdm
import yaml
from selenium import webdriver
import selenium
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc


# Constants
HEADERS_FILE = "./backend/scraper/headers.yml"
USER_AGENTS_FILE = "./backend/scraper/user_agents.yml"
BASE_URL = "https://www.partselect.com/"
FREE_PROXY_URL = "https://free-proxy-list.net"
CATEGORIES = ["Dishwasher", "Refrigerator"]

logging.basicConfig(level=logging.INFO)


class BaseScraper:
    """Base class for scraping."""

    def __init__(
        self,
        headful: bool = False,
        verbose: bool = False,
        driver_type: str = "undetected",
    ):
        self.headless = not headful
        self.verbose = verbose
        self.driver_type = driver_type
        self.browser_headers = self._load_browser_headers()
        self.user_agents = self._load_user_agents()
        self._get_good_proxies()
        self.driver = None

    @staticmethod
    def _load_browser_headers():
        """Load headers from the headers.yml file."""
        with open(HEADERS_FILE, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    @staticmethod
    def _load_user_agents():
        """Load user-agents from the user_agents.yml file."""
        with open(USER_AGENTS_FILE, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def _get_good_proxies(self):
        """Get a list of good proxies from https://free-proxy-list.net."""
        if self.verbose:
            logging.info("Getting good proxies...")
        try:
            response = requests.get(FREE_PROXY_URL, timeout=5)
            proxy_list = pd.read_html(StringIO(response.text))[0]
            proxy_list["url"] = "http://" + proxy_list["IP Address"] + ":" + proxy_list["Port"].astype(str)
            https_proxies = proxy_list[proxy_list["Https"] == "yes"]
            url = "https://httpbin.org/ip"
            # Test if self.good_proxies exists
            if not hasattr(self, "good_proxies"):
                self.good_proxies = set()
            headers = self.browser_headers["Chrome"]
            for proxy_url in https_proxies["url"]:
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url,
                }

                try:
                    response = requests.get(url, headers=headers, proxies=proxies, timeout=2)
                    self.good_proxies.add(proxy_url)
                    if self.verbose:
                        logging.info("Proxy %s OK, added to good_proxy list", proxy_url)
                except (TimeoutException, requests.exceptions.RequestException):
                    pass

            # Add a variable to save the time
            self.proxies_time = time.time()

        except (TimeoutException, requests.exceptions.RequestException) as e:
            logging.error("Error getting proxies: %s", e)

    def _get_random_header(self, browser_type):
        """Get a random header and user-agent for the specified browser type."""
        header = self.browser_headers[browser_type]
        user_agent = random.choice(self.user_agents[browser_type])
        header["User-Agent"] = user_agent
        return header

    def _get_random_wait_time(self):
        """Get a random wait time between 0.01 and 1 second."""
        return random.uniform(0.001, 0.1) if self.headless else 0.5

    def _setup_driver(self):
        """Set up the browser driver."""
        # First quit the previous driver if it exists
        if self.driver:
            self.driver.quit()

        browser_type = "Chrome" if self.driver_type == "undetected" else self.driver_type.capitalize()
        header = self._get_random_header(browser_type)

        # Reload the proxies if the time is more than 10 minutes
        if time.time() - self.proxies_time > 600:
            self._get_good_proxies()

        proxy_url = random.choice(list(self.good_proxies))
        proxy = proxy_url.replace("http://", "")

        if self.driver_type == "Firefox":
            options = webdriver.FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            profile = webdriver.FirefoxProfile()
            for key, value in header.items():
                profile.set_preference("general.useragent.override", header["User-Agent"])
                profile.set_preference(f"{key}", value)
            options.profile = profile
            options.add_argument(f"--proxy-server={proxy}")
            return webdriver.Firefox(options=options)

        if self.driver_type == "Chrome":
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            for key, value in header.items():
                options.add_argument(f"{key}={value}")
            options.add_argument(f"--proxy-server={proxy}")
            return webdriver.Chrome(options=options)

        if self.driver_type == "undetected":
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=True")
            for key, value in header.items():
                options.add_argument(f"{key}={value}")
            options.add_argument(f"--proxy-server={proxy}")
            return uc.Chrome(options=options)

        raise ValueError("Invalid driver type")

    def __del__(self):
        """Clean up the driver when the scraper is deleted."""
        if self.driver:
            self.driver.quit()


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
    parser = argparse.ArgumentParser(description="Scrape ...")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode.")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output.")
    parser.add_argument(
        "--driver",
        type=str,
        default="undetected",
        help="Type of driver to use (undetected, Firefox, Chrome).",
    )
    args = parser.parse_args()

    scraper = ModelsScraper(headful=args.headful, verbose=args.verbose, driver_type=args.driver)
    scraper.scrape_models()


if __name__ == "__main__":
    main()
