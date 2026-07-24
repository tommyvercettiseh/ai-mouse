# AI Mouse

Minimalistische lokale Windows-demo voor het opnemen en visueel terugspelen van je eigen muisprofiel.

## Starten

Dubbelklik op:

```text
Start AI Mouse Hub.bat
```

De launcher maakt automatisch een virtuele omgeving en installeert de benodigde dependency voor globale muistracking.

## Gebruik

1. Kies een label, bijvoorbeeld `Browsing` of `Gaming`.
2. Klik **Record**.
3. Gebruik je computer normaal over al je schermen.
4. Gebruik **Pauze/Hervat** wanneer nodig.
5. Klik **Opslaan**.
6. Selecteer een opname.
7. Klik **Profiel vernieuwen**.
8. Klik **Replay profiel** voor de lokale fading-trace.

## Wat de app doet

- volgt de muis globaal over alle Windows-schermen;
- registreert bewegingen, klikken en scrollen;
- toont een live fading trace;
- slaat sessies lokaal op;
- splitst lange pauzes en verdachte cursorwarps automatisch;
- verbindt nooit twee losse segmenten met een kunstmatige lijn;
- speelt een veilige profielvariant uitsluitend binnen de app af.

## Privacy

De app registreert geen toetsenbordinput en geen getypte tekst. Alle data blijft lokaal onder `data/`.

## Mappen

```text
data/recordings/
data/profiles/
data/stress_lab/
data/logs/
```

## Veiligheidsgrens

Replay is een visuele lokale demo en bestuurt geen externe applicaties.
