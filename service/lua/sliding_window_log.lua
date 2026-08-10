-- KEYS[1] = zset key
-- ARGV[1] = now (unix seconds, float)
-- ARGV[2] = window_seconds
-- ARGV[3] = limit
-- ARGV[4] = unique member id for this request

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

local allowed = 0
if count < limit then
    redis.call('ZADD', key, now, member)
    allowed = 1
    count = count + 1
end
redis.call('EXPIRE', key, window + 1)

return {allowed, count}
