"""Fix audit_logs schema inconsistencies

Revision ID: f00293a22f41
Revises: 002_trace_id_audit_enhancement
Create Date: 2025-06-22 16:28:09.358539

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f00293a22f41'
down_revision = '002_trace_id_audit_enhancement'
branch_labels = None
depends_on = None


def upgrade():
    """Fix schema inconsistencies between database and models"""
    
    # Get database connection to check existing schema
    conn = op.get_bind()
    
    # Check if audit_logs.user_id column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'user_id'
    """))
    
    user_id_exists = result.fetchone() is not None
    
    if not user_id_exists:
        # Add missing user_id column (this was supposed to be added in migration 002 but seems missing)
        op.add_column('audit_logs', sa.Column('user_id', sa.String(36), nullable=True))
        print("Added missing user_id column to audit_logs")
    
    # Check if audit_logs.entity_type column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'entity_type'
    """))
    
    entity_type_exists = result.fetchone() is not None
    
    if not entity_type_exists:
        # Add missing entity_type column
        op.add_column('audit_logs', sa.Column('entity_type', sa.String(50), nullable=True))
        print("Added missing entity_type column to audit_logs")
    
    # Check if audit_logs.entity_id column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'entity_id'
    """))
    
    entity_id_exists = result.fetchone() is not None
    
    if not entity_id_exists:
        # Add missing entity_id column
        op.add_column('audit_logs', sa.Column('entity_id', sa.String(36), nullable=True))
        print("Added missing entity_id column to audit_logs")
    
    # Check if audit_logs.audit_metadata column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'audit_metadata'
    """))
    
    audit_metadata_exists = result.fetchone() is not None
    
    if not audit_metadata_exists:
        # Add missing audit_metadata column
        op.add_column('audit_logs', sa.Column('audit_metadata', sa.Text(), nullable=True))
        print("Added missing audit_metadata column to audit_logs")
    
    # Check if audit_logs.ip_address column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'ip_address'
    """))
    
    ip_address_exists = result.fetchone() is not None
    
    if not ip_address_exists:
        # Add missing ip_address column
        op.add_column('audit_logs', sa.Column('ip_address', sa.String(45), nullable=True))
        print("Added missing ip_address column to audit_logs")
    
    # Check if audit_logs.user_agent column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'user_agent'
    """))
    
    user_agent_exists = result.fetchone() is not None
    
    if not user_agent_exists:
        # Add missing user_agent column
        op.add_column('audit_logs', sa.Column('user_agent', sa.String(500), nullable=True))
        print("Added missing user_agent column to audit_logs")
    
    # Check if audit_logs.created_at column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'created_at'
    """))
    
    created_at_exists = result.fetchone() is not None
    
    if not created_at_exists:
        # Add missing created_at column
        op.add_column('audit_logs', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')))
        print("Added missing created_at column to audit_logs")
    
    # Now add missing indexes (check if they exist first)
    indexes_to_create = [
        ('idx_audit_logs_user_id', 'audit_logs', ['user_id']),
        ('idx_audit_logs_entity_type', 'audit_logs', ['entity_type']),
        ('idx_audit_logs_created_at', 'audit_logs', ['created_at']),
        ('idx_audit_logs_trace_id', 'audit_logs', ['trace_id']),
        ('idx_transactions_trace_id', 'transactions', ['trace_id']),
        ('idx_transactions_source', 'transactions', ['source'])
    ]
    
    for index_name, table_name, columns in indexes_to_create:
        # Check if index exists
        result = conn.execute(sa.text(f"""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = '{table_name}' AND indexname = '{index_name}'
        """))
        
        index_exists = result.fetchone() is not None
        
        if not index_exists:
            try:
                op.create_index(index_name, table_name, columns, unique=False)
                print(f"Created missing index: {index_name}")
            except Exception as e:
                print(f"Warning: Could not create index {index_name}: {e}")
    
    # Populate created_at field with timestamp values for existing records where it's null
    conn.execute(sa.text("UPDATE audit_logs SET created_at = timestamp WHERE created_at IS NULL"))
    print("Populated created_at field from timestamp for existing records")


def downgrade():
    """Remove the columns and indexes added in this migration"""
    
    # Note: We only remove what this migration added, not what should have been there
    # This is a conservative approach to avoid breaking existing functionality
    
    # Drop indexes that this migration created
    indexes_to_drop = [
        'idx_audit_logs_user_id',
        'idx_audit_logs_entity_type', 
        'idx_audit_logs_created_at',
        'idx_audit_logs_trace_id',
        'idx_transactions_trace_id',
        'idx_transactions_source'
    ]
    
    conn = op.get_bind()
    
    for index_name in indexes_to_drop:
        try:
            result = conn.execute(sa.text(f"""
                SELECT indexname FROM pg_indexes 
                WHERE indexname = '{index_name}'
            """))
            
            if result.fetchone():
                op.drop_index(index_name)
                print(f"Dropped index: {index_name}")
        except Exception as e:
            print(f"Warning: Could not drop index {index_name}: {e}")
    
    # Note: We don't drop columns in downgrade as they might contain data
    # and other migrations depend on them. This is a data-safe approach.
    print("Schema fix migration downgrade completed (columns preserved for data safety)") 