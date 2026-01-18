import asyncio
import logging
import sys
import os

# Add the parent directory to sys.path to allow imports from src
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.config.env import POSTGRES_DB_URI
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    if not POSTGRES_DB_URI:
        logger.error("POSTGRES_DB_URI is not set.")
        sys.exit(1)

    logger.info("Initializing database connection...")
    
    # Adjust connection string for psycopg
    conn_info = POSTGRES_DB_URI.replace("postgresql+psycopg://", "postgresql://")
    
    try:
        async with AsyncConnectionPool(conninfo=conn_info, min_size=1, max_size=1, open=False, kwargs={"autocommit": True}) as pool:
            await pool.open()
            logger.info("Connection pool setup complete.")
            
            checkpointer = AsyncPostgresSaver(pool)
            logger.info("Running checkpointer setup (creating tables if not exist)...")
            await checkpointer.setup()
            
            logger.info("Database initialization completed successfully.")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_db())
