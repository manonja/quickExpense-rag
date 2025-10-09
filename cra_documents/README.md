# CRA Regulatory Documents for RAG System

Downloaded: 2025-10-09

## Documents Overview

This directory contains core CRA regulatory documents for bookkeeping and expense management RAG ingestion.

### 1. T4002 Business Expenses Guide
- **File**: `T4002-Business-Expenses-Guide.pdf`
- **Size**: 1,013 KB (113 pages)
- **Source**: https://www.canada.ca/content/dam/cra-arc/formspubs/pub/t4002/t4002-24e.pdf
- **Version**: 2024 edition
- **Coverage**:
  - Comprehensive business expense categories
  - Deductibility rules
  - Current vs capital expense distinctions
  - Motor vehicle, home office, and other common expenses
  - Form T2125 guidance

### 2. IC78-10R5 Books and Records Retention/Destruction
- **File**: `IC78-10R5-Books-Records-Retention.pdf`
- **Size**: 176 KB (6 pages)
- **Source**: https://www.canada.ca/content/dam/cra-arc/formspubs/pub/ic78-10r5/ic78-10r5-10e.pdf
- **Revision**: R5 (10th edition)
- **Coverage**:
  - Mandatory record-keeping requirements
  - 6-year retention period (section 5800 Income Tax Regulations)
  - Electronic record standards
  - Source document requirements
  - Acceptable storage formats

### 3. GST/HST Memorandum 8.4 Documentary Requirements for ITCs
- **File**: `GST-HST-Memo-8-4-Documentary-Requirements.html`
- **Size**: 9.7 KB
- **Source**: https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/8-4/documentary-requirements-claiming-input-tax-credits.html
- **Format**: HTML (PDF not available from CRA)
- **Coverage**:
  - Invoice information requirements for Input Tax Credits
  - Required fields for GST/HST compliance
  - Disclosure provisions
  - Supporting documentation standards

### 4. IC05-1R1 Electronic Record Keeping
- **File**: `IC05-1R1-Electronic-Record-Keeping.pdf`
- **Size**: 180 KB (6 pages)
- **Source**: https://www.canada.ca/content/dam/cra-arc/formspubs/pub/ic05-1r1/ic05-1r1-10e.pdf
- **Revision**: R1 (10th edition)
- **Coverage**:
  - Electronic record-keeping system requirements
  - Digital record retention standards
  - "Electronically readable and useable" format definition
  - Imaging and conversion requirements
  - Acceptable electronic storage methods

## Receipt/Invoice Requirements Summary

Based on these documents, CRA-compliant receipts must contain:

1. Date of purchase
2. Name and address of seller/supplier
3. Name and address of buyer
4. Full description of goods/services
5. Vendor's business number (for GST/HST registrants on purchases $100+)
6. GST/HST information or applicable tax rate

## RAG Implementation Notes

### Recommended Processing Pipeline:
1. **PDF Extraction**: Use `pdfplumber`, `PyPDF2`, or `pymupdf` for the 3 PDF files
2. **HTML Processing**: Parse `GST-HST-Memo-8-4-Documentary-Requirements.html` with BeautifulSoup or similar
3. **Chunking Strategy**:
   - Chunk by regulation topic (expense categories, retention rules, invoice requirements)
   - Include metadata: document type, section numbers, effective dates
   - Tag by regulation area: deductibility, record-keeping, GST/HST, electronic records

### Key Retention Rule:
Records must be kept for **6 years** from the end of the tax year (with specific exceptions per section 5800 of Income Tax Regulations)

## Additional Documents to Consider

For expanded coverage:
- **T4044** - Employment Expenses (for employee reimbursements)
- **RC4022** - General Information for GST/HST Registrants
- Additional GST/HST Memoranda for specific scenarios

## Document Versions

These are the latest publicly available versions as of October 2025. Archived versions dating back to 1988 are available for T4002 at the CRA website.
