#include <Arduino.h>
#include "Q4HX711.h"

Q4HX711::    Q4HX711(byte output_pin0, byte output_pin1, byte output_pin2, byte output_pin3, byte clock_pin) {
  CLOCK_PIN  = clock_pin;
  OUT_PIN[0]  = output_pin0;
  OUT_PIN[1]  = output_pin1;
  OUT_PIN[2]  = output_pin2;
  OUT_PIN[3]  = output_pin3;
  GAIN = 1;
  pinsConfigured = false;
}

Q4HX711::~Q4HX711() {
}

bool Q4HX711::readyToSend() {
  if (!pinsConfigured) {
    // We need to set the pin mode once, but not in the constructor
    pinMode(CLOCK_PIN, OUTPUT);
    for (byte i=0; i<3; i++) {
      pinMode(OUT_PIN[i], INPUT);
    }
    pinsConfigured = true;
  }
  bool CombinedReturn = true;
  for (byte i=0; i<3; i++) {
    if (digitalRead(OUT_PIN[i]) == HIGH) CombinedReturn = false;
  }
  return CombinedReturn;
}

void Q4HX711::setGain(byte gain) {
  switch (gain) {
    case 128:
      GAIN = 1;
      break;
    case 64:
      GAIN = 3;
      break;
    case 32:
      GAIN = 2;
      break;
  }

  digitalWrite(CLOCK_PIN, LOW);
  read();
}

void Q4HX711::read() {
  while (!readyToSend());

  byte data[NHX711INSTANCES][3];

  for (byte k=0; k<NHX711INSTANCES; k++) { 
    for (byte i=0; i<3; i++) {data[k][i] = 0; } 
  }

  for (byte i=3; i--; ) {
    for (byte l = 0; l < 8; ++l) {
      digitalWrite(CLOCK_PIN, HIGH);
      for (byte k=0; k<NHX711INSTANCES; k++) { 
        data[k][i] |= digitalRead( OUT_PIN[k]) << (7 - l);
      }
      digitalWrite(CLOCK_PIN, LOW);
    }
  }

  // set gain
  for (int i = 0; i < GAIN; i++) {
    digitalWrite(CLOCK_PIN, HIGH);
    digitalWrite(CLOCK_PIN, LOW);
  }

  for (byte k=0; k<NHX711INSTANCES; k++) { 
    data[k][2] ^= 0x80;
    dataRead[k] = ((uint32_t) data[k][2] << 16) | ((uint32_t) data[k][1] << 8) | (uint32_t) data[k][0];
  }
}
