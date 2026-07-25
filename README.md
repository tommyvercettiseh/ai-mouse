# AI Mouse

Minimalistische lokale Windows-demo voor het opnemen, analyseren en visueel vergelijken van je eigen muisgedrag.

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

1. Maak normale recordings via de hoofdapp.
2. Open **Aim Lab**.
3. Kies context, targetgrootte, vorm en afstand.
4. Klik **Zelf testen**.
5. Klik de targets zelf aan met je echte muis.
6. Na target 20 wordt je masterprofiel automatisch bijgewerkt.
7. Gebruik **Profiel replay** om het gecombineerde profiel te bekijken.

## Aim Lab v0.9.1

### Zelf testen

Jij klikt de targets zelf aan. Targets variëren in:

- klein, middel en groot;
- rond en vierkant;
- korte, middelgrote en lange afstanden;
- hoeken, randen, diagonalen en korte sprongen.

Per target worden lokaal opgeslagen:

- targetpositie, vorm en grootte;
- volledige muisroute met timestamps;
- reactietijd en bewegingstijd;
- werkelijk afgelegd pad;
- overshoot en mini-correcties;
- eindoffset;
- clickdelay en click-holdduur;
- aantal misklikken en handmatige resets.

Een misklik stopt de test niet meer. De interne klikstatus wordt direct schoongemaakt. Klik met de **rechtermuisknop** om alleen de huidige targetactie opnieuw te beginnen. De rest van de sessie blijft behouden.

### Automatisch masterprofiel

Na een voltooide menselijke Aim Lab-run wordt `data/profiles/master_profile.json` automatisch opnieuw opgebouwd uit:

- normale recordings onder `data/recordings/`;
- menselijke Aim Lab-runs onder `data/aim_lab/`.

Aim Lab-templates krijgen extra gewicht omdat targetpositie, vorm en grootte exact bekend zijn. Normale recordings blijven onderdeel van het profiel voor spontane curves en natuurlijk gedrag.

### Profiel replay

De virtuele cursor gebruikt het gecombineerde masterprofiel. De daadwerkelijke clicks worden niet gekopieerd of uitgevoerd.

Iedere Aim Lab-run wordt lokaal opgeslagen onder:

```text
data/aim_lab/
```

## Bestaande recordings

Bestaande recordings onder `data/recordings/` blijven bruikbaar en hoeven niet verwijderd te worden. Ze leveren spontane curves, timing en pre-click-bewegingen uit echte situaties. Zelfgespeelde Aim Lab-sessies zijn nauwkeuriger voor targetanalyse omdat de app exact weet waar het target stond.

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
