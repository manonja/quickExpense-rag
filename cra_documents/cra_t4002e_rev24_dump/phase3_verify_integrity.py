#!/usr/bin/env python3
"""
Task 3.3: Automated Integrity Verification

Validates:
- All 13 HTML files exist with expected filenames
- All files meet minimum size requirements
- No broken internal links (all href targets exist)
- Assets directory is properly populated

Outputs: integrity_report.json
"""

import json
from pathlib import Path
from typing import TypedDict

from bs4 import BeautifulSoup


class FileCheck(TypedDict):
    exists: bool
    size: int
    meets_min_size: bool


class LinkCheck(TypedDict):
    total_links: int
    broken_links: list[str]
    all_valid: bool


class IntegrityReport(TypedDict):
    all_html_files_exist: bool
    all_sizes_valid: bool
    all_links_valid: bool
    assets_complete: bool
    overall_status: str
    file_checks: dict[str, FileCheck]
    link_checks: dict[str, LinkCheck]
    assets_checks: dict[str, FileCheck]


EXPECTED_PAGES = [
    "t4002-1.html",
    "t4002-2.html",
    "t4002-3.html",
    "t4002-4.html",
    "t4002-5.html",
    "t4002-6.html",
    "t4002-8.html",
    "t4002-9.html",
    "t4002-10.html",
    "t4002-11.html",
    "t4002-12.html",
    "t4002-14.html",
    "t4002-15.html",
]

EXPECTED_ASSETS = [
    "assets/theme.min.css",
    "assets/noscript.min.css",
    "assets/fontawesome-all.css",
]

MIN_FILE_SIZE = 1024  # 1KB minimum


def check_file_exists_and_size(file_path: Path) -> FileCheck:
    """Check if file exists and meets minimum size requirement."""
    exists = file_path.exists()
    size = file_path.stat().st_size if exists else 0
    meets_min_size = size >= MIN_FILE_SIZE

    return {
        "exists": exists,
        "size": size,
        "meets_min_size": meets_min_size,
    }


def check_internal_links(html_file: Path, output_dir: Path) -> LinkCheck:
    """Check that all internal links point to existing files."""
    content = html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    broken_links: list[str] = []
    total_links = 0

    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Only check local t4002 links (ignore anchors and external links)
        if href.startswith("t4002-") and ".html" in href:
            total_links += 1

            # Extract filename without anchor
            filename = href.split("#")[0]
            target_file = output_dir / filename

            if not target_file.exists():
                broken_links.append(href)

    return {
        "total_links": total_links,
        "broken_links": broken_links,
        "all_valid": len(broken_links) == 0,
    }


def run_integrity_verification() -> IntegrityReport:
    """Run full integrity verification and generate report."""
    output_dir = Path(__file__).parent
    print(f"Running integrity verification in: {output_dir}\n")

    # Check HTML files
    print("=" * 70)
    print("STEP 1: Checking HTML files")
    print("=" * 70)

    file_checks: dict[str, FileCheck] = {}
    all_html_files_exist = True
    all_sizes_valid = True

    for filename in EXPECTED_PAGES:
        file_path = output_dir / filename
        check = check_file_exists_and_size(file_path)
        file_checks[filename] = check

        status = "✓" if (check["exists"] and check["meets_min_size"]) else "✗"
        size_kb = check["size"] / 1024 if check["exists"] else 0

        print(f"{status} {filename}: {size_kb:.1f} KB")

        if not check["exists"]:
            all_html_files_exist = False
        if not check["meets_min_size"]:
            all_sizes_valid = False

    # Check assets
    print("\n" + "=" * 70)
    print("STEP 2: Checking CSS assets")
    print("=" * 70)

    assets_checks: dict[str, FileCheck] = {}
    assets_complete = True

    for asset_path in EXPECTED_ASSETS:
        file_path = output_dir / asset_path
        check = check_file_exists_and_size(file_path)
        assets_checks[asset_path] = check

        status = "✓" if (check["exists"] and check["meets_min_size"]) else "✗"
        size_kb = check["size"] / 1024 if check["exists"] else 0

        print(f"{status} {asset_path}: {size_kb:.1f} KB")

        if not (check["exists"] and check["meets_min_size"]):
            assets_complete = False

    # Check internal links
    print("\n" + "=" * 70)
    print("STEP 3: Checking internal links")
    print("=" * 70)

    link_checks: dict[str, LinkCheck] = {}
    all_links_valid = True

    for filename in EXPECTED_PAGES:
        file_path = output_dir / filename

        if file_path.exists():
            check = check_internal_links(file_path, output_dir)
            link_checks[filename] = check

            status = "✓" if check["all_valid"] else "✗"
            print(
                f"{status} {filename}: {check['total_links']} links, "
                f"{len(check['broken_links'])} broken"
            )

            if not check["all_valid"]:
                all_links_valid = False
                for broken in check["broken_links"]:
                    print(f"   - BROKEN: {broken}")

    # Overall status
    overall_status = (
        "PASS"
        if (
            all_html_files_exist
            and all_sizes_valid
            and all_links_valid
            and assets_complete
        )
        else "FAIL"
    )

    report: IntegrityReport = {
        "all_html_files_exist": all_html_files_exist,
        "all_sizes_valid": all_sizes_valid,
        "all_links_valid": all_links_valid,
        "assets_complete": assets_complete,
        "overall_status": overall_status,
        "file_checks": file_checks,
        "link_checks": link_checks,
        "assets_checks": assets_checks,
    }

    return report


def main() -> None:
    """Main entry point."""
    report = run_integrity_verification()

    # Print summary
    print("\n" + "=" * 70)
    print("INTEGRITY VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"All HTML files exist: {report['all_html_files_exist']}")
    print(f"All sizes valid: {report['all_sizes_valid']}")
    print(f"All links valid: {report['all_links_valid']}")
    print(f"Assets complete: {report['assets_complete']}")
    print(f"\nOverall status: {report['overall_status']}")
    print("=" * 70)

    # Save report
    output_dir = Path(__file__).parent
    report_file = output_dir / "integrity_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nReport saved to: {report_file}")

    if report["overall_status"] == "PASS":
        print("\n✓ Task 3.3 COMPLETE - All integrity checks passed!")
        print("\nNext: Task 3.4 - Manual user acceptance testing")
    else:
        print("\n✗ Task 3.3 FAILED - See report for details")
        exit(1)


if __name__ == "__main__":
    main()
