ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return "0"

    chars = []
    while n > 0:
        chars.append(ALPHABET[n % BASE])
        n //= BASE
    chars.reverse()
    return "".join(chars)


def decode(s):
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if s == "":
        raise ValueError("s must not be empty")

    value = 0
    for char in s:
        index = ALPHABET.find(char)
        if index == -1:
            raise ValueError("s contains a character outside the Base62 alphabet")
        value = value * BASE + index
    return value
