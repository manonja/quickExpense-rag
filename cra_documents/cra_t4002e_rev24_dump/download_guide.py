#!/usr/bin/env python3
"""
CRA T4002 Guide Downloader
Downloads and processes the T4002 Self-employed Business guide from canada.ca
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002/"
OUTPUT_DIR = Path(__file__).parent
ASSETS_DIR = OUTPUT_DIR / "assets"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Expected pages
EXPECTED_PAGES = [
    "t4002-1.html",
    "t4002-2.html",
    "t4002-3.html",
    "t4002-4.html",
    "t4002-5.html",
    "t4002-6.html",
    "t4002-8.html",  # Note: t4002-7.html does not exist
    "t4002-9.html",
    "t4002-10.html",
    "t4002-11.html",
    "t4002-12.html",
    "t4002-14.html",  # Note: t4002-13.html does not exist
    "t4002-15.html",
]


def setup_session() -> requests.Session:
    """Create a configured requests session with proper headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })
    return session


def download_with_retry(session: requests.Session, url: str, max_retries: int = MAX_RETRIES) -> str:
    """Download content with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Attempt {attempt}/{max_retries}: {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()

            if response.status_code == 200:
                print(f"  ✓ Success: {len(response.content)} bytes")
                return response.text
            else:
                print(f"  ✗ HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"  ✗ Error: {e}")

        if attempt < max_retries:
            print(f"  Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    raise Exception(f"Failed to download {url} after {max_retries} attempts")


def task_1_1_download_initial_page(session: requests.Session) -> bool:
    """
    Task 1.1: Environment Setup & Initial Page Download
    """
    print("\n=== Task 1.1: Environment Setup & Initial Page Download ===")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory: {OUTPUT_DIR}")

    # Download t4002-1.html
    url = urljoin(BASE_URL, "t4002-1.html")
    print(f"\nDownloading: {url}")

    try:
        content = download_with_retry(session, url)

        # Save to file
        output_file = OUTPUT_DIR / "t4002-1.html"
        output_file.write_text(content, encoding="utf-8")
        print(f"✓ Saved to: {output_file}")

        # Validation
        print("\nValidation:")
        file_size = output_file.stat().st_size
        print(f"  File size: {file_size} bytes")

        if file_size == 0:
            print("  ✗ FAIL: File is empty")
            return False
        print("  ✓ File size > 0")

        # Check for expected content
        if "table of contents" in content.lower():
            print("  ✓ Contains 'table of contents'")
        else:
            print("  ✗ FAIL: Expected content not found")
            return False

        print("\n✓ Task 1.1 PASSED")
        return True

    except Exception as e:
        print(f"\n✗ Task 1.1 FAILED: {e}")
        return False


def task_1_2_discover_urls(session: requests.Session) -> List[str]:
    """
    Task 1.2: URL Discovery & Page Count Verification
    """
    print("\n=== Task 1.2: URL Discovery & Page Count Verification ===")

    # Read the downloaded TOC page
    toc_file = OUTPUT_DIR / "t4002-1.html"
    if not toc_file.exists():
        print("✗ FAIL: t4002-1.html not found. Run Task 1.1 first.")
        return []

    content = toc_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Find all links
    discovered_urls = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Check if it's a t4002 page link
        if "t4002-" in href and ".html" in href:
            # Extract just the filename
            if "#" in href:
                href = href.split("#")[0]  # Remove anchor

            # Handle different URL formats
            if href.startswith("http"):
                # Full URL
                discovered_urls.add(href)
            elif href.startswith("/"):
                # Absolute path
                discovered_urls.add(f"https://www.canada.ca{href}")
            else:
                # Relative path
                discovered_urls.add(urljoin(BASE_URL, href))

    # Convert to sorted list
    urls = sorted(list(discovered_urls))

    print(f"\nDiscovered {len(urls)} URLs:")
    for i, url in enumerate(urls, 1):
        filename = url.split("/")[-1]
        print(f"  {i}. {filename}")

    # Validation
    print("\nValidation:")
    if len(urls) == 13:
        print(f"  ✓ Found exactly 13 pages")
    else:
        print(f"  ✗ FAIL: Expected 13 pages, found {len(urls)}")
        return []

    # Check against expected pages
    discovered_filenames = {url.split("/")[-1] for url in urls}
    expected_set = set(EXPECTED_PAGES)

    if discovered_filenames == expected_set:
        print("  ✓ All expected pages found")
    else:
        missing = expected_set - discovered_filenames
        extra = discovered_filenames - expected_set
        if missing:
            print(f"  ✗ Missing pages: {missing}")
        if extra:
            print(f"  ✗ Unexpected pages: {extra}")
        return []

    print("\n✓ Task 1.2 PASSED")
    return urls


def main():
    """Main execution."""
    print("CRA T4002 Guide Downloader")
    print("=" * 60)

    session = setup_session()

    # Task 1.1: Download initial page
    if not task_1_1_download_initial_page(session):
        print("\n✗ FATAL: Task 1.1 failed. Stopping.")
        sys.exit(1)

    # Task 1.2: Discover URLs
    urls = task_1_2_discover_urls(session)
    if not urls:
        print("\n✗ FATAL: Task 1.2 failed. Stopping.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Phase 1 Complete!")
    print("Next: Run Task 1.3 (structure analysis with gemini)")
    print("=" * 60)


if __name__ == "__main__":
    main()
