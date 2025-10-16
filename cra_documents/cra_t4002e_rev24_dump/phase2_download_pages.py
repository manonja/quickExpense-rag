#!/usr/bin/env python3
"""
Phase 2: Download all 13 T4002 pages individually with per-page verification
Each page is downloaded and validated before proceeding to the next
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002/"
OUTPUT_DIR = Path(__file__).parent
ASSETS_DIR = OUTPUT_DIR / "assets"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
MAX_RETRIES = 3
RETRY_DELAY = 5

# All 13 pages in order
PAGES = [
    {"file": "t4002-1.html", "name": "Table of Contents", "min_size": 1024},
    {"file": "t4002-2.html", "name": "What's new / Definitions", "min_size": 1024},
    {"file": "t4002-3.html", "name": "Chapter 1: General", "min_size": 1024},
    {"file": "t4002-4.html", "name": "Chapter 2: Income", "min_size": 1024},
    {"file": "t4002-5.html", "name": "Chapter 3: Expenses", "min_size": 1024},
    {"file": "t4002-6.html", "name": "Chapter 4: CCA", "min_size": 1024},
    {"file": "t4002-8.html", "name": "Chapter 5: Losses", "min_size": 1024},
    {"file": "t4002-9.html", "name": "Chapter 6: Capital gains", "min_size": 1024},
    {"file": "t4002-10.html", "name": "CCA rates", "min_size": 1024},
    {"file": "t4002-11.html", "name": "Inventory", "min_size": 1024},
    {"file": "t4002-12.html", "name": "GST/HST", "min_size": 1024},
    {"file": "t4002-14.html", "name": "Digital services", "min_size": 1024},
    {"file": "t4002-15.html", "name": "More information", "min_size": 1024},
]


def setup_session() -> requests.Session:
    """Create configured session."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def download_with_retry(session: requests.Session, url: str) -> str:
    """Download with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"    Attempt {attempt}/{MAX_RETRIES}")
            response = session.get(url, timeout=30)
            response.raise_for_status()

            if response.status_code == 200:
                print(f"    ✓ Downloaded: {len(response.content):,} bytes")
                return response.text

        except requests.exceptions.RequestException as e:
            print(f"    ✗ Error: {e}")

        if attempt < MAX_RETRIES:
            print(f"    Waiting {RETRY_DELAY}s before retry...")
            time.sleep(RETRY_DELAY)

    raise Exception(f"Failed after {MAX_RETRIES} attempts")


def extract_css_links(soup: BeautifulSoup) -> Set[str]:
    """Extract all CSS stylesheet links from page."""
    css_links = set()
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            css_links.add(href)
    return css_links


def extract_internal_links(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Extract internal t4002 links from page."""
    internal_links = []
    anchor_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "t4002-" in href and ".html" in href:
            # Internal guide link
            internal_links.append(href)

        if href.startswith("#"):
            # Anchor link within page
            anchor_links.append(href)

    return {
        "internal": list(set(internal_links)),
        "anchors": list(set(anchor_links)),
    }


def download_and_verify_page(
    session: requests.Session,
    page_info: Dict,
    task_num: int,
) -> Dict:
    """Download a single page with full verification."""
    filename = page_info["file"]
    page_name = page_info["name"]
    min_size = page_info["min_size"]

    print(f"\n{'=' * 70}")
    print(f"Task 2.{task_num}: Download {filename} ({page_name})")
    print(f"{'=' * 70}")

    url = urljoin(BASE_URL, filename)
    output_file = OUTPUT_DIR / filename

    # Download
    print(f"\n1. Downloading from: {url}")
    try:
        content = download_with_retry(session, url)
    except Exception as e:
        print(f"\n✗ FATAL: Download failed: {e}")
        print(f"✗ Task 2.{task_num} FAILED - STOPPING")
        return {"success": False, "error": str(e)}

    # Save
    print(f"\n2. Saving to: {filename}")
    output_file.write_text(content, encoding="utf-8")
    file_size = output_file.stat().st_size
    print(f"   ✓ File saved: {file_size:,} bytes")

    # Validation
    print(f"\n3. Validation:")
    errors = []

    # Check file size
    if file_size == 0:
        errors.append("File is empty (0 bytes)")
    elif file_size < min_size:
        errors.append(f"File too small ({file_size} < {min_size} bytes)")
    else:
        print(f"   ✓ File size: {file_size:,} bytes (> {min_size:,})")

    # Parse HTML
    soup = BeautifulSoup(content, "html.parser")

    # Check for h1 heading
    h1 = soup.find("h1")
    if h1:
        print(f"   ✓ H1 heading found: {h1.get_text()[:60]}...")
    else:
        errors.append("No H1 heading found")

    # Extract CSS dependencies
    css_links = extract_css_links(soup)
    print(f"   ✓ CSS files identified: {len(css_links)}")
    for css in sorted(css_links):
        print(f"     - {css}")

    # Extract internal links
    links = extract_internal_links(soup)
    print(f"   ✓ Internal t4002 links: {len(links['internal'])}")
    print(f"   ✓ Anchor links: {len(links['anchors'])}")

    # Final verdict
    if errors:
        print(f"\n✗ Task 2.{task_num} FAILED:")
        for error in errors:
            print(f"   ✗ {error}")
        print("\n✗ STOPPING - Fix errors before proceeding")
        return {"success": False, "errors": errors}

    print(f"\n✓ Task 2.{task_num} PASSED")

    return {
        "success": True,
        "filename": filename,
        "size": file_size,
        "css_links": list(css_links),
        "internal_links": links["internal"],
        "anchor_links": links["anchors"],
    }


def main():
    """Main execution for Phase 2."""
    print("\n" + "=" * 70)
    print("PHASE 2: Download All 13 Pages Individually")
    print("=" * 70)
    print("\nEach page must pass validation before proceeding to next page")
    print()

    session = setup_session()
    results = []
    all_css_links = set()

    # Download each page sequentially
    for i, page_info in enumerate(PAGES, start=1):
        result = download_and_verify_page(session, page_info, i)

        if not result["success"]:
            print("\n" + "=" * 70)
            print("✗ FATAL: Page download failed")
            print("=" * 70)
            print(f"\nFailed on: {page_info['file']}")
            print("Fix the issue and re-run this script")
            sys.exit(1)

        results.append(result)

        # Collect CSS links
        if "css_links" in result:
            all_css_links.update(result["css_links"])

        # Small delay between pages to be polite
        if i < len(PAGES):
            time.sleep(1)

    # Save metadata
    print("\n" + "=" * 70)
    print("Saving Download Metadata")
    print("=" * 70)

    metadata = {
        "total_pages": len(results),
        "pages": results,
        "unique_css_links": sorted(list(all_css_links)),
    }

    metadata_file = OUTPUT_DIR / "download_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"✓ Metadata saved to: {metadata_file}")

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 2 COMPLETE!")
    print("=" * 70)
    print(f"\n✓ All {len(results)} pages downloaded successfully")
    print(f"✓ {len(all_css_links)} unique CSS files identified")
    print("\nUnique CSS files to download:")
    for css in sorted(all_css_links):
        print(f"  - {css}")

    print("\nNext: Task 2.14 - Download CSS assets")
    print("=" * 70)


if __name__ == "__main__":
    main()
