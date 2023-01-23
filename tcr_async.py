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


def parse_lenght_bytes(msg):
    if msg[0] == 0xFF:
        length = int.from_bytes(msg[1:3], byteorder='little')
        del msg[:3]
    else:
        length = msg[0]
        del msg[:1]
    return length


def skip_command_header(msg):
    del msg[:2]
    return parse_lenght_bytes(msg)


def fmt_bytes(bytes):
    if type(bytes) == int:
        return fmt_bytes(bytearray([bytes]))
    return bytes.hex(sep=' ').upper()


def parse_lllvar(msg):
    if len(msg) < 3:
        raise Exception(f'Tried to parse LLLVAR with {len(msg)} bytes')
    length = 0
    for i in range(3):
        length *= 10
        if (msg[i] & 0xF0) != 0xF0:
            raise Exception(f'Tried to parse LLVAR with {fmt_bytes(msg[i])} as {i}th byte')
        length += msg[i] & 0x0F
    del msg[:3]
    if len(msg) < length:
        raise Exception(f'Length of message is shorter ({len(msg)} bytes than LLVAR encoded length ({length} bytes)')
    res = bytes(msg[:length])
    del msg[:length]
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

    # async def send_auth(self, amount):
    #     cents = int(round(amount * 100))
    #     amount_bytes = bytearray(6)
    #     for i in range(6, -1, -1):
    #         low = cents % 10
    #         cents //= 10
    #         high = cents % 10
    #         cents //= 10
    #         amount_bytes[i] = low + 16 * high
    #     msg = self.send_query(b'\x06\x01\x12\x04' + amount_bytes + b'\x49' + euro_cc + b'\x19\x40\x06\x04\x40\x02\xff\x00')
    #     while status := try_parse_intermediate_status():
    #         msg = self.recv_message()
    #     check_and_skip_command_header(msg, b'\x04\x0F')

    async def query_pending_pre_auth(self):
        msg = await self.send_query(b'\x06\x23\x03\x87\xFF\xFF')
        check_and_skip_command_header(msg, b'\x06\x1E')
        if len(msg) < 4:
            raise Exception('Preauth query response too short!')
        if msg[:2] != b'\xB8\x87':
            raise Exception('Preauth response data block does not start with B8 87!')
        return None if msg[2:4] == b'\xFF\xFF' else msg[2:4]


    async def send_and_log_chat(self, data, logfile, complete_code=b'\x06\x0F', prefix=True):
        with ChatFile(logfile) as f:
            f.write_msg(data)
            msg = await self.send_query(data)
            f.write_msg(msg)
            while not msg.startswith(complete_code):
                msg = await self.recv_message()
                f.write_msg(msg)
            f.write_msg(msg)


def parse_tlv_entry(msg: bytearray, is_primitive: bool):
    if len(msg) == 0:
        raise Exception('Tried to parse empty TLV entry')
    # parse length
    if not (msg[0] & 0x80):
        tlv_len = msg[0]
        del msg[0]
    elif msg[0] == 0x81:
        if len(msg) == 1:
            raise Exception("Incomplete 2 byte TLV length found")
        tlv_len = msg[1]
        del msg[:2]
    elif msg[0] == 0x82:
        tlv_len = int.from_bytes(msg[1:3], byteorder='big')
        del msg[:3]
    else:
        raise Exception(f'Unexpected TLV length byte {fmt_bytes(msg[0])}')
    if len(msg) < tlv_len:
        raise Exception(f'Remaining data ({len(msg)} bytes) shorter than TLV entry ({tlv_len})')
    if is_primitive:
        data = bytes(msg[:tlv_len])
        del msg[:tlv_len]
        return data
    ret = dict()
    while len(msg) > 0:
        class_type = msg[0] >> 6
        if class_type == 0:
            class_type_string = 'universal'
        elif class_type == 1:
            class_type_string = 'application'
        elif class_type == 2:
            class_type_string = 'context-specific'
        else:
            class_type_string = 'private'
        is_primitive = (msg[0] & 32) == 0
        tag_no = int(msg[0] & 31)
        del msg[0]
        if tag_no == 31:
            tag_no = 0
            while True:
                next_byte = msg[0]
                del msg[0]
                tag_no |= next_byte & 127
                if not (next_byte & 128):
                    break
                tag <<= 7
        key = (class_type_string, tag_no)
        existing = ret.get(key)
        if existing is None:
            ret[key] = parse_tlv_entry(msg, is_primitive)
        else:
            if type(existing) != list:
                ret[key] = [existing]
            ret[key].append(parse_tlv_entry(msg, is_primitive))
    return ret


