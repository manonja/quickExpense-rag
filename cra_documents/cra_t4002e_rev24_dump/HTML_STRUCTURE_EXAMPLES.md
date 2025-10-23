# HTML Structure Examples from CRA T4002 Business Rules

## Overview

The CRA T4002 guide contains business expense rules structured using semantic HTML with:

- Hierarchical headings (h2, h3, h4, h5)
- Unique anchor IDs for cross-referencing
- Icons indicating rule applicability (business, farm, fish)
- Structured lists, tables, and examples
- Panels/sections for notes and warnings

______________________________________________________________________

## Example 1: Simple Business Expense Rule

**Source**: t4002-5.html (Chapter 3: Expenses) **Rule**: Prepaid Expenses

### HTML Structure:

```html
<h3><a id="tocch3aprpgxpnss"></a>Prepaid expenses</h3>

<p>A prepaid expense is an expense you paid for ahead of time. Under the <strong>accrual method</strong> of accounting, claim the expense you prepay in the year or years in which you get the related benefit. Suppose your fiscal year-end is <span class="nowrap">December 31, 2024</span>. On <span class="nowrap">June 30, 2024,</span> you prepay the rent on your building for a full year (<span class="nowrap">July 1, 2024,</span> to <span class="nowrap">June 30, 2025</span>). You can only deduct one-half of this rent as an expense in 2024. You can deduct the other half as an expense in 2025.</p>

<p>Under the <strong>cash method</strong> of accounting, you cannot deduct a prepaid expense amount (other than for inventory) relating to a tax year that is two or more years after the year the expense is paid. However, you can deduct the part of an amount you paid in a previous year for benefits received in the current tax year. These amounts are deductible as long as you have not previously deducted them.</p>

<p>If you paid $600 for a three-year service contract for office equipment in 2024, you can deduct $400 in 2024. This represents the part of the expense that applies to 2024 and 2025. On your <span class="nowrap">2026 income</span> tax return, you could then deduct the balance of $200 for the part of the prepaid lease that applies to 2026.</p>

<p>For more information, see <a href="/en/revenue-agency/services/forms-publications/publications/it417r2.html">Interpretation <span class="nowrap">Bulletin IT-417</span>, Prepaid Expenses and Deferred Charges</a>.</p>
```

### Key Elements:

- **Anchor ID**: `tocch3aprpgxpnss` (for cross-referencing)
- **Structure**: h3 heading → paragraphs → external link
- **Formatting**: `<strong>` for emphasis, `<span class="nowrap">` for date formatting
- **Example embedded**: Concrete dollar amounts and scenarios

______________________________________________________________________

## Example 2: Rule with Icons and Line Numbers

**Source**: t4002-5.html **Rule**: Meals and Entertainment Expenses (Line 8523)

### HTML Structure:

