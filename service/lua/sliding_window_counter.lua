-- KEYS[1] = key prefix for this identity
-- ARGV[1] = now (unix seconds, float)
-- ARGV[2] = window_seconds
-- ARGV[3] = limit

local prefix = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

local bucket_id = math.floor(now / window)
local current_key = prefix .. ':' .. bucket_id
local prev_key = prefix .. ':' .. (bucket_id - 1)

local current = tonumber(redis.call('GET', current_key) or '0')
local prev = tonumber(redis.call('GET', prev_key) or '0')

local elapsed_in_current = now - (bucket_id * window)
local weight_prev = (window - elapsed_in_current) / window
if weight_prev < 0 then weight_prev = 0 end

local estimate = prev * weight_prev + current

local allowed = 0
if estimate < limit then
    current = redis.call('INCR', current_key)
    redis.call('EXPIRE', current_key, window * 2)
    allowed = 1
    estimate = estimate + 1
end

return {allowed, tostring(estimate)}
