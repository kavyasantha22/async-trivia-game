import random

def generate_mathematics_question():
    OPERANDS_RANGE = [1, 1000]
    OPERATORS = ["+", "-"]
    operands = random.randint(2, 5)
    ret = ""

    ret += str(random.randint(OPERANDS_RANGE[0], OPERANDS_RANGE[1]))
    operands -= 1
    while operands:
        ret += " " + random.choice(OPERATORS) + " " + str(random.randint(*OPERANDS_RANGE))
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


def generate_roman_numerals_question():
    ROMAN_RANGE = [1, 3999]
    number = random.randint(ROMAN_RANGE[0], ROMAN_RANGE[1])

    return _int_to_roman(number)

def _generate_ip_cidr():
    BIT_RANGE = [0, 255]
    HOST_BITS_RANGE = [1, 30]

    ip = [str(random.randint(*BIT_RANGE)) for _ in range(4)]
    
    ret = ".".join(ip)
    ret += "/" + str(random.randint(*HOST_BITS_RANGE))

    return ret


def generate_usable_addresses_question():
    return _generate_ip_cidr()


def generate_network_broadcast_question():
    return _generate_ip_cidr()

    



