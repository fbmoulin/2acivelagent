-- Sistema de Automacao Juridica - Database Initialization
-- PostgreSQL 15

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS judicial;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO judicial, public;

-- =====================================================
-- MAIN TABLES
-- =====================================================

-- Cases table
CREATE TABLE IF NOT EXISTS judicial.cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number VARCHAR(50) NOT NULL UNIQUE,
    tribunal VARCHAR(20) NOT NULL,
    court VARCHAR(100),
    class_code INTEGER,
    class_name VARCHAR(255),
    subject_codes INTEGER[],
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for case search
CREATE INDEX IF NOT EXISTS idx_cases_number ON judicial.cases(case_number);
CREATE INDEX IF NOT EXISTS idx_cases_tribunal ON judicial.cases(tribunal);
CREATE INDEX IF NOT EXISTS idx_cases_status ON judicial.cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created ON judicial.cases(created_at);

-- Documents table
CREATE TABLE IF NOT EXISTS judicial.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),
    extracted_text TEXT,
    page_count INTEGER,
    checksum VARCHAR(64),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for document search
CREATE INDEX IF NOT EXISTS idx_documents_case ON judicial.documents(case_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON judicial.documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_text_gin ON judicial.documents USING gin(to_tsvector('portuguese', extracted_text));

-- FIRAC Analysis table
CREATE TABLE IF NOT EXISTS judicial.firac_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    document_id UUID REFERENCES judicial.documents(id) ON DELETE SET NULL,
    facts TEXT,
    issues TEXT,
    rules TEXT,
    analysis TEXT,
    conclusion TEXT,
    raw_response JSONB,
    model_used VARCHAR(50),
    tokens_used INTEGER,
    confidence_score DECIMAL(3,2),
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_firac_case ON judicial.firac_analyses(case_id);

-- Jurisprudence Search Results table
CREATE TABLE IF NOT EXISTS judicial.jurisprudence_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    search_query JSONB NOT NULL,
    tribunal VARCHAR(20),
    total_results INTEGER,
    results JSONB,
    search_duration_ms INTEGER,
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jurisprudence_case ON judicial.jurisprudence_searches(case_id);
CREATE INDEX IF NOT EXISTS idx_jurisprudence_tribunal ON judicial.jurisprudence_searches(tribunal);

-- Distinguish Analysis table
CREATE TABLE IF NOT EXISTS judicial.distinguish_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    jurisprudence_search_id UUID REFERENCES judicial.jurisprudence_searches(id) ON DELETE SET NULL,
    current_facts TEXT NOT NULL,
    precedent_data JSONB,
    is_applicable BOOLEAN,
    similarities TEXT,
    differences TEXT,
    recommendation TEXT,
    raw_response JSONB,
    confidence_score DECIMAL(3,2),
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_distinguish_case ON judicial.distinguish_analyses(case_id);

-- Generated Documents table
CREATE TABLE IF NOT EXISTS judicial.generated_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    firac_analysis_id UUID REFERENCES judicial.firac_analyses(id) ON DELETE SET NULL,
    distinguish_analysis_id UUID REFERENCES judicial.distinguish_analyses(id) ON DELETE SET NULL,
    document_type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    google_docs_id VARCHAR(255),
    google_docs_url VARCHAR(500),
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_case ON judicial.generated_documents(case_id);
CREATE INDEX IF NOT EXISTS idx_generated_type ON judicial.generated_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_generated_status ON judicial.generated_documents(status);

-- Notifications table
CREATE TABLE IF NOT EXISTS judicial.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES judicial.cases(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255),
    subject VARCHAR(255),
    message TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_case ON judicial.notifications(case_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON judicial.notifications(status);

-- =====================================================
-- AUDIT TABLES
-- =====================================================

-- Audit log table
CREATE TABLE IF NOT EXISTS audit.logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID,
    action VARCHAR(20) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_table ON audit.logs(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_record ON audit.logs(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit.logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit.logs(created_at);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to relevant tables
CREATE TRIGGER update_cases_updated_at
    BEFORE UPDATE ON judicial.cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_generated_documents_updated_at
    BEFORE UPDATE ON judicial.generated_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Audit logging function
CREATE OR REPLACE FUNCTION audit.log_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit.logs (table_name, record_id, action, new_data)
        VALUES (TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, NEW.id, 'INSERT', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.logs (table_name, record_id, action, old_data, new_data)
        VALUES (TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, NEW.id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit.logs (table_name, record_id, action, old_data)
        VALUES (TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, OLD.id, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers
CREATE TRIGGER audit_cases
    AFTER INSERT OR UPDATE OR DELETE ON judicial.cases
    FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

CREATE TRIGGER audit_documents
    AFTER INSERT OR UPDATE OR DELETE ON judicial.documents
    FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

CREATE TRIGGER audit_generated_documents
    AFTER INSERT OR UPDATE OR DELETE ON judicial.generated_documents
    FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

-- =====================================================
-- VIEWS
-- =====================================================

-- Case summary view
CREATE OR REPLACE VIEW judicial.case_summary AS
SELECT
    c.id,
    c.case_number,
    c.tribunal,
    c.court,
    c.class_name,
    c.status,
    c.priority,
    c.received_at,
    c.processed_at,
    COUNT(DISTINCT d.id) AS document_count,
    COUNT(DISTINCT f.id) AS firac_analysis_count,
    COUNT(DISTINCT g.id) AS generated_document_count,
    MAX(g.generated_at) AS last_document_generated
FROM judicial.cases c
LEFT JOIN judicial.documents d ON d.case_id = c.id
LEFT JOIN judicial.firac_analyses f ON f.case_id = c.id
LEFT JOIN judicial.generated_documents g ON g.case_id = c.id
GROUP BY c.id;

-- Processing statistics view
CREATE OR REPLACE VIEW judicial.processing_stats AS
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS total_cases,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_cases,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending_cases,
    COUNT(CASE WHEN status = 'error' THEN 1 END) AS error_cases,
    AVG(EXTRACT(EPOCH FROM (processed_at - received_at))) AS avg_processing_seconds
FROM judicial.cases
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert common document types
CREATE TABLE IF NOT EXISTS judicial.document_types (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

INSERT INTO judicial.document_types (code, name, description) VALUES
    ('sentenca', 'Sentenca', 'Decisao judicial que resolve o merito da causa'),
    ('despacho', 'Despacho', 'Ato judicial de mero expediente'),
    ('decisao', 'Decisao Interlocutoria', 'Decisao que resolve questao incidente'),
    ('acordao', 'Acordao', 'Decisao colegiada de tribunal'),
    ('peticao', 'Peticao', 'Documento da parte'),
    ('parecer', 'Parecer', 'Opiniao tecnica do Ministerio Publico')
ON CONFLICT (code) DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA judicial TO n8n_user;
GRANT USAGE ON SCHEMA audit TO n8n_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA judicial TO n8n_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO n8n_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA judicial TO n8n_user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'Schemas created: judicial, audit';
    RAISE NOTICE 'Tables created: cases, documents, firac_analyses, jurisprudence_searches, distinguish_analyses, generated_documents, notifications';
END $$;
