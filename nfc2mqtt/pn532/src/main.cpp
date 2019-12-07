#include <Arduino.h>
#include <SoftwareSerial.h>
#include <PN532_SWHSU.h>
#include <PN532.h>

SoftwareSerial SWSerial( 10, 11 ); // RX, TX
PN532_SWHSU pn532swhsu( SWSerial );
PN532 nfc( pn532swhsu );

void setup(void) {
  Serial.begin(115200);
  Serial.println("{\"status\":\"started\"}");
  byte tries = 10;
  uint32_t versiondata=0;
  while ((tries>0) && (!versiondata)) {
    nfc.begin();
    versiondata = nfc.getFirmwareVersion();
    if (!versiondata) {
      Serial.println("{\"status\":\"No PN53x module found.\"}");
      delay(100);
      tries--;
    }
  }
  if (!versiondata) {
    Serial.println("{\"status\":\"Finally no PN53x module found.\"}");
    while (1); // Halt
  }

  // Got valid data, print it out!  
  Serial.print("{\"system\":{\"chipType\":\"PN5");
  Serial.print((versiondata>>24) & 0xFF, HEX);
  Serial.print("\", \"firmware\":\"");
  Serial.print((versiondata>>16) & 0xFF, DEC);
  Serial.print('.'); 
  Serial.print((versiondata>>8) & 0xFF, DEC);
  Serial.println("\"} }");

  // Configure board to read RFID tags
  nfc.SAMConfig();
  Serial.println("{\"status\":\"waiting for ISO14443A cards\"}");
}

void loop(void) {
  boolean success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
  uint8_t uidLength;                       // Length of the UID (4 or 7 bytes depending on ISO14443A card type)
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, &uid[0], &uidLength);
  if (success) {
//    Serial.println("Found A Card!");
//    Serial.print("UID Length: ");Serial.print(uidLength, DEC);Serial.println(" bytes");
    Serial.print("{\"cardUID\": \"0x");
    for (uint8_t i=0; i < uidLength; i++) {
      Serial.print(uid[i], HEX);
    }
    Serial.println("\"}");
    delay(1000);
  } else {
    // PN532 probably timed out waiting for a card
    Serial.println("{\"status\": \"waiting for ISO14443A cards\"}");
    delay(100);
  }
}
