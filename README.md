# AI Mouse Lab

Een minimalistische lokale Windows-app die jouw **eigen muisgedrag** vastlegt en analyseert.

De voorkant blijft bewust eenvoudig:

- **Record**
- **Stop**
- **Play trace / Stop trace**
- **Replay profile**
- **Open recordings**
- **Build profile**
- een abstracte liveweergave van alle aangesloten schermen
- ingebouwde **Aim Lab**
- ingebouwde **Gaming 360°**

De technische analyse gebeurt op de achtergrond. De app registreert uitsluitend muisdata; geen toetsenbordinput, getypte tekst of screenshots.

## Starten

Dubbelklik op:

```text
Start Project.bat
```

Directe launchers:

```text
Start AI Mouse Lab.bat
Start Aim Lab.bat    # compatibility launcher
Stop Project.bat
```

Aim Lab en Gaming 360° zijn normaal gewoon pagina's binnen AI Mouse Lab. De losse Aim Lab-launcher blijft alleen behouden voor backwards compatibility.

De launcher maakt automatisch `.venv`, installeert dependencies en schrijft fouten naar `data/logs/launcher.log`.

## Wat wordt geregistreerd?

### Normaal gebruik

- absolute X/Y-positie over alle monitoren;
- beweging, muisknoppen en scroll;
- timestamps en actieve monitor;
- snelheid, acceleratie, remfase en padverhouding;
- korte, middellange en lange bewegingen;
- monitorovergangen;
- click down/up, holdduur en beweging tijdens vasthouden;
- automatisch onderscheid tussen normale absolute bediening en relatieve game-input.

### Scroll

Scrolls worden volledig gelogd, maar uitsluitend gebruikt voor een apart scrollprofiel:

- richting;
- stapgrootte;
- pauze tussen stappen;
- aantal stappen per burst;
- burstduur;
- richtingomkeringen.

Scrollgegevens veranderen nooit de vorm, snelheid of bochten van een muistrace.

### Gaming

Windows Raw Input wordt alleen voor de muis gebruikt. Daardoor blijven relatieve `dx/dy`-bewegingen doorlopen wanneer een game de cursor in het midden vasthoudt. De app bewaart onbeperkte relatieve rotatie in raw counts. Na een optionele 360°-kalibratie kan dit ook als virtuele yaw/pitch worden opgeslagen.

### Aim Lab

Je kiest niets zelf. De scheduler bewaakt automatisch een evenwichtige dataset:

- 25% klein + dichtbij;
- 25% klein + veraf;
- 25% groot + dichtbij;
- 25% groot + veraf.

Rondjes, vierkanten, driehoeken en verschillende schermzones worden eveneens gebalanceerd. Per target worden route, reactie, snelheid, overshoot, correcties, eindoffset, click delay en click hold opgeslagen.

## Traceweergave

De live trace draait op een vaste renderloop. Recente segmenten zijn helder en oudere segmenten vervagen na ongeveer 1,6 seconde. Tijdens playback verandert de knop automatisch van `Play trace` naar `Stop trace`.

`Replay profile` maakt een uitsluitend visuele trace:

- bij 0% profielsterkte vrijwel recht;
- bij meer data steeds meer gemeten bochten en microvariatie;
- overshoot pas wanneer voldoende Aim Lab-targets dit ondersteunen;
- de replay bestuurt nooit een externe applicatie.

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

Schema versie 2 houdt drie lagen bewust apart:

- movementprofiel;
- clickprofiel;
- scrollprofiel.

## Turbo Repo Hub

De repository bevat `turbo-project.json` met:

- versie;
- preview;
- Windows-startcommando;
- PID- en logbestand;
- healthcheckcommando;
- geïntegreerde pagina's en featureflags.

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
```