```html
<h3>
  <a id="tocch3ln8523"></a>
  <img alt="business icon" src="/content/dam/cra-arc/migration/cra-arc/E/pub/tg/t4002/icon_business.gif" title="business icon"/>
  <img alt="fish icon" src="/content/dam/cra-arc/migration/cra-arc/E/pub/tg/t4002/icon_fish.gif" title="fish icon"/>
  <span class="nowrap">Line 8523 –</span> Meals and entertainment
</h3>

<p>The maximum amount you can claim for food, beverages and entertainment expenses is 50% of the lesser of the following amounts:</p>

<ul>
  <li>the amount incurred for these expenses</li>
  <li>an amount that is reasonable in the circumstances</li>
</ul>

<p>When you claim expenses on this line, you will have to calculate the allowable part you can claim for business use.</p>

<p>These limits also apply to the cost of your meals when you travel or go to a convention, conference, or similar event. Special rules can affect your claim for meals in these cases. For more information, see <a href="#tocch3dcnvtnxpnss">Convention expenses for business and professional</a>.</p>

<p>These limits do not apply in any of these cases:</p>

<ul>
  <li>Your business regularly provides food, beverages or entertainment to customers for compensation (for example, a restaurant, hotel or motel)</li>
  <li>You bill your client or customer for the meal and entertainment costs, and you show these costs on the bill</li>
  <li>You include the amount of meal and entertainment expenses in an employee's income or would include them if the employee did not work at a remote or special work location. In addition, the amount cannot be paid or payable for a conference, convention, seminar or similar event and the special work location must be at least <span class="nowrap">30 kilometres</span> from the closest urban centre with a population of 40,000 or more; visit <a href="https://www.statcan.gc.ca/en/start">Statistics Canada</a></li>
  <li>You incur meal and entertainment expenses for an office party or similar event, and you invite all your employees from a particular location. The limit is <span class="nowrap">six such</span> events per year</li>
  <li>The meal and entertainment expenses you incur are for a fund-raising event that was mainly for the benefit of a registered charity</li>
  <li>You provide meals to an employee housed at a temporary work camp constructed or installed specifically to provide meals and accommodation to employees working at a construction site (note that the employee cannot be expected to return home daily)</li>
</ul>
```

### Key Elements:

- **Icons**: Business and fish icons indicate applicability
- **Line number**: `Line 8523` is the form line reference
- **50% rule**: Clear percentage-based deduction limit
- **Exceptions list**: Unordered list with 6 specific exceptions
- **Internal links**: `#tocch3dcnvtnxpnss` for related content
- **External links**: Statistics Canada reference

______________________________________________________________________

## Example 3: Rule with Formula and Examples

**Source**: t4002-5.html **Rule**: Private Health Services Plan (PHSP) Deduction

### HTML Structure:

```html
<h4><a id="ch3ytyytrt"></a>If you did not have any employees throughout 2024</h4>

<p>Your <abbr title="private health services plan">PHSP</abbr> deduction is restricted by an annual dollar limit. The limit is a maximum of:</p>

<ul>
  <li>$1,500 for yourself</li>
  <li>$1,500 for your spouse or common-law partner and each household member that is <span class="nowrap">18 years</span> of age or older at the start of the period they were insured</li>
  <li>$750 for each household member under the age of 18 at the start of the period</li>
</ul>

<p>The maximum deduction is also limited by the number of days that person was insured. Calculate your allowable maximum for the year by using the following formula:</p>

<p>A <abbr title="divided by">÷</abbr> 365 <abbr title="times">×</abbr> (B <abbr title="plus">+</abbr> C), where:</p>

<ul>
  <li>A is the number of days during the period of the year you insured yourself and your household members, if applicable</li>
  <li>B equals $1,500 <abbr title="times">×</abbr> the number of household members 18 and over insured during that period</li>
  <li>C equals $750 <abbr title="times">×</abbr> the number of household members under the age of 18 insured during that period</li>
</ul>

<!-- Example Panel -->
<div class="mwspanel section">
  <section class="panel panel-default well">
    <header class="panel-heading">
      <h5 class="panel-title">Example 1</h5>
    </header>
    <div class="panel-body">
      <p>Edwin was a sole proprietor who ran his business alone in 2024. He had no employees and did not insure any of his household members. Edwin paid $2,000 for <abbr title="private health services plan">PHSP</abbr> coverage in 2024. His coverage lasted from <span class="nowrap">July 1</span> to <span class="nowrap">December 31, 2024</span> (a total of <span class="nowrap">184 days</span>).</p>

      <p>Edwin's maximum allowable <abbr title="private health services plan">PHSP</abbr> deduction is calculated as follows:</p>

      <p>184 <abbr title="divided by">÷</abbr> 365 <abbr title="times">×</abbr> $1,500 <abbr title="equals">=</abbr> $756</p>

      <p>Even though Edwin paid $2,000 in premiums in 2024, he can only deduct $756 because the annual limit is $1,500 and he was only insured for half of the year. If he had been insured for the entire year, his deduction limit would be $1,500.</p>
    </div>

    <header class="panel-heading">
      <h5 class="panel-title">Example 2</h5>
    </header>
    <div class="panel-body">
      <p>Bruce was a sole proprietor who ran his business alone in 2024. He had no employees. From <span class="nowrap">January 1</span> to <span class="nowrap">December 31</span>, he insured himself, his wife and his two sons. Bruce paid $1,800 to insure himself, $1,800 to insure his wife and $1,000 for each of his sons. One of his sons was <span class="nowrap">15 years</span> old and the other turned 18 on <span class="nowrap">September 1</span>. Bruce's <abbr title="private health services plan">PHSP</abbr> deduction is limited to the following amounts:</p>

      <ul>
        <li>$1,500 for himself</li>
        <li>$1,500 for his wife</li>
        <li>$750 for his 15-year-old son</li>
        <li>$750 for the son who turned 18. This limit applies because he did not turn 18 until after the insured period began</li>
      </ul>
    </div>
  </section>
</div>
```

