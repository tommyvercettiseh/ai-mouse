# Changelog

## 0.6.0

### Added
- Moderne minimalistische multi-monitorweergave in de hoofdapp
- Automatische detectie van alle aangesloten Windows-schermen
- Actieve schermhighlight tijdens live opname en profielreplay
- Schermnummer, resolutie en primaire-monitorstatus in het canvas
- Knop `Open opnamemap` die direct `data/recordings` opent in Windows Verkenner
- Nieuwe module `screen_layout.py` voor monitorgeometrie en puntdetectie

### Changed
- `Start AI Mouse Hub.bat` start nu de nieuwe moderne interface
- Hero, statusbalk, opnamepaneel en profielpaneel zijn compacter en moderner vormgegeven
- Versie verhoogd naar 0.6.0

### Safety
- Replay blijft uitsluitend visueel binnen AI Mouse Hub
- Geen toetsenbordinput of getypte tekst
- Geen externe applicatiebesturing

## 0.5.0

### Added
- Moderne minimalistische gradient-interface
- Duidelijke knop voor masterprofiel maken en vernieuwen
- Kliktest direct vanuit de hoofdapp openen

## 0.4.0

### Added
- Losse minimalistische `Profile Click Test`
- Willekeurige doelvlakken binnen een lokaal testvenster
- Zichtbaar profielpad met approach, correctie en overshoot
- Fading trace tijdens iedere testactie
- Directe lijn als visuele referentie
- Metingen voor directe afstand, werkelijk pad, overshoot, correcties en klikafstand
- Eigen Windows-launcher: `Start Profile Click Test.bat`
- Tests voor padtransformatie, eindpunten en overshootmetingen

### Safety
- De kliktest werkt uitsluitend binnen het eigen lokale canvas
- De test verplaatst of klikt niet in externe applicaties
- Profielgegevens blijven lokaal

## 0.3.0

### Added
- Pauze en hervat tijdens globale opname
- Automatische segmentatie op stilstand en lange pauzes
- Cursorwarp-detectie op basis van afstand, tijd en snelheid
- Replay die losse segmenten nooit kunstmatig met elkaar verbindt
- Profielreplay met fading trace binnen de lokale app
- Tests voor warpfiltering, pauzes en recorderstatus

### Changed
- Interface teruggebracht tot Record, Pauze, Opslaan, sessiekeuze en Replay
- Uitgebreide analyse draait automatisch onder de motorkap

## 0.2.0

### Added
- Globale muistracking over de volledige Windows virtual desktop
- Ondersteuning voor meerdere schermen en negatieve schermcoördinaten
- Registratie van bewegingen, klikken, scrollen en actief venstertitel
- Visuele live trace en replay met instelbare fading
- Privacy metadata en automatische installatie van `pynput`

## 0.1.0

### Added
- Standalone lokale muisrecorder
- Gelabelde sessies en masterprofiel
- Replayvergelijking en Stress Lab
- Windows-launchers, logging, tests en GitHub Actions
