# AI Mouse

Minimalistische lokale Windows-app met twee onderdelen:

1. **AI Mouse Hub** voor opnemen, stoppen, afspelen en de opnamemap openen.
2. **Aim Lab** waarin je zelf willekeurige targets aanklikt.

## Starten

Hoofdapp:

```text
Start AI Mouse Hub.bat
```

Aim Lab:

```text
Start Aim Lab Test.bat
```

## AI Mouse Hub

De hoofdapp bevat alleen de basis:

- Record;
- Stop + opslaan;
- geselecteerde opname afspelen;
- `data/recordings/` openen;
- label kiezen voor Gaming, Browsing, Werk of Precision;
- compact overzicht van alle aangesloten monitoren;
- actieve monitor en actuele muispositie tonen.

Opnames worden lokaal opgeslagen onder:

```text
data/recordings/
```

## Aim Lab

De Aim Lab kiest automatisch per target:

- rondje, vierkant of driehoek;
- klein, middel of groot;
- korte, middelgrote of lange beweging;
- midden, rand, hoek of diagonale sprong.

Per geldig target worden onder andere opgeslagen:

- volledige muisroute met timestamps;
- targetvorm, positie en grootte;
- accuracy en eindoffset;
- overshoot;
- mini-correcties;
- reactietijd;
- bewegingstijd;
- clickdelay;
- click-holdduur;
- gemiddelde en maximale snelheid;
- misklikken en handmatige resets.

Een misklik stopt de test niet. Klik met de **rechtermuisknop** om alleen het huidige target opnieuw te starten.

Aim Lab-resultaten worden lokaal opgeslagen onder:

```text
data/aim_lab/
```

## Privacy

- Alleen muisbewegingen, muisknoppen en scroll worden opgenomen.
- Geen toetsenbordinput of getypte tekst.
- Geen screenshots.
- Alles blijft lokaal.
- Replay bestuurt geen externe applicaties.
