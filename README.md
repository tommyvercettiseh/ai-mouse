# AI Mouse

Moderne minimalistische lokale Windows-app voor het opnemen en visueel terugspelen van je eigen muisprofiel.

## Starten

Hoofdapp:

```text
Start AI Mouse Hub.bat
```

Visuele profieltest:

```text
Start Profile Click Test.bat
```

## Hoofdworkflow

1. Kies een label, bijvoorbeeld `Browsing` of `Gaming`.
2. Klik **Record**.
3. Gebruik je computer normaal over al je schermen.
4. Gebruik **Pauze/Hervat** wanneer nodig.
5. Klik **Opslaan**.
6. Klik **Masterprofiel maken** of **Masterprofiel vernieuwen**.
7. Selecteer een opname en klik **Replay profiel**.
8. Open de visuele doeltest via **Kliktest**.

## Multi-monitorvisualisatie

De hoofdapp detecteert automatisch je echte Windows-schermindeling. Ieder scherm wordt als afzonderlijk vlak getoond met:

- schermnummer;
- resolutie;
- aanduiding van het primaire scherm;
- een heldere highlight rond het scherm waar de cursor zich bevindt;
- dezelfde actieve-schermweergave tijdens profielreplay.

Negatieve Windows-coördinaten, bijvoorbeeld een monitor links van je primaire scherm, worden ondersteund.

## Opnames openen

Klik in de hoofdapp op **Open opnamemap**. Windows Verkenner opent dan direct:

```text
data/recordings/
```

Iedere opname heeft een eigen map met `points.csv` en `metadata.json`.

## Profile Click Test

De losse kliktest gebruikt het gebouwde masterprofiel om binnen een lokaal canvas naar willekeurige doelvlakken te bewegen. Je ziet het volledige pad, approach, correctie, overshoot, klikmoment en de directe lijn als vergelijking.

De test bestuurt geen andere applicaties en verplaatst je echte Windows-cursor niet.

## Privacy

De app registreert geen toetsenbordinput en geen getypte tekst. Alle data blijft lokaal onder `data/`.

## Veiligheidsgrens

Replay en Profile Click Test zijn visuele lokale demo's en besturen geen externe applicaties.
