
TOKEN_BUCKET_SCRIPT = """
-- Arguments
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local requested_tokens = tonumber(ARGV[3])
local ttl_seconds = tonumber(ARGV[4])

-- Get current time from Redis server
local redis_time = redis.call("TIME")

local current_time_ms =
    (tonumber(redis_time[1]) * 1000)
    + math.floor(tonumber(redis_time[2]) / 1000)

-- Read existing bucket state
local tokens = tonumber(
    redis.call("HGET", KEYS[1], "tokens")
)

local last_refill = tonumber(
    redis.call("HGET", KEYS[1], "last_refill")
)

-- Initialize a new bucket as full
if tokens == nil or last_refill == nil then
    tokens = capacity
    last_refill = current_time_ms
end

-- Calculate elapsed time
local elapsed_ms = math.max(
    0,
    current_time_ms - last_refill
)

local elapsed_seconds = elapsed_ms / 1000

-- Refill tokens
local new_tokens = math.min(
    capacity,
    tokens + (elapsed_seconds * refill_rate)
)

-- Check whether enough tokens are available
local allowed = 0
local retry_after_ms = 0

if new_tokens >= requested_tokens then

    -- Consume tokens
    new_tokens = new_tokens - requested_tokens
    allowed = 1

else

    -- Calculate time required to obtain requested tokens
    local missing_tokens = requested_tokens - new_tokens

    retry_after_ms = math.ceil(
        (missing_tokens / refill_rate) * 1000
    )

end

-- Save updated bucket state
redis.call(
    "HSET",
    KEYS[1],
    "tokens",
    tostring(new_tokens),
    "last_refill",
    tostring(current_time_ms)
)

-- Automatically expire inactive bucket keys
redis.call("EXPIRE", KEYS[1], ttl_seconds)

-- Calculate time until bucket becomes full
local reset_after_ms = math.ceil(
    ((capacity - new_tokens) / refill_rate) * 1000
)

-- Return:
-- 1. allowed (1 or 0)
-- 2. remaining tokens
-- 3. retry_after_ms
-- 4. reset_after_ms

return {
    allowed,
    tostring(new_tokens),
    retry_after_ms,
    reset_after_ms
}
"""
