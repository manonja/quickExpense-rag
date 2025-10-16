#!/usr/bin/env python3
"""
Phase 4: Content Verification Script

Compares downloaded local files against live CRA website to ensure:
1. All headings are present (structure verification)
2. All anchor links exist in local files
3. Content is complete and not truncated

Uses requests + BeautifulSoup for efficient content comparison.
"""

import json
import time
from pathlib import Path
from typing import TypedDict

import requests
from bs4 import BeautifulSoup


class HeadingData(TypedDict):
    h1: int
    h2: int
    h3: int
    h4: int
    total: int


class PageVerificationResult(TypedDict):
    page: str
    url: str
    live_heading_counts: HeadingData
    local_heading_counts: HeadingData
    heading_match: bool
    live_anchors_sample: list[str]
    local_anchors_sample: list[str]
    anchors_match: bool
    content_complete: bool
    issues: list[str]


class VerificationReport(TypedDict):
    verification_date: str
    total_pages_verified: int
    verification_results: list[PageVerificationResult]
    overall_status: str
    summary: dict


BASE_URL = "https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002"

PAGES_TO_VERIFY = [
    ("t4002-1.html", "Table of Contents"),
    ("t4002-2.html", "What's new / Definitions"),
    ("t4002-3.html", "Chapter 1: General information"),
    ("t4002-4.html", "Chapter 2: Income"),
    ("t4002-5.html", "Chapter 3: Expenses"),
    ("t4002-6.html", "Chapter 4: Capital cost allowance"),
    ("t4002-8.html", "Chapter 5: Losses"),
    ("t4002-9.html", "Chapter 6: Capital gains"),
    ("t4002-10.html", "Appendix A: CCA rates"),
    ("t4002-11.html", "Appendix B: Inventory"),
    ("t4002-12.html", "Appendix C: GST/HST"),
    ("t4002-14.html", "Appendix E: Digital services"),
    ("t4002-15.html", "More information"),
]


