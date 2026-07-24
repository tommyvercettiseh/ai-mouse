# AI Mouse Profile Hub

Standalone lokale desktop-app voor het opnemen, labelen, analyseren en visueel naspelen van muisbewegingen over je volledige Windows-desktop.

## Starten op Windows

Dubbelklik op:

- `Start AI Mouse Hub.bat`
- `Start Profile Stress Lab.bat`

De launcher maakt automatisch een virtuele Python-omgeving en installeert `pynput` voor globale muistracking.

## Functies

- Globale muistracking over alle aangesloten schermen
- Ondersteuning voor browsen, gamen en andere applicaties
- Registratie van muisbewegingen, klikken en scrollen
- Actieve venstertitel per gebeurtenis voor context
- Geen registratie van toetsenbordinput of ingevoerde tekst
- Visuele live trace met fading
- Replay binnen de hub met instelbare snelheid en fadingduur
- Recordings labelen en lokaal opslaan
- Masterprofiel bouwen uit geselecteerde sessies
- Profile Stress Lab met 10–5000 versnelde runs
- JSON-rapporten en JSONL-data
- Windows-launchers, logs, tests en GitHub Actions

## Gebruik

1. Open `Start AI Mouse Hub.bat`.
2. Kies een label, bijvoorbeeld `Browsing` of `Gaming`.
3. Klik op **Start globale opname**.
4. Gebruik je computer normaal over al je schermen.
5. Ga terug naar AI Mouse en klik op **Stop & opslaan**.
6. Selecteer de opname en klik op **Replay** om de fading trace te bekijken.
7. Bouw daarna optioneel een masterprofiel en voer de 100× stresstest uit.

## Privacy

AI Mouse registreert alleen muisdata:

- X- en Y-coördinaten
- tijdstempels
- muisklikken
- scrollbewegingen
- actieve venstertitel

Er worden geen toetsaanslagen, wachtwoorden, berichten of andere ingevoerde teksten opgeslagen. Replay bestuurt geen externe applicaties en vindt uitsluitend visueel binnen de hub plaats.

## Data

Alle lokale data staat onder `data/` en hoort niet in Git te worden opgeslagen:

```text
data/recordings/
data/profiles/
data/stress_lab/
data/logs/
```
