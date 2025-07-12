#!/usr/bin/env python3
"""
Interactive GetComics.org scraper and downloader
Allows user to choose which comics to download
"""

import os
import requests
from bs4 import BeautifulSoup
import argparse
import re
import json
from urllib.parse import quote
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://getcomics.org/page/{}/?s={}"
DOWNLOAD_DIR = None  # Will be set based on user choice

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


class Comic:
    """Represents a comic with its metadata"""

    def __init__(self, title: str, page_url: str, download_link: str = None):
        self.title = title
        self.page_url = page_url
        self.download_link = download_link
        self.downloaded = False

    def __str__(self):
        status = "✓" if self.downloaded else "○"
        return f"[{status}] {self.title}"


def write_to_json(comics_dict: Dict[str, str], filename: str) -> None:
    """Write dictionary to JSON file"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(comics_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully wrote {len(comics_dict)} entries to {filename}")
    except Exception as e:
        logger.error(f"Error writing to JSON file: {e}")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters"""
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def create_download_dir(download_path: str = None) -> bool:
    """Create download directory if it doesn't exist"""
    if download_path is None:
        download_path = DOWNLOAD_DIR

    if not os.path.exists(download_path):
        try:
            os.makedirs(download_path)
            logger.info(f"Created download directory: {download_path}")
        except Exception as e:
            logger.error(f"Could not create download directory: {e}")
            return False
    return True


def get_download_directory() -> str:
    """Get download directory from user choice"""
    while True:
        print("\n" + "=" * 60)
        print("DOWNLOAD LOCATION")
        print("=" * 60)
        print("1. Current directory (where you run the script)")
        print("2. Custom directory")
        print("=" * 60)

        choice = input("Choose download location (1-2): ").strip()

        if choice == "1":
            cwd = os.getcwd()
            comics_dir = os.path.join(cwd, "Comics")
            print(f"📁 Will download to: {comics_dir}")
            return comics_dir

        elif choice == "2":
            custom_dir = input("Enter custom directory path: ").strip()
            if custom_dir:
                # Expand user home directory if needed
                custom_dir = os.path.expanduser(custom_dir)
                print(f"📁 Will download to: {custom_dir}")
                return custom_dir
            else:
                print("❌ Invalid directory path")

        else:
            print("❌ Invalid choice. Please enter 1 or 2")


def download_file(link: str, filename: str, download_dir: str = None) -> bool:
    """Download file from given link"""


def download_file(link: str, filename: str, download_dir: str = None) -> bool:
    """Download file from given link"""
    try:
        if download_dir is None:
            download_dir = DOWNLOAD_DIR

        if not create_download_dir(download_dir):
            return False

        filename = sanitize_filename(filename)

        if ".zip" in link.lower():
            filename += ".zip"
        else:
            filename += ".cbr"

        filepath = os.path.join(download_dir, filename)

        if os.path.exists(filepath):
            logger.info(f"File already exists: {filename}")
            return True

        logger.info(f"Downloading: {filename}")

        with requests.get(
            link, headers=HEADERS, allow_redirects=True, stream=True
        ) as r:
            r.raise_for_status()

            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Show progress for large files
                    if total_size > 1024 * 1024:  # > 1MB
                        progress = (downloaded / total_size) * 100
                        print(f"\rProgress: {progress:.1f}%", end="", flush=True)

            if total_size > 1024 * 1024:
                print()  # New line after progress

        logger.info(f"Successfully downloaded: {filename}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading {filename}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")
        return False


def extract_download_link(page_url: str) -> Optional[str]:
    """Extract download link from comic page"""
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        page_parsed = BeautifulSoup(response.content, "html.parser")

        download_divs = page_parsed.find_all("div", {"class": "aio-button-center"})
        if not download_divs:
            logger.warning(f"No download button found on {page_url}")
            return None

        download_button = str(download_divs[0])

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


def search_comics(search_term: str, max_results: int = 20) -> List[Comic]:
    """Search for comics and return list of Comic objects, stopping at max_results"""
    all_comics = []
    encoded_search = quote(search_term)
    page = 1

    while len(all_comics) < max_results:
        try:
            search_url = BASE_URL.format(page, encoded_search)
            logger.info(f"Searching page {page}: {search_url}")

            response = requests.get(search_url, headers=HEADERS, timeout=10)
            response.raise_for_status()

            parsed_data = BeautifulSoup(response.content, "html.parser")
            posts_lists = parsed_data.find_all("article")

            if not posts_lists:
                logger.warning(f"No articles found on page {page}")
                break  # No more results

            page_comics = []
            for post in posts_lists:
                try:
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

                    comic = Comic(heading, page_url)
                    page_comics.append(comic)

                except Exception as e:
                    logger.error(f"Error processing post: {e}")
                    continue

            if not page_comics:
                logger.warning(f"No valid comics found on page {page}")
                break  # No more valid results

            all_comics.extend(page_comics)

            # If we have enough results, trim to max_results
            if len(all_comics) >= max_results:
                all_comics = all_comics[:max_results]
                break

            page += 1

            # Safety check to prevent infinite loops
            if page > 10:  # Don't search beyond 10 pages
                logger.warning("Reached maximum page limit (10)")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error on page {page}: {e}")
            break
        except Exception as e:
            logger.error(f"Error processing page {page}: {e}")
            break

    return all_comics


def display_comics(comics: List[Comic]) -> None:
    """Display list of comics with numbers"""
    print("\n" + "=" * 80)
    print("AVAILABLE COMICS")
    print("=" * 80)

    for i, comic in enumerate(comics, 1):
        print(f"{i:3d}. {comic}")

    print("=" * 80)
    print(f"Total: {len(comics)} comics found")


