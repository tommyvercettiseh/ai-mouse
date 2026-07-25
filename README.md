# AI Mouse

Minimalistische lokale Windows-demo voor het opnemen, analyseren en visueel afspelen van je eigen muisgedrag.

## Starten

Hoofdapp:

```text
Start AI Mouse Hub.bat
```

Aim Lab:

```text
Start Aim Lab Test.bat
```

## Simpele workflow

1. Kies `Gaming`, `Browsing`, `Werk` of `Precision`.
2. Klik **Record**.
3. Gebruik je muis normaal en maak echte clicks.
4. Klik **Opslaan**.
5. Open **Aim Lab**.
6. Kies context en targetgrootte.
7. Klik **Start**.

## Wat v0.8.0 anders doet

De Aim Lab-test rekt niet langer één volledige sessie uit tot een rechte lijn. De app haalt afzonderlijke bewegingen vlak vóór echte clicks uit je recordings en gebruikt die als persoonlijke templates.

Per template worden onder andere bewaard:

- natuurlijke curve;
- bewegingstijd;
- afstand en werkelijk afgelegd pad;
- overshoot;
- mini-correcties;
- kwaliteitsscore;
- context;
- gemeten vertraging tussen aankomst en click.

De daadwerkelijke clicks worden niet gekopieerd of uitgevoerd. De clickdelay wordt alleen als timing gebruikt voor het virtuele klikmoment in de demo.

## Aim Lab

De lokale Aim Lab genereert kleine, middelgrote en grote targets. Tijdens iedere actie zie je:

- het volledige persoonlijke pad;
- approach in blauw;
- overshoot en correcties in paars;
- het virtuele klikmoment in groen;
- afstand, padlengte, overshoot, correcties, eindoffset, beweegtijd en clickdelay.

Iedere run wordt lokaal opgeslagen onder:

```text
data/aim_lab/
```

Daar staan per actie het gekozen bronsegment, target, volledige gegenereerde route en alle metingen.

## Multi-monitor en opnames

De hoofdapp toont je echte Windows-schermindeling en markeert het actieve scherm. Met **Open opnamemap** open je direct:

```text
data/recordings/
```

## Privacy en grens

- Alleen muisbewegingen, clicks en scroll worden opgenomen.
- Geen toetsenbordinput of getypte tekst.
- Geen screenshots.
- Alles blijft lokaal.
- Replay en Aim Lab gebruiken een virtuele cursor en besturen geen externe applicaties.
