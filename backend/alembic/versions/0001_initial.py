"""Initial schema migration — creates all tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('owner_id', sa.String(100), nullable=True),
        sa.Column('meta', sa.JSON, nullable=True),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('model', sa.String(200), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('grounding', sa.String(30), nullable=True),
        sa.Column('sources_used', sa.JSON, nullable=True),
        sa.Column('retrieval_meta', sa.JSON, nullable=True),
    )

    op.create_table(
        'sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(1000), nullable=False),
        sa.Column('author', sa.String(500), nullable=True),
        sa.Column('canonical_url', sa.String(2000), nullable=True),
        sa.Column('external_id', sa.String(500), nullable=True, unique=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('word_count', sa.Integer, nullable=True),
        sa.Column('date_published', sa.String(20), nullable=True),
        sa.Column('meta', sa.JSON, nullable=True),
    )

    op.create_table(
        'transcript_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('char_count', sa.Integer, nullable=True),
        sa.Column('token_count', sa.Integer, nullable=True),
        sa.Column('section_heading', sa.String(500), nullable=True),
        sa.Column('speaker', sa.String(200), nullable=True),
        sa.Column('start_char', sa.Integer, nullable=True),
        sa.Column('embedding', sa.LargeBinary, nullable=True),
        sa.Column('embedding_model', sa.String(200), nullable=True),
        sa.Column('meta', sa.JSON, nullable=True),
        sa.UniqueConstraint('source_id', 'chunk_index', name='uq_chunk_source_index'),
    )

    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_format', sa.String(20), nullable=False, default='markdown'),
        sa.Column('source_references', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        sa.Column('meta', sa.JSON, nullable=True),
    )

    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_files', sa.Integer, nullable=True),
        sa.Column('processed_files', sa.Integer, nullable=True),
        sa.Column('failed_files', sa.Integer, nullable=True),
        sa.Column('sources_created', sa.Integer, nullable=True),
        sa.Column('chunks_created', sa.Integer, nullable=True),
        sa.Column('errors', sa.JSON, nullable=True),
        sa.Column('meta', sa.JSON, nullable=True),
    )

    op.create_table(
        'evaluation_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dataset_version', sa.String(50), nullable=True),
        sa.Column('test_case_id', sa.String(100), nullable=True),
        sa.Column('question', sa.Text, nullable=True),
        sa.Column('expected_answer', sa.Text, nullable=True),
        sa.Column('actual_answer', sa.Text, nullable=True),
        sa.Column('recall_at_k', sa.Float, nullable=True),
        sa.Column('citation_correct', sa.Integer, nullable=True),
        sa.Column('answer_relevant', sa.Float, nullable=True),
        sa.Column('abstained', sa.Integer, nullable=True),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('meta', sa.JSON, nullable=True),
    )

    # Indexes for common queries
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('ix_chunks_source_index', 'transcript_chunks', ['source_id', 'chunk_index'])
    op.create_index('ix_sources_type', 'sources', ['source_type'])


def downgrade():
    op.drop_table('evaluation_records')
    op.drop_table('ingestion_jobs')
    op.drop_table('artifacts')
    op.drop_table('transcript_chunks')
    op.drop_table('sources')
    op.drop_table('messages')
    op.drop_table('conversations')
