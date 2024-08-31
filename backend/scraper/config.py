"""Configuration file for the scraper module."""

import argparse
import logging

logging.basicConfig(level=logging.INFO)


class CustomArgumentParser(argparse.ArgumentParser):
    """Custom argument parser for the scraper module."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._add_arguments()

    def _add_arguments(self):
        """Add arguments to the parser."""
        self.add_argument("--headful", action="store_true", help="Run browser in headful mode.")
        self.add_argument("--verbose", action="store_true", help="Print verbose output.")
        self.add_argument(
            "--driver",
            type=str,
            default="undetected",
            help="Type of driver to use (undetected, Firefox, Chrome).",
        )
        self.add_argument("--no-proxy", action="store_false", help="Don't use a proxy.")
        self.add_argument("--collection", type=str, default=None, help="Collection of data to scrape (test, popular or all).")


# Usage
def get_args():
    """Get command line arguments."""
    parser = CustomArgumentParser()
    return parser.parse_args()
