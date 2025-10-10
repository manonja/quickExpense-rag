"""
Comprehensive unit tests for Pydantic models.

Tests cover:
- Enum validation
- Field validation (citation_id, source_url, version, chunk_count)
- Immutability (frozen models)
- Legal disclaimer presence in serialization
- Type safety and mypy compliance
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from quickexpense_rag.search.enums import BusinessType, Province
from quickexpense_rag.search.models import (
    ExpenseQuery,
    IndexManifest,
    SearchResult,
    SourceFile,
)


@pytest.mark.unit
class TestEnumValidation:
    """Test enum value validation."""

    def test_invalid_province_raises_validation_error(self) -> None:
        """Invalid province value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(query="test query", province="ZZ")  # type: ignore[arg-type]

        error = exc_info.value.errors()[0]
        assert "province" in error["loc"]
        assert "Input should be" in error["msg"]

    def test_invalid_business_type_raises_validation_error(self) -> None:
        """Invalid business type value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(
                query="test query",
                business_type="invalid_type",  # type: ignore[arg-type]
            )

        error = exc_info.value.errors()[0]
        assert "business_type" in error["loc"]

    def test_invalid_expense_types_raises_validation_error(self) -> None:
        """Invalid expense types value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(
                query="test query",
                expense_types="invalid_expense",  # type: ignore[arg-type]
            )

        error = exc_info.value.errors()[0]
        assert "expense_types" in error["loc"]


@pytest.mark.unit
class TestExpenseQueryValidation:
    """Test ExpenseQuery model validation."""

    def test_empty_query_raises_validation_error(self) -> None:
        """Empty query string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(query="")

        error = exc_info.value.errors()[0]
        assert "query" in error["loc"]
        assert "at least 3 characters" in error["msg"]

    def test_short_query_raises_validation_error(self) -> None:
        """Query shorter than 3 characters should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(query="ab")

        error = exc_info.value.errors()[0]
        assert "query" in error["loc"]

    def test_top_k_zero_raises_validation_error(self) -> None:
        """top_k of 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(query="test query", top_k=0)

        error = exc_info.value.errors()[0]
        assert "top_k" in error["loc"]
        assert "greater than or equal to 1" in error["msg"]

    def test_top_k_over_limit_raises_validation_error(self) -> None:
        """top_k over 50 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExpenseQuery(query="test query", top_k=51)

        error = exc_info.value.errors()[0]
        assert "top_k" in error["loc"]
        assert "less than or equal to 50" in error["msg"]

    def test_valid_query_passes(self) -> None:
        """Valid ExpenseQuery should be created successfully."""
        query = ExpenseQuery(
            query="restaurant meal expense",
            province=Province.BC,
            business_type=BusinessType.SOLE_PROPRIETORSHIP,
            expense_types=["meals", "travel"],
            top_k=10,
        )

        assert query.query == "restaurant meal expense"
        assert query.province == Province.BC
        assert query.business_type == BusinessType.SOLE_PROPRIETORSHIP
        assert query.expense_types == ["meals", "travel"]
        assert query.top_k == 10

    def test_query_with_none_filters_passes(self) -> None:
        """ExpenseQuery with None filters should be valid."""
        query = ExpenseQuery(query="test query")

        assert query.query == "test query"
        assert query.province is None
        assert query.business_type is None
        assert query.expense_types is None
        assert query.top_k == 5  # Default value


