"""Add trace ID and enhanced audit logging

Revision ID: 002_trace_id_audit_enhancement
Revises: 001_encryption_logging
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '002_trace_id_audit_enhancement'
down_revision = '001_encryption_logging'
branch_labels = None
depends_on = None


def upgrade():
    """Apply the migration - add new fields and enhance audit logging"""
    
    # 1. Add new fields to transactions table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trace_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('source', sa.Enum('manual_entry', 'file_upload', name='transactionsource'), nullable=False, server_default='manual_entry'))
        batch_op.add_column(sa.Column('processing_metadata', sa.Text(), nullable=True))
    
    # Create indexes for new transaction fields
    op.create_index('idx_transactions_trace_id', 'transactions', ['trace_id'], unique=False)
    op.create_index('idx_transactions_source', 'transactions', ['source'], unique=False)
    
    # 2. Enhance audit_logs table with new fields
    # First, add new columns to existing table
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trace_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('entity_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('entity_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('audit_metadata', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ip_address', sa.String(length=45), nullable=True))
        batch_op.add_column(sa.Column('user_agent', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Create indexes for enhanced audit log fields
    op.create_index('idx_audit_logs_trace_id', 'audit_logs', ['trace_id'], unique=False)
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_logs_entity_type', 'audit_logs', ['entity_type'], unique=False)
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    
    # 3. Update existing transaction source values based on transaction_type
    # For PostgreSQL
    if op.get_context().dialect.name == 'postgresql':
        op.execute("""
            UPDATE transactions 
            SET source = CASE 
                WHEN transaction_type = 'pdf_parsed' THEN 'file_upload'::transactionsource
                ELSE 'manual_entry'::transactionsource
            END
        """)
    else:
        # For SQLite
        op.execute("""
            UPDATE transactions 
            SET source = CASE 
                WHEN transaction_type = 'pdf_parsed' THEN 'file_upload'
                ELSE 'manual_entry'
            END
        """)
    
    # 4. Populate created_at field with timestamp values for existing records
    op.execute("UPDATE audit_logs SET created_at = timestamp WHERE created_at IS NULL")


def downgrade():
    """Rollback the migration - remove new fields with safe index handling"""
    
    # Get database connection to check existing indexes
    conn = op.get_bind()
    
    # Drop indexes with existence check - handle gracefully if they don't exist
    indexes_to_drop = [
        ('idx_audit_logs_created_at', 'audit_logs'),
        ('idx_audit_logs_entity_type', 'audit_logs'), 
        ('idx_audit_logs_user_id', 'audit_logs'),
        ('idx_audit_logs_trace_id', 'audit_logs'),
        ('idx_transactions_source', 'transactions'),
        ('idx_transactions_trace_id', 'transactions')
    ]
    
    for index_name, table_name in indexes_to_drop:
        try:
            # Check if index exists before trying to drop it
            result = conn.execute(sa.text(f"""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = '{table_name}' AND indexname = '{index_name}'
            """))
            
            if result.fetchone():
                op.drop_index(index_name, table_name=table_name)
                print(f"Dropped index: {index_name}")
            else:
                print(f"Index {index_name} does not exist, skipping")
        except Exception as e:
            print(f"Warning: Could not drop index {index_name}: {e}")
            # Continue with other indexes even if one fails
            pass
    
    # Remove new columns from audit_logs table
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        # Check if columns exist before dropping them
        try:
            batch_op.drop_column('created_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('user_agent')
        except Exception:
            pass
        try:
            batch_op.drop_column('ip_address')
        except Exception:
            pass
        try:
            batch_op.drop_column('audit_metadata')
        except Exception:
            pass
        try:
            batch_op.drop_column('entity_id')
        except Exception:
            pass
        try:
            batch_op.drop_column('entity_type')
        except Exception:
            pass
        try:
            batch_op.drop_column('user_id')
        except Exception:
            pass
        try:
            batch_op.drop_column('trace_id')
        except Exception:
            pass
    
    # Remove new columns from transactions table
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        try:
            batch_op.drop_column('processing_metadata')
        except Exception:
            pass
        try:
            batch_op.drop_column('source')
        except Exception:
            pass
        try:
            batch_op.drop_column('trace_id')
        except Exception:
            pass
    
    # Drop the enum type if using PostgreSQL
    if op.get_context().dialect.name == 'postgresql':
        try:
            op.execute("DROP TYPE IF EXISTS transactionsource")
        except Exception:
            pass 