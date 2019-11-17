#include <SPI.h>
#include <epd2in9.h>
#include <epdpaint.h>
#include <qrcode.h>
#include <avr/boot.h>
#include <Q4HX711.h>


// Serial Number of 32U4 from
// https://forum.pololu.com/t/a-star-adding-serial-numbers/7651
byte serialNumber[10];
byte firmwareVersion[4] = {0,0,0,1};

void readSerialNumber() {
  for(uint8_t i = 14; i < 24; i++) {
    serialNumber[i-14] = boot_signature_byte_get(i);
  }
}

//Trigger Arduino reset via software
//Alternative option to reset Arduino via Computer:
//Open and Close the serial port at 1200 Baud
void(* resetFunc) (void) = 0; //declare reset function @ address 0

#define pITypeLength 50
char pIType[pITypeLength]; //Product Info: Type
#define pIDescriptionLength 50
char pIDescription[pIDescriptionLength]; //Product Info: Description


#define COLORED     0
#define UNCOLORED   1

/**
  * Due to RAM not enough in Arduino UNO, a frame buffer is not allowed.
  * In this case, a smaller image buffer is allocated and you have to 
  * update a partial display several times.
  * 1 byte = 8 pixels, therefore you have to set 8*N pixels at a time.
  */
unsigned char image[1024];
Paint paint(image, 0, 0);    // width should be the multiple of 8
Epd epd;
unsigned long time_start_ms;
unsigned long time_now_s;

void einkShowUninitialised() {
  if (epd.Init(lut_full_update) != 0) {
    Serial.print("e-Paper init failed");
    return;
  }

  //Clear screen
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.DisplayFrame();

  //Draw something helpful
  paint.SetRotate(ROTATE_270);
  paint.SetWidth(24); //Effektiv: Höhe des Kastens
  paint.SetHeight(296); //Effektiv: Breite des Kastens

  /* For simplicity, the arguments are explicit numerical coordinates */
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, "Fehlende", &Font24, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 10/*y-Koordinate, oben=0*/, 0 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, "Konfiguration", &Font24, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 35, 0, paint.GetWidth(), paint.GetHeight());

  //And now add the QR Code
  if (epd.Init(lut_partial_update) != 0) {
    Serial.print("e-Paper init failed");
    return;
  }

  QRCode qrcode;
  uint8_t qrcodeData[qrcode_getBufferSize(3)];
  qrcode_initText(&qrcode, qrcodeData, 3, 0, "https://github.com/pbotte/zeitlos");

  paint.SetWidth(64);
  paint.SetHeight(64);

  paint.Clear(UNCOLORED);
  for (uint8_t y = 0; y < qrcode.size; y++) {
    for (uint8_t x = 0; x < qrcode.size; x++) {
      if (qrcode_getModule(&qrcode, x, y)) {
        paint.DrawPixel(x*2+5,  y*2+5,COLORED);
        paint.DrawPixel(x*2+1+5,y*2+5,COLORED);
        paint.DrawPixel(x*2+5,  y*2+5+1,COLORED);
        paint.DrawPixel(x*2+1+5,y*2+5+1,COLORED);
      }
    }
  }
  epd.SetFrameMemory(paint.GetImage(), 60/*y*/, 5/*x*/, paint.GetWidth(), paint.GetHeight());

  paint.SetWidth(24); //Effektiv: Höhe des Kastens
  paint.SetHeight(232); //Effektiv: Breite des Kastens
  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, "Einrichtungstipps:", &Font16, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 85/*y-Koordinate, oben=0*/, 64 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());

  epd.DisplayFrame();
}

