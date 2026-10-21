# U1 Planspiel Cockpit

## Öffnen

`dist/index.html` per Doppelklick oder mit `Dashboard öffnen.cmd` öffnen. Die App benötigt weder Installation noch Internet noch einen Server. HTML, CSS, JavaScript, Diagramme und PDF-Daten sind lokal vorhanden. Browserdaten wie Szenarien können bei `file:` je Browser unterschiedlich gespeichert werden; Export und Import als JSON funktionieren unabhängig davon.

Die Bereiche sind Überblick, Markt & Kosten, Produktion & Personal, Finanzen, Szenario-Labor, Empfehlungen und Quellen. Kennzahlenkarten, Wettbewerber und Quellen öffnen Details. Tooltips funktionieren auch mit der Tastatur. Im Szenario aktualisieren sich Ergebnisse bei jeder Eingabe; Empfehlungen werden erst durch einen bewussten Klick übernommen.

## Daten aktualisieren

1. Neue Original-PDFs in den übergeordneten Planspiel-Ordner legen.
2. `Aktualisieren.cmd` ausführen. Alternativ `python refresh_data.py` mit installiertem `pypdf` aufrufen.
3. Dashboard neu laden.

Der Import durchsucht **alle PDFs** im Projektordner. Echte U1-Berichte werden über die Executive Summary und die dortige Periodennummer erkannt; Probe-Dateien sind ausgeschlossen. Gewinnübersichten ergänzen Perioden ohne Detailbericht. Aktuell sind Detailberichte für P1, P2 und P4 vorhanden, für P3 nur die Gewinnübersicht. `P3_korrigiert_U1.pdf` enthält tatsächlich Periode 2. Die nächste passende Business-News wird anhand ihrer Periodennummer zugeordnet.

`dist/data.js` und `data.json` enthalten die aufbereiteten Werte, alle Fundstellen und extrahierten PDF-Seiten. Die Originaldokumente werden nicht verändert. Ein grundsätzlich anderes Berichtslayout kann eine Anpassung des Importers erfordern. Ist ein Schlüsselwert nicht lesbar, bricht der Import mit einer Meldung ab, statt Werte zu erfinden.

## Modellgrenzen und Kostenrechnung

Das Labor ist eine **bedingte Planrechnung**, keine Nachbildung der geheimen TOPSIM-Nachfrageformel. Absatz ist eine eigene, veränderbare Annahme. Preis-, Werbe-, Vertriebs- und F&E-Entscheidungen verändern die Kosten bzw. den Umsatz je verkaufter Einheit; sie erzeugen keine erfundene Nachfragewirkung. Die P5-Nachrichten geben lediglich stabile bis leicht steigende Nachfrage an. Der Startwert von rund +2 % und der Sensitivitätsbereich ±10 % sind ausdrücklich Annahmen.

- Produktion ist durch Anlagen begrenzt. Zeitarbeit ergänzt den Bedarf an Arbeitsleistung anteilig.
- Großhandel wird vor dem Shop beliefert; verbleibende Stücke bleiben im Lager.
- Materialfehlmengen werden zu dokumentierten Einzelbestellpreisen ergänzt. Zusätzliche Vorräte verursachen Lagerkosten und Liquiditätsbindung.
- Herstellkosten dienen der Lagerbewertung. Material, Löhne, Zeitarbeit und Anlagenaufwand werden genau einmal erfasst. Durchschnittliche Herstellkosten werden nicht ein zweites Mal als Aufwand abgezogen.
- Neue Anlage: 55.000 € Auszahlung, 2.500 € sonstige Fixkosten + 5.000 € Wartung pro Periode, 5.000 € Abschreibung. Kaufpreis und Abschreibung werden getrennt behandelt.
- Gemeinsame Kosten werden für die Herstellwertschätzung nach Personalanteilen auf die Fertigung verteilt. Das entspricht näherungsweise dem P4-Bericht und ist keine vollständig veröffentlichte Spielregel.
- Lagerbewertung der Fertigwaren erfolgt zum gewichteten Durchschnitt aus übernommenem Lagerwert und neuen Herstellkosten. Verwaltungskosten werden mit dem im Handbuch beschriebenen Umsatzanteil von 2 % plus 5.000 € gerechnet.
- Kasse: übernommene Kasse + Forderungen + 75 % des Szenarioumsatzes + neue Kredite / Anlagenverkauf, abzüglich laufender Auszahlungen, alter Kredite, Investitionen, Steuern, Zinsen und 50 % des letzten Gewinns als Dividende. Überziehungszinsen sind in der iterativen Fehlbetragsberechnung enthalten.
- Anlagenverkauf erfolgt im Modell älteste zuerst, zum Buchwert der letzten Auswertung, mit 25 % Erlös; dies ist eine sichtbar bezeichnete zeitliche Annahme.

