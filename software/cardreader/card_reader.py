#!/usr/bin/python3

import paho.mqtt.client as paho
import asyncio
import asyncio_mqtt as aiomqtt
import logging
import argparse
from cr_pt_class import *
import json
import signal
import sys


loop_var = True
def signal_handler(sig, frame):
    global loop_var
    logger.info('You pressed Ctrl+C! Preparing for graceful termination.')
    loop_var = False
#    sys.exit(0)
#signal.signal(signal.SIGINT, signal_handler) ##not yet solved...

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


async def main():
    # filename = 'preauth_testkarte3_erfolgreich.log'
    # filename = 'preauth_girocard_eingeschoben.log'
    # filename = 'book_total.log'
    # res = parse_res_from_chatfile(filename)
    
    # uncomment for age test
    #data = bytearray(
    #    b'\x04\x0f\xff\xfe\x01\x06\x82\x01\xfa\x1fl\x01\x03\x1f\x12\x01\x02!\x82\x01\xdb\x05\x03\x00\x00\x00\x05\x03\x00\x00\x01\x05\x03\x00\x00\x02\x05\x03\x00\x00\x03\x05\x03\x00\x00\x04\x05\x03\x00\x00\x05\x05\x03\x00\x00\x06\x05\x03\x00\x00\x07\x05\x03\x00\x00\x08\x05\x03\x00\x00\t\x05\x03\x00\x00\x10\x05\x03\x00\x00\x11\x05\x03\x00\x00\x12\x05\x03\x00\x00\x13\x05\x03\x00\x00\x14\x05\x03\x00\x00\x15\x05\x03\x00\x00\x16\x05\x03\x00\x00\x17\x05\x03\x00\x00\x18\x05\x03\x00\x00\x19\x05\x03\x00\x00 \x05\x03\x00\x00!\x05\x03\x00\x00"\x05\x03\x00\x00#\x05\x03\x00\x00$\x05\x03\x00\x00%\x05\x03\x00\x00&\x05\x03\x00\x00\'\x05\x03\x00\x00(\x05\x03\x00\x00)\x05\x03\x00\x000\x05\x03\x00\x001\x05\x03\x00\x002\x05\x03\x00\x003\x05\x03\x00\x004\x05\x03\x00\x005\x05\x03\x00\x006\x05\x03\x00\x007\x05\x03\x00\x008\x05\x03\x00\x009\x05\x03\x00\x00@\x05\x03\x00\x00A\x05\x03\x00\x00B\x05\x03\x00\x00C\x05\x03\x00\x00D\x05\x03\x00\x00E\x05\x03\x00\x00F\x05\x03\x00\x00G\x05\x03\x00\x00H\x05\x03\x00\x00P\x05\x03\x00\x00Q\x05\x03\x00\x00R\x05\x03\x00\x00S\x05\x03\x00\x00T\x05\x03\x00\x00U\x05\x03\x00\x00V\x05\x03\x00\x00W\x05\x03\x00\x00X\x05\x03\x00\x00Y\x05\x03\x00\x00`\x05\x03\x00\x00a\x05\x03\x00\x00b\x05\x03\x00\x00c\x05\x03\x00\x00d\x05\x03\x00\x00e\x05\x03\x00\x00f\x05\x03\x00\x00g\x05\x03\x00\x00\x81\x05\x03\x00\x00\x82\x05\x03\x00\x00\x83\x05\x03\x00\x00\x84\x05\x03\x00\x00\x86\x05\x03\x00\x00\x87\x05\x03\x00\x00\x88\x05\x03\x00\x00\x89\x05\x03\x00\x00\x91\x05\x03\x00\x00\x92\x05\x03\x00\x00\x93\x05\x03\x00\x00\x94\x05\x03\x00\x00\x95\x05\x03\x00\x01\x10\x05\x03\x00\x010\x05\x03\x00\x011\x05\x03\x00\x012\x05\x03\x00\x013\x05\x03\x00\x014\x05\x03\x00\x015\x05\x03\x00\x016\x05\x03\x00\x01\x80\x05\x03\x00\x01\x81\x05\x03\x00\x01\x84\x05\x03\x00\x01\x85\x05\x03\x00\x01\x86\x05\x03\x00\x01\x87\x05\x03\x00\x01\x90b\x11`\x0fC\n\xa0\x00\x00\x03Y\x10\x10\x02\x80\x01A\x01\x05'
    #)
    #res = parse_result_msg(data, logger)

    # Create a LWT
    will = aiomqtt.Will("homie/cardreader/state", payload="0", qos=2, retain=True)

    mqtt_client = aiomqtt.Client(hostname="localhost", port=1883, will=will, keepalive=10) #comment for age test
    logger.info(f'MQTT Client created.')
    logger.info(f'Trying to option connection to terminal... (if unsuccesful, check IP address)')
    ptc = await make_pt_connection(args.terminal_ip, 20007, mqtt_client, logger) #comment for age test
    #ptc = await make_pt_connection("192.168.10.78", 20007, None, logger) #uncomment for age test
    #await ptc.check_age3() #uncomment for age test
    #return  #uncomment for age test

    reconnect_interval = 5  # In seconds
    while loop_var:
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


# sending last state

#client = paho.Client("cardreader") #paho.CallbackAPIVersion.VERSION1, 
#paho.Client.publish.single("homie/cardreader/state", payload="0", qos=2, retain=True, hostname="localhost",
#        port=1883, client_id="cardreader", keepalive=60 )