void updateDisplayFull() {
    if (epd.Init(lut_full_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

  paint.SetRotate(ROTATE_270);
  paint.SetWidth(24); //Effektiv: Höhe des Kastens
  paint.SetHeight(296); //Effektiv: Breite des Kastens

  //paint.DrawLine(296, 20, 1, 18, COLORED);
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black

  /* For simplicity, the arguments are explicit numerical coordinates */
  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, pIType, &Font24, COLORED);
  for (int x=0;x<296;x++){
    paint.DrawPixel(x,22,COLORED);
    paint.DrawPixel(x,23,COLORED);
  }
  epd.SetFrameMemory(paint.GetImage(), 5/*y-Koordinate, oben=0*/, 0 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, pIDescription, &Font16, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 35/*y-Koordinate, oben=0*/, 0 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());


  epd.DisplayFrame();

  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.SetFrameMemory(paint.GetImage(), 5, 0, paint.GetWidth(), paint.GetHeight());
  // epd.DisplayFrame();

  if (epd.Init(lut_partial_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

}

void sendSerialPacket(int fCmdType, byte fData=0) {
  uint8_t c[]= {0x5a, 0xa5, 0, 1,  0, 1/*data bytes number*/, fData, 0};
  c[3] = fCmdType&0xff;
  c[2] = (fCmdType>>8) & 0xff;
  byte checksum=0;
  for (byte i=0; i<sizeof(c)-1; i++) 
    checksum += c[i];
  c[sizeof(c)-1] = checksum;
  Serial.write(c, sizeof(c));
}
void sendSerialPacket2(int fCmdType, byte fData[], byte fNData) {
  uint8_t c[]= {0x5a, 0xa5, 0, 1,  0, 1/*data bytes number*/};
  c[3] = fCmdType&0xff;
  c[2] = (fCmdType>>8) & 0xff;
  c[5] = fNData & 0xff;
  c[4] = (fNData>>8) & 0xff;
  byte checksum=0;
  for (byte i=0; i<sizeof(c); i++)
    checksum += c[i];
  for (byte i=0; i<fNData; i++)
    checksum += fData[i];
  Serial.write(c, sizeof(c));
  Serial.write(fData, fNData);
  Serial.write(checksum);
}

void setup() {
  readSerialNumber();
  
  delay(1000); //give computer some time, to launch the scale controller. 
               //in case this is not successfull within 1sec, show hint
  if (!Serial) einkShowUninitialised();
  while (!Serial); //https://www.arduino.cc/en/Guide/ArduinoLeonardoMicro

  Serial.begin(115200); //Baud rate not important, due to Serial over USB: See Arduino Leonardo manual
}


byte receiveFSMState = 0; //FSM State for Serial Reception 
int receivedFSMCmd = 0;
int receivedFSMNData = 0;
int receivedFSMNBytesReceived = 0;
byte receivedFSMChecksum = 0;
#define NMAXNBYTES 100
byte receivedFSMData[NMAXNBYTES];

void loop() {
  //
  //updateDisplayFull();


  int ib;

  if (Serial.available() > 0) {
    ib = Serial.read();
    receivedFSMChecksum += ib;
    if ((receiveFSMState==0) && (ib == 0x5a)) {//Wait for start sequence 1st byte
      receiveFSMState=1;
      receivedFSMChecksum = ib; //Reset Checksum calculation
    } else if ((receiveFSMState==1) && (ib == 0xa5)) { //Wait for start sequence 2nd byte
      receiveFSMState=2;
    } else if (receiveFSMState==2) {//Wait for cmd byte 1st byte
      receivedFSMCmd = (ib<<8);
      receiveFSMState=3;
    } else if (receiveFSMState==3) {//Wait for cmd byte 2nd byte
      receivedFSMCmd += ib;
      receiveFSMState=4;
    } else if (receiveFSMState==4) {//Wait for Number of data bytes 1st byte
      receivedFSMNData = (ib<<8);
      receiveFSMState=5;
    } else if (receiveFSMState==5) {//Wait for Number of data bytes 2nd byte
      receivedFSMNData += ib;
      receivedFSMNBytesReceived=0;
      if (receivedFSMNData==0) {
        receiveFSMState=7;
      } else {
        receiveFSMState=6;
      }
    } else if (receiveFSMState==6) {//Wait for data bytes
      receivedFSMData[receivedFSMNBytesReceived] = ib;
      receivedFSMNBytesReceived++;
      if (receivedFSMNBytesReceived>=receivedFSMNData) { //All Data Bytes received?
        receiveFSMState=7;
      }
      if (receivedFSMNBytesReceived >= NMAXNBYTES) { //Too long for our current buffer
        receiveFSMState=0;
      }
    } else if (receiveFSMState==7) {//Wait for checksum
      receivedFSMChecksum -= ib;
      receiveFSMState=0;
      if (receivedFSMChecksum == ib) { //Checksum ok?
        if (receivedFSMCmd==0) resetFunc(); //(Kindof) hardare resets the Arduino
        if (receivedFSMCmd==1) sendSerialPacket2(1, serialNumber, sizeof(serialNumber));
        if (receivedFSMCmd==2) sendSerialPacket2(2, firmwareVersion, sizeof(firmwareVersion));
        if (receivedFSMCmd==102) { //Received Type
          byte i;
          for (i=0; (i<pITypeLength-1) && (i<receivedFSMNData); i++)
            pIType[i] = receivedFSMData[i];
          pIType[i] = 0;
        }
        if (receivedFSMCmd==103) { //Received Description
          byte i;
          for (i=0; (i<pIDescriptionLength-1) && (i<receivedFSMNData); i++)
            pIDescription[i] = receivedFSMData[i];
          pIDescription[i] = 0;
        }
        if (receivedFSMCmd==100) updateDisplayFull();
      }
    } else {
      receiveFSMState=0;
    }
  }
    
}
