#ifndef Q4HX711_h
#define Q4HX711_h
#include "Arduino.h"

#define NHX711INSTANCES 4

class Q4HX711
{
  private:
    byte CLOCK_PIN;
    byte GAIN;
    bool pinsConfigured;

  public:
    long dataRead[NHX711INSTANCES]; //after read(), use these values
    Q4HX711(byte clock_pin);
    virtual ~Q4HX711();
    bool readyToSend();
    void setGain(byte gain = 128);
    void read();
    void power_down();
    void power_up();
};


#endif /* Q4HX711_h */
