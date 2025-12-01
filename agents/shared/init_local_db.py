"""
Initialize Supabase local database with migrations
Run this after docker-compose up to setup tables and seed data
"""

import os
import asyncio
from pathlib import Path
from loguru import logger
import psycopg2
from psycopg2 import sql
import time


def wait_for_postgres(max_retries=30):
    """Wait for PostgreSQL to be ready"""
    import socket
    
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    
    for attempt in range(max_retries):
        try:
            sock = socket.create_connection((host, port), timeout=1)
            sock.close()
            logger.success(f"✓ PostgreSQL is ready at {host}:{port}")
            return True
        except (socket.timeout, ConnectionRefusedError):
            logger.info(f"⏳ Waiting for PostgreSQL... ({attempt + 1}/{max_retries})")
            time.sleep(1)
    
    logger.error("❌ PostgreSQL did not start in time")
    return False


def get_connection():
    """Get PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres")
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return None


def run_migrations():
    """Run SQL migration files"""
    logger.info("🔧 Running database migrations...")
    
    migrations_dir = Path('/app/migrations')
    
    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return False
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.error("No migration files found")
        return False
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        for migration_file in migration_files:
            logger.info(f"Applying: {migration_file.name}")
            
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Execute migration
            cursor.execute(migration_sql)
            conn.commit()
            
            logger.success(f"✓ {migration_file.name}")
        
        logger.success("✅ All migrations applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def create_schemas():
    """Ensure schemas and extensions exist"""
    logger.info("📦 Creating schemas and extensions...")
    
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Create extensions
        extensions = [
            "uuid-ossp",
            "pgcrypto",
            "json_enhancements",
        ]
        
        for ext in extensions:
            try:
                cursor.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}"')
                logger.debug(f"✓ Extension: {ext}")
            except Exception as e:
                logger.debug(f"Skipping extension {ext}: {str(e)}")
        
        conn.commit()
        logger.success("✓ Schemas and extensions ready")
        return True
        
    except Exception as e:
        logger.error(f"Schema creation failed: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()


async def seed_market_rates():
    """Seed market rates after tables are created"""
    try:
        from agents.shared.seed_market_rates import seed_market_rates_sync
        
        logger.info("🌱 Seeding market rates...")
        result = seed_market_rates_sync()
        
        if result:
            logger.success("✅ Market rates seeded successfully!")
            return True
        else:
            logger.warning("⚠ Market rates seeding had issues (non-critical)")
            return True
            
    except Exception as e:
        logger.warning(f"⚠ Could not seed market rates: {str(e)}")
        return True  # Non-critical


def initialize_db():
    """Complete database initialization"""
    logger.info("\n" + "=" * 70)
    logger.info("🗄️  DesiYatra Database Initialization")
    logger.info("=" * 70)
    
    # Step 1: Wait for PostgreSQL
    logger.info("\n[1/4] Waiting for PostgreSQL...")
    if not wait_for_postgres():
        return False
    
    # Step 2: Create schemas and extensions
    logger.info("\n[2/4] Creating schemas and extensions...")
    if not create_schemas():
        return False
    
    # Step 3: Run migrations
    logger.info("\n[3/4] Running migrations...")
    if not run_migrations():
        return False
    
    # Step 4: Seed data
    logger.info("\n[4/4] Seeding initial data...")
    asyncio.run(seed_market_rates())
    
    logger.info("\n" + "=" * 70)
    logger.success("✅ Database initialization complete!")
    logger.info("=" * 70 + "\n")
    
    return True


if __name__ == "__main__":
    success = initialize_db()
    exit(0 if success else 1)
