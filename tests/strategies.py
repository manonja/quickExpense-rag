"""Reusable Hypothesis strategies for property-based testing.

This module provides composable strategies for generating valid test data
for the extraction pipeline's core data models.
"""

from datetime import datetime, timezone

from hypothesis import strategies as st
from qe_tax_rag.extraction.ca.schema import (
    ApplicabilityType,
    ExpertSource,
    ExtractedRule,
    RuleSet,
)


# Strategy for generating valid rule numbers (line numbers)
# Range: 1000-9999 (realistic CRA line numbers)
rule_numbers = st.integers(min_value=1000, max_value=9999)

# Strategy for generating non-empty text content
# Excludes null characters and control characters
non_empty_text = st.text(
    min_size=1,
    max_size=500,
    alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Cn")),
).filter(lambda s: s.strip() != "")

# Strategy for generating short titles
titles = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Cn")),
).filter(lambda s: s.strip() != "")

# Strategy for generating realistic content
content = st.text(
    min_size=10,
    max_size=1000,
    alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Cn")),
).filter(lambda s: s.strip() != "")

# Strategy for generating ApplicabilityType lists
applicability_types = st.lists(
    st.sampled_from(ApplicabilityType),
    min_size=1,
    max_size=3,
    unique=True,
)

# Strategy for generating source citations
source_citations = st.builds(
    lambda n: f"Line {n}",
    rule_numbers,
)

# Strategy for generating chapter titles
chapters = st.sampled_from([
    "Chapter 1 – General Information",
    "Chapter 2 – Income",
    "Chapter 3 – Business Expenses",
    "Chapter 4 – Net Income",
])

# Strategy for generating section titles (optional)
sections = st.one_of(
    st.none(),
    st.sampled_from([
        "Part 1 – Meals and Entertainment",
        "Part 2 – Travel Expenses",
        "Part 3 – Motor Vehicle Expenses",
        "Part 4 – Home Office Expenses",
    ]),
)

# Strategy for generating source filenames
source_files = st.sampled_from([
    "t4002-1.html",
    "t4002-2.html",
    "t4002-3.html",
    "t4002-4.html",
    "t4002-5.html",
])

# Strategy for generating expert sources
expert_sources = st.sampled_from(ExpertSource)

# Strategy for generating HTML anchor IDs (optional)
anchor_ids = st.one_of(
    st.none(),
    st.builds(
        lambda n: f"tocch3ln{n}",
        rule_numbers,
    ),
)

# Strategy for generating confidence scores
confidence_scores = st.floats(min_value=0.0, max_value=1.0)


@st.composite
def extracted_rule_strategy(draw: st.DrawFn) -> ExtractedRule:
    """Generate a valid ExtractedRule instance.

    This strategy ensures all Pydantic constraints are satisfied:
    - rule_number is a positive integer
    - title and content are non-empty strings
    - applies_to is a non-empty list of unique ApplicabilityType
    - confidence_score is between 0.0 and 1.0
    - All required fields are populated

    Args:
        draw: Hypothesis draw function

    Returns:
        A valid ExtractedRule instance
    """
    return ExtractedRule(
        rule_number=draw(rule_numbers),
        title=draw(titles),
        content=draw(content),
        applies_to=draw(applicability_types),
        source_citation=draw(source_citations),
        chapter=draw(chapters),
        section=draw(sections),
        source_file=draw(source_files),
        expert_source=draw(expert_sources),
        anchor_id=draw(anchor_ids),
        confidence_score=draw(confidence_scores),
    )


@st.composite
def ruleset_strategy(draw: st.DrawFn) -> RuleSet:
    """Generate a valid RuleSet instance.

    This strategy generates a RuleSet with 0-10 rules, realistic schema
    version, and valid ISO 8601 timestamp.

    Args:
        draw: Hypothesis draw function

    Returns:
        A valid RuleSet instance
    """
    # Generate list of rules
    rules = draw(st.lists(extracted_rule_strategy(), min_size=0, max_size=10))

    # Schema version follows semantic versioning
    schema_version = "1.0"

    # Generate realistic ISO 8601 timestamp
    extraction_timestamp = datetime.now(tz=timezone.utc).isoformat()

    return RuleSet(
        rules=rules,
        schema_version=schema_version,
        extraction_timestamp=extraction_timestamp,
    )
