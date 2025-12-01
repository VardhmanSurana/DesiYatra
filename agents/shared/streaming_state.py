import asyncio
import json
from typing import Optional
from agents.shared.redis_client import redis_client
from loguru import logger

async def push_to_queue(call_id: str, text: str):
    """Pushes text to the Redis queue for the given call_id."""
    key = f"call_queue:{call_id}"
    try:
        await redis_client.rpush(key, text)
        # Set expiry to auto-cleanup old queues (e.g., 1 hour)
        await redis_client.expire(key, 3600)
    except Exception as e:
        logger.error(f"Redis push failed: {e}")

async def pop_from_queue(call_id: str, timeout: int = 5) -> Optional[str]:
    """
    Pops text from the Redis queue. 
    Waits for `timeout` seconds. Returns None if empty.
    """
    key = f"call_queue:{call_id}"
    try:
        # blpop returns (key, value) tuple or None
        result = await redis_client.blpop(key, timeout=timeout)
        if result:
            return result[1] # result[0] is the key, result[1] is the value
        return None
    except Exception as e:
        logger.error(f"Redis pop failed: {e}")
        return None

async def clear_call_queue(call_id: str):
    """Clears the Redis queue for the call."""
    key = f"call_queue:{call_id}"
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis delete failed: {e}")

# Backward compatibility aliases (if needed temporarily, but better to replace usage)
get_call_queue = None 
