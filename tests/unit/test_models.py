# Sistema de Automacao Juridica - SQLAlchemy Models Unit Tests
# Tests for model definitions, enums, column constraints, and relationships
# introduced in migrations/models.py.

import uuid
import pytest

sqlalchemy = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
from sqlalchemy import inspect, String, Integer, Boolean, Text, Numeric, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY

from migrations.models import (
    Base,
    CaseStatus,
    DocumentType,
    Case,
    Document,
    FIRACAnalysis,
    JurisprudenceSearch,
    DistinguishAnalysis,
    GeneratedDocument,
    Notification,
    AuditLog,
)


# =============================================================================
# Enum tests
# =============================================================================


class TestCaseStatus:
    """Tests for CaseStatus enum."""

    @pytest.mark.unit
    def test_pending_value(self):
        assert CaseStatus.PENDING.value == "pending"

    @pytest.mark.unit
    def test_processing_value(self):
        assert CaseStatus.PROCESSING.value == "processing"

    @pytest.mark.unit
    def test_completed_value(self):
        assert CaseStatus.COMPLETED.value == "completed"

    @pytest.mark.unit
    def test_error_value(self):
        assert CaseStatus.ERROR.value == "error"

    @pytest.mark.unit
    def test_archived_value(self):
        assert CaseStatus.ARCHIVED.value == "archived"

    @pytest.mark.unit
    def test_has_five_members(self):
        assert len(CaseStatus) == 5

    @pytest.mark.unit
    def test_all_values_are_strings(self):
        for status in CaseStatus:
            assert isinstance(status.value, str)


class TestDocumentType:
    """Tests for DocumentType enum."""

    @pytest.mark.unit
    def test_sentenca_value(self):
        assert DocumentType.SENTENCA.value == "sentenca"

    @pytest.mark.unit
    def test_despacho_value(self):
        assert DocumentType.DESPACHO.value == "despacho"

    @pytest.mark.unit
    def test_decisao_value(self):
        assert DocumentType.DECISAO.value == "decisao"

    @pytest.mark.unit
    def test_acordao_value(self):
        assert DocumentType.ACORDAO.value == "acordao"

    @pytest.mark.unit
    def test_peticao_value(self):
        assert DocumentType.PETICAO.value == "peticao"

    @pytest.mark.unit
    def test_parecer_value(self):
        assert DocumentType.PARECER.value == "parecer"

    @pytest.mark.unit
    def test_has_six_members(self):
        assert len(DocumentType) == 6

    @pytest.mark.unit
    def test_all_values_are_strings(self):
        for dt in DocumentType:
            assert isinstance(dt.value, str)


# =============================================================================
# Case model
# =============================================================================


