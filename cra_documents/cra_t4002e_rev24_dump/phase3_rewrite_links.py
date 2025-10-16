#!/usr/bin/env python3
"""
Phase 3: Rewrite links for local navigation
Tasks 3.1 & 3.2: Rewrite internal guide links and CSS references
"""

import re
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

# Configuration
OUTPUT_DIR = Path(__file__).parent
PAGES = [f"t4002-{i}.html" for i in [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15]]

# CSS mapping: original URL → local path
CSS_MAPPING = {
    "/etc/designs/canada/wet-boew/css/theme.min.css": "assets/theme.min.css",
    "/etc/designs/canada/wet-boew/css/noscript.min.css": "assets/noscript.min.css",
    "https://use.fontawesome.com/releases/v5.15.4/css/all.css": "assets/fontawesome-all.css",
}


def rewrite_internal_links(soup: BeautifulSoup) -> int:
    """
    Rewrite internal t4002 links to relative paths.
    Returns number of links rewritten.
    """
    count = 0

    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Check if it's an internal t4002 link
        if "t4002-" in href and ".html" in href:
            # Extract just the filename and anchor
            # Examples:
            #   /en/.../t4002-5.html → t4002-5.html
            #   /en/.../t4002-5.html#section → t4002-5.html#section
            #   https://.../t4002-5.html#section → t4002-5.html#section

            # Use regex to extract t4002-X.html and optional #anchor
            match = re.search(r'(t4002-\d+\.html)(#[^"\']*)?', href)
            if match:
                filename = match.group(1)
                anchor = match.group(2) or ""
                new_href = filename + anchor

                if new_href != href:
                    link["href"] = new_href
                    count += 1

    return count


def rewrite_css_links(soup: BeautifulSoup) -> int:
    """
    Rewrite CSS links to point to local assets/ directory.
    Returns number of CSS links rewritten.
    """
    count = 0

    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if not href:
            continue

        # Check if this CSS file needs to be rewritten
        if href in CSS_MAPPING:
            link["href"] = CSS_MAPPING[href]
            count += 1

    return count


def process_html_file(filepath: Path) -> Dict:
    """Process a single HTML file to rewrite links."""
    print(f"\nProcessing: {filepath.name}")

    # Read HTML
    content = filepath.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Rewrite internal links
    internal_count = rewrite_internal_links(soup)
    print(f"  ✓ Rewrote {internal_count} internal t4002 links")

    # Rewrite CSS links
    css_count = rewrite_css_links(soup)
    print(f"  ✓ Rewrote {css_count} CSS links")

    # Save modified HTML
    filepath.write_text(str(soup), encoding="utf-8")
    print(f"  ✓ Saved modified file")

    return {
        "filename": filepath.name,
        "internal_links_rewritten": internal_count,
        "css_links_rewritten": css_count,
    }


def verify_rewrites(filepath: Path) -> List[str]:
    """Verify that links were rewritten correctly."""
    errors = []
    content = filepath.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Check for unrewritten internal links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "canada.ca" in href and "t4002-" in href:
            errors.append(f"Unrewritten internal link: {href}")

    # Check for unrewritten CSS links
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href", "")
        if href in CSS_MAPPING:
            errors.append(f"Unrewritten CSS link: {href}")

    return errors


def main():
    """Main execution for Phase 3."""
    print("\n" + "=" * 70)
    print("PHASE 3: Rewrite Links for Local Navigation")
    print("=" * 70)
    print("\nTasks 3.1 & 3.2: Internal links + CSS references")

    results = []
    total_internal = 0
    total_css = 0

    # Process each page
    for filename in PAGES:
        filepath = OUTPUT_DIR / filename

        if not filepath.exists():
            print(f"\n✗ ERROR: {filename} not found!")
            continue

        result = process_html_file(filepath)
        results.append(result)

        total_internal += result["internal_links_rewritten"]
        total_css += result["css_links_rewritten"]

    # Verification
    print("\n" + "=" * 70)
    print("Verification")
    print("=" * 70)

    all_errors = []
    for filename in PAGES:
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            errors = verify_rewrites(filepath)
            if errors:
                print(f"\n✗ {filename}:")
                for error in errors:
                    print(f"    {error}")
                all_errors.extend(errors)

    if all_errors:
        print(f"\n✗ FAILED: {len(all_errors)} verification errors")
        return

    print("\n✓ All verifications passed")
    print("  ✓ No unrewritten internal t4002 links found")
    print("  ✓ No unrewritten CSS links found")

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 3 COMPLETE!")
    print("=" * 70)
    print(f"\n✓ Processed {len(results)} pages")
    print(f"✓ Rewrote {total_internal} internal guide links")
    print(f"✓ Rewrote {total_css} CSS references")
    print("\nAll links are now local and ready for offline browsing")
    print("\nNext: Task 3.3 - Automated integrity verification")
    print("=" * 70)


if __name__ == "__main__":
    main()
