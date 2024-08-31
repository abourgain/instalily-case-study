"""Scraper to extract detailed model information from the PartSelect website."""

import csv
import json
import os
import time

from tqdm import tqdm
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


from backend.scraper.scraper import BaseScraper
from backend.scraper.config import logging, get_args

BASE_URL = "https://www.partselect.com/"


class PartsDetailsScraper(BaseScraper):
    """Class to scrape parts details on the PartSelect website."""

    def _section_exists(self, section_name):
        """Verifies if a section exists by checking the section links in the mobile view."""
        try:
            # Wait until the section links are present
            section_list = WebDriverWait(self.driver, self._get_random_wait_time()).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pd__section-links.js-PSPDP-OFF")))

            # Check if the section link exists in the section list
            section_link = section_list.find_elements(By.CSS_SELECTOR, f"a[href='#{section_name}']")

            if section_link:
                return True
            return False

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error checking section '{section_name}': {e}")
            return False

    def _get_basic_infos(self):
        """Extract basic information about the part."""
        try:
            url = self.driver.current_url
            part_id = url.split('/')[-1].split('.')[0]
            name = self.driver.find_element(By.CLASS_NAME, 'title-lg').text.strip()

            partselect_num = self.driver.find_element(By.CSS_SELECTOR, "[itemprop='productID']").text.strip()
            assert partselect_num == part_id.split('-')[0], f"PartSelect number mismatch: {partselect_num} vs {part_id.split('-')[0]}"

            manufacturer_part_num = self.driver.find_element(By.CSS_SELECTOR, "[itemprop='mpn']").text.strip()

            manufacturer = self.driver.find_element(By.CSS_SELECTOR, "[itemprop='brand'] [itemprop='name']").text.strip()
            assert manufacturer == part_id.split('-')[1], f"Manufacturer mismatch: {manufacturer} vs {part_id.split('-')[1]}"

            brand_destination = self.driver.find_element(By.CSS_SELECTOR, "[itemprop='brand']").find_element(By.XPATH, "./following-sibling::span").text.strip()
            try:
                price = self.driver.find_element(By.CLASS_NAME, 'js-partPrice').text.strip()
                status = self.driver.find_element(By.CLASS_NAME, 'js-partAvailability').text.strip()
            except selenium.common.exceptions.NoSuchElementException:
                price = "No longer available"
                status = "No longer available"

            details = {
                "url": url,
                "id": part_id,
                "name": name,
                "partselect_num": partselect_num,
                "manufacturer_part_num": manufacturer_part_num,
                "manufacturer": manufacturer,
                "brand_destination": brand_destination,
                "price": price,
                "status": status,
            }

            try:
                difficulty = self.driver.find_element(By.XPATH, "//div[contains(@class, 'pd__repair-rating')]//p[contains(., 'Difficult') or contains(., 'Easy')]").text.strip()
                time_required = self.driver.find_element(By.XPATH, "//div[contains(@class, 'pd__repair-rating')]//p[contains(., 'mins')]").text.strip()
            except selenium.common.exceptions.NoSuchElementException:
                difficulty = None
                time_required = None

            if difficulty and time_required:
                details["installation_difficulty"] = difficulty
                details["installation_time"] = time_required

            return details

        except selenium.common.exceptions.NoSuchElementException as e:
            logging.debug(f"Error extracting basic info: {e}")
            return {}

    def _get_description(self):
        """Extracts the product description from the part details page."""
        if not self._section_exists("ProductDescription"):
            return None

        try:
            # Wait until the description section is present
            return self.driver.find_element(By.CSS_SELECTOR, "div[itemprop='description']").text.strip()

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting product description: {e}")
            return None

    def _get_video_links(self):
        """Extracts video details across multiple pages, stopping when the correct number of videos is reached."""
        if not self._section_exists("PartVideos"):
            return []

        videos = []
        try:
            part_videos_section = self.driver.find_element(By.ID, "PartVideos")

            # Locate the div immediately following the PartVideos section
            video_container = part_videos_section.find_element(By.XPATH, "following-sibling::div[1]")
            video_elements = video_container.find_elements(By.CLASS_NAME, "yt-video")

            for video_element in video_elements:
                # Extract the YouTube video ID and construct the full link
                yt_video_id = video_element.get_attribute('data-yt-init')
                youtube_link = f"https://www.youtube.com/watch?v={yt_video_id}"
                video_title = video_element.find_element(By.XPATH, ".//img").get_attribute("alt").strip()

                videos.append({"youtube_link": youtube_link, "video_title": video_title})

            return videos

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting video details: {e}")
            return videos

    def _get_troubleshooting(self):
        """Extracts troubleshooting details from the part details page."""
        if not self._section_exists("Troubleshooting"):
            return {}

        try:
            # Locate the Troubleshooting section directly by its ID
            troubleshooting_title_section = self.driver.find_element(By.ID, "Troubleshooting")
            troubleshooting_section = troubleshooting_title_section.find_element(By.XPATH, "following-sibling::div[1]")

            # Initialize variables to store the extracted data
            symptoms_fixed = ""
            works_with_products = ""
            parts_replaced_list = []

            # Iterate over each relevant div with class 'col-md-6 mt-3'
            elements = troubleshooting_section.find_elements(By.XPATH, ".//div[@class='col-md-6 mt-3']")
            for element in elements:
                # Check the content of the element to determine what it contains
                text_content = element.text.strip()
                if "This part fixes the following symptoms:" in text_content:
                    symptoms_fixed = text_content.split("This part fixes the following symptoms:")[1].strip()
                elif "This part works with the following products:" in text_content:
                    works_with_products = text_content.split("This part works with the following products:")[1].replace(".", "").strip()
                elif "Part# " in text_content:
                    # Click on "Show more" if it exists to reveal hidden parts
                    try:
                        show_more_button = element.find_element(By.XPATH, ".//span[@data-collapse-trigger='show-more']")
                        show_more_button.click()
                    except selenium.common.exceptions.NoSuchElementException:
                        pass  # "Show more" button not found, so no need to click it

                    # Print the entire text content of the parent div after revealing the hidden parts
                    parent_div = element.find_element(By.XPATH, ".//div[@data-collapse-container]").text.strip()
                    parts_replaced_list = parent_div.split('\n')[0].split(', ')

            # Clean the list of parts
            parts_replaced_list = [part.strip() for part in parts_replaced_list]

            return {
                "symptoms_fixed": symptoms_fixed,
                "works_with_products": works_with_products,
                "replaces_manufacturer_part_nums": parts_replaced_list,
            }

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting troubleshooting info: {e}")
            return {}

    def _get_all_repair_stories(self):
        """Extracts all repair stories from multiple pages, navigating through pagination until 'Next' is disabled."""
        if not self._section_exists("RepairStories"):
            return []

        repair_stories = []

        # Locate the section using data-event-source="Repair Story"
        repair_stories_section = self.driver.find_element(By.CSS_SELECTOR, "div[data-event-source='Repair Story']")
        n_stories = int(repair_stories_section.get_attribute("data-total-items"))

        while True:
            repair_stories.extend(self._extract_repair_stories_from_page())

            # Check if the "Next" button is enabled
            next_button_li = repair_stories_section.find_element(By.CSS_SELECTOR, ".pagination .next")

            if "disabled" in next_button_li.get_attribute("class"):
                break

            # Click the "Next" button to go to the next page
            next_button = next_button_li.find_element(By.TAG_NAME, "span")
            next_button.click()
            time.sleep(self._get_random_wait_time())

        assert len(repair_stories) == n_stories, f"Number of stories mismatch: {len(repair_stories)} vs {n_stories}"

        return list(repair_stories)

    def _extract_repair_stories_from_page(self):
        """Extracts repair stories from the current page."""
        stories = []
        try:
            repair_stories_section = self.driver.find_element(By.CSS_SELECTOR, "div[data-event-source='Repair Story']")
            story_elements = repair_stories_section.find_elements(By.CLASS_NAME, "repair-story")

            for story_element in story_elements:
                story_title = story_element.find_element(By.CLASS_NAME, "repair-story__title").text.strip()
                story_content = story_element.find_element(By.CLASS_NAME, "repair-story__instruction").text.strip()

                # Extract additional details like difficulty level, repair time, and tools
                details_list = story_element.find_elements(By.CLASS_NAME, "repair-story__details li")
                difficulty_level = ""
                total_repair_time = ""
                tools = ""

                for detail_item in details_list:
                    detail_text = detail_item.text.strip()

                    if "Difficulty Level:" in detail_text:
                        difficulty_level = detail_text.split("Difficulty Level:")[1].strip()
                    elif "Total Repair Time:" in detail_text:
                        total_repair_time = detail_text.split("Total Repair Time:")[1].strip()
                    elif "Tools:" in detail_text:
                        tools = detail_text.split("Tools:")[1].strip()

                stories.append(
                    {
                        "title": story_title,
                        "content": story_content,
                        "difficulty": difficulty_level,
                        "repair_time": total_repair_time,
                        "tools": tools,
                    }
                )

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting repair stories from page: {e}")

        return stories

    def _get_all_qnas(self):
        """Extracts all questions and answers from multiple pages, navigating through pagination until 'Next' is disabled."""
        if not self._section_exists("QuestionsAndAnswers"):
            return []

        all_qnas = []

        # Locate the section using data-event-source="Part Detail Q&A"
        qnas_section = self.driver.find_element(By.CSS_SELECTOR, "div[data-handler='QuestionsAndAnswers']")
        n_qnas = int(qnas_section.get_attribute("data-total-items"))
        if n_qnas == 0:
            return []

        while True:
            # Extract Q&As from the current page
            all_qnas.extend(self._extract_qnas_from_page())

            # Check if the "Next" button is enabled
            next_button_li = qnas_section.find_element(By.CSS_SELECTOR, ".pagination .next")

            if "disabled" in next_button_li.get_attribute("class"):
                break

            # Click the "Next" button to go to the next page
            next_button = next_button_li.find_element(By.TAG_NAME, "span")
            next_button.click()
            time.sleep(self._get_random_wait_time())

        assert len(all_qnas) == n_qnas, f"Number of Q&As mismatch: {len(all_qnas)} vs {n_qnas}"

        return all_qnas

    def _extract_qnas_from_page(self):
        """
        Extracts Q&As from the current page.
        """
        qnas = []
        try:
            qnas_section = self.driver.find_element(By.CSS_SELECTOR, "div[data-handler='QuestionsAndAnswers']")
            qna_elements = qnas_section.find_elements(By.CLASS_NAME, "qna__question")  # Locate all individual Q&A entries
            for qna_element in qna_elements:
                question = qna_element.find_element(By.CLASS_NAME, "js-searchKeys").text.strip()
                try:
                    model = qna_element.find_element(By.CSS_SELECTOR, ".bold.mt-3.mb-3").text.strip().split("number ")[1]
                except selenium.common.exceptions.NoSuchElementException:
                    model = "Not specified"
                answer = qna_element.find_element(By.CLASS_NAME, "qna__ps-answer__msg").text.strip()
                date = qna_element.find_element(By.CLASS_NAME, "qna__question__date").text.strip()

                qna = {
                    "question": question,
                    "model": model,
                    "answer": answer,
                    "date": date,
                }

                related_parts = []
                try:
                    related_parts_section = qna_element.find_elements(By.CLASS_NAME, "qna__question__related")
                    for part in related_parts_section:
                        part_name = part.find_element(By.CLASS_NAME, "d-block.bold.mb-2").text.strip()
                        part_url = part.find_element(By.TAG_NAME, "a").get_attribute("href").split('?')[0]
                        part_id = part_url.split('/')[-1].split('.')[0]
                        try:
                            part_price = part.find_element(By.CSS_SELECTOR, ".text-teal.price.bold").text.strip()
                            part_status = part.find_element(By.CLASS_NAME, "d-inline-flex.bold.mt-1.js-tooltip").text.strip()
                        except selenium.common.exceptions.NoSuchElementException:
                            part_price = "No longer available"
                            part_status = "No longer available"
                        related_parts.append(
                            {
                                "part_name": part_name,
                                "part_id": part_id,
                                "part_url": part_url,
                                "part_price": part_price,
                                "part_status": part_status,
                            }
                        )
                except selenium.common.exceptions.NoSuchElementException:
                    related_parts = "No related parts specified"

                if related_parts:
                    qna["related_parts"] = related_parts

                # Add all extracted information to the list
                qnas.append(qna)

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting Q&As from page: {e}")

        return qnas

    def _get_all_related_parts(self):
        """Extracts all related parts from the current page."""
        if not self._section_exists("RelatedParts"):
            return []

        related_parts = []

        try:
            related_parts_container = self.driver.find_element(By.CLASS_NAME, "pd__related-parts-wrap")
            part_elements = related_parts_container.find_elements(By.CLASS_NAME, "pd__related-part")

            for part_element in part_elements:
                link_tag = part_element.find_element(By.CSS_SELECTOR, "a.bold")
                part_name = link_tag.text.strip()
                part_link = link_tag.get_attribute("href").split('?')[0]
                part_id = part_link.split('/')[-1].split('.')[0]

                try:
                    price = part_element.find_element(By.CLASS_NAME, "price").text.strip()
                    status = part_element.find_element(By.CLASS_NAME, "js-tooltip").text.strip()
                except selenium.common.exceptions.NoSuchElementException:
                    price = "No longer available"
                    status = "No longer available"

                related_parts.append(
                    {
                        "name": part_name,
                        "id": part_id,
                        "link": part_link,
                        "price": price,
                        "status": status,
                    }
                )

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting related parts: {e}")

        return related_parts

    def _get_all_compatible_models(self):
        """
        Extracts all models that the part works with, including the brand, model number, and description.
        """
        if not self._section_exists("ModelCrossReference"):
            return []

        compatible_models = []

        try:
            models_container = self.driver.find_element(By.CSS_SELECTOR, "div[data-handler='ModelCrossReference']")
            models_list = models_container.find_element(By.CLASS_NAME, "pd__crossref__list")
            model_elements = models_list.find_elements(By.CLASS_NAME, "row")

            for model_element in model_elements:
                brand = model_element.find_element(By.CSS_SELECTOR, "div.col-md-3").text.strip()
                model_link_element = model_element.find_element(By.CSS_SELECTOR, "a.col-lg-2")
                model_number = model_link_element.text.strip()
                model_link = model_link_element.get_attribute("href")
                description = model_element.find_element(By.CSS_SELECTOR, "div.col-lg-7").text.strip()

                compatible_models.append(
                    {
                        "brand": brand,
                        "model_num": model_number,
                        "model_link": model_link,
                        "description": description,
                    }
                )

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            logging.debug(f"Error extracting compatible models: {e}")

        return compatible_models

    def scrape_part_details(self, url: str):
        """Scrape model details."""
        self.driver = self._setup_driver()
        self.driver.get(url)
        time.sleep(self._get_random_wait_time())

        return {
            **self._get_basic_infos(),
            "description": self._get_description(),
            "videos": self._get_video_links(),
            "troubleshooting": self._get_troubleshooting(),
            "repair_stories": self._get_all_repair_stories(),
            "qnas": self._get_all_qnas(),
            "related_parts": self._get_all_related_parts(),
            "compatible_models": self._get_all_compatible_models(),
        }

    def _load_already_scraped_parts(self, collection: str = None) -> list:
        """Load the URLs of parts that have already been scraped."""
        folder_path = f"./backend/scraper/data/parts.{collection}" if collection else "./backend/scraper/data/parts"
        already_scraped_parts = []
        for file in os.listdir(folder_path):
            if file.endswith(".json"):
                already_scraped_parts.append(f"{BASE_URL}{file.split('.')[0]}.htm")
        return already_scraped_parts

    def _load_parts(self, collection: str = None) -> list:
        """Load the URLs of parts to scrape."""
        already_scraped_parts = self._load_already_scraped_parts(collection)
        file_path = f"./backend/scraper/data/parts.{collection}.csv" if collection else "./backend/scraper/data/parts.csv"

        parts = set()  # Use a set to automatically handle duplicates
        with open(file_path, mode='r', encoding="utf-8") as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if row and row[0].strip() not in already_scraped_parts:
                    parts.add(row[0].strip())  # Add each URL to the set after stripping any extra whitespace
        logging.info(f"Loaded {len(parts)} parts URLs from {file_path}")
        return list(parts)  # Convert the set back to a list and return

    def _save_part_details(self, part_details: dict, collection: str = None) -> None:
        """Save the part details to a JSON file."""
        folder_path = f"./backend/scraper/data/parts.{collection}" if collection else "./backend/scraper/data/parts"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = f"{folder_path}/{part_details['id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(part_details, f, indent=4)

    def scrape_all_parts_details(
        self,
        save_local: bool = True,
        collection: str = None,
    ):
        """Scrape all model details."""
        parts_urls = self._load_parts(collection)

        for url in tqdm(parts_urls, desc="Scraping parts details"):
            part_details = self.scrape_part_details(url)

            # Save part details to the database
            if save_local:
                self._save_part_details(part_details, collection)


def main():
    """Run the scraper."""
    args = get_args()

    scraper = PartsDetailsScraper(
        headful=args.headful,
        verbose=args.verbose,
        driver_type=args.driver,
        use_proxy=args.no_proxy,
    )
    scraper.scrape_all_parts_details(collection=args.collection)


if __name__ == "__main__":
    main()
