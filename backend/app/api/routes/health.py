from fastapi import APIRouter, Depends
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])


def get_redis_client(settings: Settings = Depends(get_settings)) -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )


@router.get("")
def health_check(
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
) -> dict[str, str]:
    try:
        redis_client.ping()
        redis_status = "connected"
    except RedisError:
        redis_status = "disconnected"

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "redis": redis_status,
    }
