# TimeSheet Management

Eine zentrale, lokal betriebene Arbeitszeiterfassung für kleine Teams. Das
Projekt verbindet eine unkomplizierte Windows-Desktop-Anwendung mit einem
langfristig geplanten Google-Workflow für Tabellen, E-Mail-Kommunikation,
Genehmigungen und Auswertungen.

> **Projektstatus:** frühe MVP-Version. Die Kernfunktionen arbeiten lokal. Die
> Google-Anbindung ist architektonisch vorbereitet, aber noch nicht aktiviert.

## Vision

TimeSheet Management soll für kleine Unternehmen als übersichtliches
Arbeitszeit-Launchpad dienen: Ein zentraler Rechner steht dem Team zur Verfügung,
Mitarbeiter melden sich lokal an und erfassen Beginn, Pause und Ende ihres
Arbeitstags mit wenigen Klicks. Abwesenheiten und nachträgliche Korrekturen
folgen klaren Genehmigungsprozessen.

Die Anwendung soll auf Dauer drei Bereiche zusammenführen:

1. **Schnelle tägliche Bedienung:** anmelden, Aktion auswählen, fertig.
2. **Nachvollziehbare Verwaltung:** Genehmigungen, Änderungsverlauf,
   Arbeitszeitregeln und Monatsauswertungen.
3. **Offene Google-Integration:** Google Sheets als kontrollierbare zentrale
   Datenablage und Gmail als strukturierter Kommunikationskanal.

Das Ziel ist kein schwergewichtiges Personalverwaltungssystem, sondern ein
verständlich aufgebautes Werkzeug, das transparent bleibt und schrittweise mit
dem Betrieb wachsen kann.

## Aktueller Funktionsumfang

### Anmeldung und Benutzer

- sichere lokale Anmeldung
- Ersteinrichtungsassistent statt ausgeliefertem Standardpasswort
- passwortbasierte Speicherung mit PBKDF2-SHA256 und individuellem Salt
- Rollen `Mitarbeiter` und `Administrator`
- Anlage weiterer Mitarbeiterkonten durch Administratoren
- lokale Speicherung; Google-Kennwörter werden nicht verwendet

### Arbeitszeiterfassung

- Arbeitsbeginn
- Pausenbeginn
- Pausenende
- Arbeitsende
- Schutz vor unlogischen Buchungsreihenfolgen
- laufende Anzeige von Arbeitszeit und Pausenzeit
- minutengenauer Tagessaldo gegenüber acht Sollstunden
- Tagesliste aller Zeitereignisse
- tatsächliche Ereignisse werden auch bei Regelverstößen dokumentiert

### Arbeitszeit- und Pausenregeln

Die MVP-Konfiguration orientiert sich am deutschen Arbeitszeitgesetz und den
festgelegten betrieblichen Rahmenbedingungen:

- Sollzeit Montag bis Freitag
- regulärer Zeitrahmen von 08:00 bis 16:30 Uhr
- acht Stunden Soll-Arbeitszeit
- 30 Minuten unbezahlte Regelpause
- bei mehr als sechs bis einschließlich neun Stunden mindestens 30 Minuten Pause
- bei mehr als neun Stunden mindestens 45 Minuten Pause
- Warnung bei einem ununterbrochenen Arbeitsblock von mehr als sechs Stunden
- Warnung bei mehr als zehn Stunden täglicher Arbeitszeit

Regelverstöße werden absichtlich **nicht automatisch korrigiert oder gelöscht**.
Das System kennzeichnet sie, bewahrt aber die tatsächlich erfassten Zeiten. So
bleibt die Dokumentation vollständig und kann durch einen Administrator geprüft
werden.

Die Software ist ein technisches Hilfsmittel und ersetzt keine rechtliche oder
personalwirtschaftliche Prüfung besonderer Tarif-, Branchen- oder
Betriebsvereinbarungen.

### Abwesenheiten

Aktuell unterstützte Arten:

- Urlaub
- Feiertag
- Überstundenabbau

Mitarbeiter wählen Art und Zeitraum und können eine Bemerkung hinterlegen. Neue
Anträge erhalten zunächst den Status `Offen`. Ein Administrator kann sie
genehmigen oder ablehnen. In der persönlichen Übersicht bleibt der Status
nachvollziehbar.

### Nachträgliche Korrekturen

