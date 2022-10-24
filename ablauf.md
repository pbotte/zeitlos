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
  AF["Fehler bei Authentifizierung (13)"]
  B["Kunde authentifiziert (2)"]
  C["Kunde betritt/verlässt gerade den Laden (3)"]
  CC["Kunde möglicherweise im Laden (11)"]
  CCC["Kunde sicher im Laden (12)"]
  D["Möglicherweise: Einkauf finalisiert / Kunde nicht mehr im Laden (4)"]
  E["Einkauf beendet und abgerechnet (5)"]
  G["Warten auf: Vorbereitung für nächsten Kunden (7)"]
  W["Laden geschlossen (10)"]
  Y["Technischer Fehler aufgetreten (8)"]
  Z["Kunde benötigt Hilfe (9)"]
  AA --> G
  AA --> |Timeout| Y
  A --> |gültiger QR-Code| B
  A --> |ungültiger QR-Code| AF
  AF --> |Timeout| A
  B --> |Timeout| A
  B --> |Türkontakt = offen| C
  C --> |Tür=zu| CC
  CC --> |Distanzsensoren=im Laden| CCC
  CCC --> |Tür=offen| C
  CCC -->|Timeout| Z
  CC --> |alle Distanzsensoren = leer| D
  D --> |nach 5 Sek.| E
  D --> |Tür=offen| C
  D --> |Distanzsensor=im Laden| CCC
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
