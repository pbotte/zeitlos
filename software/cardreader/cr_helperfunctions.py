# cardreader helper functions

euro_cc = b"\x09\x78"


def pop_bytes(msg, count):
    if len(msg) < count:
        raise Exception(
            f"Tried to retrieve {count} bytes from message but there are only {len(msg)} left"
        )
    taken = msg[:count]
    del msg[:count]
    return taken


def pop_byte(msg):
    if len(msg) == 0:
        raise Exception("Tried to retrieved byte but there are none remaining")
    byte = msg[0]
    del msg[0]
    return byte


def parse_lenght_bytes(msg):
    length = pop_byte(msg)
    if length == 0xFF:
        length = int.from_bytes(pop_bytes(msg, 2), byteorder="little")
    return length


def skip_command_header(msg):
    del msg[:2]
    return parse_lenght_bytes(msg)


def fmt_bytes(bytes):
    if type(bytes) == int:
        return fmt_bytes(bytearray([bytes]))
    return bytes.hex(sep=" ").upper()


def parse_lvar(llen, msg):
    if len(msg) < llen:
        raise Exception(f"Tried to parse LLLVAR with {len(msg)} bytes")
    length = 0
    for i in range(llen):
        length *= 10
        if (msg[i] & 0xF0) != 0xF0:
            raise Exception(
                f"Tried to parse LLVAR with {fmt_bytes(msg[i])} as {i}th byte"
            )
        length += msg[i] & 0x0F
    del msg[:llen]
    if len(msg) < length:
        raise Exception(
            f"Length of message is shorter ({len(msg)} bytes than LVAR encoded length ({length} bytes)"
        )
    res = bytes(pop_bytes(msg, length))
    return res


def parse_bcd(msg, width):
    if len(msg) < width:
        raise Exception(
            f"Tried to parse a {width} byte BCD but there are only {len(msg)} bytes left"
        )
    s = pop_bytes(msg, width).hex()
    if any(map(lambda c: c not in "0123456789", s)):
        raise Exception(f'Tried to parse "{s}" as BCD')
    return int(s)


def encode_bcd(width, num):
    res = bytearray(width)
    for i in range(width - 1, -1, -1):
        res[i] = int(f"{num % 100}", 16)
        num //= 100
        if num == 0:
            break
    return res


def check_and_skip_command_header(msg, header):
    if not msg.startswith(header):
        raise Exception(
            f"Found instead expected header {fmt_bytes(header)}: {fmt_bytes(msg)}"
        )
    return skip_command_header(msg)


def try_parse_intermediate_status(msg):
    if not msg.startswith(b'\x04\xFF'):
        return None
    skip_command_header(msg)
    res = dict()
    res['status'] = msg[0]
    del msg[0]
    if len(msg) > 0:
        res['timeout_min'] = pop_byte(msg)
        if len(msg) > 0:
            tag = pop_byte(msg)
            if tag != 0x06:
                raise Exception(f'Expected TLV container but found tag {fmt_bytes(tag)}')
            res['tlv'] = parse_tlv_containter(msg)
    if len(msg) > 0:
        raise Exception(f'Trailing bytes after intermediate status: {fmt_bytes(msg)}')
    return res




def parse_tlv_containter(msg: bytearray, is_primitive: bool = False):
    if len(msg) == 0:
        raise Exception('Tried to parse empty TLV entry')
    # parse length
    tlv_len = pop_byte(msg)
    if tlv_len & 0x80:
        if tlv_len == 0x81:
            if len(msg) == 0:
                raise Exception('Incomplete 2 byte TLV length found')
            tlv_len = pop_byte(msg)
        elif tlv_len == 0x82:
            if len(msg) < 2:
                raise Exception('Incomplete 3 byte TLV length found')
            tlv_len = int.from_bytes(pop_bytes(msg, 2), byteorder='big')
        else:
            raise Exception(f'Unexpected TLV length byte {fmt_bytes(msg[0])}')
    if len(msg) < tlv_len:
        raise Exception(f'Remaining data ({len(msg)} bytes) shorter than TLV entry ({tlv_len})')
    if is_primitive:
        data = bytes(pop_bytes(msg, tlv_len))
        return data
    msg = pop_bytes(msg, tlv_len)
    ret = dict()
    while len(msg) > 0:
        tag = pop_byte(msg)
        is_primitive = (tag & 32) == 0
        if tag & 31 == 31:
            while True:
                tag <<= 8
                tag |= pop_byte(msg)
                if tag & 128 == 0:
                    break
        existing = ret.get(tag)
        if existing is None:
            ret[tag] = parse_tlv_containter(msg, is_primitive)
        else:
            if type(existing) != list:
                ret[tag] = [existing]
            ret[tag].append(parse_tlv_containter(msg, is_primitive))
    return ret