- Antrag für ein bestimmtes Datum
- gewünschter Beginn und gewünschtes Ende
- gewünschte Pausendauer
- verpflichtende Begründung
- Freigabe oder Ablehnung durch einen Administrator
- genehmigte Korrekturen erzeugen gekennzeichnete Zeitereignisse
- ursprüngliche Anträge und Prüfdaten bleiben in der Datenbank erhalten

### Administration und Auswertung

- Mitarbeiterkonten anlegen
- offene Abwesenheitsanträge bearbeiten
- offene Korrekturanträge bearbeiten
- Monatsauswertung je Mitarbeiter
- gesamte erfasste Arbeitszeit
- Überstunden- beziehungsweise Minusstundensaldo
- genehmigte Abwesenheitstage
- Anzahl der Tage mit Pausen- oder Arbeitszeitwarnungen

### Darstellung

- standardmäßig aktivierter Dark Mode
- dunkelgraue, an moderne GPT-Oberflächen angelehnte Grundfläche
- hell- beziehungsweise neonblaue Akzente an Buttons, Feldern, Tabs und Tabellen
- jederzeit wechselbarer Light Mode
- persistente Darstellungseinstellung pro Windows-Arbeitsplatz

## Schnellstart

### Voraussetzungen

- Windows 11
- Python 3.11 oder neuer
- Python-Komponente `Tcl/Tk` beziehungsweise `tkinter`

Bei der regulären Python-Installation für Windows muss die optionale Komponente
`tcl/tk and IDLE` aktiviert sein. Für `pyenv-win` muss zuerst eine vollständige
Python-Version installiert und als lokale oder globale Version ausgewählt werden.

### Anwendung starten

PowerShell im Projektordner öffnen und ausführen:

```powershell
.\run.ps1
```

Beim ersten Start erscheint die Ersteinrichtung:

1. lokalen Admin-Benutzernamen eingeben
2. Anzeigenamen vergeben
3. Passwort mit mindestens acht Zeichen festlegen
4. Einrichtung abschließen
5. im Administrationsbereich die Mitarbeiterkonten anlegen

Es werden keine vorgegebenen Zugangsdaten ausgeliefert.

## Bedienkonzept

### Typischer Arbeitstag

1. Mitarbeiter meldet sich am zentralen Rechner an.
2. Er wählt `Arbeit beginnen`.
3. Vor der Pause wählt er `Pause beginnen`.
4. Nach der Pause wählt er `Pause beenden`.
5. Zum Feierabend wählt er `Arbeit beenden`.
6. Die Tagesübersicht zeigt Arbeitszeit, Pause, Saldo und mögliche Warnungen.

### Urlaub beantragen

1. Mitarbeiter öffnet `Abwesenheiten`.
2. Er wählt `Urlaub`, Startdatum und Enddatum.
3. Optional ergänzt er eine Bemerkung.
4. Der Administrator sieht den offenen Antrag.
5. Der Administrator genehmigt oder lehnt ihn ab.

### Vergessene Buchung korrigieren

1. Mitarbeiter öffnet `Korrekturen`.
2. Er trägt Datum, Beginn, Ende und Pausenzeit ein.
3. Er beschreibt den Grund der Änderung.
4. Nach Adminfreigabe ersetzt die genehmigte Korrektur die Tagesereignisse.
5. Die Herkunft `correction` bleibt in der Datenbank dokumentiert.

## Datenspeicherung

Die erste Version verwendet SQLite. Standardpfad:

```text
%LOCALAPPDATA%\TimeSheetManagement\timesheet.db
```

Die Darstellungseinstellung liegt unter:

```text
%LOCALAPPDATA%\TimeSheetManagement\settings.json
```

Lokale Laufzeitdaten, Datenbanken und OAuth-Dateien sind über `.gitignore` vom
Repository ausgeschlossen.

### Datenmodell

| Tabelle | Zweck |
|---|---|
| `users` | lokale Konten, Rollen und Passwort-Hashes |
| `time_events` | einzelne Zeitereignisse mit Quelle und Zeitstempel |
| `absence_requests` | Abwesenheitsanträge und Genehmigungsstatus |
| `correction_requests` | beantragte Zeitkorrekturen und Prüfdaten |
| `audit_log` | protokollierte Aktionen für spätere Nachvollziehbarkeit |

Zeitwerte werden als ISO-8601-Zeitstempel gespeichert. Die Anwendung verwendet
die lokale Windows-Zeitzone. Überstunden werden nicht gerundet.

