"""
File to create the BaseScraper class.
"""

from io import StringIO
import time
import random

import pandas as pd
import requests
import yaml
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

from backend.scraper.config import logging


# Constants
HEADERS_FILE = "./backend/scraper/headers.yml"
USER_AGENTS_FILE = "./backend/scraper/user_agents.yml"
FREE_PROXY_URL = "https://free-proxy-list.net"


class BaseScraper:
    """Base class for scraping."""

    def __init__(
        self,
        headful: bool = False,
        verbose: bool = False,
        driver_type: str = "undetected",
        use_proxy: bool = True,
    ):
        self.headless = not headful
        self.verbose = verbose
        self.driver_type = driver_type
        self.use_proxy = use_proxy

        self.browser_headers = self._load_browser_headers()
        self.user_agents = self._load_user_agents()
        if self.use_proxy:
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
        return random.uniform(0.001, 0.01) if self.headless else 0.5

    def _setup_driver(self):
        """Set up the browser driver."""
        # First quit the previous driver if it exists
        if self.driver:
            self.driver.quit()

        browser_type = "Chrome" if self.driver_type == "undetected" else self.driver_type.capitalize()
        header = self._get_random_header(browser_type)

        if self.use_proxy:
            # Reload the proxies if the time is more than 10 minutes
            if time.time() - self.proxies_time > 600:
                self._get_good_proxies()

            proxy_url = random.choice(list(self.good_proxies))
            proxy = proxy_url.replace("http://", "")

        options = None
        match self.driver_type:
            case "Firefox":
                options = webdriver.FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                profile = webdriver.FirefoxProfile()
                for key, value in header.items():
                    profile.set_preference("general.useragent.override", header["User-Agent"])
                    profile.set_preference(f"{key}", value)
                options.profile = profile
                if self.use_proxy:
                    options.add_argument(f"--proxy-server={proxy}")
                return webdriver.Firefox(options=options)

            case "Chrome":
                options = webdriver.ChromeOptions()
                if self.headless:
                    options.add_argument("--headless")
                for key, value in header.items():
                    options.add_argument(f"{key}={value}")
                if self.use_proxy:
                    options.add_argument(f"--proxy-server={proxy}")
                return webdriver.Chrome(options=options)

            case "undetected":
                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=True")
                for key, value in header.items():
                    options.add_argument(f"{key}={value}")
                if self.use_proxy:
                    options.add_argument(f"--proxy-server={proxy}")
                return uc.Chrome(options=options)

            case _:
                raise ValueError("Invalid driver type")

    def __del__(self):
        """Clean up the driver when the scraper is deleted."""
        if self.driver:
            self.driver.quit()
