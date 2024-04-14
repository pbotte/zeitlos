import asyncio
import asyncio_mqtt as aiomqtt
import logging
import json
from cr_helperfunctions import *
from cr_chatfile import *


encoding = 'latin-1'


class PTConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, mqtt_client: aiomqtt.Client = None, logger:logging=None):
        self.reader = reader
        self.writer = writer
        self.mqtt_client = mqtt_client
        self.logger = logger

    def set_mqtt_client(self, client):
        self.mqtt_client = client

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

        elif msg.startswith(b"\x06\xD3"): # text block
                    if self.mqtt_client:
                        skip_command_header(msg)
                        if pop_byte(msg) != 0x06:
                            raise Exception('Test block data does not start with 06')
                        tlv = parse_tlv_containter(msg)
                        if 0x25 in tlv and 7 in tlv[0x25]:
                            await self.mqtt_client.publish("homie/cardreader/text_block",
                                payload="\n".join(map(lambda l: l.decode(encoding=encoding), tlv[0x25][7])))
                        else:
                            self.logger.error("text block in 06 D3 message not found")

        elif msg.startswith(b"\x04\xFF"):
                  skip_command_header(msg)
                  if self.mqtt_client and len(msg) > 3 and msg[2] == 6:
                      del msg[:3]
                      tlv = parse_tlv_containter(msg)
                      if text := tlv.get(0x24):
                          if line := text.get(0x07):
                              if type(line) == list:
                                  line_printout = ' '.join(x.decode(encoding=encoding) for x in line)
                              else:
                                  line_printout = line.decode(encoding=encoding)
                              self.logger.info(f"{line_printout=}")
                              await self.mqtt_client.publish("homie/cardreader/text", payload=f'{json.dumps(line_printout)}')


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

    async def do_with_timeout(self, awaitable, timeout_secs):
        msg = 1
        try:
            msg = await asyncio.wait_for(awaitable, timeout_secs)
        except asyncio.TimeoutError:
            if self.mqtt_client:
                await self.mqtt_client.publish("homie/cardreader/timeout", payload=timeout_secs)
        return msg


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
        self.logger.info(f"query_pending_pre_auth(): receipt_no: {receipt_no}\n  full list: {tlv_return}")
        return receipt_no, tlv_return

    async def wait_for_and_parse_status(self, msg):
        while msg.startswith(b"\x04\xFF"):
            skip_command_header(msg)
            if self.mqtt_client and len(msg) > 3 and msg[2] == 6:
                del msg[:3]
                tlv = parse_tlv_containter(msg)
                if text := tlv.get(0x24):
                    if line := text.get(0x07):
                        if type(line) == list:
                            line_printout = ' '.join(x.decode(encoding=encoding) for x in line)
                        else:
                            line_printout = line.decode(encoding=encoding)
                        self.logger.info(f"{line_printout=}")
                        await self.mqtt_client.publish("homie/cardreader/text", payload=f'{json.dumps(line_printout)}')
            msg = await self.recv_message()

        if msg.startswith(b"\x06\xD3"): # text block
          if self.mqtt_client:
                        skip_command_header(msg)
                        if pop_byte(msg) != 0x06:
                            raise Exception('Test block data does not start with 06')
                        tlv = parse_tlv_containter(msg)
                        if 0x25 in tlv and 7 in tlv[0x25]:
                            await self.mqtt_client.publish("homie/cardreader/text_block",
                                payload="\n".join(map(lambda l: l.decode(encoding=encoding), tlv[0x25][7])))
                        else:
                            self.logger.error("text block in 06 D3 message not found")
          msg = await self.recv_message()

        if not msg.startswith(b"\x04\x0F"):
            raise Exception(f"Instead 04 0F receivd {fmt_bytes(msg)}")
        return parse_result_msg(msg, self.logger)

    async def wait_for_completion(self, count):
        res = 0
        i = 0
        while (i:=i+1) <= count:
            self.logger.debug(f"wait_for_completion(): Loop {i}")
            try:
                msg = await asyncio.wait_for(self.recv_message(), timeout=10)
