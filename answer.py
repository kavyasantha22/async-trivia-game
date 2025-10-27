
def generate_answer(question_type, short_question) -> str:
    # print("generating answer...")
    # print(question_type, short_question)
    if question_type == "Usable IP Addresses of a Subnet":
        return _generate_usable_ipv4_answer(short_question)
    elif question_type == "Network and Broadcast Address of a Subnet":
        return _generate_network_broadcast_answer(short_question)
    elif question_type == "Roman Numerals":
        return _generate_roman_numerals_answer(short_question)
    elif question_type == "Mathematics":
        return _generate_mathematics_answer(short_question)
    else:
        print("Unrecognised question type.")
        print(question_type)
        return ""

def _generate_mathematics_answer(short_question):
    ans = 0
    pos = True
    cur = ""
    for char in short_question:
        if char == " ":
            continue
        elif char == "+":
            if pos:
                ans += int(cur)
            else:
                ans += (-1) * int(cur)

            cur = ""
            pos = True
        elif char == "-":
            if pos:
                ans += int(cur)
            else:
                ans += (-1) * int(cur)
                
            cur = ""
            pos = False
        else:
            cur += char
    
    if pos:
        ans += int(cur)
    else:
        ans += (-1) * int(cur)


    return str(ans)


def _generate_roman_numerals_answer(short_question: str):
    ROMAN_SYMBOLS = {
        'M': 1000,
        'D': 500,
        'C': 100,
        'L': 50,
        'X': 10,
        'V': 5,
        'I': 1
    }
    short_question = short_question.upper()
    i = 0
    ans = 0
    while i < len(short_question):
        cur = ROMAN_SYMBOLS[short_question[i]] 
        if i + 1 < len(short_question) and cur < ROMAN_SYMBOLS[short_question[i+1]]:
            ans += ROMAN_SYMBOLS[short_question[i+1]] - cur
            i += 2
        else:
            ans += cur
            i += 1

    return str(ans)

def _parse_ip_cidr(short_question: str):
    ip = 0x0
    cidr = 0
    cur = ""

    for char in short_question:
        if char == '.' or char == '/':
            ip = ip << 8 | int(cur)
            cur = ""            
        else:
            cur += char
    cidr = int(cur)

    return (ip, cidr)


def _generate_network_broadcast(short_question: str):
    # print("generating answer for network broadcast...")
    ip, cidr = _parse_ip_cidr(short_question)
    mask = 0xFFFFFFFF << (32 - cidr) & 0xFFFFFFFF
    inv_mask = ~mask & 0xFFFFFFFF

    network = ip & mask
    broadcast = network | inv_mask

    return (network, broadcast)


def _convert_to_ip(num):
    return ".".join([str(num >> shift & 0xFF) for shift in (24, 16, 8, 0)])
    

def _generate_network_broadcast_answer(short_question):
    network, broadcast = _generate_network_broadcast(short_question)
    # print("returning...")
    # return "EXIT"
    return str(_convert_to_ip(network)) + " and " + str(_convert_to_ip(broadcast))
    

def _generate_usable_ipv4_answer(short_question):
    network, broadcast = _generate_network_broadcast(short_question)

    return str(broadcast - network + 1 - 2)