def take_from_dict(d, *args):
    if len(args) == 0:
        return d
    val = d.get(args[0])
    if val is None:
        return None
    else:
        res = take_from_dict(val, *args[1:]) if type(val) == dict else val
        if type(val) != dict or len(val) == 0:
            del d[args[0]]
        return res



def wrap_if_no_list(data):
    return data if type(data) == list else [data]


def parse_bmps(msg):
    res = {}
    while len(msg) > 0:
        bmp = pop_byte(msg)
        if bmp == 0x04:
            res['amount'] = parse_bcd(msg, 6)
        elif bmp == 0x0B:
            res['trace'] = parse_bcd(msg, 3)
        elif bmp == 0x37:
            res['orig-trace'] = parse_bcd(msg, 3)
        elif bmp == 0x0C:
            res['time'] = parse_bcd(msg, 3)
        elif bmp == 0x0D:
            res['date'] = parse_bcd(msg, 2)
        elif bmp == 0x0E:
            res['exp-date'] = parse_bcd(msg, 2)
        elif bmp == 0x17:
            res['seq-no'] = parse_bcd(msg, 2)
        elif bmp == 0x19:
            res['payment-type'] = pop_byte(msg)
        elif bmp == 0x22:
            res['ef-id'] = parse_lvar(2, msg)
        elif bmp == 0x29:
            res['terminal-id'] = parse_bcd(msg, 4)
        elif bmp == 0x3B:
            res['auth-id'] = pop_bytes(msg, 8)
        elif bmp == 0x49:
            res['cc'] = parse_bcd(msg, 2)
        elif bmp == 0x4C:
            res['blocked-goods-groups'] = parse_lvar(2, msg)
        elif bmp == 0x87:
            res['receipt-no'] = parse_bcd(msg, 2)
        elif bmp == 0x8A:
            res['card-type'] = pop_byte(msg)
        elif bmp == 0x8C:
            res['card-type-id'] = pop_byte(msg)
        elif bmp == 0x9A:
            res['geldkarte-payment-record'] = parse_lvar(3, msg)
        elif bmp == 0xBA:
            res['auth-id-param'] = pop_bytes(msg, 5)
        elif bmp == 0x2A:
            res['VU-number'] = pop_bytes(msg, 15)
        elif bmp == 0x3C:
            res['additional text'] = parse_lvar(3, msg)
        elif bmp == 0x60:
            res['individual totals'] = parse_lvar(3, msg)
        elif bmp == 0xA0:
            res['result-code-AS'] = pop_byte(msg)
        elif bmp == 0x88:
            res['turnover-no'] = parse_bcd(msg, 3)
        elif bmp == 0x8B:
            res['card-name'] = parse_lvar(2, msg)
        elif bmp == 0x06:
            tlv = parse_tlv_containter(msg)
            for tag, val in tlv.items():
                if tag == 0x41:
                    if type(val) != bytes or len(val) != 1:
                        raise Exception('Unexpected TLV card type')
                    card_type = val[0]
                    if res.setdefault('card-type', card_type) != card_type:
                        raise Exception('Card type mismatch between TLV and BMP')
                elif tag == 0x21:
                    if type(val) != dict or len(val) > 1 or 5 not in val:
                        raise Exception('Unexpected good groups')
                    res['good-groups'] = list(map(lambda x: parse_bcd(bytearray(x), 3), wrap_if_no_list(val[5])))
                elif tag == 0x45:
                    if len(val) != 4:
                        raise Exception('Unexpected TLV receipt parameter length')
                    res['receipt-param'] = parse_bcd(bytearray(val), 4)
        else:
            raise Exception(f'Tried to parse BMP but found invalid BMP number {fmt_bytes(bmp)}')
    return res


def parse_result_msg(msg, logger):
    if len(msg) < 2 or not msg.startswith(b'\x04\x0F'):
        raise Exception('result message does not start with 04 0F')
    skip_command_header(msg)
    if pop_byte(msg) != 0x27:
        raise Exception('result data block does not start with 27!')
    result_code = pop_byte(msg)
    if result_code != 0:
        #in case an error occured, eg non card presented, etc.
        logger.debug(f'parse_result_msg(): result code not 00 but {fmt_bytes(result_code)}!')
    return parse_bmps(msg)

