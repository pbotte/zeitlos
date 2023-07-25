/*
  Use the Qwiic Scale to read load cells and scales
  By: Nathan Seidle @ SparkFun Electronics
  Date: March 3rd, 2019
  License: This code is public domain but you buy me a beer if you use this
  and we meet someday (Beerware license).

  The NAU7802 supports up to 400kHz. You can also pass different wire ports
  into the library.

  SparkFun labored with love to create this code. Feel like supporting open
  source? Buy a board from SparkFun!
  https://www.sparkfun.com/products/15242

  Hardware Connections:
  Plug a Qwiic cable into the Qwiic Scale and a RedBoard Qwiic
  If you don't have a platform with a Qwiic connection use the SparkFun Qwiic Breadboard Jumper (https://www.sparkfun.com/products/14425)
  Open the serial monitor at 9600 baud to see the output
*/

// Funktioniert mit geänderter Library

#include <Wire.h>
#include <SoftWire.h>
#include <AsyncDelay.h>

SoftWire sw(6, 7);
// These buffers must be at least as large as the largest read or write you perform.
char swTxBuffer[16];
char swRxBuffer[16];

AsyncDelay readInterval;

#include "SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h" // Click here to get the library: http://librarymanager/All#SparkFun_NAU8702

// NAU
NAU7802 myScale;                          // Create instance of the NAU7802 class
#define NUMBER_OF_SCALE_READINGS_BUFFER 8 // should multiple of 2^N for fast division
long last_scale_raw_readings[NUMBER_OF_SCALE_READINGS_BUFFER];
byte last_scale_raw_readings_ringbuffer_index = 0; // points to the actual index used
long averaged_reading_sum = 0;                     // helper variable to average all entries in last_scale_raw_readings. needs to be divided by NUMBER_OF_SCALE_READINGS_BUFFER to get real average
long averaged_reading = 0;                         // regularly updated: averaged_reading_sum/NUMBER_OF_SCALE_READINGS_BUFFER
long last_scale_raw_reading = 0;                   // raw value from ADC

void receiveEvent(int numBytes)
{
  uint8_t addr = Wire.getIncomingAddress();   // get the address that triggered this function
  addr = addr >> 1; //shift to the address bits, not r/w bit.
  Serial.println(addr, HEX);

  while (Wire.available())
  {
    char c = Wire.read();
    Serial.print("Neu: (0x");
    Serial.print(c, HEX);
    Serial.print("): ");
    Serial.println(c);

    if (c == 'H')
    {
      digitalWrite(LED_BUILTIN, HIGH);
    }
    else if (c == 'L')
    {
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}


void requestHandler() {
  uint8_t bytes_read = Wire.getBytesRead();
  uint8_t addr = Wire.getIncomingAddress();   // get the address that triggered this function
  addr = addr >> 1; //shift to the address bits, not r/w bit.
  Serial.println(addr, HEX);

//  if (addr == 0) {
//        Wire.write(50);
//  }
//  for (byte i = 0; i < 2; i++) {
//    Wire.write("hello");
//  }

}

void setup()
{
  for (byte i = 0; i < NUMBER_OF_SCALE_READINGS_BUFFER; i++)
    last_scale_raw_readings[i] = 0;

  sw.setTxBuffer(swTxBuffer, sizeof(swTxBuffer));
  sw.setRxBuffer(swRxBuffer, sizeof(swRxBuffer));
  sw.setDelay_us(5);
  sw.setTimeout_ms(200);
  sw.begin();

  Serial.begin(115200);
  Serial.println("Qwiic Scale Example");

  //  Wire.begin(); //This line won't compile on an Uno. This example is for other platforms that have multiple I2C ports.
  //  Wire.setClock(400000); //We can increase I2C clock speed to 400kHz, the NAU7802 supports it

  if (myScale.begin(sw) == false) // Pass the Wire port to the library
  {
    Serial.println("Scale not detected. Please check wiring. ");
    //while (1)
      ;
  }
  Serial.println("Scale detected!");

  ///**************************************
  Wire.swap(1); //Select the right pins

  // Initializing slave with secondary address
  // 1st argument: 1st address to listen to
  // 2nd argument: listen to general broadcast or "general call" (address 0x00)
  // 3rd argument: bits 7-1: second address if bit 0 is set true
  //               or bit mask of an address if bit 0 is set false
  Wire.begin(0x5, true, WIRE_ALT_ADDRESS(10));
  Wire.setClock(1000);

  // Handler für das I2C-Empfangsereignis festlegen (siehe unten)
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestHandler);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW); // Bord-LED
}

void loop()
{
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

    //Serial.print("Reading (avg): ");
    //Serial.println(averaged_reading);
  }
}
