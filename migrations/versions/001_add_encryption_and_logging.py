"""Add encryption support and logging tables

Revision ID: 001_encryption_logging
Revises: 
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_encryption_logging'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Apply the migration - add new tables and columns"""
    
    # Add encryption fields to transactions table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('encrypted_description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('encrypted_amount', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('encryption_key_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('is_encrypted', sa.Boolean(), nullable=True, default=False))

    # Create chat_sessions table
    op.create_table('chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_sessions
    op.create_index('idx_chat_sessions_timestamp', 'chat_sessions', ['timestamp'], unique=False)
    op.create_index('idx_chat_sessions_session_id', 'chat_sessions', ['session_id'], unique=False)
    op.create_index('idx_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('user_id_hash', sa.String(length=64), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent_hash', sa.String(length=64), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit_logs
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_logs_user_id_hash', 'audit_logs', ['user_id_hash'], unique=False)

    # Create llm_processing_logs table
    op.create_table('llm_processing_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('processing_type', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('endpoint_url', sa.String(length=200), nullable=True),
        sa.Column('request_size_bytes', sa.Integer(), nullable=True),
        sa.Column('response_size_bytes', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for llm_processing_logs
    op.create_index('idx_llm_logs_processing_type', 'llm_processing_logs', ['processing_type'], unique=False)
    op.create_index('idx_llm_logs_success', 'llm_processing_logs', ['success'], unique=False)
    op.create_index('idx_llm_logs_timestamp', 'llm_processing_logs', ['timestamp'], unique=False)


def downgrade():
    """Rollback the migration - remove new tables and columns"""
    
    # Drop indexes first
    op.drop_index('idx_llm_logs_timestamp', table_name='llm_processing_logs')
    op.drop_index('idx_llm_logs_success', table_name='llm_processing_logs')
    op.drop_index('idx_llm_logs_processing_type', table_name='llm_processing_logs')
    
    op.drop_index('idx_audit_logs_user_id_hash', table_name='audit_logs')
    op.drop_index('idx_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    
    op.drop_index('idx_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('idx_chat_sessions_session_id', table_name='chat_sessions')
    op.drop_index('idx_chat_sessions_timestamp', table_name='chat_sessions')
    
    # Drop tables
    op.drop_table('llm_processing_logs')
    op.drop_table('audit_logs')
    op.drop_table('chat_sessions')
    
    # Remove encryption columns from transactions table
    # Note: SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('is_encrypted')
        batch_op.drop_column('encryption_key_id')
        batch_op.drop_column('encrypted_amount')
        batch_op.drop_column('encrypted_description') 