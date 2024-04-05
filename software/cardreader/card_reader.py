#!/usr/bin/python3

import asyncio
import asyncio_mqtt as aiomqtt
import logging
import argparse
from cr_pt_class import *
import json
import signal


async def make_pt_connection(host, port, mqtt_client, logger):
    ptc = PTConnection(
        *(await asyncio.open_connection(host, port)), mqtt_client, logger
    )
    logger.info(f'TCP connection to terminal established.')

    # registration
    msg = await ptc.send_query(
        b"\x06\x00\x10\x00\x00\x00\x9e\x09\x78\x03\x00\x06\x06\x26\x04\x0a\x02\x06\xd3"
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

    logger.info(f'terminal ready.')

    return ptc


mqtt_client = None
continue_main_loop = True


def handle_sig_int():
    global continue_main_loop
    continue_main_loop = False
    if mqtt_client is not None:
        mqtt_client.disconnect()


signal.signal(signal.SIGINT, handle_sig_int)


async def main():
    global mqtt_client
    # filename = 'preauth_testkarte3_erfolgreich.log'
    # filename = 'preauth_girocard_eingeschoben.log'
    # filename = 'book_total.log'
    # res = parse_res_from_chatfile(filename)

    will = aiomqtt.Will("homie/cardreader/state", payload="0", qos=2, retain=True)
    mqtt_client = aiomqtt.Client(hostname="localhost", port=1883, will=will)
    logger.info(f'MQTT Client created.')
    logger.info(f'Trying to option connection to terminal... (if unsuccesful, check IP address)')
    ptc = await make_pt_connection(args.terminal_ip, 20007, mqtt_client, logger) #comment for age test

    reconnect_interval = 5  # In seconds
    while continue_main_loop:
        try:
            async with mqtt_client as client:
                await client.publish("homie/cardreader/state", payload="1", retain=True)
                await client.publish("homie/cardreader/busy", payload="0", retain=True)
                async with client.messages() as messages:
                    await client.subscribe("homie/cardreader/cmd/#")
                    async for message in messages:
                    #    logger.debug(f"MQTT message: {message.payload.decode(encoding=encoding)}")
                        if message.topic.matches("homie/cardreader/cmd/end_of_day"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            await ptc.end_of_day()
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/auth"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            res = await ptc.authorization(int(message.payload.decode(encoding=encoding)))
                            await client.publish(
                                "homie/cardreader/auth_res", payload=f"{json.dumps(res)}"
                            )
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/pre"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            preauth_res = await ptc.send_preauth(
                                int(message.payload.decode(encoding=encoding))
                            )
                            await client.publish(
                                "homie/cardreader/preauth_res", payload=f"{json.dumps(preauth_res)}"
                            )
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/list"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            rcpt_no, list_rcpt_no = await ptc.query_pending_pre_auth()
                            await client.publish(
                                "homie/cardreader/list_rcpt_no", payload=f"{list_rcpt_no}"
                            )
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/book"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            if "amount" in preauth_res:
                                book_total_res = await ptc.book_total(
                                    preauth_res, int(message.payload.decode(encoding=encoding))
                                )
                                await client.publish(
                                    "homie/cardreader/book_total_res", payload=f"{json.dumps(book_total_res)}"
                                )
                            else:
                                logger.warning(f'No data from last preauth in memory available Stop.')
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/book_json"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            data = json.loads(message.payload.decode(encoding=encoding))
                            if "amount_book" in data:
                                book_total_res = await ptc.book_total(
                                    data, data["amount_book"]
                                )
                                await client.publish(
                                    "homie/cardreader/book_total_res", payload=f"{json.dumps(book_total_res)}"
                                )
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/abort"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            await ptc.abort()
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        elif message.topic.matches("homie/cardreader/cmd/pt_activate_service_menu"):
                            await client.publish("homie/cardreader/busy", retain=True, payload="1")
                            await ptc.pt_activate_service_menu()
                            await client.publish("homie/cardreader/busy", retain=True, payload="0")
                        else:
                            logger.info(f'MQTT message received but not processed: {message.topic}')

        except aiomqtt.MqttError as error:
            logger.error(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)

    await client.publish("homie/cardreader/state", payload="0", retain=True)

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


logging.basicConfig(level=logging.WARNING, format="%(asctime)-6s %(levelname)-8s  %(message)s")
logger = logging.getLogger("cardreader")

parser = argparse.ArgumentParser(description="MQTT 2 ntfy")
parser.add_argument("-v", "--verbosity", help="increase output verbosity", default=0, action="count")
parser.add_argument("-b", "--mqtt-broker-host", help="MQTT broker hostname. default=localhost", default="localhost" )
parser.add_argument("terminal_ip", help="Terminal IP address")
args = parser.parse_args()
logger.setLevel(logging.WARNING - (args.verbosity * 10 if args.verbosity <= 2 else 20))

logger.info(f'cardread starting...')

asyncio.run(main())
