#include <Arduino.h>
#include "Q4HX711.h"

// Acquire AVR-specific ATOMIC_BLOCK(ATOMIC_RESTORESTATE) macro.
#include <util/atomic.h>
//Hint, why ATOMIC_BLOCK is used (from HX711.cpp):
// Protect the read sequence from system interrupts.  If an interrupt occurs during
// the time the PD_SCK signal is high it will stretch the length of the clock pulse.
// If the total pulse time exceeds 60 uSec this will cause the HX711 to enter
// power down mode during the middle of the read sequence.  While the device will
// wake up when PD_SCK goes low again, the reset starts a new conversion cycle which
// forces DOUT high until that cycle is completed.
//
// The result is that all subsequent bits read by shiftIn() will read back as 1,
// corrupting the value returned by read().  The ATOMIC_BLOCK macro disables
// interrupts during the sequence and then restores the interrupt mask to its previous
// state after the sequence completes, insuring that the entire read-and-gain-set
// sequence is not interrupted.  The macro has a few minor advantages over bracketing
// the sequence between `noInterrupts()` and `interrupts()` calls.


Q4HX711::Q4HX711(byte clock_pin) {
  CLOCK_PIN  = clock_pin;
  GAIN = 1;
  pinsConfigured = false;
}

Q4HX711::~Q4HX711() {
}

bool Q4HX711::readyToSend() {
  if (!pinsConfigured) {
    // We need to set the pin mode once, but not in the constructor
    pinMode(CLOCK_PIN, OUTPUT);
    DDRF = 0; //Set all Ports on PF to Input
    pinsConfigured = true;
  }
  //Check all Data pins. If they are all low, call read ()
  return !(PINF & 0xf0);
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
  // at next call read(), the gain will be changed in the ADCs
}

void Q4HX711::read() {
  //call if (readyToSend()) { Q4HX711::read() } in your code
  //to make sure, ADCs are ready

  byte buf[24];
  // Read in 24 bits, toggle the clock pin each time
  // MSB first
	ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    //Read out the 24 data bits
    for (byte i=0; i<24; ++i) {
      digitalWrite(CLOCK_PIN, HIGH);
      buf[i] = PINF;
      digitalWrite(CLOCK_PIN, LOW);
    }

    // set gain and select input channel (1-3 more bits)
    for (int i=0; i < GAIN; i++) {
      digitalWrite(CLOCK_PIN, HIGH);
  //    delayMicroseconds(1); //only needed, if timing is wrong
      digitalWrite(CLOCK_PIN, LOW);
  //    delayMicroseconds(1);
    }
  }

  for (byte j=0; j<NHX711INSTANCES; j++) {
    dataRead[j] = 0;
  }

  // convert the read in data into consecutive numbers
  for (byte i=0; i < 24; ++i) {
    for (byte j=0; j<NHX711INSTANCES; j++) {
    	bitWrite(dataRead[j], 23-i,  (buf[i]>>(7-j))&1 );
    }
  }

  //Stretch the MSB bit read out (bit 24) and "stretch" it
  for (byte k=0; k<NHX711INSTANCES; k++) { 
    if ((dataRead[k]>>16) & 0x80) {
      dataRead[k] |= 0xFF000000;
    }
  }
}

//Send the chip to power down mode
void Q4HX711::power_down() {
	digitalWrite(CLOCK_PIN, LOW);
	digitalWrite(CLOCK_PIN, HIGH);
}

void Q4HX711::power_up() {
	digitalWrite(CLOCK_PIN, LOW);
}
