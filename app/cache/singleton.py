from app.cache.redis import RedisCache
from app.core.config import settings

redis_cache = RedisCache(settings.redis_url)
