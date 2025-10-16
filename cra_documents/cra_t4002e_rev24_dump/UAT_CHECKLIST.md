# Task 3.4: Manual User Acceptance Testing

## Overview
This checklist guides you through manual testing to ensure the offline CRA T4002 guide functions correctly.

## Prerequisites
- All previous tasks (1.1-3.3) must be complete
- All files downloaded and links rewritten
- Integrity verification passed

## Testing Steps

### 1. Initial Page Load
- [ ] Open `t4002-1.html` in a web browser (Chrome, Firefox, Safari)
- [ ] Verify page renders correctly with proper styling
- [ ] Check that Canada.ca header/footer displays properly
- [ ] Confirm page title shows "Self-employed Business, Professional, Commission, Farming, and Fishing Income"

### 2. Navigation Testing
Test clicking through all pages from the table of contents:

- [ ] Click "What's new for 2024" → `t4002-2.html` loads
- [ ] Click "Chapter 1 - General information" → `t4002-3.html` loads
- [ ] Click "Chapter 2 - Business and professional income" → `t4002-4.html` loads
- [ ] Click "Chapter 3 - Business and professional expenses" → `t4002-5.html` loads
- [ ] Click "Chapter 4 - Capital cost allowance" → `t4002-6.html` loads
- [ ] Click "Chapter 5 - Business and professional losses" → `t4002-8.html` loads
- [ ] Click "Chapter 6 - Capital gains" → `t4002-9.html` loads
- [ ] Click "Appendix A - Classes of depreciable property" → `t4002-10.html` loads
- [ ] Click "Appendix B - Inventories" → `t4002-11.html` loads
- [ ] Click "Appendix C - GST/HST information for businesses" → `t4002-12.html` loads
- [ ] Click "Appendix E - Reporting Digital Platform Operators" → `t4002-14.html` loads
- [ ] Click "For more information" → `t4002-15.html` loads

### 3. CSS Rendering Verification
On each page, verify:

- [ ] Page layout is clean and readable
- [ ] Navigation menus display properly
- [ ] Font sizes and colors are correct
- [ ] No missing images or broken CSS (check browser console)
- [ ] Page is responsive (try resizing browser window)

### 4. Anchor Link Testing
Test internal section links (examples):

- [ ] On `t4002-3.html`, click a section link (e.g., "Business identification number")
- [ ] Verify page scrolls to correct section
- [ ] On `t4002-5.html`, click a cross-reference to another chapter
- [ ] Verify navigation to correct page and section

### 5. Back/Forward Navigation
- [ ] Use browser back button to return to previous page
- [ ] Use browser forward button to go forward
- [ ] Verify browser history works correctly

### 6. Error Checking
- [ ] Open browser developer console (F12)
- [ ] Navigate through all pages
- [ ] Verify no 404 errors for missing files
- [ ] Verify no console errors related to missing CSS or resources

### 7. Content Spot Check
On key pages, verify content is complete:

- [ ] `t4002-5.html` (largest file) - scroll through entire page, verify no truncated content
- [ ] `t4002-6.html` - verify CCA rate tables display properly
- [ ] `t4002-10.html` - verify appendix tables render correctly

### 8. Offline Testing (Optional)
- [ ] Disconnect from internet
- [ ] Reload pages to confirm they work offline
- [ ] Verify all navigation still functions

## Acceptance Criteria

All checkboxes above must be checked (✓) for UAT to pass.

If any issues found:
1. Document the specific issue (which page, what broke)
2. Check `integrity_report.json` for clues
3. Re-run relevant Phase 3 scripts if needed

## Sign-Off

- **Tester Name**: ___________________________
- **Date**: ___________________________
- **Overall Status**: [ ] PASS  [ ] FAIL
- **Notes**:

---

## Quick Test Command

To quickly open the guide in your default browser:

```bash
# macOS
open t4002-1.html

# Linux
xdg-open t4002-1.html

# Windows
start t4002-1.html
```
