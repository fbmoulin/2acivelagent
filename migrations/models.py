"""
Sistema de Automacao Juridica - SQLAlchemy Models

Database models for ORM and migration support.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, DateTime,
    ForeignKey, JSON, ARRAY, BigInteger, Index,
    Numeric, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()


class CaseStatus(enum.Enum):
    """Case processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    ARCHIVED = "archived"


class DocumentType(enum.Enum):
    """Legal document types"""
    SENTENCA = "sentenca"
    DESPACHO = "despacho"
    DECISAO = "decisao"
    ACORDAO = "acordao"
    PETICAO = "peticao"
    PARECER = "parecer"


class Case(Base):
    """Judicial case model"""
    __tablename__ = "cases"
    __table_args__ = (
        Index("idx_cases_number", "case_number"),
        Index("idx_cases_tribunal", "tribunal"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_created", "created_at"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(50), nullable=False, unique=True)
    tribunal = Column(String(20), nullable=False)
    court = Column(String(100))
    class_code = Column(Integer)
    class_name = Column(String(255))
    subject_codes = Column(ARRAY(Integer))
    status = Column(
        SQLEnum(CaseStatus, name="case_status", schema="judicial"),
        default=CaseStatus.PENDING
    )
    priority = Column(Integer, default=0)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    firac_analyses = relationship("FIRACAnalysis", back_populates="case", cascade="all, delete-orphan")
    jurisprudence_searches = relationship("JurisprudenceSearch", back_populates="case", cascade="all, delete-orphan")
    distinguish_analyses = relationship("DistinguishAnalysis", back_populates="case", cascade="all, delete-orphan")
    generated_documents = relationship("GeneratedDocument", back_populates="case", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded document model"""
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_case", "case_id"),
        Index("idx_documents_type", "document_type"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    document_type = Column(String(50), nullable=False)
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    extracted_text = Column(Text)
    page_count = Column(Integer)
    checksum = Column(String(64))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="documents")
    firac_analyses = relationship("FIRACAnalysis", back_populates="document")


class FIRACAnalysis(Base):
    """FIRAC analysis model"""
    __tablename__ = "firac_analyses"
    __table_args__ = (
        Index("idx_firac_case", "case_id"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("judicial.documents.id", ondelete="SET NULL"))
    facts = Column(Text)
    issues = Column(Text)
    rules = Column(Text)
    analysis = Column(Text)
    conclusion = Column(Text)
    raw_response = Column(JSONB)
    model_used = Column(String(50))
    tokens_used = Column(Integer)
    confidence_score = Column(Numeric(3, 2))
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="firac_analyses")
    document = relationship("Document", back_populates="firac_analyses")
    generated_documents = relationship("GeneratedDocument", back_populates="firac_analysis")


class JurisprudenceSearch(Base):
    """Jurisprudence search results model"""
    __tablename__ = "jurisprudence_searches"
    __table_args__ = (
        Index("idx_jurisprudence_case", "case_id"),
        Index("idx_jurisprudence_tribunal", "tribunal"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    search_query = Column(JSONB, nullable=False)
    tribunal = Column(String(20))
    total_results = Column(Integer)
    results = Column(JSONB)
    search_duration_ms = Column(Integer)
    searched_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="jurisprudence_searches")
    distinguish_analyses = relationship("DistinguishAnalysis", back_populates="jurisprudence_search")


class DistinguishAnalysis(Base):
    """Distinguish analysis model"""
    __tablename__ = "distinguish_analyses"
    __table_args__ = (
        Index("idx_distinguish_case", "case_id"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    jurisprudence_search_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judicial.jurisprudence_searches.id", ondelete="SET NULL")
    )
    current_facts = Column(Text, nullable=False)
    precedent_data = Column(JSONB)
    is_applicable = Column(Boolean)
    similarities = Column(Text)
    differences = Column(Text)
    recommendation = Column(Text)
    raw_response = Column(JSONB)
    confidence_score = Column(Numeric(3, 2))
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="distinguish_analyses")
    jurisprudence_search = relationship("JurisprudenceSearch", back_populates="distinguish_analyses")
    generated_documents = relationship("GeneratedDocument", back_populates="distinguish_analysis")


class GeneratedDocument(Base):
    """Generated legal document model"""
    __tablename__ = "generated_documents"
    __table_args__ = (
        Index("idx_generated_case", "case_id"),
        Index("idx_generated_type", "document_type"),
        Index("idx_generated_status", "status"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    firac_analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judicial.firac_analyses.id", ondelete="SET NULL")
    )
    distinguish_analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judicial.distinguish_analyses.id", ondelete="SET NULL")
    )
    document_type = Column(
        SQLEnum(DocumentType, name="document_type", schema="judicial"),
        nullable=False
    )
    title = Column(String(255))
    content = Column(Text, nullable=False)
    google_docs_id = Column(String(255))
    google_docs_url = Column(String(500))
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="generated_documents")
    firac_analysis = relationship("FIRACAnalysis", back_populates="generated_documents")
    distinguish_analysis = relationship("DistinguishAnalysis", back_populates="generated_documents")


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_case", "case_id"),
        Index("idx_notifications_status", "status"),
        {"schema": "judicial"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("judicial.cases.id", ondelete="CASCADE"))
    notification_type = Column(String(50), nullable=False)
    recipient_email = Column(String(255))
    subject = Column(String(255))
    message = Column(Text)
    status = Column(String(50), default="pending")
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="notifications")


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "logs"
    __table_args__ = (
        Index("idx_audit_table", "table_name"),
        Index("idx_audit_record", "record_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
        {"schema": "audit"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True))
    action = Column(String(20), nullable=False)
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    user_id = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
