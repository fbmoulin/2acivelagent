"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2024-12-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS judicial")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE judicial.case_status AS ENUM (
                'pending', 'processing', 'completed', 'error', 'archived'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE judicial.document_type AS ENUM (
                'sentenca', 'despacho', 'decisao', 'acordao', 'peticao', 'parecer'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create cases table
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_number', sa.String(50), nullable=False),
        sa.Column('tribunal', sa.String(20), nullable=False),
        sa.Column('court', sa.String(100), nullable=True),
        sa.Column('class_code', sa.Integer(), nullable=True),
        sa.Column('class_name', sa.String(255), nullable=True),
        sa.Column('subject_codes', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'processing', 'completed', 'error', 'archived',
                                            name='case_status', schema='judicial', create_type=False),
                  server_default='pending', nullable=True),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number'),
        schema='judicial'
    )
    op.create_index('idx_cases_number', 'cases', ['case_number'], schema='judicial')
    op.create_index('idx_cases_tribunal', 'cases', ['tribunal'], schema='judicial')
    op.create_index('idx_cases_status', 'cases', ['status'], schema='judicial')
    op.create_index('idx_cases_created', 'cases', ['created_at'], schema='judicial')

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_documents_case', 'documents', ['case_id'], schema='judicial')
    op.create_index('idx_documents_type', 'documents', ['document_type'], schema='judicial')

    # Create firac_analyses table
    op.create_table(
        'firac_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('facts', sa.Text(), nullable=True),
        sa.Column('issues', sa.Text(), nullable=True),
        sa.Column('rules', sa.Text(), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('conclusion', sa.Text(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['judicial.documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_firac_case', 'firac_analyses', ['case_id'], schema='judicial')

    # Create jurisprudence_searches table
    op.create_table(
        'jurisprudence_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('search_query', postgresql.JSONB(), nullable=False),
        sa.Column('tribunal', sa.String(20), nullable=True),
        sa.Column('total_results', sa.Integer(), nullable=True),
        sa.Column('results', postgresql.JSONB(), nullable=True),
        sa.Column('search_duration_ms', sa.Integer(), nullable=True),
        sa.Column('searched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_jurisprudence_case', 'jurisprudence_searches', ['case_id'], schema='judicial')
    op.create_index('idx_jurisprudence_tribunal', 'jurisprudence_searches', ['tribunal'], schema='judicial')

    # Create distinguish_analyses table
    op.create_table(
        'distinguish_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('jurisprudence_search_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('current_facts', sa.Text(), nullable=False),
        sa.Column('precedent_data', postgresql.JSONB(), nullable=True),
        sa.Column('is_applicable', sa.Boolean(), nullable=True),
        sa.Column('similarities', sa.Text(), nullable=True),
        sa.Column('differences', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['jurisprudence_search_id'], ['judicial.jurisprudence_searches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_distinguish_case', 'distinguish_analyses', ['case_id'], schema='judicial')

    # Create generated_documents table
    op.create_table(
        'generated_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('firac_analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('distinguish_analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_type', postgresql.ENUM('sentenca', 'despacho', 'decisao', 'acordao', 'peticao', 'parecer',
                                                   name='document_type', schema='judicial', create_type=False),
                  nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('google_docs_id', sa.String(255), nullable=True),
        sa.Column('google_docs_url', sa.String(500), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
        sa.Column('status', sa.String(50), server_default='draft', nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['firac_analysis_id'], ['judicial.firac_analyses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['distinguish_analysis_id'], ['judicial.distinguish_analyses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_generated_case', 'generated_documents', ['case_id'], schema='judicial')
    op.create_index('idx_generated_type', 'generated_documents', ['document_type'], schema='judicial')
    op.create_index('idx_generated_status', 'generated_documents', ['status'], schema='judicial')

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), server_default='pending', nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['judicial.cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='judicial'
    )
    op.create_index('idx_notifications_case', 'notifications', ['case_id'], schema='judicial')
    op.create_index('idx_notifications_status', 'notifications', ['status'], schema='judicial')

    # Create audit logs table
    op.create_table(
        'logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('old_data', postgresql.JSONB(), nullable=True),
        sa.Column('new_data', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    op.create_index('idx_audit_table', 'logs', ['table_name'], schema='audit')
    op.create_index('idx_audit_record', 'logs', ['record_id'], schema='audit')
    op.create_index('idx_audit_action', 'logs', ['action'], schema='audit')
    op.create_index('idx_audit_created', 'logs', ['created_at'], schema='audit')

    # Create update timestamp trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply update triggers
    op.execute("""
        CREATE TRIGGER update_cases_updated_at
            BEFORE UPDATE ON judicial.cases
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_generated_documents_updated_at
            BEFORE UPDATE ON judicial.generated_documents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove all database objects."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_generated_documents_updated_at ON judicial.generated_documents")
    op.execute("DROP TRIGGER IF EXISTS update_cases_updated_at ON judicial.cases")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('logs', schema='audit')
    op.drop_table('notifications', schema='judicial')
    op.drop_table('generated_documents', schema='judicial')
    op.drop_table('distinguish_analyses', schema='judicial')
    op.drop_table('jurisprudence_searches', schema='judicial')
    op.drop_table('firac_analyses', schema='judicial')
    op.drop_table('documents', schema='judicial')
    op.drop_table('cases', schema='judicial')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS judicial.document_type")
    op.execute("DROP TYPE IF EXISTS judicial.case_status")

    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE")
    op.execute("DROP SCHEMA IF EXISTS judicial CASCADE")
