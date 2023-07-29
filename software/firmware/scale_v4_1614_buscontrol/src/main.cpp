// Seriell <-> I2C Adapter
// Commands:
// Commands start with "r"/"w" and end with single character "\n"
//
// write to I2C address 0xC1 data: 0x01 0x02 0x03
// wC1010203\n
//
// read from I2C address 0xC2 max 17 (=0x11) characters
// rC211\n

#include <Wire.h> //I2C-Bibliothek

#define VALUES_LENGTH 16
byte values[VALUES_LENGTH];
#define BUFFER_LENGTH VALUES_LENGTH * 2 + 1
char buffer[BUFFER_LENGTH];

void setup()
{
  Serial.begin(115200);
  Serial.setTimeout(10000);
  Wire.begin(); // I2C-Aktivierung
  byte res = Wire.setClock(1000);
  Serial.print("Set I2C clock to 1000Hz, return value: ");
  Serial.println(res);
}

void loop()
{
  if (Serial.available())
  {
    byte len = Serial.readBytesUntil('\n', buffer, BUFFER_LENGTH);
//    Serial.println(buffer);

    // Reformat all bytes except the first
    byte i = 1;
    byte len_values = 0;
    while (
        (i < BUFFER_LENGTH) && (((buffer[i] >= '0') && (buffer[i] <= '9')) ||
                                ((buffer[i] >= 'A') && (buffer[i] <= 'F'))))
    {
      // Make 'A' come next after '9'
      if (buffer[i] > '9')
        buffer[i] = buffer[i] - 'A' + '9'+1;
      // Substract '0' from every value
      buffer[i] -= '0';
      i++;
      len = i;
      if (i%2==1) len_values++;
    }

    for (byte i = 0; i < VALUES_LENGTH; i++)
    {
      values[i] = (buffer[i * 2 + 1] << 4) + (buffer[i * 2 + 2]);
    }

    // Print debug output
    //Serial.print("Summary: cmd: ");
    Serial.print(buffer[0]);
    //Serial.print(" ");

    //Serial.print(" values:");
    // for (byte i = 0; i < len_values; i++)
    // {
    //   // Serial.print(" ");
    //   if ((uint8_t)values[i] <= 0xf) {
    //     Serial.print("0");
    //   }
    //   Serial.print((uint8_t)values[i], HEX);
    // }
    // Serial.print(" ");

    // Process commands
    if (buffer[0] == 'r') // read cmd
    {
      if (len_values == 2)
      {
        // Serial.print("Read from 0x");
        // Serial.print((uint8_t)values[0], HEX);
        // Serial.print(" number of char: ");
        // Serial.println((uint8_t)values[1]);

        Serial.print(" ");
        uint8_t n = Wire.requestFrom(values[0], values[1]);
        // Serial.print("(");
        // Serial.print(Wire.available());
        // Serial.print(", ");
          if ((uint8_t)n <= 0xf) {
            Serial.print("0");
          }
        Serial.print((uint8_t)n, HEX);
        // Serial.print(")");

        while (Wire.available())
        {                       // peripheral may send less than requested
          char c = Wire.read(); // receive a byte as character
          Serial.print(" ");
          if ((uint8_t)c <= 0xf) {
            Serial.print("0");
          }
          Serial.print((uint8_t)c, HEX); // print the character
        }
        // Serial.println();
      }
      else
      {
        Serial.print(" ERROR: number of characters is ");
        Serial.print(len);
        Serial.print(" but expected 5.");
      }
    }
    else if (buffer[0] == 'w') // write cmd
    {
      // Serial.print("Write ");
      // Serial.print(len_values-1);
      // Serial.print(" values to 0x");
      // Serial.print((uint8_t)values[0], HEX);
      // Serial.print(":");

      for (byte i = 1; i < len_values; i++)
      {
        // Serial.print(" 0x");
        // Serial.print((uint8_t)values[i], HEX);
      }
      // Serial.print(" ");

      Wire.beginTransmission(values[0]);
      for (byte i = 1; i < len_values; i++)
      {
        Wire.write(values[i]);
      }
      byte res = Wire.endTransmission();
      //Serial.print("Return code: ");
      Serial.print(" ");
      if (res <= 0xf) {
        Serial.print("0");
      }
      Serial.print((uint8_t)res, HEX);
    } 
    else 
    {
      Serial.print("error");
    }
    Serial.println();
  }
}