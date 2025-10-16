# CRA T4002 Guide Extraction Plan

## Project Overview

**Objective:** Download the complete CRA T4002 Self-employed Business guide from canada.ca for RAG ingestion.

**Target URL:** https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002/

**Output Directory:** `/Users/manonjacquin/Documents_local/POCs/quickExpense-rag/cra_documents/cra_t4002e_rev24_dump`

**Asset Strategy:** HTML + CSS only (no JavaScript required for static content)

---

## Phase 1: Initial Setup & Structure Analysis

### Task 1.1: Environment Setup & Initial Page Download

**Instructions:**
1. Create output directory if it doesn't exist
2. Set up Python environment with `requests` and `beautifulsoup4` libraries
3. Configure HTTP headers with User-Agent to mimic standard browser
4. Download `t4002-1.html` (Table of Contents page) from base URL
5. Save raw HTML to output directory

**Acceptance Criteria:**
- Output directory exists at specified path
- File `t4002-1.html` exists in output directory
- File size is greater than 0 bytes
- File contains HTML tag: `<h1>Table of contents</h1>` or similar
- Script completes without network exceptions
- HTTP response status is 200

**Error Handling:**
- Catch `requests.exceptions.RequestException` for network errors
- Verify HTTP status code is 200, else raise exception with status and URL
- Terminate script if initial page fails (subsequent tasks depend on it)

---

### Task 1.2: URL Discovery & Page Count Verification

**Instructions:**
1. Parse downloaded `t4002-1.html` using BeautifulSoup
2. Locate table of contents navigation element
3. Extract all `<a>` tags with href matching pattern `t4002-*.html`
4. Build list of unique absolute URLs (13 pages expected)
5. Print discovered URLs to console for manual verification

**Expected Pages:**
- t4002-1.html - Table of Contents
- t4002-2.html - What's new / Definitions
- t4002-3.html - Chapter 1: General information
- t4002-4.html - Chapter 2: Income
- t4002-5.html - Chapter 3: Expenses
- t4002-6.html - Chapter 4: Capital cost allowance
- t4002-8.html - Chapter 5: Losses (note: t4002-7.html does not exist)
- t4002-9.html - Chapter 6: Capital gains
- t4002-10.html - CCA rates
- t4002-11.html - Mandatory inventory adjustment
- t4002-12.html - GST/HST for farmers and fishers
- t4002-14.html - Digital services (note: t4002-13.html does not exist)
- t4002-15.html - For more information

**Acceptance Criteria:**
- Exactly 13 unique URLs discovered
- All URLs match the base pattern: `https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/t4002/t4002-*.html`
- Manual verification confirms all 13 expected pages are in the list
- No duplicate URLs in the list

**Error Handling:**
- If URL count is not 13, halt execution and log critical error
- Indicates website structure has changed and scraper logic needs review

---

### Task 1.3: Structure Analysis of Sample Page

**Instructions:**
1. Download `t4002-3.html` (Chapter 1) as test page
2. Use **clink gemini** (Gemini 2.5 Pro) to analyze page structure due to large size
3. Document the following:
   - Main content sections and headings
   - Nested subsections and hierarchy depth
   - Internal anchor links (e.g., `#section-name`)
   - Navigation elements (Previous/Next page links)
   - All CSS file references
4. Verify: Are there any sub-pages beyond the main 13 pages?
5. Create structure documentation for reference

