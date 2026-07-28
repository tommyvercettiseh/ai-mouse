# Changelog

## 1.1.0 — Integrated learning hub

### Added
- Aim Lab als ingebouwde pagina binnen AI Mouse Lab.
- Gaming 360° als ingebouwde Raw Input-pagina binnen AI Mouse Lab.
- `Replay profile` met confidence-gewogen bochten en alleen bewezen Aim Lab-overshoot.
- Aparte clickprofielen per muisknop met holdduur en beweging tijdens vasthouden.
- Apart scrollprofiel voor richting, stapgrootte, bursts, pauzes en omkeringen.
- Turbo Repo Hub-featuremetadata voor geïntegreerde pagina's en replayfuncties.

### Changed
- Trace rendering draait nu op een vaste renderloop en vervaagt na ongeveer 1,6 seconde.
- Nieuwe muispunten forceren niet meer bij ieder event een volledige directe redraw.
- `Play trace` verandert tijdens afspelen in `Stop trace`.
- Scrollgegevens beïnvloeden uitsluitend scrolllogica en niet de muiscurve.
- Masterprofiel gebruikt schema versie 2 met gescheiden movement-, click- en scrolllagen.

### Fixed
- Gaming 360° leest nu de juiste `yaw_deg`, `pitch_deg` en raw-countvelden.
- Profile Replay gebruikt de echte laterale Y-afwijking van genormaliseerde traces.
- Click releases bevatten direct de gekoppelde holdduur en sleepafstand.

### Manual verification
- Framerate en fade moeten op de doel-pc met drie monitoren visueel worden gecontroleerd.
- Windows Raw Input moet per game worden gecontroleerd, omdat games en overlays verschillend met input omgaan.
- Aim Lab-resizing en DPI-scaling moeten op de gebruikte Windows-schaalfactor worden gecontroleerd.

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
