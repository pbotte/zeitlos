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

//Funktioniert mit geänderter Library

#include <Wire.h>
#include <SoftWire.h>
#include <AsyncDelay.h>

SoftWire sw(6, 7);
// These buffers must be at least as large as the largest read or write you perform.
char swTxBuffer[16];
char swRxBuffer[16];

AsyncDelay readInterval;

#include "SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h" // Click here to get the library: http://librarymanager/All#SparkFun_NAU8702

NAU7802 myScale; //Create instance of the NAU7802 class


void receiveEvent(int howMany){
  while(Wire.available())
  {
    char c = Wire.read();
    Serial.print("Neu: ");
    Serial.println(c);
    
    if(c == 'H')
    {
      digitalWrite(LED_BUILTIN,HIGH);
    }
    else if(c == 'L')
    {
      digitalWrite(LED_BUILTIN,LOW);
    }
  }
}

void setup()
{
  sw.setTxBuffer(swTxBuffer, sizeof(swTxBuffer));
  sw.setRxBuffer(swRxBuffer, sizeof(swRxBuffer));
  sw.setDelay_us(5);
  sw.setTimeout_ms(200);
  sw.begin();
  
  Serial.begin(115200);
  Serial.println("Qwiic Scale Example");

//  Wire.begin(); //This line won't compile on an Uno. This example is for other platforms that have multiple I2C ports.
//  Wire.setClock(400000); //We can increase I2C clock speed to 400kHz, the NAU7802 supports it

  if (myScale.begin(sw) == false) //Pass the Wire port to the library
  {
    Serial.println("Scale not detected. Please check wiring. Freezing...");
    while (1);
  }
  Serial.println("Scale detected!");



  ///**************************************
  //I2C-Adresszuweisung: Slave 6
  Wire.swap(1);
  Wire.begin(6);

  //Handler für das I2C-Empfangsereignis festlegen (siehe unten)
  Wire.onReceive(receiveEvent); 

  pinMode(LED_BUILTIN,OUTPUT); digitalWrite(LED_BUILTIN,LOW); // Bord-LED
}

void loop()
{
  if (myScale.available())
  {
    long currentReading = myScale.getReading();
    Serial.print("Reading: ");
    Serial.println(currentReading);
  }
}
