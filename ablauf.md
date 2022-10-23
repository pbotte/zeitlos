# Einkauf

```mermaid
sequenceDiagram
    actor Kunde
    participant Zugangskontrolle
    participant shopcontroller
    participant Waagen
    participant Einkaufsanzeige
    Kunde->>Zugangskontrolle: Authentifikation (Girocard)
    Zugangskontrolle->>Kunde: Vorabbuchung durchgeführt + Einlass
    Zugangskontrolle->>shopcontroller: Kunde eingelassen
    shopcontroller->>Waagen: Reset
    shopcontroller->>Einkaufsanzeige: Reset
    Kunde->>Waagen: Entnimmt Produkte
    shopcontroller->>Einkaufsanzeige: Anzeige aktueller Einkauf
    Waagen->>Waagen: Produkte dürfen auch wieder zurückgelegt werden
    Zugangskontrolle->>shopcontroller: Geschäft verlassen, Einkauf beendet.
    shopcontroller->>Kunde: Abbuchung des finalen Geldbetrags
```

# Mögliche Zustände Shop_Controller
```mermaid
graph TD
  AA["Geräte Initialisierung (0)"]
  A["Bereit, Kein Kunde im Laden (1)"]
  B["Kunde authentifiziert (2)"]
  C["Kunde im Laden (3)"]
  D["Einkauf finalisiert (4) / Kunde nicht mehr im Laden"]
  E["Einkauf abgerechnet (5)"]
  G["Warten auf: Vorbereitung für nächsten Kunden (7)"]
  W["Laden geschlossen (10)"]
  Y["Technischer Fehler aufgetreten (8)"]
  Z["Kunde benötigt Hilfe (9)"]
  AA --> G
  AA --> |Timeout| Y
  A --> |gültiger QR-Code| B
  B --> |Timeout| A
  B --> |Türkontakt = offen| C
  C -->|Timeout| Z
  C --> |Türkontakt = zu UND alle Distanzsensoren = leer| D
  D --> |nach 5 Sek.| E
  D --> |Tür=offen ODER Distanzsensor=im Laden| C
  E --> G
  G --> A
  
```


# Bestückung
```mermaid
sequenceDiagram
    actor Verkäufer
    participant Zugangskontrolle
    participant shopcontroller
    participant Waagen
    participant Einkaufsanzeige
    Verkäufer->>Zugangskontrolle: Authentifikation
    Zugangskontrolle->>Verkäufer: Einlass
    Verkäufer->>Waagen: Legt neue Produkte auf Waagen
    Waagen->>Waagen: Produktmenge darf angepasst werden
    Zugangskontrolle->>Verkäufer: Geschäft verlassen.
```
