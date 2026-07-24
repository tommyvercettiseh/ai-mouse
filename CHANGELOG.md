# Changelog

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
- README herschreven rond de eenvoudige workflow

### Safety
- Verdachte jumps blijven in de ruwe opname maar worden niet als doorlopende beweging afgespeeld
- Geen toetsenbordinput of getypte tekst
- Replay bestuurt geen externe applicaties

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
