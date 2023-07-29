// Scale Set MAC address

#include <mac_address.h>
#include <EEPROM.h>

// Data from EEPROM
#define I2C_ADDRESS 119

void setup()
{
  // Sleep at the beginning, to make sure voltages are stabilised,
  // see: https://github.com/SpenceKonde/megaTinyCore/tree/master/megaavr/libraries/EEPROM
  delay(100);

  Serial.begin(115200);

  Serial.print("Flash date: ");
  Serial.println(FLASH_DATE);

  Serial.print("Set scale MAC address: ");
  Serial.println(MAC_ADDRESS_NUMBER);

  Serial.print("MAC address:");

  Serial.print(" 0x");
  if (MAC_ADDRESS_5 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_5, HEX);

  Serial.print(" 0x");
  if (MAC_ADDRESS_4 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_4, HEX);

  Serial.print(" 0x");
  if (MAC_ADDRESS_3 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_3, HEX);

  Serial.print(" 0x");
  if (MAC_ADDRESS_2 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_2, HEX);

  Serial.print(" 0x");
  if (MAC_ADDRESS_1 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_1, HEX);

  Serial.print(" 0x");
  if (MAC_ADDRESS_0 <= 0xf) Serial.print("0");
  Serial.print(MAC_ADDRESS_0, HEX);

  Serial.println();

  Serial.print("I2C address: ");
  Serial.print(I2C_ADDRESS);
  Serial.print("(dec) 0x");
  Serial.print(I2C_ADDRESS, HEX);
  Serial.println("(hex)");


  Serial.print("Start writing to EEPROM... ");
  // DEBUG
  EEPROM.write(0, MAC_ADDRESS_5);
  EEPROM.write(1, MAC_ADDRESS_4);
  EEPROM.write(2, MAC_ADDRESS_3);
  EEPROM.write(3, MAC_ADDRESS_2);
  EEPROM.write(4, MAC_ADDRESS_1);
  EEPROM.write(5, MAC_ADDRESS_0);

  EEPROM.write(6, I2C_ADDRESS);

  Serial.println("Done.");
}

void loop()
{
}
