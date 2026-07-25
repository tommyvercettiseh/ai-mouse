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
3. Kies targetgrootte, vorm en afstand.
4. Klik **Zelf testen**.
5. Klik de targets zelf aan met je echte muis.
6. Gebruik **Profiel replay** om dezelfde soort test met je virtuele profiel te bekijken.

## Aim Lab v0.9.0

De Aim Lab heeft twee modi:

### Zelf testen

Jij klikt de targets zelf aan. Targets variëren in:

- klein, middel en groot;
- rond en vierkant;
- korte, middelgrote en lange afstanden;
- hoeken, randen, diagonalen en korte sprongen.

Per target worden lokaal opgeslagen:

- targetpositie, vorm en grootte;
- volledige muisroute met timestamps;
- reactietijd;
- bewegingstijd;
- werkelijk afgelegd pad;
- overshoot;
- mini-correcties;
- eindoffset;
- clickdelay;
- click-holdduur.

### Profiel replay

De virtuele cursor gebruikt templates uit bestaande recordings om targets af te spelen. De daadwerkelijke clicks worden niet gekopieerd of uitgevoerd.

Iedere run wordt lokaal opgeslagen onder:

```text
data/aim_lab/
```

## Bestaande recordings

Bestaande recordings onder `data/recordings/` blijven bruikbaar. Ze leveren spontane curves, timing en pre-click-bewegingen uit echte situaties. Aim Lab-opnames zijn voor targetanalyse nog waardevoller omdat de app exact weet waar het target stond, hoe groot het was en welke vorm het had.

Beste combinatie:

- normale Gaming/Browsing-recordings voor spontaan gedrag;
- zelfgespeelde Aim Lab-sessies voor nauwkeurige targetmetingen;
- profielreplay om beide met elkaar te vergelijken.

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
