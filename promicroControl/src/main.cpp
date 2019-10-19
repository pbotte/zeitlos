#include <SPI.h>
#include <epd2in9.h>
#include <epdpaint.h>
#include "imagedata.h"
#include <qrcode.h>
#include <avr/boot.h>


// Serial Number of 32U4 from
// https://forum.pololu.com/t/a-star-adding-serial-numbers/7651
char serialNumber[30]; //Serial number of ATMEGA32U4

char nibbleToHex(uint8_t n)
{
  if (n <= 9) { return '0' + n; }
  else { return 'a' + (n - 10); }
}

void readSerialNumber()
{
  char * p = serialNumber;
  for(uint8_t i = 14; i < 24; i++)
  {
    uint8_t b = boot_signature_byte_get(i);
    *p++ = nibbleToHex(b >> 4);
    *p++ = nibbleToHex(b & 0xF);
    *p++ = '-';
  }
  *--p = 0;
}



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
  paint.DrawStringAt(5/*x*/, 0/*y*/, "Karotten", &Font24, COLORED);
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
//  epd.DisplayFrame();

  if (epd.Init(lut_partial_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

}

void setup() {
  while (!Serial); //https://www.arduino.cc/en/Guide/ArduinoLeonardoMicro
  Serial.begin(115200);
  Serial.print("Beginn");
  delay(200);


    // Start time
    uint32_t dt = millis();

    // Create the QR code
    QRCode qrcode;
    uint8_t qrcodeData[qrcode_getBufferSize(3)];
    qrcode_initText(&qrcode, qrcodeData, 3, 0, "http://www.tusoi.de");

    // Delta time
    dt = millis() - dt;
    Serial.print("QR Code Generation Time: ");
    Serial.print(dt);
    Serial.print("\n");


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
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.DisplayFrame();
  epd.ClearFrameMemory(0xFF);   // bit set = white, bit reset = black
  epd.DisplayFrame();

  if (epd.Init(lut_partial_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }

  paint.SetRotate(ROTATE_270);
  paint.SetWidth(24); //Effektiv: Höhe des Kastens
  paint.SetHeight(296); //Effektiv: Breite des Kastens

  /* For simplicity, the arguments are explicit numerical coordinates */
  paint.Clear(UNCOLORED);
  paint.DrawStringAt(5/*x*/, 0/*y*/, "Karotten", &Font24, COLORED);
  for (int x=0;x<296;x++){
    paint.DrawPixel(x,22,COLORED);
    paint.DrawPixel(x,23,COLORED);
  }
  //paint.DrawLine(296, 20, 1, 18, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 5/*y-Koordinate, oben=0*/, 0 /*x-Koordinate, rechts=0, multiply of 8*/, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
  epd.SetFrameMemory(paint.GetImage(), 5, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(0, 0, "Aus dem eigenen Anbau.", &Font16, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 30, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
  epd.SetFrameMemory(paint.GetImage(), 30, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(0, 0, "Schriftgroesse 12", &Font12, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 50, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
  epd.SetFrameMemory(paint.GetImage(), 50, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(0, 0, "Schriftgroesse 8", &Font8, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 95, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
  epd.SetFrameMemory(paint.GetImage(), 95, 0, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();


  paint.SetWidth(64);
  paint.SetHeight(64);

  paint.Clear(UNCOLORED);

/*  paint.DrawRectangle(1, 1, 40, 50, COLORED);
  paint.DrawLine(0, 0, 40, 50, COLORED);
  paint.DrawLine(40, 0, 0, 50, COLORED);
*/
  for (uint8_t y = 0; y < qrcode.size; y++) {
        // Each horizontal module
        for (uint8_t x = 0; x < qrcode.size; x++) {
            if (qrcode_getModule(&qrcode, x, y)) {
			paint.DrawPixel(x*2+5,  y*2+5,COLORED);
			paint.DrawPixel(x*2+1+5,y*2+5,COLORED);
			paint.DrawPixel(x*2+5,  y*2+5+1,COLORED);
			paint.DrawPixel(x*2+1+5,y*2+5+1,COLORED);
		}
        }
    }


  epd.SetFrameMemory(paint.GetImage(), 50/*y*/, 5/*x*/, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
  epd.SetFrameMemory(paint.GetImage(), 50, 5, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
/*
  paint.Clear(UNCOLORED);
  paint.DrawCircle(32, 32, 30, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 10, 220, paint.GetWidth(), paint.GetHeight());

  paint.Clear(UNCOLORED);
  paint.DrawFilledRectangle(0, 0, 40, 50, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 16, 130, paint.GetWidth(), paint.GetHeight());

  paint.Clear(UNCOLORED);
  paint.DrawFilledCircle(32, 32, 30, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 72, 130, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();
*/  

//  delay(10000);

/*  if (epd.Init(lut_partial_update) != 0) {
      Serial.print("e-Paper init failed");
      return;
  }
*/
  /** 
   *  there are 2 memory areas embedded in the e-paper display
   *  and once the display is refreshed, the memory area will be auto-toggled,
   *  i.e. the next action of SetFrameMemory will set the other memory area
   *  therefore you have to set the frame memory and refresh the display twice.
   */
/*  epd.SetFrameMemory(IMAGE_DATA);
  epd.DisplayFrame();
  epd.SetFrameMemory(IMAGE_DATA);
  epd.DisplayFrame();
*/
  time_start_ms = millis();

    readSerialNumber();
    Serial.print("Seriennummer ATMEGA32U4: ");
    Serial.println(serialNumber); 


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

byte receiveFSMState = 0;
int receivedFSMCmd = 0;

void loop() {

  /*
  time_now_s = (millis() - time_start_ms) / 1000;
  char time_string[] = {'0', '0', ':', '0', '0', '\0'};
  time_string[0] = time_now_s / 60 / 10 + '0';
  time_string[1] = time_now_s / 60 % 10 + '0';
  time_string[3] = time_now_s % 60 / 10 + '0';
  time_string[4] = time_now_s % 60 % 10 + '0';

  paint.SetWidth(32);
  paint.SetHeight(96);
  paint.SetRotate(ROTATE_270);

  paint.Clear(UNCOLORED);
  paint.DrawStringAt(0, 0, time_string, &Font24, COLORED);
  epd.SetFrameMemory(paint.GetImage(), 70, 80, paint.GetWidth(), paint.GetHeight());
  epd.DisplayFrame();

  delay(500);
*/

  int ib;
  #define pITypeLength 50
  char pIType[pITypeLength]; //Product Info: Type
    //0=Waiting for start sequence 1st byte
    //1=Waiting for start sequence 2nd byte
    //2=Waiting for Command Byte, 1st byte
    //3=Waiting for Command Byte, 2nd byte
    //4=Receiving data

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
    if ((receiveFSMState==0) && (ib == 0x5a)) {//Wait for start sequence 1st byte
      receiveFSMState=1;
      sendSerialPacket(10, receiveFSMState);
    } else if ((receiveFSMState==1) && (ib == 0xa5)) { //Wait for start sequence 2nd byte
      receiveFSMState=2;
      sendSerialPacket(2, receiveFSMState);
    } else if (receiveFSMState==2) {//Wait for cmd byte 1st byte
      receivedFSMCmd = (ib<<8);
      receiveFSMState=3;
      sendSerialPacket(3);
    } else if (receiveFSMState==3) {//Wait for cmd byte 2nd byte
      receivedFSMCmd += ib;
      receiveFSMState=4;
      sendSerialPacket(4);
    } else if (receiveFSMState==4) {
      receiveFSMState=0;
      sendSerialPacket(5);
    } else {
      sendSerialPacket((byte)ib, receiveFSMState);
      receiveFSMState=0;
    }
  }
    
/*    char time_string[] = {'E', 'm', 'p', ':', '0', '\0'};
    time_string[4] = ib;

    Serial.print("Empfangen: #");
    Serial.println(ib, DEC);

    paint.SetWidth(32);
    paint.SetHeight(96);
    paint.SetRotate(ROTATE_270);

    paint.Clear(UNCOLORED);
    paint.DrawStringAt(0, 0, time_string, &Font24, COLORED);
    epd.SetFrameMemory(paint.GetImage(), 70, 80, paint.GetWidth(), paint.GetHeight());
    epd.DisplayFrame();

    if (ib == 'u') {
      updateDisplayFull();
    }*/

/*  uint8_t b[]= {0x5a, 0xa5, 1, 1,  0, 0, (0x5a+0xa5+1+1)%256};

  if (millis()%1000 == 0) {
    Serial.write(b,sizeof(b));
    delay(2);
  }*/
}

