#include <Arduino.h>
#include <SPI.h>
#include <mcp2515.h>
#include <avr/wdt.h>
#include <EEPROM.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <version.h>

// eink
#include <SPI.h>
#include "epd2in9_V2.h"
#include "epdpaint.h"
#include "imagedata.h"
#define COLORED 0
#define UNCOLORED 1

// NAU ADC
#include <Wire.h>
#include "SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h" // Click here to get the library: http://librarymanager/All#SparkFun_NAU7802

// CAN
struct can_frame canMsg;
MCP2515 mcp2515(4);       // CS connected to PIN 4
struct can_frame canMsg1; // To send messages

// OneWire
#define ONE_WIRE_BUS 23
#define TEMPERATURE_PRECISION 12
OneWire oneWire(ONE_WIRE_BUS);
DeviceAddress insideThermometer;
DallasTemperature sensors(&oneWire);
// function to print a device address
void printAddress(DeviceAddress deviceAddress)
{
  for (uint8_t i = 0; i < 8; i++)
  {
    if (deviceAddress[i] < 16)
      Serial.print("0");
    Serial.print(deviceAddress[i], HEX);
  }
}

// eink
unsigned char image[2048];
Paint paint(image, 0, 0); // width should be the multiple of 8
Epd epd;

// NAU
NAU7802 myScale;                                          // Create instance of the NAU7802 class
#define NUMBER_OF_SCALE_READINGS_BUFFER 8                 // should multiple of 2^N for fast division
#define NUMBER_OF_SCALE_READINGS_BUFFER_DEVISION_HELPER 3 //=int(log(NUMBER_OF_SCALE_READINGS_BUFFER)/log(2))
long last_scale_raw_readings[NUMBER_OF_SCALE_READINGS_BUFFER];
byte last_scale_raw_readings_ringbuffer_index = 0; // points to the actual index used
long averaged_reading_sum = 0;                     // helper variable to average all entries in last_scale_raw_readings. needs to be divided by NUMBER_OF_SCALE_READINGS_BUFFER to get real average
long averaged_reading = 0;                         // regularly updated: averaged_reading_sum/NUMBER_OF_SCALE_READINGS_BUFFER

// Overall scale variables
uint16_t scale_device_id = 0;
char scale_product_description[50];
char scale_product_details_line1[50];
char scale_product_details_line2[50];
float scale_product_price_per_unit;
float scale_product_mass_per_unit;  // in kg
float scale_calibration_slope;      // in kg/au
long scale_calibration_zero_in_raw; // in raw arbitrary units of the adc

void read_scale_properties_from_EEPROM()
{
  EEPROM.get(10, scale_product_description);
  EEPROM.get(60, scale_product_details_line1);
  EEPROM.get(110, scale_product_details_line2);
  EEPROM.get(200, scale_product_price_per_unit);
  EEPROM.get(204, scale_product_mass_per_unit);   //@ CC
  EEPROM.get(208, scale_calibration_slope);       //@ D0
  EEPROM.get(212, scale_calibration_zero_in_raw); //@ D4
}
void write_scale_properties_to_EEPROM()
{
  EEPROM.put(10, scale_product_description);    //@ 0a
  EEPROM.put(60, scale_product_details_line1);  //@ 3c
  EEPROM.put(110, scale_product_details_line2); //@ 6e
  EEPROM.put(200, scale_product_price_per_unit);
  EEPROM.put(204, scale_product_mass_per_unit);   //@ CC
  EEPROM.put(208, scale_calibration_slope);       //@ D0
  EEPROM.put(212, scale_calibration_zero_in_raw); //@ D4
}