## Architektur

```text
src/timesheet/
├── app.py             Tkinter-Oberfläche und lokale Workflows
├── database.py        SQLite-Schema und Transaktionszugriff
├── service.py         Regeln, Berechnungen und Anwendungslogik
├── security.py        Passwort-Hashing und Passwortprüfung
└── google_gateway.py  vorbereitete Grenze zur Google-Integration
```

Die Trennung zwischen Oberfläche, Geschäftslogik und Datenbank erleichtert es,
später eine andere Oberfläche, Google Sheets oder einen Hintergrunddienst
anzubinden, ohne die Arbeitszeitregeln neu schreiben zu müssen.

## Google-Integration: geplantes Konzept

Google wird ausschließlich über OAuth 2.0 angebunden. Ein normales
Google-Kontopasswort ist dafür weder erforderlich noch zulässig.

### Google Sheets

Geplant ist eine Arbeitsmappe mit getrennten, maschinenlesbaren Tabellen:

- `Employees`
- `TimeEvents`
- `Absences`
- `Corrections`
- `Approvals`
- `Settings`
- `SyncLog`

SQLite bleibt dabei als lokaler Cache und sichere Warteschlange erhalten. Bei
vorübergehend fehlender Internetverbindung können Buchungen lokal fortgesetzt
und später synchronisiert werden. Konflikte sollen nicht still überschrieben,
sondern markiert und administrativ geklärt werden.

### Gmail

Die geplante Kommunikation verwendet definierte Betreffzeilen, beispielsweise:

```text
[TSM][URLAUB][ANTRAG] Mitarbeiter – 2026-08-17 bis 2026-08-21
[TSM][URLAUB][GENEHMIGT] Antrag 42
[TSM][KORREKTUR][OFFEN] Mitarbeiter – 2026-08-14
[TSM][WARNUNG][PAUSE] Mitarbeiter – 2026-08-14
```

E-Mails erhalten zusätzlich eine eindeutige Vorgangs-ID. Dadurch müssen keine
unsicheren Freitextinterpretationen vorgenommen werden. Wiederholt gelesene
Nachrichten können anhand dieser ID erkannt werden.

### Voraussetzungen für die spätere Aktivierung

1. Google-Cloud-Projekt anlegen
2. Gmail API aktivieren
3. Google Sheets API aktivieren
4. OAuth-Zustimmungsbildschirm konfigurieren
5. OAuth-Client vom Typ `Desktop-App` erstellen
6. `credentials.json` nur lokal bereitstellen
7. Ziel-Sheet anlegen und dessen ID konfigurieren
8. benötigte Berechtigungen nach dem Prinzip der geringsten Rechte freigeben

`credentials.json`, OAuth-Tokens und Kennwörter dürfen niemals committed werden.

## Sicherheit und Datenschutz

Bereits umgesetzt:

- keine Standardzugänge
- keine Klartextpasswörter in SQLite
- PBKDF2-SHA256 mit 600.000 Iterationen und zufälligem Salt
- parametrisierte SQL-Anweisungen
- lokale OAuth-Dateien durch `.gitignore` ausgeschlossen
- Rollenprüfung in der Oberfläche
- nachvollziehbare Genehmigungsdatensätze

Vor einem produktiven Einsatz zusätzlich vorgesehen:

- Adminfunktion zum Ändern und Zurücksetzen lokaler Passwörter
- automatische Bildschirmsperre nach Inaktivität
- verschlüsselte lokale Tokens über Windows Credential Manager
- regelmäßige verschlüsselte Backups
- vollständiges manipulationsgeschütztes Audit-Protokoll
- Lösch- und Aufbewahrungskonzept
- konfigurierbare Rollen und feinere Berechtigungen
- dokumentierte DSGVO-Verantwortlichkeiten
- Wiederherstellungstest für lokale und synchronisierte Daten

## Tests

Die Tests verwenden ausschließlich die Python-Standardbibliothek:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

Aktuell geprüft werden:

- erfolgreiche und fehlgeschlagene Anmeldung
- zulässige Buchungsreihenfolge
- vollständiger Acht-Stunden-Tag
- Pausenschwellen bei sechs und neun Stunden
- Abwesenheitsgenehmigung
- genehmigte Zeitkorrektur

## Roadmap

### Phase 1 – stabiler lokaler MVP

