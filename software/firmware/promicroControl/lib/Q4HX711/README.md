Q4HX711
======

A compact parallel readout of 4 hx711 chips.

Usage
--------------

```c
//Q4HX711 hx1(4x hx711_data_pins, hx711_clock_pin);
Q4HX711 hx1(4, 12, 13, 14, 5);

void loop() {
  hx1.read();
  //read now hx1.dataRead[0]...
}
```


Special Thanks
--------------

Based on code from: https://github.com/queuetue/Q2-HX711-Arduino-Library/blob/master/src/Q2HX711.cpp


License
-------

MIT License.
