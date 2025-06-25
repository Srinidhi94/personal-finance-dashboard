"""Fix audit_logs id column type

Revision ID: fbf53e4bf5a6
Revises: f00293a22f41
Create Date: 2025-06-22 16:29:55.858444

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fbf53e4bf5a6'
down_revision = 'f00293a22f41'
branch_labels = None
depends_on = None


def upgrade():
    """Fix audit_logs id column type from integer to varchar for UUID support"""
    
    # PostgreSQL requires special handling for primary key column type changes
    # We need to recreate the table with the correct column types
    
    conn = op.get_bind()
    
    # First, check if we have any data to preserve
    result = conn.execute(sa.text("SELECT COUNT(*) FROM audit_logs"))
    row_count = result.fetchone()[0]
    
    print(f"Found {row_count} existing audit log records")
    
    if row_count > 0:
        # Create backup table with existing data
        print("Creating backup of existing audit_logs data...")
        conn.execute(sa.text("""
            CREATE TABLE audit_logs_backup AS 
            SELECT * FROM audit_logs
        """))
    
    # Drop the existing table (this will also drop all constraints and indexes)
    print("Dropping existing audit_logs table...")
    op.drop_table('audit_logs')
    
    # Recreate the table with correct column types
    print("Creating new audit_logs table with correct column types...")
    op.create_table('audit_logs',
        # New UUID-based primary key
        sa.Column('id', sa.String(36), nullable=False),
        
        # Enhanced audit fields
        sa.Column('trace_id', sa.String(100), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.String(36), nullable=True),
        sa.Column('audit_metadata', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Legacy fields for backward compatibility
        sa.Column('user_id_hash', sa.String(64), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate indexes
    print("Creating indexes...")
    op.create_index('idx_audit_logs_trace_id', 'audit_logs', ['trace_id'], unique=False)
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_logs_entity_type', 'audit_logs', ['entity_type'], unique=False)
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_logs_user_id_hash', 'audit_logs', ['user_id_hash'], unique=False)
    
    # Restore data if we had any
    if row_count > 0:
        print("Restoring audit_logs data with new UUID IDs...")
        
        # Import uuid for generating new IDs
        import uuid
        
        # Get all backup data
        result = conn.execute(sa.text("SELECT * FROM audit_logs_backup ORDER BY timestamp"))
        backup_data = result.fetchall()
        
        # Get column names from backup table
        result = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'audit_logs_backup' 
            ORDER BY ordinal_position
        """))
        backup_columns = [row[0] for row in result.fetchall()]
        
        # Insert data with new UUID IDs
        for row in backup_data:
            old_data = dict(zip(backup_columns, row))
            new_id = str(uuid.uuid4())
            
            # Map old data to new structure
            insert_data = {
                'id': new_id,
                'trace_id': old_data.get('trace_id'),
                'user_id': old_data.get('user_id'),
                'action': old_data.get('action'),
                'entity_type': old_data.get('entity_type'),
                'entity_id': old_data.get('entity_id'),
                'audit_metadata': old_data.get('audit_metadata'),
                'ip_address': old_data.get('ip_address'),
                'user_agent': old_data.get('user_agent'),
                'created_at': old_data.get('created_at') or old_data.get('timestamp'),
                'user_id_hash': old_data.get('user_id_hash'),
                'timestamp': old_data.get('timestamp'),
                'details': old_data.get('details'),
                'ip_address_hash': old_data.get('ip_address_hash'),
                'user_agent_hash': old_data.get('user_agent_hash'),
                'resource_type': old_data.get('resource_type'),
                'resource_id': old_data.get('resource_id'),
                'success': old_data.get('success', True),
                'error_message': old_data.get('error_message')
            }
            
            # Build insert statement
            columns = ', '.join(insert_data.keys())
            placeholders = ', '.join([f':{k}' for k in insert_data.keys()])
            
            conn.execute(sa.text(f"""
                INSERT INTO audit_logs ({columns}) 
                VALUES ({placeholders})
            """), insert_data)
        
        print(f"Restored {len(backup_data)} audit log records with new UUID IDs")
        
        # Drop backup table
        conn.execute(sa.text("DROP TABLE audit_logs_backup"))
        print("Cleaned up backup table")
    
    print("audit_logs table recreation completed successfully")


def downgrade():
    """Revert audit_logs id column type back to integer"""
    
    # This is a complex downgrade since we're changing primary key types
    # For safety, we'll preserve the data but note that UUIDs will be lost
    
    conn = op.get_bind()
    
    # Check if we have data to preserve
    result = conn.execute(sa.text("SELECT COUNT(*) FROM audit_logs"))
    row_count = result.fetchone()[0]
    
    if row_count > 0:
        # Create backup
        conn.execute(sa.text("""
            CREATE TABLE audit_logs_downgrade_backup AS 
            SELECT * FROM audit_logs
        """))
    
    # Drop current table
    op.drop_table('audit_logs')
    
    # Recreate with original integer ID structure
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('user_id_hash', sa.String(64), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_hash', sa.String(64), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Recreate basic indexes
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_logs_user_id_hash', 'audit_logs', ['user_id_hash'], unique=False)
    
    # Restore basic data if we had any (UUID fields will be lost)
    if row_count > 0:
        result = conn.execute(sa.text("SELECT * FROM audit_logs_downgrade_backup ORDER BY timestamp"))
        backup_data = result.fetchall()
        
        for i, row in enumerate(backup_data, 1):
            old_data = dict(zip([
                'id', 'trace_id', 'user_id', 'action', 'entity_type', 'entity_id',
                'audit_metadata', 'ip_address', 'user_agent', 'created_at',
                'user_id_hash', 'timestamp', 'details', 'ip_address_hash',
                'user_agent_hash', 'resource_type', 'resource_id', 'success', 'error_message'
            ], row))
            
            # Insert with new integer ID
            conn.execute(sa.text("""
                INSERT INTO audit_logs (
                    id, action, user_id_hash, timestamp, details, 
                    ip_address_hash, user_agent_hash, resource_type, 
                    resource_id, success, error_message
                ) VALUES (
                    :id, :action, :user_id_hash, :timestamp, :details,
                    :ip_address_hash, :user_agent_hash, :resource_type,
                    :resource_id, :success, :error_message
                )
            """), {
                'id': i,
                'action': old_data.get('action'),
                'user_id_hash': old_data.get('user_id_hash'),
                'timestamp': old_data.get('timestamp'),
                'details': old_data.get('details'),
                'ip_address_hash': old_data.get('ip_address_hash'),
                'user_agent_hash': old_data.get('user_agent_hash'),
                'resource_type': old_data.get('resource_type'),
                'resource_id': old_data.get('resource_id'),
                'success': old_data.get('success', True),
                'error_message': old_data.get('error_message')
            })
        
        # Drop backup
        conn.execute(sa.text("DROP TABLE audit_logs_downgrade_backup"))
    
    print("Downgrade completed - UUID data has been lost, reverted to integer IDs") 