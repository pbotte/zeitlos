import asyncio
import asyncio_mqtt as aiomqtt
import logging
import argparse
from cr_helperfunctions import *
from cr_chatfile import *

class PTConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def recv_until_len(self, msg: bytearray, length):
        while len(msg) < length:
            msg += await self.reader.read(length - len(msg))

    async def send_ack(self):
        self.writer.write(b"\x80\x00\x00")
        await self.writer.drain()

    async def recv_ack(self, error='Received "%m" instead of ack'):
        msg = await self.recv_message()
        if msg == b"\x84\x83\x00":
            raise Exception("Unsupported or unknown command!")
        elif msg != b"\x80\x00\x00":
            raise Exception(error.replace("%m", fmt_bytes(msg)))

    async def recv_message(self):
        msg = bytearray()
        await self.recv_until_len(msg, 3)
        if msg[2] < 0xFF:
            expected_len = int(msg[2]) + 3
        else:
            await self.recv_until_len(msg, 5)
            expected_len = int.from_bytes(msg[3:5], byteorder="little") + 5
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


    # returns pending pre_auth from PT
    # 1st parameter: receipt_no 
    # 2nd parameter: list 
    #  example return value:
    #  {35: {8: [b'\x00(', b'\x00)', b'\x000', b'\x001', b'\x002', b'\x003', b'\x004', b'\x005', b'\x006', b'\x007', b'\x008', b'\x009', b'\x00@', b'\x00A']}}
    # where as the first parameter in list is queal to receipt_no
    # hint: receipt_no is needed to finally request money
    async def query_pending_pre_auth(self):
        msg = await self.send_query(b"\x06\x23\x03\x87\xFF\xFF") #2.10.1 Enquire if Pre-Authorisations exist (06 23)
        check_and_skip_command_header(msg, b"\x06\x1E")
        if len(msg) < 4:
            raise Exception("Preauth query response too short!")
        if pop_bytes(msg, 2) != b"\xB8\x87":
            raise Exception("Preauth response data block does not start with B8 87!")
        receipt_no = pop_bytes(msg, 2) #value "receipt-no" returned from card reader
        tlv_return = None # will later be populated with full list of all receipt_no
        if receipt_no == b"\xFF\xFF":
            receipt_no = None
        elif len(msg) > 0:
            tag = pop_byte(msg)
            if tag != 0x06:
                raise Exception(
                    f"Expected TLV container starting with 06 but found byte {fmt_bytes(tag)}"
                )
            tlv_return = parse_tlv_containter(msg)
        logger.info(f"query_pending_pre_auth(): receipt_no: {receipt_no}\n  full list: {tlv_return}")
        return receipt_no, tlv_return

    async def wait_for_and_parse_status(self, msg):
        while msg.startswith(b"\x04\xFF"):
            msg = await self.recv_message()
        if not msg.startswith(b"\x04\x0F"):
            raise Exception(f"Instead 04 0F receivd {fmt_bytes(msg)}")
        return parse_result_msg(msg, logger)

    async def wait_for_completion(self, count):
        for i in range(count):
            logger.debug(f"wait_for_completion(): Loop {i}")
            try:
                msg = await asyncio.wait_for(self.recv_message(), timeout=4)
                if msg == b"\x06\x1E\x01\x6C":
                    logger.error(f"wait_for_completion(): No card within time window presented. Return: {fmt_bytes(msg)}") #Exception
                elif msg != b"\x06\x0F\x00":
                    logger.error(f"wait_for_completion(): Received not completion but {fmt_bytes(msg)}") #Exception
            except asyncio.TimeoutError:
                logger.debug("wait_for_completion(): Gave up waiting, task canceled")
        logger.debug("wait_for_completion(): completed")

    async def send_preauth(self, amount_cents):
        logger.debug("send_preauth(): start")
        msg = await self.send_query(  # see pdf: 2.8 Pre-Authorisation / Reservation (06 22)
            b"\x06\x22\x12\x04"
            + encode_bcd(6, amount_cents)
            + b"\x49"
            + euro_cc
            + b"\x19\x40" #payment type
            + b"\x06\x04\x40\x02\xff\x00"
        )
        logger.debug("send_preauth(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        logger.debug(f"send_preauth(): return: {res}")
        logger.debug("send_preauth(): wait_for_completion")
        await self.wait_for_completion(1)
        logger.debug("send_preauth(): completed")
        return res

    # requesting money from existing reservation. All infomration mandatory from the point when requesting the pre_auth
    async def book_total(self, preauth_res, amount_cents):
        logger.debug("book_total(): start")
        if amount_cents > preauth_res["amount"]:
            raise Exception("Amount bigger than preauth!")
        data = (
            b"\x87"
            + encode_bcd(2, preauth_res["receipt-no"])
            + b"\x04"
            + encode_bcd(6, amount_cents)
            + b"\x49"
            + euro_cc
            + b"\x19"
            + bytearray([preauth_res["payment-type"]])
            + b"\x0B"
            + encode_bcd(3, preauth_res["trace"])
            + b"\x8A"
            + bytearray([preauth_res["card-type"]])
        )
        data = b"\x06\x24" + bytearray([len(data)]) + data
        msg = await self.send_query(data)
        logger.debug("book_total(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        logger.debug("book_total(): wait_for_completion")
        await self.wait_for_completion(1)
        logger.debug("book_total(): completed")
        return res
    
    async def authorization(self, amount_cents): #0see pdf: 0601. Request money without preauth
        logger.debug("authorization(): start")
        data = (
            b"\x04"
            + encode_bcd(6, amount_cents)
            + b"\x49"
            + euro_cc
            + b"\x19\x40" #Payment according to PTs decision excluding GeldKarte
           # + b'\x06\x04\x40\x02\xff\x00' #EMV-Parameter, x02: "the PT should send tag 66", 
        )
        data = b"\x06\x01" + bytearray([len(data)]) + data
        msg = await self.send_query(data)
        logger.debug("authorization(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        logger.debug("authorization(): wait_for_completion")
        await self.wait_for_completion(1)
        logger.debug("authorization(): completed")
        return res
    

    # storno
    # in case the card does not support this, use: book_total(0)
    async def pre_authorisation_reversal(self, rcpt_no: bytearray): # storno, works only for some cards, not maestro and ec-cash
        logger.debug("pre_authorisation_reversal(): start")
        data = (
            b"\x87"
            +rcpt_no
        )
        data = b"\x06\x25" + bytearray([len(data)]) + data

        msg = await self.send_query(data)
        logger.debug("pre_authorisation_reversal(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        logger.debug("pre_authorisation_reversal(): wait_for_completion")
        await self.wait_for_completion(1)
        logger.debug("pre_authorisation_reversal(): completed")
        return res


    # end of day
    # clear list of preauths
    async def end_of_day(self):
        logger.debug("end_of_day(): start")
        data = (b'\x00\x00\x00')
        data = b"\x06\x50" + bytearray([len(data)]) + data

        msg = await self.send_query(data)
        logger.debug("end_of_day(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        logger.debug("pre_autend_of_dayhorisation_reversal(): wait_for_completion")
        await self.wait_for_completion(1)
        logger.debug("end_of_day(): completed")
        return res





    async def send_and_log_chat(
        self, data, logfile, complete_code=b"\x06\x0F", prefix=True
    ):
        with ChatFile(logfile) as f:
            f.write_msg(data)
            msg = await self.send_query(data)
            f.write_msg(msg)
            while not msg.startswith(complete_code):
                msg = await self.recv_message()
                f.write_msg(msg)
            f.write_msg(msg)


async def make_pt_connection(host, port):
    ptc = PTConnection(*(await asyncio.open_connection(host, port)))

    # registration
    msg = await ptc.send_query(
        b"\x06\x00\x10\x00\x00\x00\x08\x09\x78\x03\x00\x06\x06\x26\x04\x0a\x02\x06\xd3"
    )
    check_and_skip_command_header(msg, b"\x06\x0F")
    tlv = None
    while len(msg) > 0:
        tag = pop_byte(msg)
        if tag == 0x19:
            data = pop_byte(msg)
            if data & 1:
                raise Exception("PT initialization necessary")
            if data & 2:
                raise Exception("Diagnosis necessary")
            if data & 4:
                raise Exception("OPT action necessary")
            ptc.filling_station_mode = bool(data & 8)
            ptc.vending_machine_mode = bool(data & 16)
        elif tag == 0x29:
            ptc.tid = bytes(pop_bytes(msg, 4))
        elif tag == 0x49:
            cc = pop_bytes(msg, 2)
            if cc != euro_cc:
                raise Exception(
                    f"Received currency code {fmt_bytes(cc)} instead of expected € code {fmt_bytes(euro_cc)} after registration"
                )
        elif tag == 0x06:
            tlv = parse_tlv_containter(msg)
        else:
            raise Exception(
                f"Received unexpected tag {fmt_bytes(tag)} after registration"
            )
    if tlv is not None:
        supported_commands = take_from_dict(tlv, 38, 10)
        if supported_commands is not None:
            ptc.supported_commands = supported_commands
            if b"\x05\x01" not in supported_commands:
                raise Exception("Terminal does not support status enquiry")

    # status enquiry
    msg = await ptc.send_query(b"\x05\x01\x03\x00\x00\x00")
    while status := try_parse_intermediate_status(msg):
        msg = await ptc.recv_message()
    check_and_skip_command_header(msg, b"\x06\x0F")
    ptc.software_version = parse_lvar(3, msg)
    if len(msg) == 0:
        raise Exception("Status enquiry response too short!")
    if msg[0] == 0xDC:
        # raise Exception('Terminal not ready because card inserted!')
        logger.warning("terminal not ready - card still inserted")
    elif msg[0] != 0x00:
        # raise Exception(f'Terminal not ready - returned status byte {fmt_bytes(msg[0])}')
        logger.warning(f"terminal not ready - error status {fmt_bytes(msg[0])}")
        pass

    return ptc


async def main():
    # filename = 'preauth_testkarte3_erfolgreich.log'
    # filename = 'preauth_girocard_eingeschoben.log'
    # filename = 'book_total.log'
    # res = parse_res_from_chatfile(filename)

    mqtt = aiomqtt.Client("192.168.180.2")
    #    await mqtt.connect()

    ptc = await make_pt_connection("192.168.179.167", 20007)

    #Request directly some money
#    await ptc.authorization(5000)

    preauth_res = await ptc.send_preauth(5000)

    rcpt_no, list_rcpt_no = await ptc.query_pending_pre_auth()


    #reverse pre_auth
 #   await ptc.pre_authorisation_reversal(list_rcpt_no[35][8][-1]) #the last entry in list = list_rcpt_no[35][8][-1]



    if "amount" in preauth_res:
      book_total_res = await ptc.book_total(preauth_res, 1111)

    await ptc.end_of_day()


    # await ptc.send_and_log_chat(
    #     data=b'\x05\x01\x03\x00\x00\x00',
    #     logfile='statusenquiry.log.dat'
    # )


#    await ptc.send_and_log_chat(
#        data=b'\x06\x22\x12\x04\x00\x00\x00\x01\x00\x00\x49\x09\x78\x19\x40\x06\x04\x40\x02\xff\x00',
#        logfile='preauth_feb_giro.log'
#    )

#    await mqtt.disconnect()


logging.basicConfig(
    level=logging.WARNING, format="%(asctime)-6s %(levelname)-8s  %(message)s"
)
logger = logging.getLogger("cardreader")

parser = argparse.ArgumentParser(description="MQTT 2 ntfy")
parser.add_argument(
    "-v", "--verbosity", help="increase output verbosity", default=0, action="count"
)
parser.add_argument(
    "-b",
    "--mqtt-broker-host",
    help="MQTT broker hostname. default=localhost",
    default="localhost",
)
args = parser.parse_args()
logger.setLevel(logging.WARNING - (args.verbosity * 10 if args.verbosity <= 2 else 20))


asyncio.run(main())
