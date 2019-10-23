#include <SPI.h>
#include <epd2in9.h>
#include <epdpaint.h>
#include "imagedata.h"
#include <qrcode.h>
#include <avr/boot.h>


// Serial Number of 32U4 from
// https://forum.pololu.com/t/a-star-adding-serial-numbers/7651
char serialNumber[30]; //Serial number of ATMEGA32U4

char nibbleToHex(uint8_t n) {
  if (n <= 9) { return '0' + n; }
  else { return 'a' + (n - 10); }
}

void readSerialNumberOld() {
  char * p = serialNumber;
  for(uint8_t i = 14; i < 24; i++) {
    uint8_t b = boot_signature_byte_get(i);
    *p++ = nibbleToHex(b >> 4);
    *p++ = nibbleToHex(b & 0xF);
    *p++ = '-';
  }
  *--p = 0;
}
void readSerialNumber() {
  char * p = serialNumber;
  for(uint8_t i = 14; i < 24; i++) {
    uint8_t b = boot_signature_byte_get(i);
    *p++ = b;
  }
  *p = 0;
}

#define pITypeLength 50
char pIType[pITypeLength]; //Product Info: Type
byte pITypeActLength = 0; //Length of actual String


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

void updateDisplayFull() {
    if (epd.Init(lut_full_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

  /**
   *  there are 2 memory areas embedded in the e-paper display
   *  and once the display is refreshed, the memory area will be auto-toggled,
   *  i.e. the next action of SetFrameMemory will set the other memory area
   *  therefore you have to clear the frame memory twice.
   */
  paint.SetRotate(ROTATE_270);
  paint.SetWidth(24); //Effektiv: Höhe des Kastens
  paint.SetHeight(296); //Effektiv: Breite des Kastens

  /* For simplicity, the arguments are explicit numerical coordinates */
  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, pIType, &Font24, COLORED);
  for (int x=0;x<296;x++){
    paint.DrawPixel(x,22,COLORED);
    paint.DrawPixel(x,23,COLORED);
  }
  //paint.DrawLine(296, 20, 1, 18, COLORED);
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.SetFrameMemory(paint.GetImage(), 5/*y-Koordinate, oben=0*/, 0 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();

  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.SetFrameMemory(paint.GetImage(), 5, 0, paint.GetWidth(), paint.GetHeight());
  // epd.DisplayFrame();

  if (epd.Init(lut_partial_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

}

int sendSerialPacket(int fCmdType, byte fData=0) {
  uint8_t c[]= {0x5a, 0xa5, 0, 1,  0, 1/*data bytes number*/, fData, 0};
  c[3] = fCmdType&0xff;
  c[2] = (fCmdType>>8) & 0xff;
  byte checksum=0;
  for (int i=0; i<sizeof(c)-1; i++) 
    checksum += c[i];
  c[sizeof(c)-1] = checksum;
  Serial.write(c,sizeof(c));
}
int sendSerialPacket2(int fCmdType, byte fData[], int fNData) {
  uint8_t c[]= {0x5a, 0xa5, 0, 1,  0, 1/*data bytes number*/};
  c[3] = fCmdType&0xff;
  c[2] = (fCmdType>>8) & 0xff;
  c[5] = fNData & 0xff;
  c[4] = (fNData>>8) & 0xff;
  byte checksum=0;
  for (int i=0; i<sizeof(c); i++)
    checksum += c[i];
  for (int i=0; i<fNData; i++)
    checksum += fData[i];
  Serial.write(c,sizeof(c));
  Serial.write(fData, fNData);
  Serial.write(checksum);
}

void setup() {
//  while (!Serial); //https://www.arduino.cc/en/Guide/ArduinoLeonardoMicro
  Serial.begin(115200);

  // Create the QR code
  QRCode qrcode;
  uint8_t qrcodeData[qrcode_getBufferSize(3)];
  qrcode_initText(&qrcode, qrcodeData, 3, 0, "http://www.tusoi.de");

  readSerialNumber();
//  Serial.print("Seriennummer ATMEGA32U4: ");
//  Serial.println(serialNumber);

  sendSerialPacket2(111, serialNumber, 30);
}


byte receiveFSMState = 0; //FSM State for Serial Reception 
int receivedFSMCmd = 0;
int receivedFSMNData = 0;
int receivedFSMNBytesReceived = 0;
byte receivedFSMChecksum = 0;
#define NMAXNBYTES 100
byte receivedFSMData[NMAXNBYTES];

void loop() {
  int ib;
  // data transfer protocoll
  //  min. length: 7 bytes 
  //  [Start Sequence] [Command Byte, 2bytes] [Number of data bytes, 2bytes] [Data bytes] [Checksum byte]
  //  Start Sequence: 0x5a a5 = 2 bytes, fixed
  //  Command Byte: 0x00 00 = Update Display
  //                0x00 01 = Update Product Info Type
  //  Number of data bytes: 2 bytes
  //  Data bytes: up to the number advertised in [Number of data bytes]
  //  Checksum byte: Sum of all (also start bytes) bytes except checksum byte modulo 256

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
        sendSerialPacket(12);
        receiveFSMState=0;
      }
    } else if (receiveFSMState==7) {//Wait for checksum
      receivedFSMChecksum -= ib;
      receiveFSMState=0;
      if (receivedFSMChecksum == ib) { //Checksum ok?
        sendSerialPacket(10, receivedFSMCmd&0xff);
        sendSerialPacket(11, receivedFSMNData&0xff);
        sendSerialPacket(12, receivedFSMData[0]);
        if (receivedFSMCmd==2) {
          pITypeActLength=1;
          pIType[0] = receivedFSMData[0];
          pIType[1] = receivedFSMData[1];
          pIType[2] = receivedFSMData[2];
          pIType[3] = receivedFSMData[3];
          pIType[4] = receivedFSMData[4];
          pIType[5] = 0;
        }
        if (receivedFSMCmd==3) updateDisplayFull();
        if (receivedFSMCmd==4) sendSerialPacket2(111, serialNumber, 10);
      }
    } else {
      receiveFSMState=0;
    }
  }
    
}