def get_user_selection(comics: List[Comic]) -> List[int]:
    """Get user selection of which comics to download"""
    while True:
        print("\nSelect comics to download:")
        print("Examples:")
        print("  - Single: 1")
        print("  - Multiple: 1,3,5")
        print("  - Range: 1-5")
        print("  - Mixed: 1,3,7-10,15")
        print("  - All: all")
        print("  - Quit: q")

        selection = input("\nEnter your choice: ").strip().lower()

        if selection == "q":
            return []

        if selection == "all":
            return list(range(len(comics)))

        try:
            selected_indices = []
            parts = selection.split(",")

            for part in parts:
                part = part.strip()
                if "-" in part:
                    # Handle range
                    start, end = part.split("-")
                    start_idx = int(start) - 1
                    end_idx = int(end) - 1

                    if 0 <= start_idx < len(comics) and 0 <= end_idx < len(comics):
                        selected_indices.extend(range(start_idx, end_idx + 1))
                    else:
                        print(f"Invalid range: {part}")
                        continue
                else:
                    # Handle single number
                    idx = int(part) - 1
                    if 0 <= idx < len(comics):
                        selected_indices.append(idx)
                    else:
                        print(f"Invalid number: {part}")
                        continue

            # Remove duplicates and sort
            selected_indices = sorted(list(set(selected_indices)))

            if selected_indices:
                print(f"\nSelected {len(selected_indices)} comics:")
                for idx in selected_indices:
                    print(f"  - {comics[idx].title}")

                confirm = input("\nConfirm download? (y/n): ").strip().lower()
                if confirm == "y":
                    return selected_indices
            else:
                print("No valid selections made.")

        except ValueError:
            print("Invalid input format. Please try again.")


def download_selected_comics(
    comics: List[Comic], selected_indices: List[int], download_dir: str
) -> None:
    """Download selected comics"""
    print(f"\nStarting download of {len(selected_indices)} comics...")
    print(f"📁 Download location: {download_dir}")

    downloaded_links = {}

    for i, idx in enumerate(selected_indices, 1):
        comic = comics[idx]
        print(f"\n[{i}/{len(selected_indices)}] Processing: {comic.title}")

        # Get download link if not already available
        if not comic.download_link:
            comic.download_link = extract_download_link(comic.page_url)

        if comic.download_link:
            downloaded_links[comic.title] = comic.download_link

            if download_file(comic.download_link, comic.title, download_dir):
                comic.downloaded = True
                print(f"✓ Successfully downloaded: {comic.title}")
            else:
                print(f"✗ Failed to download: {comic.title}")
        else:
            print(f"✗ Could not find download link for: {comic.title}")

    # Save download links to JSON in the same directory
    if downloaded_links:
        json_path = os.path.join(download_dir, "downloaded_comics.json")
        write_to_json(downloaded_links, json_path)

    # Summary
    successful = sum(1 for idx in selected_indices if comics[idx].downloaded)
    print(f"\n" + "=" * 50)
    print(f"DOWNLOAD SUMMARY")
    print(f"=" * 50)
    print(f"Total attempted: {len(selected_indices)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(selected_indices) - successful}")
    print(f"Location: {download_dir}")
    print(f"=" * 50)


def main():
    """Main interactive function"""
    parser = argparse.ArgumentParser(description="Interactive GetComics.org Downloader")
    parser.add_argument("search", type=str, help="Search term")
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum number of results to show (default: 20)",
    )
    parser.add_argument(
        "--auto-save", action="store_true", help="Auto-save search results to JSON"
    )
    parser.add_argument(
        "--cwd", action="store_true", help="Download to current working directory"
    )
    parser.add_argument("--download-dir", type=str, help="Custom download directory")

    args = parser.parse_args()

    # Validate arguments
    if not args.search.strip():
        logger.error("Search term cannot be empty")
        return

    if args.max_results <= 0:
        logger.error("Max results must be positive")
        return

    # Determine download directory
    global DOWNLOAD_DIR
    if args.download_dir:
        DOWNLOAD_DIR = os.path.expanduser(args.download_dir)
        print(f"📁 Using custom download directory: {DOWNLOAD_DIR}")
    elif args.cwd:
        DOWNLOAD_DIR = os.path.join(os.getcwd(), "Comics")
        print(f"📁 Using current working directory: {DOWNLOAD_DIR}")
    else:
        DOWNLOAD_DIR = get_download_directory()

    print(
        f"🔍 Searching for '{args.search}' (showing top {args.max_results} results)..."
    )

    # Search for comics
    comics = search_comics(args.search, args.max_results)

    if not comics:
        print("No comics found. Try a different search term.")
        return

    print(f"✅ Found {len(comics)} comics")

    # Auto-save search results if requested
    if args.auto_save:
        search_results = {comic.title: comic.page_url for comic in comics}
        json_filename = f"search_results_{args.search.replace(' ', '_')}.json"
        json_path = os.path.join(DOWNLOAD_DIR, json_filename)
        write_to_json(search_results, json_path)

    # Interactive selection loop
    while True:
        display_comics(comics)
        selected_indices = get_user_selection(comics)

        if not selected_indices:
            print("👋 Goodbye!")
            break

        download_selected_comics(comics, selected_indices, DOWNLOAD_DIR)

        # Ask if user wants to continue
        continue_choice = (
            input("\nWould you like to download more comics? (y/n): ").strip().lower()
        )
        if continue_choice != "y":
            print("👋 Goodbye!")
            break


if __name__ == "__main__":
    main()