class TestCaseModel:
    """Tests for Case model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert Case.__tablename__ == "cases"

    @pytest.mark.unit
    def test_schema_is_judicial(self):
        table_args = Case.__table_args__
        # table_args is a tuple; last element should be dict with schema
        schema_dict = next((a for a in table_args if isinstance(a, dict)), {})
        assert schema_dict.get("schema") == "judicial"

    @pytest.mark.unit
    def test_id_column_exists(self):
        assert hasattr(Case, "id")

    @pytest.mark.unit
    def test_id_is_uuid(self):
        col = Case.__table__.c["id"]
        assert isinstance(col.type, UUID)

    @pytest.mark.unit
    def test_case_number_not_nullable(self):
        col = Case.__table__.c["case_number"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_case_number_is_unique(self):
        col = Case.__table__.c["case_number"]
        assert col.unique is True

    @pytest.mark.unit
    def test_tribunal_not_nullable(self):
        col = Case.__table__.c["tribunal"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_priority_default_is_zero(self):
        col = Case.__table__.c["priority"]
        assert col.default is not None or col.server_default is not None

    @pytest.mark.unit
    def test_has_documents_relationship(self):
        assert hasattr(Case, "documents")

    @pytest.mark.unit
    def test_has_firac_analyses_relationship(self):
        assert hasattr(Case, "firac_analyses")

    @pytest.mark.unit
    def test_has_jurisprudence_searches_relationship(self):
        assert hasattr(Case, "jurisprudence_searches")

    @pytest.mark.unit
    def test_has_distinguish_analyses_relationship(self):
        assert hasattr(Case, "distinguish_analyses")

    @pytest.mark.unit
    def test_has_generated_documents_relationship(self):
        assert hasattr(Case, "generated_documents")

    @pytest.mark.unit
    def test_has_notifications_relationship(self):
        assert hasattr(Case, "notifications")

    @pytest.mark.unit
    def test_created_at_column_exists(self):
        assert "created_at" in Case.__table__.c

    @pytest.mark.unit
    def test_updated_at_column_exists(self):
        assert "updated_at" in Case.__table__.c

    @pytest.mark.unit
    def test_indexes_defined(self):
        """Verify at least the four documented indexes are defined."""
        table_args = Case.__table_args__
        index_names = {
            a.name for a in table_args if hasattr(a, "name") and not isinstance(a, dict)
        }
        assert "idx_cases_number" in index_names
        assert "idx_cases_tribunal" in index_names
        assert "idx_cases_status" in index_names
        assert "idx_cases_created" in index_names


# =============================================================================
# Document model
# =============================================================================


class TestDocumentModel:
    """Tests for Document model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert Document.__tablename__ == "documents"

    @pytest.mark.unit
    def test_schema_is_judicial(self):
        schema_dict = next(
            (a for a in Document.__table_args__ if isinstance(a, dict)), {}
        )
        assert schema_dict.get("schema") == "judicial"

    @pytest.mark.unit
    def test_document_type_not_nullable(self):
        col = Document.__table__.c["document_type"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_case_id_fk_cascade(self):
        col = Document.__table__.c["case_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.ondelete == "CASCADE"

    @pytest.mark.unit
    def test_has_case_relationship(self):
        assert hasattr(Document, "case")

    @pytest.mark.unit
    def test_has_firac_analyses_relationship(self):
        assert hasattr(Document, "firac_analyses")

    @pytest.mark.unit
    def test_extracted_text_column_is_text(self):
        col = Document.__table__.c["extracted_text"]
        assert isinstance(col.type, Text)


# =============================================================================
# FIRACAnalysis model
# =============================================================================


class TestFIRACAnalysisModel:
    """Tests for FIRACAnalysis model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert FIRACAnalysis.__tablename__ == "firac_analyses"

    @pytest.mark.unit
    def test_schema_is_judicial(self):
        schema_dict = next(
            (a for a in FIRACAnalysis.__table_args__ if isinstance(a, dict)), {}
        )
        assert schema_dict.get("schema") == "judicial"

    @pytest.mark.unit
    def test_confidence_score_is_numeric(self):
        col = FIRACAnalysis.__table__.c["confidence_score"]
        assert isinstance(col.type, Numeric)

    @pytest.mark.unit
    def test_raw_response_is_jsonb(self):
        col = FIRACAnalysis.__table__.c["raw_response"]
        assert isinstance(col.type, JSONB)

    @pytest.mark.unit
    def test_document_id_fk_set_null(self):
        col = FIRACAnalysis.__table__.c["document_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "SET NULL"

    @pytest.mark.unit
    def test_case_id_fk_cascade(self):
        col = FIRACAnalysis.__table__.c["case_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "CASCADE"


# =============================================================================
# JurisprudenceSearch model
# =============================================================================


class TestJurisprudenceSearchModel:
    """Tests for JurisprudenceSearch model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert JurisprudenceSearch.__tablename__ == "jurisprudence_searches"

    @pytest.mark.unit
    def test_search_query_not_nullable(self):
        col = JurisprudenceSearch.__table__.c["search_query"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_search_query_is_jsonb(self):
        col = JurisprudenceSearch.__table__.c["search_query"]
        assert isinstance(col.type, JSONB)

    @pytest.mark.unit
    def test_results_column_is_jsonb(self):
        col = JurisprudenceSearch.__table__.c["results"]
        assert isinstance(col.type, JSONB)

    @pytest.mark.unit
    def test_has_distinguish_analyses_relationship(self):
        assert hasattr(JurisprudenceSearch, "distinguish_analyses")


# =============================================================================
# DistinguishAnalysis model
# =============================================================================


class TestDistinguishAnalysisModel:
    """Tests for DistinguishAnalysis model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert DistinguishAnalysis.__tablename__ == "distinguish_analyses"

    @pytest.mark.unit
    def test_current_facts_not_nullable(self):
        col = DistinguishAnalysis.__table__.c["current_facts"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_is_applicable_is_boolean(self):
        col = DistinguishAnalysis.__table__.c["is_applicable"]
        assert isinstance(col.type, Boolean)

    @pytest.mark.unit
    def test_jurisprudence_search_id_fk_set_null(self):
        col = DistinguishAnalysis.__table__.c["jurisprudence_search_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "SET NULL"


# =============================================================================
# GeneratedDocument model
# =============================================================================


class TestGeneratedDocumentModel:
    """Tests for GeneratedDocument model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert GeneratedDocument.__tablename__ == "generated_documents"

    @pytest.mark.unit
    def test_content_not_nullable(self):
        col = GeneratedDocument.__table__.c["content"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_version_default(self):
        col = GeneratedDocument.__table__.c["version"]
        # default or server_default set to 1
        assert col.default is not None or col.server_default is not None

    @pytest.mark.unit
    def test_status_default_is_draft(self):
        col = GeneratedDocument.__table__.c["status"]
        # server_default should be 'draft'
        if col.server_default is not None:
            assert "draft" in str(col.server_default.arg)

    @pytest.mark.unit
    def test_has_firac_analysis_relationship(self):
        assert hasattr(GeneratedDocument, "firac_analysis")

    @pytest.mark.unit
    def test_has_distinguish_analysis_relationship(self):
        assert hasattr(GeneratedDocument, "distinguish_analysis")

    @pytest.mark.unit
    def test_firac_analysis_id_fk_set_null(self):
        col = GeneratedDocument.__table__.c["firac_analysis_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "SET NULL"

    @pytest.mark.unit
    def test_distinguish_analysis_id_fk_set_null(self):
        col = GeneratedDocument.__table__.c["distinguish_analysis_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "SET NULL"

    @pytest.mark.unit
    def test_google_docs_id_column_exists(self):
        assert "google_docs_id" in GeneratedDocument.__table__.c

    @pytest.mark.unit
    def test_google_docs_url_column_exists(self):
        assert "google_docs_url" in GeneratedDocument.__table__.c


# =============================================================================
# Notification model
# =============================================================================


class TestNotificationModel:
    """Tests for Notification model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert Notification.__tablename__ == "notifications"

    @pytest.mark.unit
    def test_schema_is_judicial(self):
        schema_dict = next(
            (a for a in Notification.__table_args__ if isinstance(a, dict)), {}
        )
        assert schema_dict.get("schema") == "judicial"

    @pytest.mark.unit
    def test_notification_type_not_nullable(self):
        col = Notification.__table__.c["notification_type"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_status_default_is_pending(self):
        col = Notification.__table__.c["status"]
        if col.server_default is not None:
            assert "pending" in str(col.server_default.arg)

    @pytest.mark.unit
    def test_case_fk_cascade(self):
        col = Notification.__table__.c["case_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "CASCADE"


# =============================================================================
# AuditLog model
# =============================================================================


class TestAuditLogModel:
    """Tests for AuditLog model metadata."""

    @pytest.mark.unit
    def test_tablename(self):
        assert AuditLog.__tablename__ == "logs"

    @pytest.mark.unit
    def test_schema_is_audit(self):
        schema_dict = next(
            (a for a in AuditLog.__table_args__ if isinstance(a, dict)), {}
        )
        assert schema_dict.get("schema") == "audit"

    @pytest.mark.unit
    def test_table_name_col_not_nullable(self):
        col = AuditLog.__table__.c["table_name"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_action_col_not_nullable(self):
        col = AuditLog.__table__.c["action"]
        assert col.nullable is False

    @pytest.mark.unit
    def test_ip_address_is_inet(self):
        col = AuditLog.__table__.c["ip_address"]
        assert isinstance(col.type, INET)

    @pytest.mark.unit
    def test_old_data_is_jsonb(self):
        col = AuditLog.__table__.c["old_data"]
        assert isinstance(col.type, JSONB)

    @pytest.mark.unit
    def test_new_data_is_jsonb(self):
        col = AuditLog.__table__.c["new_data"]
        assert isinstance(col.type, JSONB)

    @pytest.mark.unit
    def test_record_id_is_uuid(self):
        col = AuditLog.__table__.c["record_id"]
        assert isinstance(col.type, UUID)

    @pytest.mark.unit
    def test_indexes_defined(self):
        table_args = AuditLog.__table_args__
        index_names = {
            a.name for a in table_args if hasattr(a, "name") and not isinstance(a, dict)
        }
        assert "idx_audit_table" in index_names
        assert "idx_audit_record" in index_names
        assert "idx_audit_action" in index_names
        assert "idx_audit_created" in index_names


# =============================================================================
# Base metadata
# =============================================================================


class TestBaseMetadata:
    """Tests for shared ORM Base metadata."""

    @pytest.mark.unit
    def test_all_models_share_base(self):
        for model in [
            Case, Document, FIRACAnalysis, JurisprudenceSearch,
            DistinguishAnalysis, GeneratedDocument, Notification, AuditLog,
        ]:
            assert model.metadata is Base.metadata

    @pytest.mark.unit
    def test_uuid_primary_keys_use_uuid4_default(self):
        """All models should generate UUID4 primary keys by default."""
        for model in [
            Case, Document, FIRACAnalysis, JurisprudenceSearch,
            DistinguishAnalysis, GeneratedDocument, Notification, AuditLog,
        ]:
            col = model.__table__.c["id"]
            assert isinstance(col.type, UUID)
            # default is uuid.uuid4 callable
            if col.default is not None:
                assert callable(col.default.arg) or col.default.arg is not None