"""Scraper to extract detailed model information from the PartSelect website."""

import argparse
import json
import time

from selenium import webdriver
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
import undetected_chromedriver as uc

from backend.scraper.scraper import BaseScraper
from backend.scraper.config import logging


class ModelsDetailsScraper(BaseScraper):
    """Class to scrape detailed model information on the PartSelect website."""

    def __init__(
        self,
        headful: bool = False,
        verbose: bool = False,
        driver_type: str = "Chrome",
        use_proxy: bool = True,
        url: str = None,
    ):
        super().__init__(headful, verbose, driver_type, use_proxy)
        self.url = url

    def _section_exists(self, section_name):
        """
        Verifies if a section exists by checking the navigation summary.
        """
        try:
            # Wait until the navigation summary is present
            nav_section = WebDriverWait(self.driver, self._get_random_wait_time()).until(EC.presence_of_element_located((By.CLASS_NAME, "mega-m__nav")))

            # Check if the section link exists in the navigation summary
            section_link = nav_section.find_elements(By.CSS_SELECTOR, f"a[data-page-name='{section_name}']")

            if section_link:
                return True
            return False

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error checking section '{section_name}': {e}")
            return False

    def _get_name(self):
        return self.driver.find_element(By.ID, 'main').get_attribute('data-description')

    def _get_brand(self):
        return self.driver.find_element(By.ID, 'main').get_attribute('data-brand')

    def _get_model_num(self):
        return self.driver.find_element(By.ID, 'main').get_attribute('data-model-num')

    def _get_model_type(self):
        return self.driver.find_element(By.ID, 'main').get_attribute('data-modeltype')

    def _get_sections_pdf_links(self):
        """Get the number of sections schema, verify count, and get name and link of each schema."""
        if not self._section_exists("Sections"):
            return []

        try:
            # Get the section count from the section title
            section_count_element = self.driver.find_element(By.CLASS_NAME, 'section-title__count')
            section_count_text = section_count_element.text
            total_section_count = int(section_count_text.split(' ')[-1][:-1])  # Extract number from "[Viewing 6 of 6]"

            # Get all section schema elements
            section_elements = self.driver.find_elements(By.CSS_SELECTOR, '.row.mb-3 .col-6')

            # Verify the number of schema matches the displayed count
            if len(section_elements) != total_section_count:
                logging.error("Mismatch in section count: Found %d, but expected %d", len(section_elements), total_section_count)
                return []

            sections = []
            # Loop through each section to extract the name and link
            for section in section_elements:
                link_element = section.find_element(By.TAG_NAME, 'a')
                section_name = link_element.find_element(By.TAG_NAME, 'span').text.strip()
                section_link = link_element.get_attribute('href')
                sections.append({'name': section_name, 'link': section_link})

            return sections

        except selenium.common.exceptions.NoSuchElementException as e:
            logging.error("Error finding section schema elements: %s", e)
            return []
        except (TimeoutException, ValueError) as e:
            logging.error("Error processing section schemas: %s", e)
            return []

    def _get_manuals_links(self):
        """Get all names and links to each manual in the Manuals & Care Guides section."""
        if not self._section_exists("Manuals"):
            return []

        try:
            # Find all manual links within the section
            manual_links = self.driver.find_elements(By.CSS_SELECTOR, '.d-flex.flex-wrap.mt-2.mb-4 a.mega-m__manuals')

            manuals = []
            for manual in manual_links:
                manual_name = manual.find_element(By.CLASS_NAME, 'mega-m__manuals__title').text.strip()
                manual_url = manual.get_attribute('href')
                manuals.append({'name': manual_name, 'link': manual_url})

            return manuals

        except selenium.common.exceptions.NoSuchElementException as e:
            logging.error("Error finding manual section elements: %s", e)
            return []
        except (TimeoutException, ValueError) as e:
            logging.error("Error processing manuals: %s", e)
            return []

    def _get_parts(self, url: str):
        """Extracts part details across multiple pages."""
        # Check if the Parts section exists
        if not self._section_exists("Parts"):
            return []

        parts_url = f"{url}/Parts"
        self.driver.get(parts_url)
        time.sleep(self._get_random_wait_time())

        try:
            # Get the total number of parts from the summary text
            summary_text = self.driver.find_element(By.CLASS_NAME, 'summary').text
            range_text, _, total_parts = summary_text.partition(' of ')
            total_parts = int(total_parts)  # Total number of parts
            start, _, end = range_text.partition(' - ')
            parts_per_page = int(end) - int(start) + 1  # Calculate parts per page dynamically

            total_pages = (total_parts + parts_per_page - 1) // parts_per_page  # Calculate total pages needed

            part_details = []

            for page_num in range(1, total_pages + 1):
                # Navigate to the specific page
                paginated_url = f"{parts_url}/?start={page_num}"
                self.driver.get(paginated_url)
                time.sleep(self._get_random_wait_time())

                # Locate all part elements on the current page
                part_elements = self.driver.find_elements(By.CLASS_NAME, 'mega-m__part')

                for part_element in part_elements:
                    try:
                        part_name = part_element.find_element(By.CLASS_NAME, 'mega-m__part__name').text.strip()
                        part_link = part_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        part_id = part_link.split('/')[-1].split('-')[0]
                        try:
                            part_price = part_element.find_element(By.CLASS_NAME, 'mega-m__part__price').text.strip()
                            part_status = part_element.find_element(By.CLASS_NAME, 'js-tooltip').text.strip()
                        except selenium.common.exceptions.NoSuchElementException:
                            part_price = "No longer available"
                            part_status = "No longer available"

                        part_details.append(
                            {
                                'name': part_name,
                                'id': part_id,
                                'link': part_link,
                                'price': part_price,
                                'status': part_status,
                            }
                        )
                    except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
                        print(f"Error extracting part details: {e}")

                # Break the loop if all parts are collected
                if len(part_details) >= total_parts:
                    break

            # Verify that the number of extracted parts matches the total number of parts
            assert len(part_details) == total_parts, f"Expected {total_parts} parts, but extracted {len(part_details)}."

            # Return on the model page
            self.driver.get(url)
            time.sleep(self._get_random_wait_time())

            return part_details

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting part details: {e}")
            return []

    def _extract_qna_details(self):
        """Extracts all Q&A details across multiple pages, stopping when the correct number of Q&As is reached."""
        if not self._section_exists("Questions & Answers"):
            return []

        try:
            # Get the number of questions reported by the page
            qna_section = self.driver.find_element(By.ID, 'QuestionsAndAnswersContent')
            total_items = int(qna_section.get_attribute('data-total-items'))
            extracted_qnas = []

            while len(extracted_qnas) < total_items:
                # Find all questions on the current page
                question_elements = qna_section.find_elements(By.CLASS_NAME, 'qna__question')

                for question_element in question_elements:
                    # Extract question details
                    question_date = question_element.find_element(By.CLASS_NAME, 'qna__question__date').text.strip()
                    question_text = question_element.find_element(By.CLASS_NAME, 'js-searchKeys').text.strip()
                    answer_text = question_element.find_element(By.CLASS_NAME, 'qna__ps-answer__msg').text.strip()

                    # Extract related parts details
                    related_parts = []
                    related_parts_elements = question_element.find_elements(By.CLASS_NAME, 'qna__question__related')
                    for part_element in related_parts_elements:
                        part_name = part_element.find_element(By.CLASS_NAME, 'bold').text.strip()
                        part_link = part_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        part_id = part_link.split('/')[-1].split('-')[0]
                        part_price = part_element.find_element(By.CLASS_NAME, 'price').text.strip()
                        part_status = part_element.find_element(By.CLASS_NAME, 'js-tooltip').text.strip()
                        related_parts.append(
                            {
                                'name': part_name,
                                'id': part_id,
                                'link': part_link,
                                'price': part_price,
                                'status': part_status,
                            }
                        )

                    # Add the extracted details to the list
                    extracted_qnas.append({'date': question_date, 'question': question_text, 'answer': answer_text, 'related_parts': related_parts})

                    # Stop if the required number of Q&As have been extracted
                    if len(extracted_qnas) >= total_items:
                        break

                # If more Q&As are needed, check if there is a "Next" button and click it to go to the next page
                if len(extracted_qnas) < total_items:
                    next_button = qna_section.find_elements(By.CSS_SELECTOR, '.pagination .next span')
                    if next_button and "Next" in next_button[0].text:
                        next_button[0].click()
                        time.sleep(2)  # Wait for the next page to load
                        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, 'QuestionsAndAnswersContent')))
                        qna_section = self.driver.find_element(By.ID, 'QuestionsAndAnswersContent')
                    else:
                        break

            # Verify the number of extracted Q&As matches the total reported
            assert len(extracted_qnas) == total_items, f"Expected {total_items} Q&As, but extracted {len(extracted_qnas)}"

            return extracted_qnas

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting Q&A details: {e}")
            return []

    def _get_common_symptoms(self):
        # Check if the Symptoms section exists
        if not self._section_exists("Symptoms"):
            return []

        symptoms_details = []

        try:
            # Get the total number of symptoms reported by the page
            symptoms_section = self.driver.find_element(By.ID, 'Symptoms')
            total_symptoms_text = symptoms_section.find_element(By.CLASS_NAME, 'section-title__count').text
            total_symptoms = int(total_symptoms_text.split(' of ')[1].strip(']'))

            # Extract all symptom elements on the main page
            symptom_elements = self.driver.find_elements(By.CLASS_NAME, 'symptoms')
            symptoms = []

            for symptom_element in symptom_elements:
                symptom_name = symptom_element.find_element(By.CLASS_NAME, 'symptoms__descr').text.strip()
                symptom_url = symptom_element.get_attribute('href')
                symptoms.append((symptom_name, symptom_url))

            for symptom_name, symptom_link in symptoms:
                # Navigate to the specific symptom page
                self.driver.get(symptom_link)
                time.sleep(self._get_random_wait_time())

                # Extract the details from the symptom page
                symptom_details = self._extract_symptom_details(symptom_name)

                # Store the details for the symptom
                symptoms_details.append(symptom_details)

            # Verify that the number of extracted symptoms matches the total number of symptoms
            assert len(symptoms_details) == total_symptoms, f"Expected {total_symptoms} symptoms, but extracted {len(symptoms_details)}."
            return symptoms_details

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting symptom details: {e}")
            return symptoms_details

    def _extract_part_details_type1(self, part_element):
        """Extracts part details for Type 1 (Detailed symptom page)."""
        part_name = part_element.find_element(By.CLASS_NAME, 'header').find_element(By.TAG_NAME, 'a').text.strip()
        part_link = part_element.find_element(By.CLASS_NAME, 'header').find_element(By.TAG_NAME, 'a').get_attribute('href')
        part_id = part_link.split('/')[-1].split('-')[0]
        fix_percent = part_element.find_element(By.CLASS_NAME, 'symptoms__percent').text.strip()
        try:
            part_price = part_element.find_element(By.CLASS_NAME, 'price').text.strip()
            part_status = part_element.find_element(By.CLASS_NAME, 'js-partAvailability').text.strip()
        except selenium.common.exceptions.NoSuchElementException:
            part_price = "No longer available"
            part_status = "No longer available"

        part_details = {
            'name': part_name,
            'id': part_id,
            'link': part_link,
            'price': part_price,
            'fix_percent': fix_percent,
            'status': part_status,
        }

        customer_stories = self._extract_customer_stories(part_element)
        if customer_stories:
            part_details['customer_stories'] = customer_stories

        return part_details

    def _extract_part_details_type2(self, part_element):
        """Extracts part details for Type 2 (Simple symptom page)."""
        if 'd-none' in part_element.get_attribute('class'):
            self.driver.execute_script("arguments[0].classList.remove('d-none');", part_element)

        part_name = part_element.find_element(By.CLASS_NAME, 'bold').text.strip()
        part_link = part_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
        part_id = part_link.split('/')[-1].split('-')[0]
        fix_percent = part_element.find_element(By.CLASS_NAME, 'symptoms__percent').text.strip()
        try:
            part_price = part_element.find_element(By.CLASS_NAME, 'mega-m__part__price').text.strip()
            part_status = part_element.find_element(By.CLASS_NAME, 'js-tooltip').text.strip()
        except selenium.common.exceptions.NoSuchElementException:
            part_price = "No longer available"
            part_status = "No longer available"

        return {
            'name': part_name,
            'id': part_id,
            'link': part_link,
            'price': part_price,
            'fix_percent': fix_percent,
            'status': part_status,
        }

    def _extract_customer_stories(self, part_element):
        """Extracts customer stories if available."""
        customer_stories = []
        story_elements = part_element.find_elements(By.CLASS_NAME, 'repair-story')
        for story_element in story_elements:
            story_title = story_element.find_element(By.CLASS_NAME, 'repair-story__title').text.strip()
            story_content = story_element.find_element(By.CLASS_NAME, 'repair-story__instruction__content').text.strip()
            difficulty, repair_time, tools = self._extract_story_details(story_element)

            customer_stories.append({'title': story_title, 'content': story_content, 'difficulty': difficulty, 'repair_time': repair_time, 'tools': tools})
        return customer_stories

    def _extract_story_details(self, story_element):
        """Extracts additional details like difficulty, repair time, and tools from a customer story."""
        difficulty = ""
        repair_time = ""
        tools = ""

        details_list = story_element.find_elements(By.CSS_SELECTOR, '.repair-story__details li')
        for detail_item in details_list:
            detail_text = detail_item.text.strip()
            if "Difficulty Level:" in detail_text:
                difficulty = detail_text.split("Difficulty Level:")[1].strip()
            elif "Total Repair Time:" in detail_text:
                repair_time = detail_text.split("Total Repair Time:")[1].strip()
            elif "Tools:" in detail_text:
                tools = detail_text.split("Tools:")[1].strip()

        return difficulty, repair_time, tools

    def _extract_symptom_details(self, symptom_name):
        """Extracts the details of a specific symptom from its page."""
        parts_details = []

        try:
            part_elements = self.driver.find_elements(By.CLASS_NAME, 'symptoms')

            for part_element in part_elements:
                if part_element.find_elements(By.CLASS_NAME, 'header'):
                    # Type 1: Detailed symptom
                    part_details = self._extract_part_details_type1(part_element)
                else:
                    # Type 2: Simple symptom
                    part_details = self._extract_part_details_type2(part_element)

                parts_details.append(part_details)

            return {
                'symptom_name': symptom_name,
                'fixing_parts': parts_details,
            }

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting parts for symptom '{symptom_name}': {e}")
            return {'symptom_name': symptom_name, 'fixing_parts': []}

    def _get_video_links(self, url: str):
        """Extracts video details across multiple pages, stopping when the correct number of videos is reached."""
        # Check if the Videos section exists
        if not self._section_exists("Videos"):
            return []

        videos_url = f"{url}/Videos"
        self.driver.get(videos_url)
        time.sleep(self._get_random_wait_time())

        try:
            # Get the total number of videos from the summary text
            summary_text = self.driver.find_element(By.CLASS_NAME, 'summary').text
            range_text, _, total_videos = summary_text.partition(' of ')
            total_videos = int(total_videos)  # Total number of videos
            start, _, end = range_text.partition(' - ')
            videos_per_page = int(end) - int(start) + 1  # Calculate videos per page dynamically

            total_pages = (total_videos + videos_per_page - 1) // videos_per_page  # Calculate total pages needed

            video_details = []

            for page_num in range(1, total_pages + 1):
                # Navigate to the specific page
                paginated_url = f"{videos_url}/?start={page_num}"
                self.driver.get(paginated_url)
                time.sleep(self._get_random_wait_time())

                # Locate all video elements on the current page
                video_elements = self.driver.find_elements(By.CLASS_NAME, 'yt-video')

                for video_element in video_elements:
                    # Extract YouTube video link
                    yt_video_id = video_element.get_attribute('data-yt-init')
                    youtube_link = f"https://www.youtube.com/watch?v={yt_video_id}"

                    # Extract video title
                    video_title = video_element.find_element(By.XPATH, "../div[@class='mb-3 video__title']").text.strip()

                    # Extract associated parts
                    part_elements = video_element.find_elements(By.XPATH, "../div[@class='mega-m__part mb-5']")
                    parts = []

                    for part_element in part_elements:
                        part_name = part_element.find_element(By.CLASS_NAME, 'mega-m__part__name').text.strip()
                        part_link = part_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                        part_id = part_link.split('/')[-1].split('-')[0]
                        part_price = part_element.find_element(By.CLASS_NAME, 'mega-m__part__price').text.strip()
                        part_status = part_element.find_element(By.CLASS_NAME, 'js-tooltip').text.strip()

                        parts.append(
                            {
                                'name': part_name,
                                'id': part_id,
                                'link': part_link,
                                'price': part_price,
                                'status': part_status,
                            }
                        )

                    # Store the details for the video
                    video_details.append({'youtube_link': youtube_link, 'video_title': video_title, 'parts': parts})

                    # Stop if the required number of videos have been extracted
                    if len(video_details) >= total_videos:
                        break

            # Verify that the number of extracted videos matches the total number of videos
            assert len(video_details) == total_videos, f"Expected {total_videos} videos, but extracted {len(video_details)}."

            # Return on the model page
            self.driver.get(url)
            time.sleep(self._get_random_wait_time())

            return video_details

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting video details: {e}")
            return []

    def _get_installation_instructions(self, url: str):
        """Extracts repair instructions across multiple pages, stopping when the correct number of instructions is reached."""
        # Check if the Instructions section exists
        if not self._section_exists("Instructions"):
            return []

        instructions_url = f"{url}/Instructions"
        self.driver.get(instructions_url)
        time.sleep(self._get_random_wait_time())

        try:
            # Get the total number of instructions from the summary text
            summary_text = self.driver.find_element(By.CLASS_NAME, 'summary').text
            range_text, _, total_instructions = summary_text.partition(' of ')
            total_instructions = int(total_instructions)  # Total number of instructions
            start, _, end = range_text.partition(' - ')
            instructions_per_page = int(end) - int(start) + 1  # Calculate instructions per page dynamically

            total_pages = (total_instructions + instructions_per_page - 1) // instructions_per_page  # Calculate total pages needed

            instruction_details = []

            for page_num in range(1, total_pages + 1):
                # Navigate to the specific page
                paginated_url = f"{instructions_url}/?start={page_num}"
                self.driver.get(paginated_url)
                time.sleep(self._get_random_wait_time())

                # Locate all instruction elements on the current page
                instruction_elements = self.driver.find_elements(By.CLASS_NAME, 'repair-story')

                if not instruction_elements:
                    total_extracted = n_elements_page + (page_num - 2) * instructions_per_page
                    assert total_extracted == len(instruction_details), f"Expected {total_extracted} instructions, but extracted {len(instruction_details)}"
                    break

                n_elements_page = len(instruction_elements)

                for instruction_element in instruction_elements:
                    # Extract instruction title
                    instruction_title = instruction_element.find_element(By.CLASS_NAME, 'repair-story__title').text.strip()

                    # Extract instruction content
                    instruction_content = instruction_element.find_element(By.CLASS_NAME, 'repair-story__instruction__content').text.strip()

                    # Extract parts used in the repair
                    parts = []
                    parts_elements = instruction_element.find_elements(By.CLASS_NAME, 'repair-story__parts a')
                    for part_element in parts_elements:
                        part_name = part_element.find_element(By.TAG_NAME, 'span').text.strip()
                        part_link = part_element.get_attribute('href')
                        part_id = part_link.split('/')[-1].split('-')[0]

                        parts.append(
                            {
                                'name': part_name,
                                'id': part_id,
                                'link': part_link,
                            }
                        )

                    # Extract difficulty level, repair time, and tools (if available) using <li> tags
                    details_list = instruction_element.find_elements(By.CSS_SELECTOR, '.repair-story__details li')
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

                    # Store the details for the instruction
                    instruction_details.append(
                        {
                            'title': instruction_title,
                            'content': instruction_content,
                            'parts_used': parts,
                            'difficulty_level': difficulty_level,
                            'total_repair_time': total_repair_time,
                            'tools': tools,
                        }
                    )

            # Return on the model page
            self.driver.get(url)
            time.sleep(self._get_random_wait_time())

            return instruction_details

        except (selenium.common.exceptions.NoSuchElementException, TimeoutException) as e:
            print(f"Error extracting instruction details: {e}")
            return []

    def scrape_model_details(self, url: str):
        """Scrape model details."""
        self.driver = self._setup_driver()
        self.driver.get(url)
        time.sleep(self._get_random_wait_time())

        return {
            "url": url,
            "name": self._get_name(),
            "brand": self._get_brand(),
            "model_num": self._get_model_num(),
            "model_type": self._get_model_type(),
            "sections": self._get_sections_pdf_links(),
            "manuals": self._get_manuals_links(),
            "parts": self._get_parts(url),
            "qnas": self._extract_qna_details(),
            "videos": self._get_video_links(url),
            "installation_instructions": self._get_installation_instructions(url),
            "common_symptoms": self._get_common_symptoms(),
        }

    def _load_models(self, test: bool = False):
        file_path = "./backend/scraper/data/models.test.json" if test else "./backend/scraper/data/models.json"
        # Load models from the database
        with open(file_path, encoding="utf-8") as f:
            models = json.load(f)
        return models

    def _save_model_details(self, model_details: dict):
        with open(f"./backend/scraper/data/models/{model_details['model_num']}.json", "w", encoding="utf-8") as f:
            json.dump(model_details, f, indent=4)

    def scrape_all_models_details(
        self,
        save_local: bool = True,
        test: bool = False,
    ):
        """Scrape all model details."""
        models = self._load_models(test)

        for category, model_list in models.items():
            if self.verbose:
                logging.info(f"Scraping {category} models")

            for model in tqdm(model_list, desc=f"Scraping {category} models"):
                model_details = self.scrape_model_details(model["url"])

                # Save model details to the database
                if save_local:
                    self._save_model_details(model_details)

            break  # Remove this line to scrape all categories


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
    parser.add_argument("--no-proxy", action="store_false", help="Don't use a proxy.")
    parser.add_argument("--test", action="store_true", help="Run in test mode.")
    args = parser.parse_args()

    url = "https://www.partselect.com/Models/004621710A/"  # Replace with the actual URL
    scraper = ModelsDetailsScraper(
        headful=args.headful,
        verbose=args.verbose,
        driver_type=args.driver,
        use_proxy=args.no_proxy,
        url=url,
    )
    scraper.scrape_all_models_details(test=args.test)


if __name__ == "__main__":
    main()