- [x] Ersteinrichtung und lokale Anmeldung
- [x] Arbeits- und Pausenbuchungen
- [x] Überstundenberechnung
- [x] Abwesenheitsworkflow
- [x] Korrekturworkflow
- [x] Adminansicht
- [x] Monatsauswertung
- [x] Dark und Light Mode
- [ ] automatische Feiertage für Bayern und das Augsburger Friedensfest
- [ ] Passwortverwaltung
- [ ] CSV-Export
- [ ] Backup und Wiederherstellung
- [ ] Windows-Installer

### Phase 2 – Google Sheets und Gmail

- [ ] OAuth-Einrichtungsassistent
- [ ] Google-Sheets-Struktur automatisch anlegen
- [ ] bidirektionaler Sync mit lokaler Warteschlange
- [ ] strukturierte Gmail-Benachrichtigungen
- [ ] Idempotenz und Konfliktbehandlung
- [ ] Syncstatus in der Oberfläche
- [ ] manuelle Wiederholung fehlgeschlagener Übertragungen

### Phase 3 – erweiterte Zeitwirtschaft

- [ ] unterschiedliche Wochenmodelle und Teilzeit
- [ ] individuelle Sollstunden
- [ ] Feiertagskalender und regionale Sondertage
- [ ] Krankheit und weitere Abwesenheitstypen
- [ ] halbe Urlaubstage
- [ ] Pausenerinnerungen
- [ ] Ruhezeitprüfung zwischen Arbeitstagen
- [ ] Ausgleichszeitraum für längere Arbeitstage
- [ ] Überstundenkonten mit Freigabegrenzen
- [ ] Monatsabschluss und Sperrung abgeschlossener Perioden

### Phase 4 – Berichte und Betrieb

- [ ] CSV- und PDF-Berichte
- [ ] Jahresübersichten und Urlaubssaldo
- [ ] grafische Trends und Warnungsanalyse
- [ ] revisionsfähige Änderungsverläufe
- [ ] automatische Backups
- [ ] konfigurierbare Datenaufbewahrung
- [ ] Diagnose- und Supportpakete ohne personenbezogene Geheimnisse
- [ ] signierte Windows-Pakete und Updateprozess

### Langfristige Möglichkeiten

- Betrieb auf mehreren Terminals mit zentralem Sync
- optionales Web-Dashboard für Administratoren
- Kalenderintegration für genehmigte Abwesenheiten
- mobile Erfassung mit eingeschränkten Rechten
- Projekt- und Tätigkeitszeiten
- Kostenstellen und Kundenbezug
- Import aus bestehenden Zeiterfassungen
- Export für Lohnabrechnung und Steuerberatung
- Benachrichtigungen an Teams oder andere Kommunikationsdienste
- Schnittstelle für anonymisierte betriebliche Auswertungen

Diese Erweiterungen sind bewusst als mögliche Entwicklungslinien dokumentiert.
Sie werden nicht automatisch Bestandteil des Produkts, sondern sollten nach
Nutzen, Datenschutz und Wartungsaufwand priorisiert werden.

## Bekannte Einschränkungen der ersten Version

- Google-Sync und Gmail-Versand sind noch deaktiviert.
- Feiertage werden noch nicht automatisch angelegt.
- Sollstunden sind noch fest auf acht Stunden pro Arbeitstag ausgelegt.
- Zeitkorrekturen nehmen für die Pause eine mittige Position im Arbeitstag an.
- Monatsauswertungen berücksichtigen derzeit erfasste Arbeitstage und genehmigte
  Abwesenheiten, aber noch keinen vollständigen Sollstundenkalender.
- Es gibt noch keinen Windows-Installer.
- SQLite-Dateien werden noch nicht automatisch gesichert.

## Mitwirken

Fehler und Erweiterungsideen können als GitHub Issue dokumentiert werden. Für
Änderungen empfiehlt sich ein eigener Branch mit Tests für neue Geschäftsregeln.
Insbesondere Regeln zu Arbeitszeit, Urlaub und Datenschutz sollten mit klaren
Beispielen und erwarteten Ergebnissen beschrieben werden.

## Lizenz

Für das Projekt ist noch keine Lizenz festgelegt. Bis eine Lizenzdatei ergänzt
wurde, entstehen durch die öffentliche Sichtbarkeit des Quellcodes keine
automatischen Nutzungsrechte.