**Why Use Gemini:**
- Some pages exceed 30K tokens (too large for Claude's context)
- Gemini 2.5 Pro has 1M token context window
- Prevents context limit issues during analysis

**Acceptance Criteria:**
- Full structure map documented including nesting levels
- List of all CSS dependencies identified
- Confirmation that no hidden sub-pages exist beyond the 13 main pages
- Navigation structure understood (how Previous/Next links work)
- Internal anchor link patterns documented

**Error Handling:**
- If unexpected nesting or sub-pages discovered, update URL list in Task 1.2
- Do not proceed to bulk download until structure is fully understood

---

## Phase 2: Individual Page Downloads with Per-Page Verification

### Task 2.1: Download Page 1 - t4002-1.html (TOC)

**Instructions:**
1. Download `t4002-1.html` from full URL
2. Save to output directory
3. Extract all CSS file URLs from `<link rel="stylesheet">` tags
4. Log CSS dependencies
5. Verify download immediately before proceeding

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-1.html`
- File size greater than 1KB
- File contains expected h1 heading related to table of contents
- All CSS URLs extracted and logged
- All internal t4002 links catalogued

**Error Handling:**
- Retry up to 3 times with 5-second delay between attempts
- If all retries fail, STOP and report error
- Do not proceed to Task 2.2 until this task passes all acceptance criteria

---

### Task 2.2: Download Page 2 - t4002-2.html (Definitions)

**Instructions:**
1. Download `t4002-2.html` from full URL
2. Save to output directory
3. **Use clink gemini** to analyze due to large page size
4. Extract CSS dependencies and internal links via gemini
5. Verify content structure

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-2.html`
- File size greater than 1KB
- File contains expected content about definitions and what's new
- Gemini successfully analyzes page structure
- All CSS dependencies logged
- All internal anchor links identified

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails after retries, STOP and report error
- Do not proceed to Task 2.3 until this passes

---

### Task 2.3: Download Page 3 - t4002-3.html (Chapter 1)

**Instructions:**
1. Download `t4002-3.html` from full URL
2. Save to output directory
3. **Use clink gemini** to analyze due to large page size
4. Extract CSS dependencies and internal links
5. Verify content structure and nested sections

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-3.html`
- File size greater than 1KB
- File contains Chapter 1 content about general information
- Gemini successfully analyzes page structure
- All nested subsections identified
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error
- Do not proceed until this passes

---

### Task 2.4: Download Page 4 - t4002-4.html (Chapter 2)

**Instructions:**
1. Download `t4002-4.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Log internal links
5. Verify download

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-4.html`
- File size greater than 1KB
- File contains Chapter 2 content about income
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.5: Download Page 5 - t4002-5.html (Chapter 3)

**Instructions:**
1. Download `t4002-5.html` from full URL
2. Save to output directory
3. **Use clink gemini** to analyze due to large page size
4. Extract CSS dependencies and internal links
5. Verify expense-related content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-5.html`
- File size greater than 1KB
- File contains Chapter 3 content about expenses
- Gemini successfully analyzes page structure
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.6: Download Page 6 - t4002-6.html (Chapter 4)

**Instructions:**
1. Download `t4002-6.html` from full URL
2. Save to output directory
3. **Use clink gemini** to analyze due to large page size
4. Extract CSS dependencies and internal links
5. Verify capital cost allowance content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-6.html`
- File size greater than 1KB
- File contains Chapter 4 content about CCA
- Gemini successfully analyzes page structure
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.7: Download Page 7 - t4002-8.html (Chapter 5)

**Instructions:**
1. Download `t4002-8.html` from full URL (note: t4002-7.html does not exist)
2. Save to output directory
3. Extract CSS dependencies
4. Verify losses content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-8.html`
- File size greater than 1KB
- File contains Chapter 5 content about losses
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.8: Download Page 8 - t4002-9.html (Chapter 6)

**Instructions:**
1. Download `t4002-9.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Verify capital gains content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-9.html`
- File size greater than 1KB
- File contains Chapter 6 content about capital gains
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.9: Download Page 9 - t4002-10.html (CCA Rates)

**Instructions:**
1. Download `t4002-10.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Verify CCA rates table content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-10.html`
- File size greater than 1KB
- File contains CCA rates reference table
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.10: Download Page 10 - t4002-11.html (Inventory)

**Instructions:**
1. Download `t4002-11.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Verify inventory adjustment content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-11.html`
- File size greater than 1KB
- File contains mandatory inventory adjustment content
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.11: Download Page 11 - t4002-12.html (GST/HST)

**Instructions:**
1. Download `t4002-12.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Verify GST/HST content for farmers and fishers

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-12.html`
- File size greater than 1KB
- File contains GST/HST information for farmers and fishers
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.12: Download Page 12 - t4002-14.html (Digital Services)

**Instructions:**
1. Download `t4002-14.html` from full URL (note: t4002-13.html does not exist)
2. Save to output directory
3. Extract CSS dependencies
4. Verify digital services content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-14.html`
- File size greater than 1KB
- File contains digital services information
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.13: Download Page 13 - t4002-15.html (More Information)

**Instructions:**
1. Download `t4002-15.html` from full URL
2. Save to output directory
3. Extract CSS dependencies
4. Verify additional information and resources content

**Acceptance Criteria:**
- HTTP response status is 200
- File saved with exact filename: `t4002-15.html`
- File size greater than 1KB
- File contains additional information and resources
- CSS dependencies logged

**Error Handling:**
- Retry up to 3 times with 5-second delay
- If fails, STOP and report error

---

### Task 2.14: Download CSS Assets

**Instructions:**
1. Compile unique list of CSS URLs from all 13 pages
2. Create `assets/` subdirectory in output directory
3. Download each unique CSS file
4. Save CSS files with original filenames to `assets/` directory
5. Handle both absolute and relative CSS URLs

**Acceptance Criteria:**
- `assets/` subdirectory exists in output directory
- All unique CSS files downloaded (no duplicates)
- Each CSS file has size greater than 0 bytes
- CSS filenames preserved correctly

**Error Handling:**
- Retry up to 3 times per CSS file with 5-second delay
- Log any CSS files that fail to download
- Continue with other CSS files if one fails
- Report list of failed CSS files at end

---

## Phase 3: Content Localization & Verification

### Task 3.1: Link Rewriting - Internal Guide Links

**Instructions:**
1. For each of the 13 HTML files:
   - Parse with BeautifulSoup
   - Find all `<a>` tags
   - Identify links pointing to other t4002 pages
   - Rewrite absolute URLs to relative paths
   - Example: `https://www.canada.ca/.../t4002-5.html` becomes `t4002-5.html`
   - Example: `https://www.canada.ca/.../t4002-5.html#expenses` becomes `t4002-5.html#expenses`
   - Preserve anchor fragments (hash links)
   - Leave external links unchanged (links to other CRA guides, forms)
2. Save modified HTML, overwriting original

**Acceptance Criteria:**
- All internal t4002 links are relative paths (no domain, no full path)
- Anchor fragments preserved correctly
- External links remain absolute URLs to canada.ca
- No `<a href>` contains both `canada.ca` AND `t4002-` pattern
- Previous/Next page navigation links are relative

**Error Handling:**
- Validate each rewritten file before moving to next
- If validation fails, log error with specific file and link
- Report all validation failures at end

---

### Task 3.2: Link Rewriting - CSS References

**Instructions:**
1. For each of the 13 HTML files:
   - Parse with BeautifulSoup
   - Find all `<link rel="stylesheet">` tags
   - Rewrite href attributes to point to local assets directory
   - Example: `/etc/designs/canada/wet-boew/css/theme.min.css` becomes `assets/theme.min.css`
   - Example: `https://www.canada.ca/etc/designs/.../style.css` becomes `assets/style.css`
2. Save modified HTML, overwriting previous version

**Acceptance Criteria:**
- All CSS link hrefs point to `assets/` directory
- CSS filenames match downloaded files in assets directory
- No absolute URLs in CSS link tags
- All CSS references use relative paths

**Error Handling:**
- Validate CSS links after rewriting
- Verify referenced CSS files exist in assets directory
- Log any broken CSS references

---

### Task 3.3: Automated Integrity Verification

**Instructions:**
1. Create verification script that checks:
   - Output directory exists
   - Exactly 13 HTML files present with expected filenames
   - `assets/` subdirectory exists
   - `assets/` contains at least one CSS file
   - All 13 HTML files are larger than 1KB
   - No broken internal links (all href targets exist as files)
2. Run verification script
3. Generate verification report

**Acceptance Criteria:**
- Verification script runs without errors
- All 13 expected HTML files exist
- All files meet minimum size requirement
- Assets directory exists and is populated
- No broken internal links detected
- Verification report shows 100% pass rate

**Error Handling:**
- Script reports any missing files
- Script reports any files below size threshold
- Script reports all broken links with source and target
- Detailed error report generated if any check fails

---

### Task 3.4: Manual User Acceptance Testing

**Instructions:**
1. Open `t4002-1.html` in web browser from local filesystem
2. **Test 1 - CSS Styling:**
   - Verify page renders with proper styling
   - Check fonts, colors, layout are correct
   - Confirm no missing styles or broken formatting
3. **Test 2 - Table of Contents Navigation:**
   - Click link for "Chapter 4 - Capital cost allowance"
   - Verify it loads `t4002-6.html` locally
   - Verify content is correct chapter
4. **Test 3 - Sequential Navigation:**
   - From Chapter 4 page, click "Next page" link
   - Verify it navigates to `t4002-8.html` (Chapter 5)
   - Click "Previous page" link
   - Verify it returns to `t4002-6.html`
5. **Test 4 - Anchor Link Navigation:**
   - Find a table of contents entry with anchor link (e.g., `#section-name`)
   - Click the link
   - Verify page scrolls to correct section
6. **Test 5 - External Links:**
   - Find a link to another CRA guide or form
   - Click the link
   - Verify it attempts to open the live canada.ca URL
   - Confirm internal links were not affected

**Acceptance Criteria:**
- All pages render with correct CSS styling
- Table of contents links navigate to correct local pages
- Previous/Next navigation works bidirectionally
- Anchor links jump to correct sections within pages
- External links still point to canada.ca
- No 404 errors or broken links
- All content is readable and properly formatted

**Error Handling:**
- Document any rendering issues
- Note any broken navigation links
- Report any missing content or formatting problems
- Log any unexpected behavior

---

## Final Deliverable Structure

```
cra_t4002e_rev24_dump/
├── EXTRACT_CRA_RULES.md          (this file)
├── t4002-1.html                  (Table of Contents)
├── t4002-2.html                  (What's new / Definitions)
├── t4002-3.html                  (Chapter 1: General information)
├── t4002-4.html                  (Chapter 2: Income)
├── t4002-5.html                  (Chapter 3: Expenses)
├── t4002-6.html                  (Chapter 4: Capital cost allowance)
├── t4002-8.html                  (Chapter 5: Losses)
├── t4002-9.html                  (Chapter 6: Capital gains)
├── t4002-10.html                 (CCA rates)
├── t4002-11.html                 (Mandatory inventory adjustment)
├── t4002-12.html                 (GST/HST farmers/fishers)
├── t4002-14.html                 (Digital services)
├── t4002-15.html                 (More information)
└── assets/
    ├── theme.min.css             (CRA theme styles)
    ├── wet-boew.min.css          (Web Experience Toolkit styles)
    └── [other CSS files]
```

## Success Criteria

Project is complete when:
- All 13 HTML pages downloaded successfully
- All CSS assets downloaded
- All internal links rewritten to relative paths
- All CSS references point to local assets
- Automated verification script passes 100%
- Manual UAT passes all 5 tests
- Content is self-contained and browsable offline
- Ready for RAG ingestion pipeline

## Notes for Implementation Team

- **Use Gemini for large pages:** Tasks 2.2, 2.3, 2.5, 2.6 involve large pages that may exceed token limits
- **Sequential execution required:** Each task must pass before proceeding to next
- **100% accuracy per page:** Do not batch downloads without per-page verification
- **Missing page numbers:** Note that t4002-7.html and t4002-13.html do not exist in the guide
- **No JavaScript required:** Static HTML content only needs CSS for formatting
- **Preserve anchor links:** Many internal links use fragments (e.g., `#section`) for navigation
- **External links unchanged:** Links to other CRA guides should remain absolute URLs
