bit = require('bit')
struct = require('struct')

local mmh3 = {}

-- The implementation of MurmurHash3 is the 32-bit variation, based on the
-- example implementations here: https://en.wikipedia.org/wiki/MurmurHash
function mmh3.hash32(key, seed)
    local c1 = 0xcc9e2d51
    local c2 = 0x1b873593
    local r1 = 15
    local r2 = 13
    local m = 5
    local n = 0xe6546b64
    if seed == nil then
        seed = 0
    end

    local function multiply(x, y)
        -- This is required to emulate uint32 overflow correctly -- otherwise,
        -- higher order bits are simply truncated and discarded.
        return (bit.band(x, 0xffff) * y) + bit.lshift(bit.band(bit.rshift(x, 16) * y,  0xffff), 16)
    end

    local hash = bit.tobit(seed)
    local remainder = #key % 4

    for i = 1, #key - remainder, 4 do
        local k = struct.unpack('<I4', key, i)
        k = multiply(k, c1)
        k = bit.rol(k, r1)
        k = multiply(k, c2)
        hash = bit.bxor(hash, k)
        hash = bit.rol(hash, r2)
        hash = multiply(hash, m) + n
    end

    if remainder ~= 0 then
        local k1 = struct.unpack('<I' .. remainder, key, #key - remainder + 1)
        k1 = multiply(k1, c1)
        k1 = bit.rol(k1, r1)
        k1 = multiply(k1, c2)
        hash = bit.bxor(hash, k1)
    end

    hash = bit.bxor(hash, #key)
    hash = bit.bxor(hash, bit.rshift(hash, 16))
    hash = multiply(hash, 0x85ebca6b)
    hash = bit.bxor(hash, bit.rshift(hash, 13))
    hash = multiply(hash, 0xc2b2ae35)
    hash = bit.bxor(hash, bit.rshift(hash, 16))
    return hash
end

return mmh3