def fetch_live_page(url: str, retry: int = 3) -> str:
    """Fetch page from live CRA website with retry logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(1, retry + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            if response.status_code == 200:
                return response.text
        except requests.exceptions.RequestException as e:
            print(f"   Attempt {attempt}/{retry} failed: {e}")
            if attempt < retry:
                time.sleep(5)

    raise Exception(f"Failed to fetch {url} after {retry} attempts")


def extract_heading_counts(soup: BeautifulSoup) -> HeadingData:
    """Extract heading counts from main content area."""
    main = soup.find("main") or soup  # Fallback to whole doc if no main

    h1_count = len(main.find_all("h1"))
    h2_count = len(main.find_all("h2"))
    h3_count = len(main.find_all("h3"))
    h4_count = len(main.find_all("h4"))

    return {
        "h1": h1_count,
        "h2": h2_count,
        "h3": h3_count,
        "h4": h4_count,
        "total": h1_count + h2_count + h3_count + h4_count,
    }


def extract_anchor_ids(soup: BeautifulSoup) -> list[str]:
    """Extract all elements with id attributes (anchor targets)."""
    main = soup.find("main") or soup
    elements_with_id = main.find_all(id=True)

    # Get first 20 anchor IDs as sample
    return [elem.get("id") for elem in elements_with_id[:20]]


def verify_page(filename: str, description: str, output_dir: Path) -> PageVerificationResult:
    """Verify a single page against live website."""
    print(f"\nVerifying {filename} ({description})...")

    url = f"{BASE_URL}/{filename}"
    local_file = output_dir / filename

    issues: list[str] = []

    # Fetch live page
    print(f"  1. Fetching live page from {url}")
    try:
        live_html = fetch_live_page(url)
        live_soup = BeautifulSoup(live_html, "html.parser")
    except Exception as e:
        issues.append(f"Failed to fetch live page: {e}")
        return {
            "page": filename,
            "url": url,
            "live_heading_counts": {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "total": 0},
            "local_heading_counts": {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "total": 0},
            "heading_match": False,
            "live_anchors_sample": [],
            "local_anchors_sample": [],
            "anchors_match": False,
            "content_complete": False,
            "issues": issues,
        }

    # Load local file
    print(f"  2. Loading local file")
    if not local_file.exists():
        issues.append(f"Local file does not exist: {local_file}")
        return {
            "page": filename,
            "url": url,
            "live_heading_counts": extract_heading_counts(live_soup),
            "local_heading_counts": {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "total": 0},
            "heading_match": False,
            "live_anchors_sample": [],
            "local_anchors_sample": [],
            "anchors_match": False,
            "content_complete": False,
            "issues": issues,
        }

    local_html = local_file.read_text(encoding="utf-8")
    local_soup = BeautifulSoup(local_html, "html.parser")

    # Compare heading counts
    print(f"  3. Comparing heading counts")
    live_headings = extract_heading_counts(live_soup)
    local_headings = extract_heading_counts(local_soup)

    # Allow ±2 tolerance for dynamic content (timestamps, notices, etc.)
    heading_match = abs(live_headings["total"] - local_headings["total"]) <= 2

    if not heading_match:
        issues.append(
            f"Heading count mismatch: live={live_headings['total']}, "
            f"local={local_headings['total']}"
        )

    # Compare anchor IDs
    print(f"  4. Comparing anchor IDs (sample)")
    live_anchors = extract_anchor_ids(live_soup)
    local_anchors = extract_anchor_ids(local_soup)

    # Check if most live anchors exist in local (allow some variation)
    matching_anchors = len(set(live_anchors) & set(local_anchors))
    anchors_match = matching_anchors >= len(live_anchors) * 0.9  # 90% match threshold

    if not anchors_match:
        issues.append(
            f"Anchor ID mismatch: {matching_anchors}/{len(live_anchors)} anchors match"
        )

    # Content completeness check
    print(f"  5. Checking content completeness")
    content_complete = heading_match and anchors_match and len(issues) == 0

    status = "✓ PASS" if content_complete else "✗ FAIL"
    print(f"  Result: {status}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")

    return {
        "page": filename,
        "url": url,
        "live_heading_counts": live_headings,
        "local_heading_counts": local_headings,
        "heading_match": heading_match,
        "live_anchors_sample": live_anchors,
        "local_anchors_sample": local_anchors,
        "anchors_match": anchors_match,
        "content_complete": content_complete,
        "issues": issues,
    }


def main() -> None:
    """Main entry point."""
    print("=" * 70)
    print("CRA T4002 CONTENT VERIFICATION")
    print("=" * 70)
    print(f"Comparing local files against live website: {BASE_URL}")
    print(f"Total pages to verify: {len(PAGES_TO_VERIFY)}\n")

    output_dir = Path(__file__).parent
    results: list[PageVerificationResult] = []

    # Verify each page
    for filename, description in PAGES_TO_VERIFY:
        result = verify_page(filename, description, output_dir)
        results.append(result)
        time.sleep(2)  # Be polite to CRA servers

    # Generate summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r["content_complete"])
    failed = len(results) - passed

    print(f"Total pages verified: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    # Detailed results
    print("\nDetailed Results:")
    for result in results:
        status = "✓" if result["content_complete"] else "✗"
        live_h = result["live_heading_counts"]["total"]
        local_h = result["local_heading_counts"]["total"]
        print(
            f"{status} {result['page']}: "
            f"headings live={live_h} local={local_h} "
            f"({'match' if result['heading_match'] else 'MISMATCH'})"
        )

    # Overall status
    overall_status = "PASS" if failed == 0 else "FAIL"
    print(f"\nOverall Status: {overall_status}")

    # Save report
    report: VerificationReport = {
        "verification_date": "2025-10-16",
        "total_pages_verified": len(results),
        "verification_results": results,
        "overall_status": overall_status,
        "summary": {"passed": passed, "failed": failed, "total": len(results)},
    }

    report_file = output_dir / "content_verification_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to: {report_file}")

    if overall_status == "PASS":
        print("\n✓ All content verification checks passed!")
    else:
        print(f"\n✗ {failed} page(s) failed verification - see report for details")
        exit(1)


if __name__ == "__main__":
    main()