void setup()
{
  for (byte i = 0; i < NUMBER_OF_SCALE_READINGS_BUFFER; i++)
    last_scale_raw_readings[i] = 0;
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(115200);

  // OneWire start
  //  Start up the library
  sensors.begin();
  Serial.print("Locating OneWire devices...");
  Serial.print("Found ");
  Serial.print(sensors.getDeviceCount(), DEC);
  Serial.println(" devices.");
  // report parasite power requirements
  Serial.print("Parasite power is: ");
  if (sensors.isParasitePowerMode())
    Serial.println("ON");
  else
    Serial.println("OFF");

  // method 1: by index
  if (!sensors.getAddress(insideThermometer, 0))
    Serial.println("Unable to find address for Device 0");
  // show the addresses we found on the bus
  Serial.print("Device 0 Address: ");
  printAddress(insideThermometer);
  Serial.println();

  sensors.setResolution(insideThermometer, TEMPERATURE_PRECISION);
  Serial.print("Device 0 Resolution: ");
  Serial.print(sensors.getResolution(insideThermometer), DEC);
  Serial.println();

  sensors.setWaitForConversion(false); // make sensors.requestTemperatures calls async
  // OneWire end

  // NAU start
  Wire.begin();

  if (myScale.begin() == false)
  {
    Serial.println("Scale not detected. Please check wiring. Freezing...");
  }
  Serial.println("Scale detected!");
  // NAU end

  // Set scale_device_id start
  // eg OneWire ROM = 28 6D 1A 2 D 0 0 41
  //-->  scale_device_id = 1A<<8 + 6d
  scale_device_id = insideThermometer[1] + (insideThermometer[2] << 8);
  Serial.print("scale_device_id (according to OneWire address): 0x");
  Serial.println(scale_device_id, HEX);
  // store this in eeprom 0 and 1 of not set already
  uint16_t scale_device_id_read;
  EEPROM.get(0, scale_device_id_read);
  if (scale_device_id_read != scale_device_id)
  {
    Serial.print("scale_device_id in EEPROM at byte 0 and 1 reads: 0x");
    Serial.println(scale_device_id_read, HEX);
    EEPROM.put(0, scale_device_id);
    Serial.println("scale_device_id in EEPROM corrected.");
  }
  // Set scale_device_id end

  // CAN start
  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS, MCP_8MHZ);
  mcp2515.setNormalMode();
  // Send actual Firmware version
  canMsg1.can_id = (0x00020000 + scale_device_id) | CAN_EFF_FLAG;
  canMsg1.can_dlc = 4;
  canMsg1.data[0] = BUILD_NUMBER & 0xff;         // build lsb
  canMsg1.data[1] = (BUILD_NUMBER >> 8) & 0xff;  //
  canMsg1.data[2] = (BUILD_NUMBER >> 16) & 0xff; //
  canMsg1.data[3] = (BUILD_NUMBER >> 24) & 0xff; // build msb
  mcp2515.sendMessage(&canMsg1);

  Serial.println("------- CAN Read ----------");
  Serial.println("ID  DLC   DATA");

  // Set CAN Filters
  // see page 34 in MCP2515 Manual
  // https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2515-Stand-Alone-CAN-Controller-with-SPI-20001801J.pdf
  // Further hint from Arduino forum:
  //    To avoid errors you need to set all masks and filters (otherwise it can be rubbish there)
  mcp2515.setConfigMode();
  mcp2515.setFilterMask(MCP2515::MASK0, true, 0x0000ffff); // Look only for device_id
  mcp2515.setFilter(MCP2515::RXF0, true, scale_device_id);
  mcp2515.setFilterMask(MCP2515::MASK1, true, 0x10000000); // and broadcast meassages
  mcp2515.setFilter(MCP2515::RXF1, true,      0x10000000);
  mcp2515.setNormalMode();
  // CAN end

  // EEPROM start
  Serial.print("eeprom: ");
  for (byte i = 0; i < 200; i++)
  {
    Serial.print(EEPROM.read(i));
    Serial.print(" ");
  }
  Serial.println();

  read_scale_properties_from_EEPROM();
  // EEPROM end

  // eink start
  // For version 2 displays, the following complete init seems to be necessary:
  // 1st clear twice the full screen
  // 2nd call SetFrameMemory_Base() with an image
  // 3rd now call "_partical" commands
  if (epd.Init() != 0)
  {
    Serial.print("e-Paper init failed");
  }

  // 1st step init process
  //  for (byte bn = 0; bn < 2; bn++)
  //  {
  epd.ClearFrameMemory(0xFF); // bit set = white, bit reset = black
  epd.DisplayFrame();
  //  }

  if (epd.Init() != 0)
  {
    Serial.print("e-Paper init failed ");
    return;
  }

  // 2nd step init process
  epd.SetFrameMemory_Base(IMAGE_DATA);
  epd.DisplayFrame();

  // 3rd step init process
  for (byte bn = 0; bn < 2; bn++)
  {
    paint.SetWidth(2);    // Effektiv: Höhe des Kastens
    paint.SetHeight(296); // Effektiv: Breite des Kastens
    paint.SetRotate(ROTATE_270);
    paint.Clear(UNCOLORED);
    for (int x = 0; x < 296; x++)
    {
      paint.DrawPixel(x, 0, COLORED);
      paint.DrawPixel(x, 1, COLORED);
    }
    epd.SetFrameMemory_Partial(paint.GetImage(), 40 /*vertikal, oben=0*/, 0 /*horizontal, links=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());

    paint.SetWidth(28); // vertical
    paint.Clear(UNCOLORED);

    paint.DrawStringAt(0, 4, scale_product_description, &Font24, COLORED);
    // x,y are relativ to the "paint" box
    epd.SetFrameMemory_Partial(paint.GetImage(), 10 /*vertical axis, top is 0*/, 0 /*horizontal axis right is 0*/, paint.GetWidth(), paint.GetHeight());

    paint.SetWidth(24);   // vertical
    paint.SetHeight(296); // horizontal
    paint.SetRotate(ROTATE_270);

    paint.Clear(UNCOLORED);

    //      paint.DrawStringAt(0, 4, scale_product_description, &Font24, COLORED);
    // x,y are relativ to the "paint" box
    //      epd.SetFrameMemory_Partial(paint.GetImage(), 10 /*vertical axis, top is 0*/, 0 /*horizontal axis right is 0*/, paint.GetWidth(), paint.GetHeight());

    paint.Clear(UNCOLORED);
    paint.DrawStringAt(0, 0, scale_product_details_line1, &Font12, COLORED);
    epd.SetFrameMemory_Partial(paint.GetImage(), 60, 0, paint.GetWidth(), paint.GetHeight());

    paint.Clear(UNCOLORED);
    paint.DrawStringAt(0, 4, scale_product_details_line2, &Font12, COLORED);
    epd.SetFrameMemory_Partial(paint.GetImage(), 75, 0, paint.GetWidth(), paint.GetHeight());

    char buffer[12];
    sprintf(buffer, "%04x", scale_device_id);
    paint.SetHeight(50); // horizontal
    paint.Clear(UNCOLORED);
    paint.DrawStringAt(0, 4, buffer, &Font12, COLORED);
    epd.SetFrameMemory_Partial(paint.GetImage(), 100 /*vertical axis, top is 0*/, 5 /*horizontal axis*/, paint.GetWidth(), paint.GetHeight());

    epd.DisplayFrame_Partial();
  }

  digitalWrite(LED_BUILTIN, HIGH);
}

