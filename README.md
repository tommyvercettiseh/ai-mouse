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

Human Score Lab:

```text
Start Human Score Lab.bat
```

## Simpele workflow

1. Maak normale recordings via de hoofdapp.
2. Klik zelf targets aan in Aim Lab.
3. Na target 20 wordt je masterprofiel automatisch bijgewerkt.
4. Start Human Score Lab.
5. Laat standaard 100 nieuwe profielruns simuleren.
6. Bekijk profielmatch, timing, targetgedrag, variatie, herhaling en datavertrouwen.

## Human Score Lab v0.10.0

De Human Score Lab genereert nieuwe virtuele targetbewegingen met jouw huidige `master_profile.json`. De standaardtest voert 100 runs uit met verschillende afstanden, richtingen en targetgroottes.

De uitslag bevat:

- Hesse Profile Score;
- menselijke profielmatch;
- timingmatch;
- natuurlijke variatie;
- overshoot- en correctiegedrag;
- herhalingscontrole via padfingerprints;
- apart datavertrouwen.

Een lage hoeveelheid data verlaagt vooral het datavertrouwen. De profielscore wordt gebaseerd op hoe goed de gegenereerde runs passen bij de beschikbare persoonlijke baseline.

De uitslag is nadrukkelijk geen absolute of algemene AI-detector. Het is een lokale vergelijking met jouw eigen opgenomen muisgedrag.

Iedere test wordt opgeslagen onder:

```text
data/human_score_lab/
```

## Aim Lab

### Zelf testen

Jij klikt de targets zelf aan. Targets variëren in:

- klein, middel en groot;
- rond en vierkant;
- korte, middelgrote en lange afstanden;
- hoeken, randen, diagonalen en korte sprongen.

Per target worden onder andere targetpositie, route, reactietijd, bewegingstijd, overshoot, mini-correcties, eindoffset, clickdelay en click-holdduur opgeslagen.

Een misklik stopt de test niet. Klik met de **rechtermuisknop** om alleen de huidige targetactie opnieuw te beginnen.

### Automatisch masterprofiel

Na een voltooide menselijke Aim Lab-run wordt `data/profiles/master_profile.json` automatisch opnieuw opgebouwd uit:

- normale recordings onder `data/recordings/`;
- menselijke Aim Lab-runs onder `data/aim_lab/`.

Aim Lab-templates krijgen extra gewicht omdat targetpositie, vorm en grootte exact bekend zijn. Normale recordings blijven onderdeel van het profiel voor spontane curves en natuurlijk gedrag.

## Bestaande recordings

Bestaande recordings onder `data/recordings/` blijven bruikbaar en hoeven niet verwijderd te worden. Ze leveren spontane curves, timing en pre-click-bewegingen uit echte situaties.

## Privacy en grens

- Alleen muisbewegingen, clicks en scroll worden opgenomen.
- Geen toetsenbordinput of getypte tekst.
- Geen screenshots.
- Alles blijft lokaal.
- Replay, Aim Lab en Human Score Lab gebruiken een virtuele cursor en besturen geen externe applicaties.