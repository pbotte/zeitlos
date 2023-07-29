#!/usr/bin/python
FILENAME_MACADDRESS = 'mac_address'
FILENAME_MACADDRESS_H = 'include/mac_address.h'
version = 'v1.'

import datetime

mac_address = 0
try:
    with open(FILENAME_MACADDRESS) as f:
        mac_address = int(f.readline()) + 1
except:
    print('Starting build number from 1..')
    mac_address = 1
with open(FILENAME_MACADDRESS, 'w+') as f:
    f.write(str(mac_address))
    print('MAC address: {}'.format(mac_address))

temp = mac_address
mac_address_0 = temp  & 0xff
temp = temp >> 8
mac_address_1 = temp  & 0xff
temp = temp >> 8
mac_address_2 = temp  & 0xff

mac_address_3 = 0x0
mac_address_4 = 0x0
mac_address_5 = 0x1

hf = f"""
#ifndef MAC_ADDRESS_NUMBER
  #define MAC_ADDRESS_NUMBER {mac_address}
  #define MAC_ADDRESS_0 {mac_address_0}
  #define MAC_ADDRESS_1 {mac_address_1}
  #define MAC_ADDRESS_2 {mac_address_2}
  #define MAC_ADDRESS_3 {mac_address_3}
  #define MAC_ADDRESS_4 {mac_address_4}
  #define MAC_ADDRESS_5 {mac_address_5}
#endif
#ifndef FLASH_DATE
  #define FLASH_DATE "{datetime.datetime.now()}"
#endif
"""
with open(FILENAME_MACADDRESS_H, 'w+') as f:
    f.write(hf)
