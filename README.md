# AI Mouse

Minimalistische lokale Windows-demo voor het opnemen en visueel terugspelen van je eigen muisprofiel.

## Starten

Hoofdapp:

```text
Start AI Mouse Hub.bat
```

Visuele profieltest:

```text
Start Profile Click Test.bat
```

De launchers maken automatisch een virtuele omgeving en installeren de benodigde dependency voor globale muistracking.

## Hoofdworkflow

1. Kies een label, bijvoorbeeld `Browsing` of `Gaming`.
2. Klik **Record**.
3. Gebruik je computer normaal over al je schermen.
4. Gebruik **Pauze/Hervat** wanneer nodig.
5. Klik **Opslaan**.
6. Selecteer een opname.
7. Klik **Profiel vernieuwen**.
8. Klik **Replay profiel** voor de lokale fading-trace.

## Profile Click Test

De losse kliktest gebruikt het gebouwde masterprofiel om binnen een lokaal canvas naar willekeurige doelvlakken te bewegen.

Je ziet daarbij:

- het volledige profielpad;
- approach in blauw;
- correctie en overshoot in paars;
- het klikmoment in groen;
- de directe lijn als grijze referentie;
- directe afstand, werkelijk pad, overshoot, correcties en klikafstand.

De test bestuurt geen andere applicaties en verplaatst je echte Windows-cursor niet.

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

Replay en Profile Click Test zijn visuele lokale demo's en besturen geen externe applicaties.
