# Changelog

## 0.2.0

### Added
- Globale muistracking over de volledige Windows virtual desktop
- Ondersteuning voor meerdere schermen en negatieve schermcoördinaten
- Registratie van bewegingen, klikken, scrollen en actief venstertitel
- Visuele live trace en replay met instelbare fading
- Replay-snelheid van 0,25× tot 4×
- Privacy metadata die bevestigt dat toetsenbord en ingevoerde tekst niet worden opgenomen
- Automatische installatie van `pynput` via de Windows-launcher
- Tests voor globale eventdata, multi-monitor metadata en privacyvelden

### Changed
- De lokale canvasrecorder is vervangen door globale tracking
- De interface gebruikt de goedgekeurde donkere AI Mouse-layout
- Versie verhoogd naar 0.2.0

### Safety
- Er worden geen toetsen, wachtwoorden of ingevoerde teksten geregistreerd
- Replay vindt alleen visueel binnen de AI Mouse Hub plaats
- Externe applicaties worden niet door replay of Stress Lab bestuurd
- Alle data blijft lokaal onder `data/`

## 0.1.0

### Added
- Standalone lokale muisrecorder binnen eigen canvas
- Gelabelde sessies en include/exclude-beheer
- Masterprofiel en profielhistorie
- Echte replayvergelijking
- Profile Stress Lab met JSON-rapporten
- Windows-launchers, logging, tests en GitHub Actions

### Safety
- Geen besturing van externe applicaties
- Ruwe recordings worden niet overschreven
- Alle data blijft lokaal onder `data/`
