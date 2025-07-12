#!/usr/bin/env python3
"""
GetComics.org scraper and downloader
Fixed and cleaned up version
"""

import os
import requests
from bs4 import BeautifulSoup
import argparse
import re
import json
from urllib.parse import quote
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://getcomics.org/page/{}/?s={}"
DOWNLOAD_DIR = "~/Downloads/"

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6",
    "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
    "sec-ch-ua-mobile": "?0",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}


def write_to_json(json_dict, filename):
    """Write dictionary to JSON file"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(json_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully wrote {len(json_dict)} entries to {filename}")
    except Exception as e:
        logger.error(f"Error writing to JSON file: {e}")


def sanitize_filename(filename):
    """Sanitize filename by removing/replacing invalid characters"""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove extra whitespace
    filename = re.sub(r"\s+", " ", filename).strip()
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def create_download_dir():
    """Create download directory if it doesn't exist"""
    if not os.path.exists(DOWNLOAD_DIR):
        try:
            os.makedirs(DOWNLOAD_DIR)
            logger.info(f"Created download directory: {DOWNLOAD_DIR}")
        except Exception as e:
            logger.error(f"Could not create download directory: {e}")
            return False
    return True


def download_file(link, filename):
    """Download file from given link"""
    try:
        if not create_download_dir():
            return False

        # Sanitize filename
        filename = sanitize_filename(filename)

        # Determine file extension
        if ".zip" in link.lower():
            filename += ".zip"
        else:
            filename += ".cbr"

        filepath = os.path.join(DOWNLOAD_DIR, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            logger.info(f"File already exists: {filename}")
            return True

        logger.info(f"Downloading: {filename}")

        # Download with streaming for large files
        with requests.get(
            link, headers=HEADERS, allow_redirects=True, stream=True
        ) as r:
            r.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        logger.info(f"Successfully downloaded: {filename}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading {filename}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")
        return False


def extract_download_link(page_url):
    """Extract download link from comic page"""
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        page_parsed = BeautifulSoup(response.content, "html.parser")

        # Look for download button
        download_divs = page_parsed.find_all("div", {"class": "aio-button-center"})
        if not download_divs:
            logger.warning(f"No download button found on {page_url}")
            return None

        download_button = str(download_divs[0])

        # Extract download link using regex
        link_pattern = re.compile(r"https://[a-zA-Z0-9./%\-=+:?&_]+")
        links = link_pattern.findall(download_button)

        if links:
            return links[0]
        else:
            logger.warning(f"No download link found in button on {page_url}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error accessing {page_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting download link from {page_url}: {e}")
        return None


def getcomic_downloader(page, search_term):
    """Download comics from a specific page"""
    try:
        search_url = BASE_URL.format(page, search_term)
        logger.info(f"Scraping page {page}: {search_url}")

        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        parsed_data = BeautifulSoup(response.content, "html.parser")
        posts_lists = parsed_data.find_all("article")

        if not posts_lists:
            logger.warning(f"No articles found on page {page}")
            return {}

        page_links = {}

        for post in posts_lists:
            try:
                # Extract comic page URL and title
                links = post.find_all("a")
                if len(links) < 3:
                    continue

                page_url = links[2].get("href")

                headings = post.find_all("h1")
                if not headings:
                    continue

                heading = headings[0].text.strip()

                if not page_url or not heading:
                    continue

                logger.info(f"Processing: {heading}")

                # Extract download link
                download_link = extract_download_link(page_url)

                if download_link:
                    page_links[heading] = download_link

                    # Download the file
                    if download_file(download_link, heading):
                        logger.info(f"Successfully processed: {heading}")
                    else:
                        logger.error(f"Failed to download: {heading}")
                else:
                    logger.warning(f"No download link found for: {heading}")

            except Exception as e:
                logger.error(f"Error processing post: {e}")
                continue

        return page_links

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error on page {page}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error processing page {page}: {e}")
        return {}


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="GetComics.org Downloader")
    parser.add_argument(
        "-o", "--output", help="Save links in a JSON file", action="store_true"
    )
    parser.add_argument("pages", type=int, help="Number of pages to scrape")
    parser.add_argument("search", type=str, help="Search term")

    args = parser.parse_args()

    # Validate arguments
    if args.pages <= 0:
        logger.error("Number of pages must be positive")
        return

    if not args.search.strip():
        logger.error("Search term cannot be empty")
        return

    # URL encode the search term
    encoded_search = quote(args.search)
    logger.info(f"Starting scraper for '{args.search}' across {args.pages} pages")

    all_links = {}

    # Process each page
    for page in range(1, args.pages + 1):
        logger.info(f"Processing page {page}/{args.pages}")

        page_links = getcomic_downloader(page, encoded_search)
        all_links.update(page_links)

        logger.info(f"Found {len(page_links)} comics on page {page}")

    logger.info(f"Total comics found: {len(all_links)}")

    # Save to JSON if requested
    if args.output:
        write_to_json(all_links, "links.json")

    logger.info("Scraping completed!")


if __name__ == "__main__":
    main()
