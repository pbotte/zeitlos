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
  AA[Geräte Initialisierung]
  A[Bereit, Kein Kunde im Laden]
  B[Kunde authentifiziert]
  C[Kunde im Laden]
  D[Einkauf finalisiert]
  E[Einkauf abgerechnet]
  F[Warten auf: Kunde verlässt Laden]
  Y[Technischer Fehler aufgetreten]
  Z[Kunde benötigt Hilfe]
  AA --> A
  AA --> |Timeout| Y
  A --> B
  B --> |Timeout| A
  B --> C
  C -->|Timeout| Z
  C --> D
  D --> E
  D -->|Timeout| Z
  E --> F
  F --> A
  F -->|Timeout| Z
  
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
