# Changelog

## 1.0.0 — Clean foundation

### Added
- Volledig nieuwe minimalistische AI Mouse Lab-interface.
- Globale muisrecorder voor move, click en scroll zonder keyboardcapture.
- Multi-monitor live map met actuele cursor en trace.
- Visuele trace playback zonder externe cursorbesturing.
- Automatisch gebalanceerde Aim Lab voor klein/groot × dichtbij/veraf.
- Automatische variatie in rondjes, vierkanten, driehoeken en schermzones.
- Logging van reaction time, movement time, click delay, click hold, snelheid, overshoot, correcties en eindoffset.
- Windows Raw Input-module voor onbeperkte relatieve gamebewegingen.
- Optionele 360°-kalibratie voor virtuele yaw/pitch.
- Profielbouwer die alle lokale recordings en Aim Lab-sessies combineert.
- Turbo Repo Hub-manifest, PID-bestand, healthcheck en vaste loglocatie.
- Windows-launchers met automatische virtuele omgeving en dependency-installatie.
- Automatische tests voor metrics, scheduler, modedetectie en profielopbouw.

### Changed
- Alle oude Score Labs, stresslabs en concurrerende dashboards zijn verwijderd.
- De normale interface toont geen technische categorieën of instellingenpanelen.
- Replay bestuurt uitsluitend een virtuele trace in het eigen venster.

### Manual verification
- Live Windows Raw Input, multi-monitorgeometrie en Tkinter-scaling moeten op de doel-pc handmatig worden gecontroleerd.