### Key Elements:

- **Abbreviations**: `<abbr>` tags with titles for accessibility
- **Formula**: Mathematical formula with variable definitions
- **Panel structure**: Bootstrap-style panels with headings
- **Multiple examples**: Real scenarios with specific names and calculations
- **Progressive complexity**: Example 2 builds on Example 1

______________________________________________________________________

## Example 4: Note Panels (Warnings/Important Information)

**Source**: t4002-5.html

### HTML Structure:

```html
<div class="mwspanel section">
  <section class="panel panel-default">
    <header class="panel-heading">
      <h3 class="panel-title">Note</h3>
    </header>
    <div class="panel-body">
      <p>When you claim the <abbr title="goods and services tax/harmonized sales tax">GST/HST</abbr> you paid or owe on your business expenses as an input tax credit, reduce the amounts of the business expenses by the amount of the input tax credit. Do this when the <abbr title="goods and services tax/harmonized sales tax">GST/HST</abbr> for which you are claiming the input tax credit was paid or became payable, whichever is earlier. Similarly, subtract any rebate, grant or assistance from the expense to which it applies. Enter the net figure on the proper line. Any such assistance you claim for the purchase of depreciable property used in your business will affect your claim for capital cost <span class="nowrap">allowance (CCA)</span>.</p>
    </div>
  </section>
</div>

<!-- Business-specific note with icon -->
<div class="mwspanel section">
  <section class="panel panel-default">
    <header class="panel-heading">
      <h3 class="panel-title">
        <img alt="business icon" src="/content/dam/cra-arc/migration/cra-arc/E/pub/tg/t4002/icon_business.gif" title="business icon"/>
        Note for business and professional
      </h3>
    </header>
    <div class="panel-body">
      <p>If you cannot apply the rebate, grant or assistance you received to reduce a particular expense, or to reduce an asset's capital cost, include the total in <span class="nowrap">Part 3C</span> at <a href="t4002-4.html#tocch2ln8230"><span class="nowrap">Line 8230 –</span> Other income</a>. For more information, see <a href="t4002-6.html#tocch4fgrntssbsdrbts">Grants, subsidies and rebates</a>.</p>
    </div>
  </section>
</div>
```

### Key Elements:

- **Panel styling**: Bootstrap panel classes
- **Conditional notes**: Business vs farm vs fishing specific guidance
- **Cross-references**: Links to other chapters and form lines
- **Visual hierarchy**: Panels visually separate from main content

______________________________________________________________________

## Example 5: Exclusion List (What NOT to Claim)

**Source**: t4002-5.html

### HTML Structure:

