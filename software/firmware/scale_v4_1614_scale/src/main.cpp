// Scale

#include <Wire.h>
#include <SoftWire.h>
#include <AsyncDelay.h>
#include <version.h>
#include <EEPROM.h>

// Soft I2C START
SoftWire sw(6, 7);
// These buffers must be at least as large as the largest read or write you perform.
char swTxBuffer[16];
char swRxBuffer[16];

AsyncDelay readInterval;
// Soft I2C END

// NAU Start
// Funktioniert mit Soft I2C nur mit geänderter Library
#include "SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h" // Click here to get the library: http://librarymanager/All#SparkFun_NAU8702

NAU7802 myScale;                          // Create instance of the NAU7802 class
#define NUMBER_OF_SCALE_READINGS_BUFFER 8 // should multiple of 2^N for fast division
long last_scale_raw_readings[NUMBER_OF_SCALE_READINGS_BUFFER];
byte last_scale_raw_readings_ringbuffer_index = 0; // points to the actual index used
long averaged_reading_sum = 0;                     // helper variable to average all entries in last_scale_raw_readings. needs to be divided by NUMBER_OF_SCALE_READINGS_BUFFER to get real average
long averaged_reading = 0;                         // regularly updated: averaged_reading_sum/NUMBER_OF_SCALE_READINGS_BUFFER
long last_scale_raw_reading = 0;                   // raw value from ADC
// NAU END

// Data from EEPROM
byte eeprom_i2c_address;
byte eeprom_mac_address[6];

bool answer_bit = false; // If set to false, device will not answer on I2C address 0x8
bool update_i2c_address_from_eeprom = false;
bool restart_at_next_possibility = false;
byte register_select_readout = 0;
byte register_compare_mac_address[6];

/// Watchdog, see: https://github.com/SpenceKonde/megaTinyCore/blob/master/megaavr/extras/Ref_Reset.md
void wdt_enable()
{
  _PROTECTED_WRITE(WDT.CTRLA, WDT_PERIOD_4KCLK_gc); // no window, 4 seconds
}

void wdt_reset()
{
  __asm__ __volatile__("wdr" ::);
}

void wdt_disable()
{
  _PROTECTED_WRITE(WDT.CTRLA, 0);
}
/// Watchdog end

/// Reset Device via Software
// Better do not use during I2C access: No ack to I2C will be send!
//Better let the watchdog bite
void resetViaSWR()
{
  _PROTECTED_WRITE(RSTCTRL.SWRR, 1);
}
/// END Reset

// Write request handler, expected: Wire.read
void receiveEvent(int numBytes)
{
  uint8_t addr = Wire.getIncomingAddress(); // get the address that triggered this function
  addr = addr >> 1;                         // shift to the address bits, not r/w bit.

  Serial.print("Write by master on address: 0x");
  Serial.print(addr, HEX);
  Serial.print(" length: ");
  Serial.println(numBytes);

  if (addr == 0x0)
  { // General call address
    // while (Wire.available())
    if (numBytes >= 1)
    {
      char c = Wire.read();
      Serial.print("data: 0x");
      Serial.println(c, HEX);
      Serial.flush();

      if (c == 0x00)
      {             // Reset scale
        Serial.println("Restart scale");
        Serial.flush();
        delay(100); // To allow serial data flush
        restart_at_next_possibility = true;
      }
      if (c == 0x01)
      { // Reset answer bit
        answer_bit = true;
      }
      if ((c == 0x02) && (numBytes == 8))
      { // Set I2C address, 8 bytes: 0x2 6bytes MAC address and 1byte I2C address
        byte temp_mac_address[6];
        for (byte i = 0; i < 6; i++)
        {
          temp_mac_address[i] = Wire.read();
        }
        byte temp_i2c_address = Wire.read();

        // check
        bool equal = true;
        for (byte i = 0; i < 6; i++)
        {
          if (eeprom_mac_address[i] != temp_mac_address[i])
          {
            equal = false;
          }
        }

        // Set I2C address
        if (equal)
        {
          answer_bit = false;
          EEPROM.write(6, temp_i2c_address);
          Serial.print("New I2C address set to: ");
          Serial.print(temp_i2c_address);
          Serial.println(". Restarting...");
          Serial.flush();
          update_i2c_address_from_eeprom = true; //set flag to update later in loop, to complete actual I2C request
        }
      }
      if ((c == 3) && (numBytes == 7)) //set reference MAC address
      {
        for (byte i = 0; i < 6; i++)
        {
          register_compare_mac_address[i] = Wire.read();
        }
      }
      if (c == 0x04)
      {
        digitalWrite(LED_BUILTIN, LOW); // Switch off
      }
      if (c == 0x05)
      {
        digitalWrite(LED_BUILTIN, HIGH); // Switch on
      }
    }
  }

  if (addr == eeprom_i2c_address)
  {
    byte c = Wire.read();

    if (c == 0x00)
    { // nächtes Lesen enthält Waagen-Wert
      register_select_readout = 0;
      Serial.println("register_select_readout set to 0.");
    }
    if (c == 0x01)
    { // nächtes Lesen enthält MAC-Adresse und LED-Status
      register_select_readout = 1;
      Serial.println("register_select_readout set to 1.");
    }
    if (c == 0x02)
    {                                 // LED aus
      digitalWrite(LED_BUILTIN, LOW); // Switch off
    }
    if (c == 0x03)
    {                                  // LED on
      digitalWrite(LED_BUILTIN, HIGH); // Switch on
    }
  }
}

// Read request handler, expected: Wire.write
void requestHandler()
{
  uint8_t bytes_read = Wire.getBytesRead();
  uint8_t addr = Wire.getIncomingAddress(); // get the address that triggered this function
  addr = addr >> 1;                         // shift to the address bits, not r/w bit.

  Serial.print("Read by master on address: 0x");
  Serial.println(addr, HEX);

  if ( (addr == 8) && (answer_bit) )
  {
    bool result_e_l_c = true; // true if eeprom_mac_address <= register_compare_mac_address
    for (byte i = 0; i < 6; i++)
    {
      Serial.print("Compare: ");
      Serial.print((uint8_t) eeprom_mac_address[i], HEX);
      Serial.print(" with ");
      Serial.println((uint8_t) register_compare_mac_address[i], HEX);
      if (eeprom_mac_address[i] > register_compare_mac_address[i])
      {
        result_e_l_c = false;
        break; // skip for loop
      }
      if (eeprom_mac_address[i] < register_compare_mac_address[i])
      {
        result_e_l_c = true;
        break; // skip for loop
      }
    }

    if (result_e_l_c)
    {
      Wire.write(0x00); // dominant on I2C bus
    }
    else
    {
      Wire.write(0xFF);
    }
  }

  if (addr == eeprom_i2c_address)
  {
    if (register_select_readout == 0)
    { // 4 Bytes, Waagenwerte
      Wire.write((byte *) &averaged_reading, sizeof(averaged_reading));
    }

    if (register_select_readout == 1)
    { // 7 Bytes, MAC Adresse und LED-Status
      for (byte i = 0; i < 6; i++)
      {
        Wire.write(eeprom_mac_address[i]);
      }
      Wire.write(digitalRead(LED_BUILTIN));
    }
  }
}

void setup()
{
  // Sleep at the beginning, to make sure voltages are stabilised,
  // see: https://github.com/SpenceKonde/megaTinyCore/tree/master/megaavr/libraries/EEPROM
  delay(100);

  // Enable Watchdog
  wdt_enable();
/*
  // DEBUG
    EEPROM.write(0,0x0);
    EEPROM.write(1,0x0);
    EEPROM.write(2,0x0);
    EEPROM.write(3,0x0);
    EEPROM.write(4,0xbe);
    EEPROM.write(5,0xef);

    EEPROM.write(6,0x9);
  */
  // DEBUG END

  // Read I2C address and MAC address
  for (byte i = 0; i < 6; i++)
  {
    eeprom_mac_address[i] = EEPROM.read(i);
  }
  eeprom_i2c_address = EEPROM.read(6);

  for (byte i = 0; i < NUMBER_OF_SCALE_READINGS_BUFFER; i++)
    last_scale_raw_readings[i] = 0;

  sw.setTxBuffer(swTxBuffer, sizeof(swTxBuffer));
  sw.setRxBuffer(swRxBuffer, sizeof(swRxBuffer));
  sw.setDelay_us(5);
  sw.setTimeout_ms(200);
  sw.begin();

  Serial.begin(115200);

  Serial.print("scale version: ");
  Serial.println(VERSION);
  Serial.print("MAC address:");
  for (byte i = 0; i < 6; i++)
  {
    Serial.print(" 0x");
    Serial.print(eeprom_mac_address[i], HEX);
  }
  Serial.println();
  Serial.print("I2C address: ");
  Serial.print(eeprom_i2c_address);
  Serial.print("(dec) 0x");
  Serial.print(eeprom_i2c_address, HEX);
  Serial.println("(hex)");

  Serial.print("Scale detected: ");
  if (myScale.begin(sw) == false)
  {
    Serial.println("NOT okay. ");
    // while (1); //Make the wathdog perform reset
  }
  else
  {
    Serial.println("okay");
  }

  ///**************************************
  Wire.swap(1); // Select the right pins

  // Initializing slave with secondary address
  // 1st argument: 1st address to listen to
  // 2nd argument: listen to general broadcast or "general call" (address 0x00)
  // 3rd argument: bits 7-1: second address if bit 0 is set true
  //               or bit mask of an address if bit 0 is set false
  Wire.begin(eeprom_i2c_address, true, WIRE_ALT_ADDRESS(8));

  // Handler für das I2C-Empfangsereignis festlegen (siehe unten)
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestHandler);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW); // Bord-LED

  answer_bit = false; // Do not answer to requests on I2C address 0x8
}

void loop()
{
  if (restart_at_next_possibility) {
    Wire.end();
    while (true) ;
    resetViaSWR();
  }
  if (update_i2c_address_from_eeprom) {
    eeprom_i2c_address = EEPROM.read(6);
    Wire.begin(eeprom_i2c_address, true, WIRE_ALT_ADDRESS(8));
    update_i2c_address_from_eeprom = false;
  }

  if (myScale.available())
  {
    last_scale_raw_reading = myScale.getReading();

    // Fill ring buffer
    last_scale_raw_readings_ringbuffer_index++;
    if (last_scale_raw_readings_ringbuffer_index >= NUMBER_OF_SCALE_READINGS_BUFFER)
      last_scale_raw_readings_ringbuffer_index = 0;
    averaged_reading_sum -= last_scale_raw_readings[last_scale_raw_readings_ringbuffer_index];
    last_scale_raw_readings[last_scale_raw_readings_ringbuffer_index] = last_scale_raw_reading;
    averaged_reading_sum += last_scale_raw_reading;
    averaged_reading = averaged_reading_sum / NUMBER_OF_SCALE_READINGS_BUFFER;

    // Serial.print("Reading (avg): ");
    // Serial.println(averaged_reading);

    wdt_reset();
  }
}