# parse TLV container, first byte must be x06
def parse_tlv_containter(msg: bytearray):
    if msg[0] != 6:
        raise Exception(f'TLV container does not start with 06 but {fmt_bytes(msg[0])}')
    del msg[0]
    return parse_tlv_entry(msg, False)


class Dummy:
    def __init__(self) -> None:
        pass


def get_recursive(key, d: dict):
    for k, v in d.items():
        if type(v) == dict:
            found = get_recursive(key, v)
            if found is not None:
                return found
        elif k == key:
            return v


def try_parse_intermediate_status(msg):
    if not msg.startswith(b'\x04\xFF'):
        return None
    skip_command_header(msg)
    res = dict()
    res['status'] = msg[0]
    del msg[0]
    if len(msg) > 0:
        res['timeout_min'] = msg[0]
        del msg[0]
        if len(msg) > 0:
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
        if msg[0] == 0x19:
            if msg[1] & 1:
                raise Exception('PT initialization necessary')
            if msg[1] & 2:
                raise Exception('Diagnosis necessary')
            if msg[1] & 4:
                raise Exception('OPT action necessary')
            ptc.filling_station_mode = bool(msg[1] & 8)
            ptc.vending_machine_mode = bool(msg[1] & 16)
            msg = msg[2:]
        elif msg[0] == 0x29:
            ptc.tid = msg[1:5]
            msg = msg[5:]
        elif msg[0] == 0x49:
            if msg[1:3] != euro_cc:
                raise Exception(f'Received currency code {fmt_bytes(msg[1:3])} instead of expected € code {fmt_bytes(euro_cc)} after registration')
            msg = msg[3:]
        elif msg[0] == 0x06:
            tlv = parse_tlv_containter(msg)
        else:
            raise Exception(f'Received unexpected tag {fmt_bytes(msg[0])} after registration')
    if tlv is not None:
        supported_commands = get_recursive(('universal', 10), tlv)
        if supported_commands is not None:
            ptc.supported_commands = supported_commands
            if b'\x05\x01' not in supported_commands:
                raise Exception('Terminal does not support status enquiry')

    # status enquiry
    msg = await ptc.send_query(b'\x05\x01\x03\x00\x00\x00')
    while status := try_parse_intermediate_status(msg):
        msg = await ptc.recv_message()
    check_and_skip_command_header(msg, b'\x06\x0F')
    ptc.software_version = parse_lllvar(msg)
    if len(msg) == 0:
        raise Exception('Status enquiry response too short!')
    if msg[0] == 0xDC:
        raise Exception('Terminal not ready because card inserted!')
    elif msg[0] != 0x00:
        raise Exception(f'Terminal not ready - returned status byte {fmt_bytes(msg[0])}')

    return ptc


async def main():
    bb = b'\xAB\x01'
    x = fmt_bytes(bb[0])

    mqtt = aiomqtt.Client("192.168.180.2")
    await mqtt.connect()

    ptc = await make_pt_connection('192.168.180.230', 20007)

    rcpt_no = await ptc.query_pending_pre_auth()
    if rcpt_no is not None:
        raise Exception(f'There is a pending pre auth with receipt no. {fmt_bytes(rcpt_no)}')

    # await ptc.send_and_log_chat(
    #     data=b'\x05\x01\x03\x00\x00\x00',
    #     logfile='statusenquiry.log.dat'
    # )

    # await ptc.send_and_log_chat(
    #    data=b'\x06\x01\x12\x04\x00\x00\x00\x00\x12\x34\x49\x09\x78\x19\x40\x06\x04\x40\x02\xff\x00',
    #    logfile='auth2.log'
    # )

    await ptc.send_and_log_chat(
        data=b'\x06\x22\x12\x04\x00\x00\x00\x01\x00\x00\x49\x09\x78\x19\x40\x06\x04\x40\x02\xff\x00',
        logfile='preauth.log'
    )

    await mqtt.disconnect()


asyncio.run(main())
