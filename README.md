# AI Mouse Hub

Moderne, minimalistische lokale Windows-demo voor het opnemen, bouwen en visueel testen van je eigen muisprofiel.

## Starten

Hoofdapp:

```text
Start AI Mouse Hub.bat
```

Losse visuele profieltest:

```text
Start Profile Click Test.bat
```

De launchers maken automatisch een virtuele omgeving en installeren de benodigde dependency voor globale muistracking.

## Hoofdworkflow

1. Kies rechts een label, bijvoorbeeld `Browsing` of `Gaming`.
2. Klik **Record**.
3. Gebruik je computer normaal.
4. Gebruik **Pauze/Hervat** wanneer nodig.
5. Klik **Opslaan**.
6. Selecteer links onderin de opname.
7. Klik rechts onderin op de grote paarse knop **Masterprofiel maken**.
8. Gebruik daarna **Replay profiel** of **Kliktest**.

Zodra een profiel bestaat verandert de knop automatisch in **Masterprofiel vernieuwen**.

Het profielbestand staat lokaal op:

```text
data/profiles/master_profile.json
```

## Moderne interface

De hoofdapp bevat bewust alleen de belangrijkste onderdelen:

- Record;
- Pauze/Hervat;
- Opslaan;
- Replay profiel;
- Kliktest;
- een duidelijke Masterprofiel-knop;
- live fading mouse trace.

De visuele stijl gebruikt een donkere interface met subtiele paarse en blauwe gradients, afgeronde panelen en heldere statuskleuren.

## Profile Click Test

De kliktest gebruikt het gebouwde masterprofiel om binnen een lokaal canvas naar willekeurige doelvlakken te bewegen.

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
