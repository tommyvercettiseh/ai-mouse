# AI Mouse Lab

Een minimalistische lokale Windows-app die jouw **eigen muisgedrag** vastlegt en analyseert.

De voorkant blijft bewust eenvoudig:

- **Record**
- **Stop**
- **Play trace**
- **Open recordings**
- **Build profile**
- een abstracte liveweergave van alle aangesloten schermen
- een losse, automatisch gebalanceerde **Aim Lab**

De technische analyse gebeurt op de achtergrond. De app registreert uitsluitend muisdata; geen toetsenbordinput, getypte tekst of screenshots.

## Starten

Dubbelklik op:

```text
Start Project.bat
```

Directe launchers:

```text
Start AI Mouse Lab.bat
Start Aim Lab.bat
Stop Project.bat
```

De launcher maakt automatisch `.venv`, installeert dependencies en schrijft fouten naar `data/logs/launcher.log`.

## Wat wordt geregistreerd?

### Normaal gebruik

- absolute X/Y-positie over alle monitoren;
- beweging, muisknoppen en scroll;
- timestamps en actieve monitor;
- snelheid, acceleratie, remfase en padverhouding;
- korte, middellange en lange bewegingen;
- monitorovergangen;
- click delay en click hold;
- automatisch onderscheid tussen normale absolute bediening en relatieve game-input.

### Gaming

Windows Raw Input wordt alleen voor de muis gebruikt. Daardoor blijven relatieve `dx/dy`-bewegingen doorlopen wanneer een game de cursor in het midden vasthoudt. De app bewaart onbeperkte relatieve rotatie in raw counts. Na een optionele 360°-kalibratie kan dit ook als virtuele yaw/pitch worden opgeslagen.

### Aim Lab

Je kiest niets zelf. De scheduler bewaakt automatisch een evenwichtige dataset:

- 25% klein + dichtbij;
- 25% klein + veraf;
- 25% groot + dichtbij;
- 25% groot + veraf.

Rondjes, vierkanten, driehoeken en verschillende schermzones worden eveneens gebalanceerd. Per target worden route, reactie, snelheid, overshoot, correcties, eindoffset, click delay en click hold opgeslagen.

## Data

```text
data/
├── recordings/   normale browse-, werk- en gamesessies
├── aim_lab/      menselijke targettests
├── profiles/     samengesteld masterprofiel
├── logs/         launcher- en app-logboeken
└── runtime/      PID-bestand voor Turbo Repo Hub
```

`Build profile` voegt alle bruikbare JSON/JSONL-sessies samen tot:

```text
data/profiles/master_profile.json
```

## Turbo Repo Hub

De repository bevat `turbo-project.json` met:

- versie;
- preview;
- Windows-startcommando;
- PID- en logbestand;
- healthcheckcommando;
- secundaire Aim Lab-launcher.

Daardoor kan een toekomstige Turbo Repo Hub de app herkennen, starten, stoppen en controleren zonder terminalcommando's.

## Veiligheidsgrens

- geen keyboard recording;
- geen screenshots;
- geen externe app-automatisering;
- trace playback is uitsluitend visueel binnen AI Mouse Lab;
- alle gegevens blijven lokaal.

## Ontwikkelen

```powershell
python -m pip install -r requirements.txt
pytest
python -m ai_mouse_lab.app
python -m ai_mouse_lab.app --aim-lab
```
