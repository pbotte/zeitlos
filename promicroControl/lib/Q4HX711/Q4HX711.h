#ifndef Q4HX711_h
#define Q4HX711_h
#include "Arduino.h"

#define NHX711INSTANCES 4

class Q4HX711
{
  private:
    byte CLOCK_PIN;
    byte OUT_PIN[4];
    byte GAIN;
    bool pinsConfigured;

  public:
    uint32_t dataRead[NHX711INSTANCES]; //after read(), use these values
    Q4HX711(byte output_pin0, byte output_pin1, byte output_pin2, byte output_pin3, byte clock_pin);
    virtual ~Q4HX711();
    bool readyToSend();
    void setGain(byte gain = 128);
    void read();
};


#endif /* Q4HX711_h */
