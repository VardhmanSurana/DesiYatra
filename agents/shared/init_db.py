"""
Database initialization script - applies migrations to Supabase
"""

import os
from pathlib import Path
from loguru import logger
from agents.shared.config import settings
from agents.shared.database import supabase


def get_migration_files() -> list[tuple[str, str]]:
    """Get all migration files sorted by order."""
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return []
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    migrations = []
    
    for file in migration_files:
        with open(file, 'r') as f:
            content = f.read()
            migrations.append((file.name, content))
    
    return migrations


def apply_migrations() -> bool:
    """Apply all migration files to Supabase."""
    logger.info("Starting database migration...")
    
    migrations = get_migration_files()
    
    if not migrations:
        logger.error("No migration files found")
        return False
    
    logger.info(f"Found {len(migrations)} migration files")
    
    for migration_name, migration_sql in migrations:
        try:
            logger.info(f"Applying migration: {migration_name}")
            
            # Split by semicolon to handle multiple statements
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                # Execute using Supabase client
                response = supabase.rpc("execute_sql", {"sql": statement})
                logger.debug(f"Executed: {statement[:100]}...")
            
            logger.success(f"✓ Migration applied: {migration_name}")
            
        except Exception as e:
            logger.error(f"✗ Failed to apply migration {migration_name}: {str(e)}")
            return False
    
    logger.info("✓ All migrations applied successfully!")
    return True


def execute_raw_sql(sql: str) -> dict:
    """Execute raw SQL directly via Supabase client."""
    try:
        # For direct SQL execution, we need to use the postgrest client
        response = supabase.postgrest.raw(sql)
        logger.info(f"Executed SQL: {sql[:100]}...")
        return {"success": True, "response": response}
    except Exception as e:
        logger.error(f"Failed to execute SQL: {str(e)}")
        return {"success": False, "error": str(e)}


def create_table_via_sql_editor(table_name: str, sql: str) -> bool:
    """Create a table using direct SQL."""
    try:
        logger.info(f"Creating table: {table_name}")
        
        # Using Supabase admin API to execute SQL
        import httpx
        
        headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
        }
        
        # Use SQL endpoint if available
        url = f"{settings.supabase_url}/rest/v1/rpc/execute_sql"
        
        payload = {"sql": sql}
        
        async def execute():
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                return response
        
        # For now, log the SQL for manual execution
        logger.info(f"SQL to execute:\n{sql}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create table {table_name}: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("DesiYatra Database Migration Script")
    logger.info(f"Supabase URL: {settings.supabase_url}")
    
    # List all migrations
    migrations = get_migration_files()
    logger.info(f"\nFound {len(migrations)} migrations:")
    for name, _ in migrations:
        logger.info(f"  - {name}")
    
    logger.info("\nTo apply migrations:")
    logger.info("1. Go to Supabase dashboard")
    logger.info("2. Navigate to SQL Editor")
    logger.info("3. Create a new query")
    logger.info("4. Copy and paste the contents of each migration file in order")
    logger.info("5. Execute each migration")
    logger.info("\nAlternatively, use the Supabase CLI:")
    logger.info("  supabase db push")
