import redis.asyncio as redis

from .config import settings

pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)

_script_shas: dict[tuple[int, str], str] = {}


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=pool)


async def eval_script(client: redis.Redis, script_text: str, num_keys: int, *args):
    """Run a Lua script by SHA, loading it into Redis on first use or after a flush."""
    cache_key = (id(client), script_text)
    sha = _script_shas.get(cache_key)
    if sha is None:
        sha = await client.script_load(script_text)
        _script_shas[cache_key] = sha
    try:
        return await client.evalsha(sha, num_keys, *args)
    except redis.ResponseError:
        sha = await client.script_load(script_text)
        _script_shas[cache_key] = sha
        return await client.evalsha(sha, num_keys, *args)
