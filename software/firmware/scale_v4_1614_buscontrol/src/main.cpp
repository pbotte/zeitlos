#include <Wire.h> //I2C-Bibliothek

void setup(){
  Serial.begin(115200);
  Wire.begin(); //I2C-Aktivierung
    Wire.setClock(1000);
}

void loop(){
  while( Serial.available() ) {
    char c = Serial.read();
    
    if(c == 'H') {
      Serial.print("H gefunden");
      Wire.beginTransmission(5); //I2C: an Adresse 5 senden
      Wire.write('H');
      Wire.endTransmission();
    }
    else if(c == 'L') {
      Serial.print("Low gefunden");
      Wire.beginTransmission(5);
      Wire.write('L');
      Wire.endTransmission();
    }
    if(c == 'h') {
      Serial.print("h gefunden");
      Wire.beginTransmission(6); //I2C: an Adresse 5 senden
      Wire.write('H');
      Wire.endTransmission();
    }
    else if(c == 'l') {
      Serial.print("low gefunden");
      Wire.beginTransmission(6);
      Wire.write('L');
      Wire.endTransmission();
    }

    if(c == 'x') {
      Serial.print("h gefunden");
      Wire.beginTransmission(0x64); //I2C: an Adresse 5 senden
      Wire.write('H');
      Wire.endTransmission();
    }
    else if(c == 'c') {
      Serial.print("low gefunden");
      Wire.beginTransmission(0x64);
      Wire.write('L');
      Wire.endTransmission();
    }

    if(c == 'a') {
      Serial.print("Broadcast 0x000000");
      Wire.beginTransmission(0x0);
      for (byte k=0; k<6; k++) {
        Wire.write(0x0);
      }
      Wire.endTransmission();
    }
    else if(c == 's') {
      Serial.print("Read from 0x0");
      uint8_t n = Wire.requestFrom(10, 1);    // request 1 byte from peripheral device #0
      Serial.print("(");
      Serial.print(Wire.available());
      Serial.print(", ");
      Serial.print(n);
      Serial.print(")");
      while (Wire.available()) { // peripheral may send less than requested
        char c = Wire.read(); // receive a byte as character
        Serial.print("0x");
        Serial.print(c,HEX);         // print the character
      }
       // TODO: Check for return value to detect errors
    }

    if(c == 'e') {
      Serial.print("e gefunden");

      Wire.requestFrom(5, 6);    // request 6 bytes from peripheral device #8
      Serial.print("(");
      Serial.print(Wire.available());
      Serial.print(")");
      while (Wire.available()) { // peripheral may send less than requested
        char c = Wire.read(); // receive a byte as character
        Serial.print(c);         // print the character
      }

    }
    if(c == 'r') {
      Serial.print("r gefunden (nix lesen test)");
      Wire.requestFrom(4, 6);    // request 6 bytes from peripheral device #8
       // TODO: Check for return value to detect errors
      Serial.print("(");
      Serial.print(Wire.available());
      Serial.print(")");
      while (Wire.available()) { // peripheral may send less than requested
        char c = Wire.read(); // receive a byte as character
        Serial.print(c);         // print the character
      }

    }

    Serial.print("Gefunden: ");
    Serial.println(c);
  }
}