unsigned long last_ADC_read = 0;
unsigned long last_regular_check = 0;
unsigned long last_request = 0;
unsigned long last_read = 0;
bool wait_for_onewire_read = false;
bool CAN_only_mode = false;

long last_scale_raw_reading = 0; // raw value from ADC

void loop()
{
  if (!CAN_only_mode)
  {
    // ADC read out
    if (millis() - last_ADC_read > 120)
    {
      last_ADC_read = millis();
      if (myScale.available() == true)
      {
        last_scale_raw_reading = myScale.getReading();

        last_scale_raw_readings_ringbuffer_index++;
        if (last_scale_raw_readings_ringbuffer_index >= NUMBER_OF_SCALE_READINGS_BUFFER)
          last_scale_raw_readings_ringbuffer_index = 0;
        averaged_reading_sum -= last_scale_raw_readings[last_scale_raw_readings_ringbuffer_index];
        last_scale_raw_readings[last_scale_raw_readings_ringbuffer_index] = last_scale_raw_reading;
        averaged_reading_sum += last_scale_raw_readings[last_scale_raw_readings_ringbuffer_index];
        averaged_reading = averaged_reading_sum >> NUMBER_OF_SCALE_READINGS_BUFFER_DEVISION_HELPER;

        last_scale_raw_reading = averaged_reading;

        Serial.print("Reading: ");
        Serial.println(last_scale_raw_reading);

        // Start CAN sending
        canMsg1.can_id = (0x00030000 + scale_device_id) | CAN_EFF_FLAG;
        canMsg1.can_dlc = sizeof(averaged_reading);
        memcpy(canMsg1.data, &averaged_reading, sizeof(averaged_reading));
        mcp2515.sendMessage(&canMsg1);
        // Stop CAN sending
      }
    }

    // eink update
    if (millis() - last_regular_check > 5000)
    {
      last_regular_check = millis();
      char str[100];
      char buffer[12];

      float actual_mass_in_kg = ((last_scale_raw_reading - scale_calibration_zero_in_raw) * scale_calibration_slope);
      dtostrf(actual_mass_in_kg * 1000, 8, 1, buffer);
      sprintf(str, "%s g %ld Stk", buffer, round(actual_mass_in_kg / scale_product_mass_per_unit));
      paint.SetHeight(220); // horizontal
      paint.SetWidth(24);   // vertical
      paint.SetRotate(ROTATE_270);
      paint.Clear(UNCOLORED);
      paint.DrawStringAt(0, 4, str, &Font20, COLORED);
      epd.SetFrameMemory_Partial(paint.GetImage(), 100, 76, paint.GetWidth(), paint.GetHeight());

      epd.DisplayFrame_Partial();
    }

    // request to all devies on the one wire bus
    if (millis() - last_request > 5000)
    {
      last_request = millis();
      // call sensors.requestTemperatures() to issue a global temperature request
      Serial.print("Requesting temperatures...");
      sensors.requestTemperatures();
      Serial.println("DONE");

      last_read = millis() + 750 / (1 << (12 - TEMPERATURE_PRECISION)); // Do read in the future
      wait_for_onewire_read = true;
    }
    // After some delay, read onewire data
    if ((wait_for_onewire_read) && (millis() > last_read))
    {
      wait_for_onewire_read = false;
      float tempC = sensors.getTempCByIndex(0);

      if (tempC != DEVICE_DISCONNECTED_C)
      {
        Serial.print("Temperature for the device 1 (index 0) is: ");
        Serial.println(tempC);

        canMsg1.can_id = (0x00040000 + scale_device_id) | CAN_EFF_FLAG;
        canMsg1.can_dlc = sizeof(tempC);
        memcpy(canMsg1.data, &tempC, sizeof(tempC));
        mcp2515.sendMessage(&canMsg1);
      }
      else
      {
        Serial.println("Error: Could not read temperature data");
      }
    }
  }

  // CAN part start
  /*  Serial.print(canMsg.can_id, HEX); // print ID
    Serial.print(" ");
    Serial.print(canMsg.can_dlc, HEX); // print DLC
    Serial.print(" ");

    for (int i = 0; i < canMsg.can_dlc; i++)
    { // print the data
      if (canMsg.data[i] < 0xa)
        Serial.print(" ");
      Serial.print(canMsg.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  */
  bool reboot_device = false;

  // mostly using 29bit EFF CAN messages
  if (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK)
  {

    // Broadcast messages:
    if (((canMsg.can_id >> 28)&1) == 1)
    {
      if (
        ((((canMsg.can_id >> 24)&0xf) == 0x1)) &&
        (canMsg.can_dlc == 4) && // data length
        (canMsg.data[0] == 0x42) && (canMsg.data[1] == 0xfa) &&
        (canMsg.data[2] == 0xbe) && (canMsg.data[3] == 0xef))
      {
        reboot_device = true;
      }
      // CAN only mode on/off
      if ((((canMsg.can_id >> 24)&0xf) == 0x2))
      {
        CAN_only_mode = true;
      }
      if ((((canMsg.can_id >> 24)&0xf) == 0x3))
      {
        CAN_only_mode = false;
      }
    }

    // Device individual messages:
    if ( (((canMsg.can_id >> 28)&1) == 0) && ((canMsg.can_id & 0xFFFF) == scale_device_id) )
    {

      // Set Raw Zero calibration to actual value
      // eg cansend can0 00093320#01
      if (((canMsg.can_id >> 16) & 0xFF) == 9)
      {
        scale_calibration_zero_in_raw = last_scale_raw_reading;
        if ((canMsg.can_dlc == 1) && (canMsg.data[0] > 0))
        {
          write_scale_properties_to_EEPROM();
        }
      }

      // Read from EEPROM
      // eg: cansend can0 00063320#cc0008
      if (((canMsg.can_id >> 16) & 0xFF) == 6)
      {
        int pos=0;
        while (pos < 256) {
          canMsg1.can_id = (0x00090000 + scale_device_id) | CAN_EFF_FLAG;
          canMsg1.can_dlc = 8;
          canMsg1.data[0] = pos&0xff;
          canMsg1.data[1] = (pos>>8)&0xff;
          for (byte i = 0; i < 6; i++)
            canMsg1.data[i+2] = EEPROM.read(pos + i);
          mcp2515.sendMessage(&canMsg1);
          delay(1);
          pos += 6;
        }
/*        if (canMsg.can_dlc == 3) // 2byte for address + 1 byte for length
        {
          word address_to_be_read = canMsg.data[0] + (canMsg.data[1] << 8);
          byte length_to_be_read = canMsg.data[2];
          if (length_to_be_read > 8)
            length_to_be_read = 8;

          canMsg1.can_id = (0x00090000 + scale_device_id) | CAN_EFF_FLAG;
          canMsg1.can_dlc = length_to_be_read;
          for (byte i = 0; i < length_to_be_read; i++)
            canMsg1.data[i] = EEPROM.read(address_to_be_read + i);
          mcp2515.sendMessage(&canMsg1);
        }
*/      }

      // Write to EEPROM
      // eg: mas per item: cansend can0 00073320#cc00dbf97e3e
      // convert value in [kg] via https://gregstoll.com/~gregstoll/floattohex/
      // have "Swap endianness" switched on
      // (Another great tool: https://cryptii.com/pipes/integer-encoder)
      //
      // eg: Change product description: Convert "Mehl" to 0x4D65686C
      // via https://www.rapidtables.com/convert/number/ascii-to-hex.html
      // next send it to the scale together with ending '\0'
      // cansend can0 00071a6d#0a004D65686C00
      if (((canMsg.can_id >> 16) & 0xFF) == 7)
      {
        byte data_length_to_be_written = canMsg.can_dlc - 2; // first two bytes are position
        word address_to_be_written = canMsg.data[0] + (canMsg.data[1] << 8);
        for (byte i = 0; i < data_length_to_be_written; i++)
        {
          EEPROM.update(address_to_be_written + i, canMsg.data[i + 2]);
        }
        read_scale_properties_from_EEPROM();
      }

      // Check for reboot
      // Check only the lower 16 bits of CAN ID
      if (((canMsg.can_id >> 16) & 0xFF) == 0)
      {
        if ((canMsg.can_dlc == 4) && // data length
            (canMsg.data[0] == 0x42) && (canMsg.data[1] == 0xfa) &&
            (canMsg.data[2] == 0xbe) && (canMsg.data[3] == 0xef))
        {
          reboot_device = true;
        }
      }
    }

    if (reboot_device)
    {
      Serial.println("REBOOT triggered");
      for (byte i = 0; i < 6; i++)
      {
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
        delay(100);
      }
      cli();                 // disable interrupts
      wdt_enable(WDTO_15MS); // watchdog timeout 15ms
      while (1)
        ; // wait for watchdog to reset mcu
    }
  }
  // CAN part end
}
