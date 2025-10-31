import random

def generate_mathematics_question(rng=None):
    rng = rng or rng
    OPERANDS_RANGE = [1, 100]
    OPERATORS = ["+", "-"]
    operands = rng.randint(2, 5)
    ret = ""

    ret += str(rng.randint(OPERANDS_RANGE[0], OPERANDS_RANGE[1]))
    operands -= 1
    while operands:
        ret += " " + rng.choice(OPERATORS) + " " + str(rng.randint(*OPERANDS_RANGE))
        operands -= 1

    return ret
    

def _int_to_roman(n: int) -> str:
    ROMAN_SYMBOLS = [
        (1000, "M"), (900, "CM"),
        (500, "D"),  (400, "CD"),
        (100, "C"),  (90, "XC"),
        (50, "L"),   (40, "XL"),
        (10, "X"),   (9, "IX"),
        (5, "V"),    (4, "IV"),
        (1, "I"),
    ]
    out = []
    for value, sym in ROMAN_SYMBOLS:
        count, n = divmod(n, value)
        if count:
            out.append(sym * count)
    return "".join(out)


def generate_roman_numerals_question(rng=None):
    rng = rng or random
    ROMAN_RANGE = [1, 3999]
    number = rng.randint(ROMAN_RANGE[0], ROMAN_RANGE[1])

    return _int_to_roman(number)

def _generate_ip_cidr(rng):
    BIT_RANGE = [0, 255]
    HOST_BITS_RANGE = [0, 32]

    ip = [str(rng.randint(*BIT_RANGE)) for _ in range(4)]
    
    ret = ".".join(ip)
    ret += "/" + str(rng.randint(*HOST_BITS_RANGE))

    return ret


def generate_usable_addresses_question(rng=None):
    rng = rng or random
    return _generate_ip_cidr(rng)


def generate_network_broadcast_question(rng=None):
    rng = rng or random
    return _generate_ip_cidr(rng)


# for _ in range(10):
#     s = generate_mathematics_question()

#     print(repr(s))

    



