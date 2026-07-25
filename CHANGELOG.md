# Changelog

## 0.9.1

### Added
- Automatische masterprofielupdate na een voltooide menselijke Aim Lab-run
- Combinatie van gewone recordings en menselijke Aim Lab-templates
- Extra selectiegewicht voor Aim Lab-data met bekende targets
- Rechtermuisknop reset alleen de huidige targetactie
- Logging van misklikken en handmatige resets per target

### Fixed
- Meerdere misklikken laten de Aim Lab niet meer vastlopen
- Mouse-downstatus wordt na iedere misser direct opgeschoond
- Profielreplay laadt na een menselijke run meteen het vernieuwde masterprofiel

### Safety
- Geen toetsenbordinput of getypte tekst
- Geen externe cursorbesturing of externe clicks

## 0.9.0

### Added
- Zelfgespeelde Aim Lab-modus waarin de gebruiker echte targets aanklikt
- Ronde en vierkante targets in klein, middel en groot
- Korte, middelgrote en lange bewegingen
- Extra nadruk op hoeken, randen en diagonale verplaatsingen
- Logging van reactietijd, bewegingstijd, clickdelay en click-holdduur
- Volledige target- en padlogging naar `data/aim_lab`
- Aparte profielreplay-modus voor vergelijking met de menselijke poging

### Changed
- De Aim Lab start standaard als menselijke test in plaats van automatische profielanimatie
- Bestaande recordings blijven bron voor spontane pre-click-curves en timing
- Zelfgespeelde Aim Lab-sessies worden de primaire bron voor exacte targetanalyse

### Safety
- Geen toetsenbordinput of getypte tekst
- Geen screenshots
- Profielreplay bestuurt geen externe applicaties

## 0.8.0

### Added
- Extractie van echte pre-click-bewegingen uit opgeslagen muissessies
- Persoonlijke templates met curve, timing, afstand, overshoot, correcties, context en kwaliteit
- Target-aware padgenerator die echte menselijke vorm behoudt bij rotatie en schaling
- Minimalistische Aim Lab met kleine, middelgrote en grote targets
- Volledige lokale logging per Aim Lab-actie naar `data/aim_lab`
- Eigen launcher: `Start Aim Lab Test.bat`
- Tests voor template-extractie, contextselectie, curvebehoud, eindoffset en clickdelay

### Changed
- De oude rechte kliktest is vervangen door een menselijke profieltest
- Echte clicks worden niet gekopieerd; alleen aankomst-tot-clickvertraging wordt als virtuele timing gebruikt
- De hoofdrecorder is teruggebracht naar uitsluitend muisdata

### Safety
- Geen toetsenbordinput of getypte tekst
- Geen externe cursorbeweging of clicks
- Aim Lab gebruikt uitsluitend een virtuele cursor in het lokale testvenster

## 0.6.0

### Added
- Moderne minimalistische multi-monitorweergave in de hoofdapp
- Automatische detectie van alle aangesloten Windows-schermen
- Actieve schermhighlight tijdens live opname en profielreplay
- Schermnummer, resolutie en primaire-monitorstatus in het canvas
- Knop `Open opnamemap` die direct `data/recordings` opent in Windows Verkenner
- Nieuwe module `screen_layout.py` voor monitorgeometrie en puntdetectie

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

## 0.3.0

### Added
- Pauze en hervat tijdens globale opname
- Automatische segmentatie op stilstand en lange pauzes
- Cursorwarp-detectie op basis van afstand, tijd en snelheid
- Replay die losse segmenten nooit kunstmatig met elkaar verbindt

## 0.2.0

### Added
- Globale muistracking over de volledige Windows virtual desktop
- Ondersteuning voor meerdere schermen en negatieve schermcoördinaten
- Registratie van bewegingen, klikken en scrollen

## 0.1.0

### Added
- Standalone lokale muisrecorder
- Gelabelde sessies en masterprofiel
- Replayvergelijking en Stress Lab