@pytest.mark.unit
class TestSearchResultValidation:
    """Test SearchResult model validation."""

    def test_invalid_citation_id_format_raises_validation_error(self) -> None:
        """Citation ID not matching pattern should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test content",
                citation_id="invalid-citation",
                source_url="https://www.canada.ca/test",
                score=0.8,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )

        error = exc_info.value.errors()[0]
        assert "citation_id" in error["loc"]
        assert "String should match pattern" in error["msg"]

    @pytest.mark.parametrize(
        "invalid_citation",
        [
            "S3-F2",  # Missing chunk and page
            "F2-C1-p1",  # Missing series
            "S3-C1-p1",  # Missing folio
            "S3-F2-p1",  # Missing chapter
            "S3-F2-C1",  # Missing page
            "invalid",  # Completely invalid
        ],
    )
    def test_various_invalid_citation_formats(self, invalid_citation: str) -> None:
        """Various invalid citation formats should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test",
                citation_id=invalid_citation,
                source_url="https://www.canada.ca/test",
                score=0.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )

        error = exc_info.value.errors()[0]
        assert "citation_id" in error["loc"]

    def test_valid_citation_id_formats_pass(self) -> None:
        """Valid citation ID formats should pass validation."""
        valid_citations = [
            "S3-F2-C1-p1",
            "S3-F2-C1-p1.25",
            "S10-F20-C30-p40.50",
        ]

        for citation in valid_citations:
            result = SearchResult(
                content="Test",
                citation_id=citation,
                source_url="https://www.canada.ca/test",
                score=0.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )
            assert result.citation_id == citation

    def test_non_https_url_raises_validation_error(self) -> None:
        """Non-HTTPS URL should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test",
                citation_id="S3-F2-C1-p1",
                source_url="http://www.canada.ca/test",
                score=0.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any("source_url must use HTTPS" in str(e) for e in errors)

    def test_non_canada_domain_raises_validation_error(self) -> None:
        """Non-canada.ca domain should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test",
                citation_id="S3-F2-C1-p1",
                source_url="https://example.com/test",
                score=0.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any("must be a 'canada.ca' domain" in str(e) for e in errors)

    @pytest.mark.parametrize(
        "valid_url",
        [
            "https://www.canada.ca/test",
            "https://subdomain.canada.ca/test",
        ],
    )
    def test_valid_canada_domains_pass(self, valid_url: str) -> None:
        """Valid canada.ca domains and subdomains should pass validation."""
        result = SearchResult(
            content="Test",
            citation_id="S3-F2-C1-p1",
            source_url=valid_url,
            score=0.5,
            province=None,
            business_type=None,
            expense_types=[],
            retrieved_at=datetime.now(timezone.utc),
        )
        assert str(result.source_url) == valid_url

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "https://cra-arc.gc.ca/test",  # gc.ca is not a canada.ca subdomain
            "https://canada.ca.example.com/test",  # Not a canada.ca domain
        ],
    )
    def test_invalid_canada_domains_fail(self, invalid_url: str) -> None:
        """Domains that are not canada.ca should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test",
                citation_id="S3-F2-C1-p1",
                source_url=invalid_url,
                score=0.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )
        errors = exc_info.value.errors()
        assert any("must be a 'canada.ca' domain" in str(e) for e in errors)

    def test_score_out_of_range_raises_validation_error(self) -> None:
        """Score outside [0.0, 1.0] range should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                content="Test",
                citation_id="S3-F2-C1-p1",
                source_url="https://www.canada.ca/test",
                score=1.5,
                province=None,
                business_type=None,
                expense_types=[],
                retrieved_at=datetime.now(timezone.utc),
            )

        error = exc_info.value.errors()[0]
        assert "score" in error["loc"]

    def test_valid_search_result_passes(self) -> None:
        """Valid SearchResult should be created successfully."""
        now = datetime.now(timezone.utc)
        result = SearchResult(
            content="Test content about meals",
            citation_id="S3-F2-C1-p1.25",
            source_url="https://www.canada.ca/en/revenue-agency/services/tax/test",
            score=0.85,
            province=Province.BC,
            business_type=BusinessType.CORPORATION,
            expense_types=["meals"],
            retrieved_at=now,
        )

        assert result.content == "Test content about meals"
        assert result.citation_id == "S3-F2-C1-p1.25"
        assert result.score == 0.85
        assert result.province == Province.BC
        assert result.retrieved_at == now


@pytest.mark.unit
class TestSearchResultDisclaimer:
    """Test legal disclaimer functionality."""

    def test_disclaimer_present_in_model_dump(self) -> None:
        """Disclaimer should be present in model_dump() output."""
        result = SearchResult(
            content="Test",
            citation_id="S3-F2-C1-p1",
            source_url="https://www.canada.ca/test",
            score=0.5,
            province=None,
            business_type=None,
            expense_types=[],
            retrieved_at=datetime.now(timezone.utc),
        )

        dumped = result.model_dump()
        assert "disclaimer" in dumped
        assert "NOT TAX ADVICE" in dumped["disclaimer"]

    def test_disclaimer_present_in_model_dump_json(self) -> None:
        """Disclaimer should be present in model_dump_json() output."""
        result = SearchResult(
            content="Test",
            citation_id="S3-F2-C1-p1",
            source_url="https://www.canada.ca/test",
            score=0.5,
            province=None,
            business_type=None,
            expense_types=[],
            retrieved_at=datetime.now(timezone.utc),
        )

        json_str = result.model_dump_json()
        assert "disclaimer" in json_str
        assert "NOT TAX ADVICE" in json_str

    def test_disclaimer_content(self) -> None:
        """Disclaimer should contain required legal warnings."""
        result = SearchResult(
            content="Test",
            citation_id="S3-F2-C1-p1",
            source_url="https://www.canada.ca/test",
            score=0.5,
            province=None,
            business_type=None,
            expense_types=[],
            retrieved_at=datetime.now(timezone.utc),
        )

        disclaimer = result.disclaimer
        assert "⚠️" in disclaimer
        assert "INFORMATIONAL ONLY" in disclaimer
        assert "NOT TAX ADVICE" in disclaimer
        assert "consult a qualified tax professional" in disclaimer
        assert "CRA rules are complex" in disclaimer