#                msg = await self.do_with_timeout(self.recv_message(),10)
                if msg.startswith(b"\x06\xD3"): # text block
                    i -= 1
                    if self.mqtt_client:
                        skip_command_header(msg)
                        if pop_byte(msg) != 0x06:
                            raise Exception('Test block data does not start with 06')
                        tlv = parse_tlv_containter(msg)
                        if 0x25 in tlv and 7 in tlv[0x25]:
                            await self.mqtt_client.publish("homie/cardreader/text_block",
                                payload="\n".join(map(lambda l: l.decode(encoding=encoding), tlv[0x25][7])))
                        else:
                            self.logger.error("text block in 06 D3 message not found")

                elif msg.startswith(b"\x04\xFF"):
                  skip_command_header(msg)
                  if self.mqtt_client and len(msg) > 3 and msg[2] == 6:
                      del msg[:3]
                      tlv = parse_tlv_containter(msg)
                      if text := tlv.get(0x24):
                          if line := text.get(0x07):
                              if type(line) == list:
                                  line_printout = ' '.join(x.decode(encoding=encoding) for x in line)
                              else:
                                  line_printout = line.decode(encoding=encoding)
                              self.logger.info(f"{line_printout=}")
                              await self.mqtt_client.publish("homie/cardreader/text", payload=f'{json.dumps(line_printout)}')

                elif msg == b"\x06\x1E\x01\x6C":
                    self.logger.info(f"wait_for_completion(): No card within time window presented. Return: {fmt_bytes(msg)}") #Exception
                    res = 1
                elif msg == b"\x06\x0F\x00":
                    self.logger.warning(f"wait_for_completion(): Received completion, with: {fmt_bytes(msg)}")
                    res = 0 #payment completed, often in 2nd loop.
                else:
                    self.logger.error(f"wait_for_completion(): Received not completion but {fmt_bytes(msg)}") #Exception
                    #this often happens in the first loop, when some text data is received
                    res = 2
            except asyncio.TimeoutError:
                self.logger.debug("wait_for_completion(): Gave up waiting, task canceled")
                res = -1*abs(res) #value negative if some timeout occured, to preserve possible absolute value
        self.logger.debug(f"wait_for_completion(): completed. result: {res}")
        return res

    async def send_preauth(self, amount_cents):
        self.logger.debug("send_preauth(): start")
        msg = await self.send_query(  # see pdf: 2.8 Pre-Authorisation / Reservation (06 22)
            b"\x06\x22\x12\x04"
            + encode_bcd(6, amount_cents)
            + b"\x49"
            + euro_cc
            + b"\x19\x40" #payment type
            + b"\x06\x04\x40\x02\xff\x00"
        )
        self.logger.debug("send_preauth(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"send_preauth(): wait_for_completion. result {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"send_preauth(): completed, res2: {res2}")
        res["return_code_completion"] = res2
    
        if self.mqtt_client:
            if res2==0: #succesful
                data = {"amount": res['amount'], "trace": res['trace'], "payment-type": res['payment-type'], "receipt-no": res['receipt-no'], "card-type": res['card-type'], "amount_book": -1}
                await self.mqtt_client.publish("homie/cardreader/data_for_book_total_json", payload=json.dumps(data))
            
        return res

    # requesting money from existing reservation. All infomration mandatory from the point when requesting the pre_auth
    async def book_total(self, preauth_res, amount_cents):
        self.logger.debug("book_total(): start")
        if amount_cents > preauth_res["amount"]:
            raise Exception("Amount bigger than preauth!")
        if amount_cents < 0:
            raise Exception("Amount is negative!")
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
        self.logger.debug("book_total(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"book_total(): wait_for_completion. result {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"book_total(): completed. result: {res2}")
        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/book_total", payload=f"{res2}")
        return res
    
    # Abort
    # does not currently work as it is not sent immediatelly if another operation (eg wait_for_and_parse_status) is still running
    async def abort(self): # see pdf: 2.23 Abort (06 B0)
        self.logger.debug("abort(): start")
        data = b"\x06\xB0\x00"
        msg = await self.send_query(data)
        self.logger.debug("abort(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"abort(): wait_for_completion. result: {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"abort(): completed. result: {res2}")
        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/abort", payload=f"{res2}")
        return res
    

    # Switch into menu
    # just sends the first few bytes and does only wait a few seconds for end service mode (leave menu by technican)
    # currently necessary to restart software to get in sync with the PT again
    async def pt_activate_service_menu(self): # see pdf: 2.55 Activate Service-Mode (08 01)
        self.logger.debug("pt_activate_service_menu(): start")
        data = b"\x08\x01\x00"
        msg = await self.send_query(data)
        self.logger.debug("pt_activate_service_menu(): wait_for_and_parse_status")
#        res = await self.wait_for_and_parse_status(msg)
#        self.logger.debug(f"pt_activate_service_menu(): wait_for_completion. result: {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"pt_activate_service_menu(): completed. result: {res2}")
#        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/pt_activate_service_menu", payload=f"{res2}")
        return res2    

    # Request directly some money, wihtout pre_auth
    async def authorization(self, amount_cents): #0see pdf: 0601. Request money without preauth
        self.logger.debug("authorization(): start")
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
        self.logger.debug("authorization(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"authorization(): wait_for_completion. result: {res}")
        res2 = await self.wait_for_completion(2)
        self.logger.debug(f"authorization(): completed. result: {res2}")
        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/authorization", payload=f"{res2}")
        return res
    

    # storno
    # in case the card does not support this, use: book_total(0)
    async def pre_authorisation_reversal(self, rcpt_no: bytearray): # storno, works only for some cards, not maestro and ec-cash
        self.logger.debug("pre_authorisation_reversal(): start")
        data = (
            b"\x87"
            +rcpt_no
        )
        data = b"\x06\x25" + bytearray([len(data)]) + data

        msg = await self.send_query(data)
        self.logger.debug("pre_authorisation_reversal(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"pre_authorisation_reversal(): wait_for_completion. result: {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"pre_authorisation_reversal(): completed. result: {res2}")
        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/pre_authorisation_reversal", payload=f"{res2}")
        return res


    # end of day
    # clear list of preauths
    async def end_of_day(self):
        self.logger.debug("end_of_day(): start")
        data = (b'\x00\x00\x00')
        data = b"\x06\x50" + bytearray([len(data)]) + data

        msg = await self.send_query(data)
        self.logger.debug("end_of_day(): wait_for_and_parse_status")
        res = await self.wait_for_and_parse_status(msg)
        self.logger.debug(f"pre_autend_of_dayhorisation_reversal(): wait_for_completion. result: {res}")
        res2 = await self.wait_for_completion(1)
        self.logger.debug(f"end_of_day(): completed. result: {res2}")
        res["return_code_completion"] = res2
        if self.mqtt_client:
            await self.mqtt_client.publish("homie/cardreader/end_of_day", payload="done")
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

