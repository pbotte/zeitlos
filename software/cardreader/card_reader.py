import asyncio
import asyncio_mqtt as aiomqtt
import logging
import argparse
from cr_pt_class import *
import json


async def make_pt_connection(host, port, mqtt_client, logger):
    ptc = PTConnection(
        *(await asyncio.open_connection(host, port)), mqtt_client, logger
    )

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

    mqtt_client = aiomqtt.Client(hostname="192.168.178.93", port=1884)
    ptc = await make_pt_connection("192.168.179.167", 20007, mqtt_client, logger)

    reconnect_interval = 5  # In seconds
    while True:
        try:
            async with mqtt_client as client:
                async with client.messages() as messages:
                    await client.subscribe("#")
                    async for message in messages:
                        print(message.payload.decode())
                        if message.topic.matches("homie/cardreader/cmd/end_of_day"):
                            await ptc.end_of_day()
                        if message.topic.matches("homie/cardreader/cmd/auth"):
                            await ptc.authorization(int(message.payload.decode()))
                        if message.topic.matches("homie/cardreader/cmd/pre"):
                            preauth_res = await ptc.send_preauth(
                                int(message.payload.decode())
                            )
                            await client.publish(
                                "preauth_res", payload=f"{preauth_res}"
                            )
                        if message.topic.matches("homie/cardreader/cmd/list"):
                            rcpt_no, list_rcpt_no = await ptc.query_pending_pre_auth()
                            await client.publish(
                                "list_rcpt_no", payload=f"{list_rcpt_no}"
                            )
                        if message.topic.matches("homie/cardreader/cmd/book"):
                            if "amount" in preauth_res:
                                book_total_res = await ptc.book_total(
                                    preauth_res, int(message.payload.decode())
                                )
                                await client.publish(
                                    "book_total_res", payload=f"{book_total_res}"
                                )
                        if message.topic.matches("homie/cardreader/cmd/book_json"):
                            data = json.loads(message.payload.decode())
                            if "amount_book" in data:
                                book_total_res = await ptc.book_total(
                                    data, data["amount_book"]
                                )
                                await client.publish(
                                    "book_total_res", payload=f"{book_total_res}"
                                )
                        if message.topic.matches("homie/cardreader/cmd/abort"):
                            await ptc.abort()
                        if message.topic.matches("homie/cardreader/cmd/pt_activate_service_menu"):
                            await ptc.pt_activate_service_menu()

        except aiomqtt.MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)

    # reverse pre_auth
    #   await ptc.pre_authorisation_reversal(list_rcpt_no[35][8][-1]) #the last entry in list = list_rcpt_no[35][8][-1]

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