@pytest.mark.unit
class TestImmutability:
    """Test frozen (immutable) model behavior."""

    def test_expense_query_is_immutable(self) -> None:
        """ExpenseQuery fields should not be reassignable."""
        query = ExpenseQuery(query="test")

        with pytest.raises(ValidationError):
            query.query = "new query"  # type: ignore[misc]

    def test_search_result_is_immutable(self) -> None:
        """SearchResult fields should not be reassignable."""
        result = SearchResult(
            content="Test",
            citation_id="S3-F2-C1-p1",
            source_url="https://www.canada.ca/test",
            score=0.5,
            province=None,
            business_type=None,
            expense_types=[],
            retrieved_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValidationError):
            result.score = 0.9  # type: ignore[misc]

    def test_source_file_is_immutable(self) -> None:
        """SourceFile fields should not be reassignable."""
        source = SourceFile(path="/path/to/file.txt", hash="abc123")

        with pytest.raises(ValidationError):
            source.path = "/new/path"  # type: ignore[misc]

    def test_index_manifest_is_immutable(self) -> None:
        """IndexManifest fields should not be reassignable."""
        manifest = IndexManifest(
            version="2024.12",
            schema_version="1.0",
            source_files=(SourceFile(path="/test", hash="abc"),),
            embedding_model="test-model",
            chunk_count=100,
            created_at=datetime.now(timezone.utc),
            sha256="abc123",
        )

        with pytest.raises(ValidationError):
            manifest.chunk_count = 200  # type: ignore[misc]

    def test_source_files_tuple_is_immutable(self) -> None:
        """IndexManifest.source_files tuple should provide deep immutability."""
        manifest = IndexManifest(
            version="2024.12",
            schema_version="1.0",
            source_files=(SourceFile(path="/test", hash="abc"),),
            embedding_model="test-model",
            chunk_count=100,
            created_at=datetime.now(timezone.utc),
            sha256="abc123",
        )

        # Tuple is immutable, so this should fail
        with pytest.raises(TypeError):
            manifest.source_files[0] = SourceFile(path="/new", hash="def")  # type: ignore[index]


@pytest.mark.unit
class TestIndexManifestValidation:
    """Test IndexManifest model validation."""

    def test_invalid_version_format_raises_validation_error(self) -> None:
        """Version not in YYYY.MM format should raise ValidationError."""
        invalid_versions = ["2024", "24.12", "2024-12", "2024.1", "2024.123"]

        for invalid_version in invalid_versions:
            with pytest.raises(ValidationError) as exc_info:
                IndexManifest(
                    version=invalid_version,
                    schema_version="1.0",
                    source_files=(SourceFile(path="/test", hash="abc"),),
                    embedding_model="test",
                    chunk_count=10,
                    created_at=datetime.now(timezone.utc),
                    sha256="abc",
                )

            error = exc_info.value.errors()[0]
            assert "version" in error["loc"]

    def test_valid_version_format_passes(self) -> None:
        """Valid YYYY.MM version format should pass."""
        manifest = IndexManifest(
            version="2024.12",
            schema_version="1.0",
            source_files=(SourceFile(path="/test", hash="abc"),),
            embedding_model="test-model",
            chunk_count=100,
            created_at=datetime.now(timezone.utc),
            sha256="abc123",
        )

        assert manifest.version == "2024.12"

    def test_chunk_count_zero_raises_validation_error(self) -> None:
        """chunk_count of 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IndexManifest(
                version="2024.12",
                schema_version="1.0",
                source_files=(SourceFile(path="/test", hash="abc"),),
                embedding_model="test",
                chunk_count=0,
                created_at=datetime.now(timezone.utc),
                sha256="abc",
            )

        error = exc_info.value.errors()[0]
        assert "chunk_count" in error["loc"]
        assert "greater than 0" in error["msg"]

    def test_chunk_count_negative_raises_validation_error(self) -> None:
        """Negative chunk_count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IndexManifest(
                version="2024.12",
                schema_version="1.0",
                source_files=(SourceFile(path="/test", hash="abc"),),
                embedding_model="test",
                chunk_count=-10,
                created_at=datetime.now(timezone.utc),
                sha256="abc",
            )

        error = exc_info.value.errors()[0]
        assert "chunk_count" in error["loc"]

    def test_valid_index_manifest_passes(self) -> None:
        """Valid IndexManifest should be created successfully."""
        now = datetime.now(timezone.utc)
        source_files = (
            SourceFile(path="/data/file1.txt", hash="hash1"),
            SourceFile(path="/data/file2.txt", hash="hash2"),
        )

        manifest = IndexManifest(
            version="2024.12",
            schema_version="1.0",
            source_files=source_files,
            embedding_model="BAAI/bge-small-en-v1.5",
            chunk_count=1234,
            created_at=now,
            sha256="abc123def456",
        )

        assert manifest.version == "2024.12"
        assert manifest.schema_version == "1.0"
        assert len(manifest.source_files) == 2
        assert manifest.chunk_count == 1234
        assert manifest.created_at == now


@pytest.mark.unit
class TestSourceFile:
    """Test SourceFile model."""

    def test_valid_source_file_creation(self) -> None:
        """Valid SourceFile should be created successfully."""
        source = SourceFile(path="/path/to/file.txt", hash="abc123def456")

        assert source.path == "/path/to/file.txt"
        assert source.hash == "abc123def456"

    def test_source_file_in_tuple(self) -> None:
        """SourceFile should work correctly in tuples."""
        sources = (
            SourceFile(path="/file1.txt", hash="hash1"),
            SourceFile(path="/file2.txt", hash="hash2"),
        )

        assert len(sources) == 2
        assert sources[0].path == "/file1.txt"
        assert sources[1].hash == "hash2"