Die App macht dokumentierte Abweichungen sichtbar: P3-Staffel vs. P4-Materialpreise, Lagerkosten, Zeitarbeitssatz, Kreditzinsen, aktuelle Produktivität, Steuerquote und ungenaue Angaben der Formularvorlage. P4-Werte sind teilweise nur eine Fortschreibung für P5. Die Empfehlung ist deshalb ein Vorschlag unter den angezeigten Annahmen.

Wichtig: Im P4-Planvergleich sind 695.130 € der **potenzielle** Shop-Umsatz. Tatsächlich wurden 714.510 € im Shop erzielt; weitere 20.000 € kamen aus dem Großhandel. Der historische Großhandelspreis lässt sich mit 400 € je Stück ableiten. Die neue P5-Offerte beträgt 380 €.

## Dateien

- `dist/index.html`, `styles.css`: Oberfläche und responsive Gestaltung.
- `dist/app.js`: Navigation, Diagramme, Tooltips, Drill-down, Eingaben, Speicherung, Export/Import.
- `dist/model.js`: getrennte, nachvollziehbare Kosten-, Kapazitäts- und Liquiditätsrechnung.
- `dist/data.js`, `data.json`: generierte Daten samt Quellen und Originaltexten.
- `refresh_data.py`: PDF-Import und dynamische Periodenerkennung.
- `tests/model.test.js`: gezielte Rechenprüfungen und Rückrechnung gegen P4.

## Prüfung

`node tests/model.test.js`

Der P4-Rückvergleich prüft Herstellkosten, Betriebsergebnis, Periodengewinn und Kassenbestand innerhalb der Rundungen des Berichts. Weitere Prüfungen decken Lieferpriorität, Kapazitätsgrenzen, Personal-/Zeitarbeitskosten, Investition vs. Abschreibung, Kreditbedarf und den Verzicht auf unbelegte Nachfragewirkungen ab. Die Oberfläche wird zusätzlich im Browser mit breitem und schmalem Ansichtsfenster geprüft.

Prüfung vom 20.10.2026: Alle neun Rechenprüfungen bestanden. Alle sieben Ansichten wurden im Browser geprüft, einschließlich 390-Pixel-Mobilansicht ohne seitlichen Seitenüberlauf. Quellen- und Kennzahlen-Drill-down, Tastatur-Tooltips, Periodenwechsel P1–P4, Parameterschieber, Speichern/Laden sowie JSON-Export/Import wurden bedient. Keine JavaScript-Fehler in der Browserkonsole. Screenshots liegen unter `qa/`.

Die Browserprüfung erfolgte über eine ausschließlich lokale HTTP-Vorschau. Der automatisierte Browser erlaubt kein `file:`-Protokoll; der direkte Dateistart wurde deshalb dort nicht geprüft. Die ausgelieferte App verwendet gewöhnliche lokale Script-Dateien und keine Netzwerkanfragen oder externen Bibliotheken. Die PDF-Links setzen voraus, dass `dashboard/` im ursprünglichen Projektordner bleibt.
