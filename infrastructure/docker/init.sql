-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema for organizing tables
CREATE SCHEMA IF NOT EXISTS canadaca;

-- Documents table (source content)
CREATE TABLE canadaca.documents (
    id VARCHAR PRIMARY KEY,
    url VARCHAR UNIQUE NOT NULL,
    title VARCHAR,
    content TEXT,
    content_hash VARCHAR,
    language VARCHAR(2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document chunks with vector embeddings
CREATE TABLE canadaca.document_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR REFERENCES canadaca.documents(id) ON DELETE CASCADE,
    content TEXT,
    embedding vector(1024),  -- amazon.titan-embed-text-v2:0 dimension
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions
CREATE TABLE canadaca.chat_sessions (
    id VARCHAR PRIMARY KEY,
    language VARCHAR(2) DEFAULT 'en',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages
CREATE TABLE canadaca.chat_messages (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES canadaca.chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_documents_url ON canadaca.documents(url);
CREATE INDEX idx_documents_language ON canadaca.documents(language);
CREATE INDEX idx_document_chunks_document_id ON canadaca.document_chunks(document_id);
CREATE INDEX idx_chat_messages_session_id ON canadaca.chat_messages(session_id);

-- Create HNSW index for fast vector similarity search
CREATE INDEX idx_document_chunks_embedding ON canadaca.document_chunks 
USING hnsw (embedding vector_cosine_ops);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for documents table
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON canadaca.documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for sessions last_activity
CREATE TRIGGER update_sessions_last_activity
    BEFORE UPDATE ON canadaca.chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
