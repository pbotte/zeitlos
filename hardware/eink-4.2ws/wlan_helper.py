import network
import myconfig
import time
import rp2
rp2.country('DE')

wlan = None

def connect(wdt):
    global wlan
    hostname = "eink"+myconfig.CLIENT_UID
    print(f"{hostname=}")
    network.country('DE')
    network.hostname(hostname)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Searching for AP...")
    wlan.config(pm = 0xa11140)  # Disable powersave mode
    #print(wlan.scan())
    wlan.connect(myconfig.wlan_SSID, myconfig.wlan_password)

    print("Waiting for WLAN connection, max 10 sec. ")
    time_left_to_connect = 10.0 #in seconds
    while time_left_to_connect>0:
        if wlan.isconnected(): #connected and got IP
            break
        print(".", end="")
        time.sleep(0.1)
        wdt.feed()
        time_left_to_connect -= 0.1

    print("WLAN connection:",wlan.isconnected())
    print(wlan.ifconfig())


def get_mac_address(wlan):
    #this does only work after the network has been initialised with
    # wlan = network.WLAN(network.STA_IF)
    # wlan.active(True)
    mac_address = wlan.config('mac')
    return ''.join('%02x' % b for b in mac_address)