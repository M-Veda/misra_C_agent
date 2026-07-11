from redis.asyncio import Redis

from misra_platform.core.config import Settings


class RedisClientFactory:
    @staticmethod
    def create(settings: Settings) -> Redis:
        return Redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )
