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
// Data from serial number chip
byte device_mac_address[6];

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
// Better let the watchdog bite
void resetViaSWR()
{
  _PROTECTED_WRITE(RSTCTRL.SWRR, 1);
}
/// END Reset

//*********** CHIP Self Test Routines Start ****************
// Chip self test
// Hints from here: https://forum.arduino.cc/t/reading-the-system-voltage-on-the-new-attiny-1-series/644885/7
#define chip_test_RESULTCOUNT 4
int16_t chip_test_results[chip_test_RESULTCOUNT];
int32_t chip_test_sum;
int16_t chip_test_average;
#define chip_test_results_i2c_buffer_LENGTH 11
int16_t chip_test_results_i2c_buffer[chip_test_results_i2c_buffer_LENGTH];

void chip_test_showHex(unsigned char b)
{
  if (b <= 0xf)
    Serial.print("0");
  Serial.print(b, HEX);
}

void chip_test_printRegisters()
{
  Serial.print("ADC0.MUXPOS: ");
  chip_test_showHex(ADC0.MUXPOS);
  Serial.print("  ADC0.CTRLC: ");
  chip_test_showHex(ADC0.CTRLC);
  Serial.print("  VREF.CTRLA: ");
  chip_test_showHex(VREF.CTRLA);
  Serial.println();
}

int16_t chip_test_runTest_without_expected(uint8_t reference, uint8_t pin)
{
  // clearResults
  for (byte x = 0; x < chip_test_RESULTCOUNT; x++)
  {
    chip_test_results[x] = -1;
  }
  chip_test_sum = 0;
  chip_test_average = 0;

  // Start test
  Serial.print("Now testing pin 0x");
  chip_test_showHex(pin);
  Serial.println();
  analogReference(reference);
  for (byte x = 0; x < chip_test_RESULTCOUNT; x++)
  {
    chip_test_results[x] = analogRead(pin);
  }
  chip_test_printRegisters();
  for (byte x = 0; x < chip_test_RESULTCOUNT; x++)
  {
    chip_test_sum += chip_test_results[x];
  }
  Serial.print("Average: ");
  chip_test_average = chip_test_sum / chip_test_RESULTCOUNT;
  Serial.println(chip_test_average);
  return chip_test_average;
}

int8_t chip_test_runTest(uint8_t reference, uint8_t pin, int16_t expected)
{
  chip_test_runTest_without_expected(reference, pin);
  Serial.print("Expected: ");
  Serial.println(expected);
  int16_t diff = expected - chip_test_average;
  if (diff < 0)
  {
    diff -= 2 * diff;
  }
  if (diff < 8)
  {
    Serial.println("PASS\n");
    // return 0;
  }
  return chip_test_average;
}

void chip_test_prepare()
{
  Serial.println("testAnalogReference");
  analogWrite(PIN_A6, 127); // Output 50% of max voltage from DAC, DAC VREF = 0.55 V, so this is 0.275 V
  Serial.println("Initial state of ADC registers: ");
  chip_test_printRegisters();
}

void chip_test_perform()
{
  Serial.println("START START START START START START START START START START");
  Serial.println("Start Test with VREF=0.55V");
  chip_test_results_i2c_buffer[0] = 508; // chip_test_runTest(INTERNAL0V55,ADC_DAC0, 508);

  Serial.println("Start Test with VREF= 1.1V");
  chip_test_results_i2c_buffer[1] = chip_test_runTest(INTERNAL1V1, ADC_DAC0, 254);

  Serial.println("Start Test with VREF= 1.5V");
  chip_test_results_i2c_buffer[2] = chip_test_runTest(INTERNAL1V5, ADC_DAC0, 186);

  Serial.println("Start Test with VREF= 2.5VV");
  chip_test_results_i2c_buffer[3] = chip_test_runTest(INTERNAL2V5, ADC_DAC0, 112);

  Serial.println("Start Test with VREF= 4.34V");
  chip_test_results_i2c_buffer[4] = chip_test_runTest(INTERNAL4V34, ADC_DAC0, 64);

  Serial.println("Start Test with VREF= Vcc 5.0V");
  int16_t vscale = chip_test_runTest_without_expected(VDD, ADC_DAC0);
  chip_test_results_i2c_buffer[5] = vscale;
  Serial.print("Voltage is: ");
  Serial.print(chip_test_average * 89);
  Serial.println("mV\n");

  Serial.println("Start Test with VREF= Vcc (5.0V) Internal Ref 0.55V");
  VREF.CTRLA = VREF_ADC0REFSEL_0V55_gc;
  chip_test_results_i2c_buffer[6] = chip_test_runTest(VDD, ADC_INTREF, (113L * vscale) / 56);

  Serial.println("Start Test with VREF= Vcc (5.0V) Internal Ref 1.1V");
  VREF.CTRLA = VREF_ADC0REFSEL_1V1_gc;
  chip_test_results_i2c_buffer[7] = chip_test_runTest(VDD, ADC_INTREF, (225L * vscale) / 56);

  Serial.println("Start Test with VREF= Vcc (5.0V) Internal Ref 1.5V");
  VREF.CTRLA = VREF_ADC0REFSEL_1V5_gc;
  chip_test_results_i2c_buffer[8] = chip_test_runTest(VDD, ADC_INTREF, (307L * vscale) / 56);

  Serial.println("Start Test with VREF= Vcc (5.0V) Internal Ref 2.5V");
  VREF.CTRLA = VREF_ADC0REFSEL_2V5_gc;
  chip_test_results_i2c_buffer[9] = chip_test_runTest(VDD, ADC_INTREF, (512L * vscale) / 56);

  Serial.println("Start Test with VREF= Vcc (5.0V) Internal Ref 4.34V");
  VREF.CTRLA = VREF_ADC0REFSEL_4V34_gc;
  chip_test_results_i2c_buffer[10] = chip_test_runTest(VDD, ADC_INTREF, (888L * vscale) / 56);
}
//*********** CHIP Self Test End *****

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
      { // Reset scale
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
          if (device_mac_address[i] != temp_mac_address[i])
          {
            equal = false;
          }
        }

        // Set I2C address
        if (equal)
        {
          answer_bit = false;
          EEPROM.write(0, temp_i2c_address);
          Serial.print("New I2C address set to: ");
          Serial.print(temp_i2c_address);
          Serial.println(". Restarting...");
          Serial.flush();
          update_i2c_address_from_eeprom = true; // set flag to update later in loop, to complete actual I2C request
        }
      }
      if ((c == 3) && (numBytes == 7)) // set reference MAC address
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
    if (c == 0x04)
    { // nächtes Lesen enthält Ergebnis des Selst Tests
      register_select_readout = 2;
      Serial.println("register_select_readout set to 2.");
      chip_test_prepare();
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

  if ((addr == 8) && (answer_bit))
  {
    bool result_e_l_c = true; // true if device_mac_address <= register_compare_mac_address
    for (byte i = 0; i < 6; i++)
    {
      Serial.print("Compare: ");
      Serial.print((uint8_t)device_mac_address[i], HEX);
      Serial.print(" with ");
      Serial.println((uint8_t)register_compare_mac_address[i], HEX);
      if (device_mac_address[i] > register_compare_mac_address[i])
      {
        result_e_l_c = false;
        break; // skip for loop
      }
      if (device_mac_address[i] < register_compare_mac_address[i])
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
      Wire.write((byte *)&averaged_reading, sizeof(averaged_reading));
    }

    if (register_select_readout == 1)
    { // 7 Bytes, MAC Adresse und LED-Status
      for (byte i = 0; i < 6; i++)
      {
        Wire.write(device_mac_address[i]);
      }
      Wire.write(digitalRead(LED_BUILTIN));
    }

    if (register_select_readout == 2)
    { // chip_test_results_i2c_buffer_LENGTH *2 Bytes: RESULTS FROM SELF TEST
      for (byte i = 0; i < chip_test_results_i2c_buffer_LENGTH; i++)
      {
        Wire.write((chip_test_results_i2c_buffer[i] >> 8) & 0xFF);
        Wire.write((chip_test_results_i2c_buffer[i]) & 0xFF);
      }
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

  Serial.begin(115200);
  Serial.print("scale version: ");
  Serial.println(VERSION);

  // SIGROW.SERNUM0 .. SERNUM9, eg:
  //  30 54 43 30 39 53 F7 75 13 45
  //  30 54 43 30 39 53 D7 FA 13 46
  //  30 54 43 30 39 53 77 F1 13 38
  //  see: https://microchip.my.site.com/s/article/Serial-number-in-AVR---Mega-Tiny-devices
  Serial.print("ATTiny chip serial: ");
  Serial.print(SIGROW.SERNUM0, HEX); // Lot Number 2nd Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM1, HEX); // Lot Number 1st Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM2, HEX); // Lot Number 4th Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM3, HEX); // Lot Number 3rd Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM4, HEX); // Lot Number 6th Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM5, HEX); // Lot Number 5th Char
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM6, HEX); // Reserved
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM7, HEX); // Wafer Number
  Serial.print(" ");
  Serial.print(SIGROW.SERNUM8, HEX); // Y-coordinate
  Serial.print(" ");
  Serial.println(SIGROW.SERNUM9, HEX); // X-coordinate

  // Set mac address
  device_mac_address[0] = SIGROW.SERNUM2; // Lot Number 4th Char
  device_mac_address[1] = SIGROW.SERNUM5; // Lot Number 5th Char
  device_mac_address[2] = SIGROW.SERNUM4; // Lot Number 6th Char
  device_mac_address[3] = SIGROW.SERNUM7; // Wafer Number
  device_mac_address[4] = SIGROW.SERNUM8; // Y-coordinate
  device_mac_address[5] = SIGROW.SERNUM9; // X-coordinate

  // Read I2C address
  eeprom_i2c_address = EEPROM.read(0);

  for (byte i = 0; i < NUMBER_OF_SCALE_READINGS_BUFFER; i++)
    last_scale_raw_readings[i] = 0;

  sw.setTxBuffer(swTxBuffer, sizeof(swTxBuffer));
  sw.setRxBuffer(swRxBuffer, sizeof(swRxBuffer));
  sw.setDelay_us(5);
  sw.setTimeout_ms(200);
  sw.begin();

  Serial.print("MAC address:");
  for (byte i = 0; i < 6; i++)
  {
    Serial.print(" 0x");
    Serial.print(device_mac_address[i], HEX);
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
  if (restart_at_next_possibility)
  {
    Wire.end();
    while (true)
      ;
    resetViaSWR();
  }
  if (update_i2c_address_from_eeprom)
  {
    eeprom_i2c_address = EEPROM.read(0);
    Wire.begin(eeprom_i2c_address, true, WIRE_ALT_ADDRESS(8));
    update_i2c_address_from_eeprom = false;
  }

  if (register_select_readout == 2)
  { // Perform self test now!
    chip_test_perform();
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
