#include <Wire.h> //I2C-Bibliothek

void setup(){
  Serial.begin(115200);
  Wire.begin(); //I2C-Aktivierung
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
    Serial.print("Gefunden: ");
    Serial.println(c);
  }
}