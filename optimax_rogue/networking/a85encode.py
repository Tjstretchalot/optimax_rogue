"""This is just the a85encoding without the z-alias for 4 0s. The z-alias is only helpful
if reducing file size is more important than reducing decryption speed, which isn't obviously
true anymore. It also mmakes the implementation more complicated which is definitely unhelpful
"""

def a85encode(inp: bytes) -> bytes:
    """Encodes blocks of 4 input bytes to 5 output bytes using ascii 33-108"""
    if len(inp) % 4 != 0:
        inp = inp + (b'\x00' * (4 - (len(inp) % 4)))

    result = bytearray((len(inp) // 4) * 5)
    for block in range(len(inp) // 4):
        off = block * 4
        remaining = (inp[off] << 24) + (inp[off + 1] << 16) + (inp[off + 2] << 8) + inp[off + 3]
        temp = remaining // 85
        off = block * 5
        result[off + 4] = 33 + (remaining - temp * 85)
        remaining = temp
        temp //= 85
        result[off + 3] = 33 + (remaining - temp * 85)
        remaining = temp
        temp //= 85
        result[off + 2] = 33 + (remaining - temp * 85)
        remaining = temp
        temp //= 85
        result[off + 1] = 33 + (remaining - temp * 85)
        result[off] = 33 + temp

    return bytes(result)