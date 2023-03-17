import asyncio
import asyncio_mqtt as aiomqtt


euro_cc = b'\x09\x78'


class ChatFile:
    def __init__(self, filename):
        self.f = open(filename, 'w')

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self.f.close()

    def write_msg(self, data: bytearray):
        hex = data.hex()
        self.f.write(' '.join(hex[i:(i+2)] for i in range(0, len(hex), 2)) + '\n')
        self.f.write('  '.join(chr(c) if chr(c).isprintable() else '.' for c in data) + '\n')
        self.f.flush()


def pop_bytes(msg, count):
    if len(msg) < count:
        raise Exception(f'Tried to retrieve {count} bytes from message but there are only {len(msg)} left')
    taken = msg[:count]
    del msg[:count]
    return taken


def pop_byte(msg):
    if len(msg) == 0:
        raise Exception('Tried to retrieved byte but there are none remaining')
    byte = msg[0]
    del msg[0]
    return byte


def parse_lenght_bytes(msg):
    length = pop_byte(msg)
    if length == 0xFF:
        length = int.from_bytes(pop_bytes(msg, 2), byteorder='little')
    return length


def skip_command_header(msg):
    del msg[:2]
    return parse_lenght_bytes(msg)


def fmt_bytes(bytes):
    if type(bytes) == int:
        return fmt_bytes(bytearray([bytes]))
    return bytes.hex(sep=' ').upper()


def parse_lvar(llen, msg):
    if len(msg) < llen:
        raise Exception(f'Tried to parse LLLVAR with {len(msg)} bytes')
    length = 0
    for i in range(llen):
        length *= 10
        if (msg[i] & 0xF0) != 0xF0:
            raise Exception(f'Tried to parse LLVAR with {fmt_bytes(msg[i])} as {i}th byte')
        length += msg[i] & 0x0F
    del msg[:llen]
    if len(msg) < length:
        raise Exception(f'Length of message is shorter ({len(msg)} bytes than LVAR encoded length ({length} bytes)')
    res = bytes(pop_bytes(msg, length))
    return res


def parse_bcd(msg, width):
    if len(msg) < width:
        raise Exception(f'Tried to parse a {width} byte BCD but there are only {len(msg)} bytes left')
    s = pop_bytes(msg, width).hex()
    if any(map(lambda c: c not in "0123456789", s)):
        raise Exception(f'Tried to parse "{s}" as BCD')
    return int(s)

def encode_bcd(width, num):
    res = bytearray(width)
    for i in range(width-1, -1, -1):
        res[i] = int(f'{num % 100}', 16)
        num //= 100
        if num == 0:
            break
    return res


def check_and_skip_command_header(msg, header):
    if not msg.startswith(header):
        raise Exception(f'Found instead expected header {fmt_bytes(header)}: {fmt_bytes(msg)}')
    return skip_command_header(msg)


class PTConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def recv_until_len(self, msg: bytearray, length):
        while len(msg) < length:
            msg += await self.reader.read(length - len(msg))

    async def send_ack(self):
        self.writer.write(b'\x80\x00\x00')
        await self.writer.drain()

    async def recv_ack(self, error='Received "%m" instead of ack'):
        msg = await self.recv_message()
        if msg == b'\x84\x83\x00':
            raise Exception('Unsupported or unknown command!')
        elif msg != b'\x80\x00\x00':
            raise Exception(error.replace('%m', fmt_bytes(msg)))

    async def recv_message(self):
        msg = bytearray()
        await self.recv_until_len(msg, 3)
        if msg[2] < 0xFF:
            expected_len = int(msg[2]) + 3
        else:
            await self.recv_until_len(msg, 5)
            expected_len = int.from_bytes(msg[3:5], byteorder='little') + 5
        await self.recv_until_len(msg, expected_len)
        await self.send_ack()
        return msg

    async def send(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def send_query(self, data):
        await self.send(data)
        await self.recv_ack()
        return await self.recv_message()

    async def query_pending_pre_auth(self):
        msg = await self.send_query(b'\x06\x23\x03\x87\xFF\xFF')
        check_and_skip_command_header(msg, b'\x06\x1E')
        if len(msg) < 4:
            raise Exception('Preauth query response too short!')
        if pop_bytes(msg, 2) != b'\xB8\x87':
            raise Exception('Preauth response data block does not start with B8 87!')
        receipt_no = pop_bytes(msg, 2)
        if receipt_no == b'\xFF\xFF':
            receipt_no = None
        if len(msg) > 0:
            tag = pop_byte(msg)
            if tag != 0x06:
                raise Exception(f'Expected TLV container starting with 06 but found byte {fmt_bytes(tag)}')
            tlv = parse_tlv_containter(msg)
        return receipt_no

    async def wait_for_and_parse_status(self, msg):
        while msg.startswith(b'\x04\xFF'):
            msg = await self.recv_message()
        if not msg.startswith(b'\x04\x0F'):
            raise Exception(f'Instead 04 0F receivd {fmt_bytes(msg)}')
        return parse_result_msg(msg)

    async def wait_for_completion(self, count):
        for i in range(count):
            msg = await self.recv_message()
            if msg != b'\x06\x0F\x00':
                raise Exception(f'Received not completion but {fmt_bytes(msg)}')

    async def send_preauth(self, amount_cents):
        msg = await self.send_query(b'\x06\x22\x12\x04' + \
                                    encode_bcd(6, amount_cents) + b'\x49' + euro_cc + b'\x19\x40\x06\x04\x40\x02\xff\x00')
        res = await self.wait_for_and_parse_status(msg)
        await self.wait_for_completion(2)
        return res

    async def book_total(self, preauth_res, amount_cents):
        if amount_cents > preauth_res['amount']:
            raise Exception('Amount bigger than preauth!')
        data = b'\x87' + encode_bcd(2, preauth_res['receipt-no']) + b'\x04' + encode_bcd(6, amount_cents) + b'\x49' + euro_cc + \
               b'\x19' + bytearray([preauth_res['payment-type']]) + \
               b'\x0B' + encode_bcd(3, preauth_res['trace']) + \
               b'\x8A' + bytearray([preauth_res['card-type']])
        data = b'\x06\x24' + bytearray([len(data)]) + data
        msg = await self.send_query(data)
        res = await self.wait_for_and_parse_status(msg)
        await self.wait_for_completion(2)
        return res

    async def send_and_log_chat(self, data, logfile, complete_code=b'\x06\x0F', prefix=True):
        with ChatFile(logfile) as f:
            f.write_msg(data)
            msg = await self.send_query(data)
            f.write_msg(msg)
            while not msg.startswith(complete_code):
                msg = await self.recv_message()
                f.write_msg(msg)
            f.write_msg(msg)


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


class Dummy:
    def __init__(self) -> None:
        pass


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


async def make_pt_connection(host, port):
    ptc = PTConnection(*(await asyncio.open_connection(host, port)))

    # registration
    msg = await ptc.send_query(b'\x06\x00\x10\x00\x00\x00\x08\x09\x78\x03\x00\x06\x06\x26\x04\x0a\x02\x06\xd3')
    check_and_skip_command_header(msg, b'\x06\x0F')
    tlv = None
    while len(msg) > 0:
        tag = pop_byte(msg)
        if tag == 0x19:
            data = pop_byte(msg)
            if data & 1:
                raise Exception('PT initialization necessary')
            if data & 2:
                raise Exception('Diagnosis necessary')
            if data & 4:
                raise Exception('OPT action necessary')
            ptc.filling_station_mode = bool(data & 8)
            ptc.vending_machine_mode = bool(data & 16)
        elif tag == 0x29:
            ptc.tid = bytes(pop_bytes(msg, 4))
        elif tag == 0x49:
            cc = pop_bytes(msg, 2)
            if cc != euro_cc:
                raise Exception(f'Received currency code {fmt_bytes(cc)} instead of expected € code {fmt_bytes(euro_cc)} after registration')
        elif tag == 0x06:
            tlv = parse_tlv_containter(msg)
        else:
            raise Exception(f'Received unexpected tag {fmt_bytes(tag)} after registration')
    if tlv is not None:
        supported_commands = take_from_dict(tlv, 38, 10)
        if supported_commands is not None:
            ptc.supported_commands = supported_commands
            if b'\x05\x01' not in supported_commands:
                raise Exception('Terminal does not support status enquiry')

    # status enquiry
    msg = await ptc.send_query(b'\x05\x01\x03\x00\x00\x00')
    while status := try_parse_intermediate_status(msg):
        msg = await ptc.recv_message()
    check_and_skip_command_header(msg, b'\x06\x0F')
    ptc.software_version = parse_lvar(3, msg)
    if len(msg) == 0:
        raise Exception('Status enquiry response too short!')
    if msg[0] == 0xDC:
        #raise Exception('Terminal not ready because card inserted!')
        print('Card still inserted')
    elif msg[0] != 0x00:
        #raise Exception(f'Terminal not ready - returned status byte {fmt_bytes(msg[0])}')
        print(f'Error status {fmt_bytes(msg[0])}')
        pass

    return ptc


def read_chat_file(filename):
    ret = []
    with open(filename, 'r') as f:
        for line in f:
            b = line.split()
            if all(map(lambda x: len(x) == 2 and all(map(lambda y: y in "0123456789ABCDEF", x.upper())), b)):
                ret.append(bytearray(map(lambda x: int(x, 16), b)))
    return ret


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


def parse_result_msg(msg):
    if len(msg) < 2 or not msg.startswith(b'\x04\x0F'):
        raise Exception('result message does not start with 04 0F')
    skip_command_header(msg)
    if pop_byte(msg) != 0x27:
        raise Exception('result data block does not start with 27!')
    result_code = pop_byte(msg)
    if result_code != 0:
        #raise Exception(f'preauth finished with result code {fmt_bytes(result_code)}!')
        print(f'result code not 00 but {fmt_bytes(result_code)}!')
    return parse_bmps(msg)


def parse_res_from_chatfile(filename):
    msg = next(filter(lambda x: x.startswith(b'\x04\x0F'), read_chat_file(filename)))
    return parse_result_msg(msg)


async def main():
    #filename = 'preauth_testkarte3_erfolgreich.log'
    #filename = 'preauth_girocard_eingeschoben.log'
    #filename = 'book_total.log'
    #res = parse_res_from_chatfile(filename)

    mqtt = aiomqtt.Client("192.168.180.2")
    await mqtt.connect()

    ptc = await make_pt_connection('192.168.180.230', 20007)

    # rcpt_no = await ptc.query_pending_pre_auth()
    # if rcpt_no is not None:
    #     data = b'\x87' + rcpt_no + b'\x04' + encode_bcd(6, 1234) + b'\x49' + euro_cc + \
    #            b'\x19' + bytearray([res['payment-type']]) + \
    #            b'\x0B' + encode_bcd(3, res['trace']) + \
    #            b'\x8A' + bytearray([res['card-type']])
    #     data = b'\x06\x24' + bytearray([len(data)]) + data
    #     await ptc.send_and_log_chat(data=data, logfile='book_total.log')

    preauth_res = await ptc.send_preauth(2000)

    await asyncio.sleep(4)

    book_total_res = await ptc.book_total(preauth_res, 1234)

    # await ptc.send_and_log_chat(
    #     data=b'\x05\x01\x03\x00\x00\x00',
    #     logfile='statusenquiry.log.dat'
    # )

#    await ptc.send_and_log_chat(
#        data=b'\x06\x01\x12\x04\x00\x00\x00\x00\x12\x34\x49\x09\x78\x19\x40\x06\x04\x40\x02\xff\x00',
#        logfile='auth_test_febr.log'
#    )

#    await ptc.send_and_log_chat(
#        data=b'\x06\x22\x12\x04\x00\x00\x00\x01\x00\x00\x49\x09\x78\x19\x40\x06\x04\x40\x02\xff\x00',
#        logfile='preauth_feb_giro.log'
#    )

    await mqtt.disconnect()


asyncio.run(main())
