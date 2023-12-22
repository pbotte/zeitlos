```mermaid
graph TD
  W1["Waagen 1..8"] <--> |I2C| WC1
  W2["Waagen 1..8"] <--> |I2C| WC2
  W3["Waagen 1..8"] <--> |I2C| WCN
  WC1["scale_v4_bussearch.py 1"] ==> |Rohdaten| WI
  WC2["scale_v4_bussearch.py 2"] ==> |Rohdaten| WI
  WCN["scale_v4_bussearch.py N"] ==> |Rohdaten| WI

  L1["Lidar 1"] --> |Serial| ST1
  L2["Lidar 2"] --> |Serial| ST2
  LN["Lidar N"] --> |Serial| STN

  ST1["Lidar Readout 1"] --> |Rohdaten| STI
  ST2["Lidar Readout 2"] --> |Rohdaten| STI
  STN["Lidar Readout N"] --> |Rohdaten| STI

  Türkontakt --> IOR

  SC["Shop controller"]


subgraph Messdaten-Input
  WI["Waagen Interpreter"]
  cardreader
  STI["Lidar Shop-Track Interpreter"]
  IOR["io-usb-readout"]
  QCS["qr-code-scanner"]
end

subgraph Ausgabe
  FSR["FSR14Control"]
  DPC["display-power-control"]

  MN["mqtt-2-ntfy"]

  Shelly["Shelly Rollladen-Controller"]
end

  SC --> Shelly --> Rollladen
 
  IOR --> SC

  DPC --> CD1
  DPC --> CD2
  DPC --> CDA

  CD1["Client Live Display 1"]
  CD2["Client Live Display 2"]
  CDA["Client Display Außen"]

  FSR --> LI["Licht innen"]
  FSR --> LA["Licht außen"]
  FSR --> Türöffner

  WI ==> |Entnommene Ware| SC
  STI ==> SC
  cardreader <==> SC
  QCS --> SC

  SC ==> FSR
  SC ==> DPC

  SC --> MN
```