```html
<p><strong>Do not include any of the following in your expenses:</strong></p>

<ul>
  <li>salary, wages (including drawings) paid to self, partner(s) or both</li>
  <li>the cost of saleable goods or services you, your family, or your partners and their families used or consumed (including items such as food, home maintenance and business properties)
    <ul>
      <li>for farmers, this includes items such as dairy products, eggs, fruit, vegetables, poultry and meat</li>
    </ul>
  </li>
  <li>donations to charities and political contributions</li>
  <li>interest and penalties you paid on your income tax</li>
  <li>most life insurance premiums; for more information on limited exceptions:
    <ul>
      <li>for farming, see <a href="#tocch3ln9804"><span class="nowrap">Line 9804</span></a></li>
      <li>for fishing, see <a href="#tocch3ln8690"><span class="nowrap">Line 8690</span></a></li>
    </ul>
  </li>
  <li>the part of any expenses that can be attributed to non-business use of business property</li>
  <li>most fines and penalties imposed, under the law of Canada or a province or a foreign country</li>
</ul>
```

### Key Elements:

- **Negative rule**: What NOT to do
- **Nested lists**: Sub-items for specific industries
- **Qualified statements**: "most" indicates exceptions exist
- **Internal cross-references**: Links to specific line numbers for exceptions

______________________________________________________________________

## Common HTML Patterns

### 1. Anchor ID Naming Convention

- `tocch[chapter][section]` - Table of contents chapter/section
- `tocch3ln8523` - Chapter 3, Line 8523
- Descriptive: `tocch3aprpgxpnss` (prepaid expenses)

### 2. Cross-Reference Links

```html
<!-- Internal to same file -->
<a href="#tocch3dcnvtnxpnss">Convention expenses</a>

<!-- Cross-file with anchor -->
<a href="t4002-4.html#tocch2ln8230">Line 8230 – Other income</a>

<!-- External CRA resource -->
<a href="/en/revenue-agency/services/forms-publications/forms/t2125.html">Form T2125</a>
```

### 3. Icons for Applicability

```html
<img alt="business icon" src="..." title="business icon"/> <!-- Business/Professional -->
<img alt="farm icon" src="..." title="farm icon"/>         <!-- Farming -->
<img alt="fish icon" src="..." title="fish icon"/>         <!-- Fishing -->
```

### 4. Abbreviations

```html
<abbr title="goods and services tax/harmonized sales tax">GST/HST</abbr>
<abbr title="private health services plan">PHSP</abbr>
<abbr title="capital cost allowance">CCA</abbr>
```

### 5. No-Wrap Formatting

```html
<span class="nowrap">December 31, 2024</span>
<span class="nowrap">Line 8523 –</span>
<span class="nowrap">30 kilometres</span>
```

______________________________________________________________________

## Data Extraction Recommendations for RAG

### Structured Fields to Extract:

1. **Rule ID**: Anchor ID (e.g., `tocch3ln8523`)
1. **Rule Title**: Heading text (e.g., "Line 8523 – Meals and entertainment")
1. **Applicability**: Icons present (business/farm/fish)
1. **Content Type**: Rule, example, note, warning
1. **Deduction Limits**: Percentages, dollar amounts
1. **Formulas**: Mathematical expressions
1. **Exceptions**: List items under "does not apply" sections
1. **Cross-References**: Internal and external links
1. **Examples**: Named scenarios with calculations

### Sample JSON Extraction:

```json
{
  "rule_id": "tocch3ln8523",
  "chapter": 3,
  "line_number": "8523",
  "title": "Meals and entertainment",
  "applies_to": ["business", "fishing"],
  "deduction_limit": "50%",
  "deduction_basis": "lesser of amount incurred or reasonable amount",
  "exceptions": [
    "Business regularly provides food for compensation",
    "Costs billed to client",
    "6 office parties per year",
    "Registered charity fundraising",
    "Temporary work camp meals"
  ],
  "related_sections": ["#tocch3dcnvtnxpnss"],
  "content_html": "...",
  "content_text": "..."
}
```

______________________________________________________________________

Generated: 2025-10-16 Source: CRA T4002 Self-employed Business Guide (2024 Revision)
