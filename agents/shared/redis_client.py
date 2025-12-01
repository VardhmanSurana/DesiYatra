import redis.asyncio as redis
from .config import settings

redis_client = redis.from_url(
    settings.redis_url,
    password=settings.redis_password if settings.redis_password else None,
    decode_responses=True
)
