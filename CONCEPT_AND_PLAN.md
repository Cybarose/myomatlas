# AUB-Tool: Konzept, Hintergrund und Bauplan

Kurzbeschreibung: Ein offenes, bildgestuetztes Entscheidungs- und Aufklaerungs-Tool
fuer starke/abnorme Regelblutung. Computer Vision segmentiert Myome im Becken-MRT,
ein Claude-Agent ordnet sie nach FIGO/PALM-COEIN ein, erzeugt einen strukturierten
Befund plus eine patientenverstaendliche Erklaerung, und eine 3D-Ansicht zeigt die
Lage. Das Tool verifiziert sich selbst gegen die offenen Ground-Truth-Daten.

---

## 1. Hintergrund fuer dich (kurzer Primer)

Was heisst AUB? AUB steht fuer "Abnormal Uterine Bleeding", also abnorme uterine
Blutung: jede Regelblutung, die von der Norm abweicht in Haeufigkeit, Regelmaessigkeit,
Dauer oder Menge. Der Alltagsbegriff dafuer ist "starke/unregelmaessige Regelblutung",
der Fachbegriff fuer die reine Mengen-Variante ist "heavy menstrual bleeding" (HMB).

Warum es zaehlt: Bis zu ein Drittel der Frauen erlebt im Leben eine AUB. Sie ist eine
Hauptursache fuer Eisenmangel und Anaemie, kostet Lebensqualitaet, Energie und
Arbeitstage, und wird trotzdem oft als "normal" abgetan. Weniger als die Haelfte der
betroffenen Frauen geht ueberhaupt zum Arzt, und wenn doch, ist die Abklaerung oft
unvollstaendig.

Das Ordnungssystem PALM-COEIN: Die FIGO teilt die Ursachen einer AUB in zwei Gruppen.
- PALM = strukturelle Ursachen (im Bild sichtbar): Polyp, Adenomyose, Leiomyom (Myom),
  Malignitaet/Hyperplasie.
- COEIN = nicht-strukturelle Ursachen (aus Anamnese/Labor): Coagulopathie,
  Ovulationsstoerung, Endometrium, Iatrogen, Not yet classified.
Unser Tool deckt vor allem das "L" (Myom) per Bild ab und laesst Claude die restlichen
Kategorien aus den klinischen Angaben mitdenken, inklusive der Malignitaets-Wachsamkeit.

Warum die Lage alles entscheidet (FIGO-Typen 0 bis 8): Myome werden nach ihrer Lage
zur Gebaermutterhoehle und zur Aussenwand klassifiziert.
- Typ 0 bis 2 (submukoes, ragt in die Hoehle): verursacht die staerksten Blutungen und
  ist am fertilitaetsrelevantesten, oft gebaermuttererhaltend per Hysteroskopie entfernbar.
- Typ 3 bis 5 (intramural, in der Wand): haeufigste Form, oft symptomarm.
- Typ 6 bis 7 (subseroes, nach aussen): eher Druck-/Bulk-Symptome.
- Typ 8: sonstige Lagen (z.B. zervikal).
Merksatz: Der Typ steuert Blutung, Fruchtbarkeit und Behandlung. Genau diese Logik wird
in der Praxis selten sauber befundet und der Patientin selten erklaert. Das ist die Luecke.

Das Problem in einem Satz: Die Ursache der Blutung entscheidet ueber die richtige
Behandlung, wird aber uneinheitlich befundet und der Frau nicht verstaendlich gemacht,
was zu verschleppter Diagnose, Anaemie und teils vermeidbarer Gebaermutterentfernung fuehrt.

---

## 2. Das Konzept

Benannter Nutzer: eine Gynaekologin oder Radiologin, die Becken-MRTs bei Blutungs-
beschwerden befundet, oder eine Frau, die ihren eigenen Befund verstehen will.

Was das Tool tut (End-to-End):
1. Bild rein (MRT-Fall aus dem offenen Datensatz oder Upload).
2. CV segmentiert Gebaermutterwand, Gebaermutterhoehle und jedes Myom, misst Groesse,
   Zahl und Lage relativ zu Hoehle und Serosa.
3. Claude-Agent nimmt den CV-Output plus eine kurze Symptom-Abfrage und:
   - vergibt den FIGO-Typ pro Myom, hergeleitet aus einer FIGO-Regeldatei, Schritt fuer
     Schritt nachvollziehbar,
   - ordnet den Fall in PALM-COEIN ein und flaggt, wenn Malignitaet auszuschliessen ist,
   - erzeugt einen strukturierten Befund plus Management-Optionen (inkl. gebaermutter-
     und fertilitaetserhaltender) fuer Shared Decision Making,
   - schreibt eine patientenverstaendliche Erklaerung.
4. 3D-Ansicht rekonstruiert die Gebaermutter mit farbcodierten Myomen aus den Masken.
5. Selbstverifikation: laeuft auf dem Held-out-Split und zeigt gemessene Segmentierungs-
   guete (Dice) und FIGO-Typ-Uebereinstimmung gegen die Experten-Annotationen.

Die Arbeitsteilung (der Pruefstein): CV sieht (Bild wird zu Geometrie). Claude schliesst
(Geometrie plus Klinik wird zu FIGO/PALM-COEIN, Management, Befund, Erklaerung). Damit ist
Claude lasttragend, nicht Deko.

Der Burggraben: die Regeldatei. Eine strukturierte Datei (JSON), die FIGO-Typen 0-8, die
PALM-COEIN-Logik und die Management-Zuordnung mit Quellen kodiert. Claude schliesst aus
dieser Datei, statt frei zu assoziieren. Das ist der Kern, der das Tool korrekt und
verteidigbar macht.

Warum es gewinnt: echtes CV auf offenen, gelabelten Daten (verifizierbar), ein Tool, das
so noch nicht existiert (PALM-COEIN wird bisher nur von Hand angewendet), eine schoene
3D-Visualisierung, und ein dokumentiert reales, breit relevantes Problem.

---

## 3. Technische Entscheidung: Web-App (nicht Qt)

Empfehlung: Web-App. Gruende: der Hackathon ist virtuell (Jury schaut aus der Ferne),
3D laeuft im Web nativ und schoen ueber three.js, ein modernes Web-Frontend wird schneller
sehr huebsch, es ist plattformuebergreifend, leicht zu demoen (URL oder lokal im Browser)
und andere Entwickler koennen es leicht starten. Qt kann 3D auch, ist aber Desktop-only,
schwerer und langsamer schoen zu machen. Beides ginge, aber Web ist hier klar besser.

Stack:
- Frontend: React + Vite + TypeScript + Tailwind. 3D ueber three.js bzw. react-three-fiber.
- Backend: Python + FastAPI.
- CV: PyTorch, Segmentierung (nnU-Net oder ein U-Net; du kannst auch YOLOv8-seg testen).
- 3D: Masken zu Mesh ueber marching cubes (scikit-image oder VTK), Export als glTF/OBJ.
- Agent: Claude Agent SDK (Python), liest die Regeldatei, nutzt die Messwerte als Tools.

---

## 4. Repo-Struktur

```
aub-tool/
  README.md
  CONCEPT_AND_PLAN.md
  .gitignore                 # ignoriert .env, data/, Modellgewichte
  .env.example               # ANTHROPIC_API_KEY=... (Platzhalter, echter Key NIE ins Repo)
  backend/
    app/
      main.py                # FastAPI-Einstieg, Endpunkte
      cv/                    # Segmentierung, Messwerte, Mesh-Erzeugung
      agent/                 # Claude-Agent-Logik und Tools
      rules/
        figo_palm_coein.json # die Regeldatei (der Burggraben)
      verification/          # Held-out-Eval: Dice + FIGO-Uebereinstimmung
    requirements.txt
  frontend/
    src/
      components/
      viewer/                # three.js 3D-Ansicht
      report/                # Befund- und Patientenerklaerung-Panel
    package.json
  data/                      # UMD liegt hier, per .gitignore ausgeschlossen
```

---

## 5. Code-Konventionen (fuer spaetere Open-Source-Mitentwickler)

- Kommentare: sparsam und praezise. Erklaere das Warum, nicht das Offensichtliche.
- Keine Gedankenstriche (Em-Dashes) und keine Emojis im Code oder in Kommentaren.
- Typisierung, wo sinnvoll (TypeScript im Frontend, Type Hints in Python).
- Kleine, benannte Funktionen statt langer Bloecke.
- Keine Geheimnisse im Code. Keys kommen aus Umgebungsvariablen.

---

## 6. Datensatz (verifiziert offen verfuegbar)

UMD (Uterine Myoma MRI Dataset), Scientific Data 2024, DOI 10.1038/s41597-024-03170-x.
- 300 Faelle T2WI sagittal Becken-MRT, Alter 21 bis 86.
- Pixelgenaue Masken fuer 4 Regionen: Gebaermutterwand, Gebaermutterhoehle, Myom,
  Nabothi-Zyste/Kapsel.
- Deckt alle 9 FIGO-Typen ab, annotiert und geprueft von 11 Aerzt:innen.
- Von den Autoren ausdruecklich fuer FIGO-Klassifikation und 3D-Rekonstruktion vorgesehen.
- Bezug: ueber den Abschnitt "Data Availability / sharing and access policies" im Paper.
  Falls dort ein kurzes Formular ist, ist der Zugang ueblicherweise sofort. Bitte den
  genauen Download-Link im Paper einmal bestaetigen, bevor Phase 1 startet.

Spine-first-Trick: Baue die gesamte Pipeline zuerst auf den mitgelieferten Ground-Truth-
Masken (Masken zu Messwerten zu FIGO zu Befund zu 3D zu Frontend). Erst danach trainierst
du den eigenen Segmentierer. So laeuft die Demo auch, wenn dein Modell noch grob ist.

---

## 7. Claude SDK, Open Source und Kosten

Wie die Abrechnung funktioniert: Die Anthropic-API rechnet pro Token ueber den API-Key ab,
der zu deinem Konto gehoert. Wichtig fuer Open Source:
- Du legst deinen Key NIE ins Repo. Er liegt in .env (per .gitignore ausgeschlossen), und
  du gibst nur eine .env.example mit Platzhalter mit.
- Wer dein Repo klont, muss seinen EIGENEN ANTHROPIC_API_KEY setzen und zahlt seine eigene
  Nutzung. Fremde, die deinen Open-Source-Code laufen lassen, kosten dich also nichts.
- Nur wenn du selbst eine oeffentliche gehostete Instanz mit deinem Key betreibst, laufen
  alle Anfragen ueber dein Konto.

Fuer den Hackathon: Halte fuer die Bewertung eine gehostete Demo bereit (durch die
200-Dollar-Credits gedeckt, mit einem einfachen Rate-Limit), oder liefere Repo plus
Demo-Video und lass Nutzer per eigenem Key selbst hosten. So machen es Open-Source-KI-Tools
normalerweise: Repo ist "bring your own key", eine optionale Demo finanziert/limitiert der
Betreiber. Aktuelle Preise und Details: https://docs.claude.com/en/docs/about-claude/pricing
und https://docs.claude.com/en/api/overview

Hinweis: Auch das Bauen mit Claude Code verbraucht Credits. 200 Dollar reichen fuer einen
Hackathon gut, wenn du gezielt promptest.

Zu Fable: Claude Fable 5 ist ein Modell (ueber die API/Claude Code ansprechbar), kein
Frontend-Framework. Du kannst es (oder Opus) als Modell nutzen, das den Frontend-Code
generiert. Ueberdenke es nicht zu sehr: Nimm zum Bauen das Modell, das Claude Code dir
anbietet, und entscheide beim Frontend spaeter, ob Fable dir dort einen Vorteil bringt.

---

## 8. Bauplan in Phasen (jeweils mit Claude-Code-Prompt)

Arbeitsweise: eine Phase nach der anderen. Nach jeder Phase kurz pruefen, ob es laeuft,
dann die naechste. Halte den Scope eng: erst die duenne End-to-End-Wirbelsaeule, dann
Qualitaet.

### Phase 0: Geruest
Ziel: Ordnerstruktur, .gitignore, .env.example, leeres FastAPI-Backend, leeres Vite-React-
Frontend, README-Grundgeruest.

Claude-Code-Prompt:
"Erstelle die Ordnerstruktur aus CONCEPT_AND_PLAN.md Abschnitt 4. Lege ein FastAPI-Backend
mit einer /health-Route und einem requirements.txt an (fastapi, uvicorn, torch, numpy,
scikit-image, nibabel, anthropic, python-dotenv). Initialisiere ein Vite-React-TypeScript-
Frontend mit Tailwind und three.js. Erstelle .gitignore (ignoriere .env, data/, *.pth,
node_modules) und .env.example mit ANTHROPIC_API_KEY-Platzhalter. Kommentare sparsam,
keine Em-Dashes, keine Emojis."

### Phase 1: Daten und Wirbelsaeule auf Ground-Truth-Masken
Ziel: UMD laden, einen Fall visualisieren, aus den mitgelieferten Masken die Messwerte
(Myom-Zahl, Groesse, Lage zu Hoehle/Wand) berechnen. Noch kein eigenes Modell.

Claude-Code-Prompt:
"Schreibe einen Loader fuer den UMD-Datensatz in backend/app/cv, der Bild und
Maskenregionen (Wand, Hoehle, Myom, Nabothi) einliest. Berechne pro Myom: Groesse in mm,
Kontakt/Ueberlappung mit der Gebaermutterhoehle und mit der Serosa, und den prozentualen
intramuralen Anteil. Gib ein strukturiertes JSON pro Fall aus. Schreibe ein kleines Skript,
das einen Beispielfall mit ueberlagerten Masken als PNG speichert."

### Phase 2: Segmentierung (dein CV)
Ziel: ein U-Net/nnU-Net auf UMD trainieren, das dieselben Regionen vorhersagt. Danach kann
die Wirbelsaeule aus Phase 1 auf den Vorhersagen statt den Ground-Truth-Masken laufen.

Claude-Code-Prompt:
"Baue in backend/app/cv eine Trainings- und Inferenzpipeline (PyTorch) fuer die
Mehrklassen-Segmentierung der UMD-Regionen. Nutze einen Train/Val-Split (z.B. 80/20, fixe
Seed). Speichere Gewichte nach data/ (gitignored). Schreibe eine Inferenzfunktion, die aus
einem Bild dieselbe Maskenstruktur wie Phase 1 liefert."

### Phase 3: 3D-Rekonstruktion
Ziel: aus den Masken ein 3D-Mesh (marching cubes), Myome nach Region/Typ eingefaerbt,
Export als glTF fuer das Frontend.

Claude-Code-Prompt:
"Schreibe in backend/app/cv eine Funktion, die aus den 3D-Masken ein glTF-Mesh erzeugt:
Gebaermutterwand halbtransparent, Hoehle und Myome als eigene, einfaerbbare Meshes.
Stelle das Mesh ueber eine FastAPI-Route bereit."

### Phase 4: Die Regeldatei (Burggraben)
Ziel: FIGO 0-8, PALM-COEIN und Management-Zuordnung als figo_palm_coein.json, mit kurzen
Quellenverweisen.

Claude-Code-Prompt:
"Erstelle backend/app/agent/rules/figo_palm_coein.json. Kodiere pro FIGO-Typ 0-8 die
geometrische Definition (Bezug zu Hoehle und Serosa), typische Symptomrelevanz und die
in Leitlinien genannten Behandlungsoptionen inkl. gebaermuttererhaltender. Ergaenze die
PALM-COEIN-Kategorien und eine Regel, wann Malignitaet auszuschliessen ist. Jede Regel mit
kurzem Quellenhinweis."

### Phase 5: Der Claude-Agent
Ziel: Agent nimmt CV-JSON plus kurze Symptom-Abfrage, leitet FIGO-Typ pro Myom her,
ordnet in PALM-COEIN ein, erzeugt strukturierten Befund, Management und Patientenbrief.

Claude-Code-Prompt:
"Baue in backend/app/agent einen Claude-Agenten mit dem Anthropic Python SDK. Tools:
get_measurements (liest das CV-JSON), lookup_rules (liest figo_palm_coein.json). Der Agent
soll pro Myom den FIGO-Typ mit Begruendung bestimmen, den Fall in PALM-COEIN einordnen,
Management-Optionen ableiten und zwei Ausgaben liefern: einen strukturierten Fachbefund und
eine patientenverstaendliche Erklaerung. Der Agent schliesst ausschliesslich aus der
Regeldatei, nicht aus freiem Wissen. Key aus Umgebungsvariable."

### Phase 6: Frontend
Ziel: Upload/Fallauswahl, 3D-Viewer, Befund-Panel, Patientenerklaerung, Chat mit dem Agenten.

Claude-Code-Prompt:
"Baue das React-Frontend: eine Seite mit Fallauswahl, einem three.js-3D-Viewer (laedt das
glTF, Myome nach FIGO-Typ farbcodiert, drehbar), einem Panel fuer den strukturierten Befund
und einem Panel fuer die Patientenerklaerung, plus ein Chatfeld zum Agenten. Sehr sauberes,
ruhiges, klinisch wirkendes Design mit Tailwind."

### Phase 7: Selbstverifikation (der Trust-Move)
Ziel: auf dem Held-out-Split Dice und FIGO-Typ-Uebereinstimmung messen und im Frontend als
kleines Trust-Panel zeigen.

Claude-Code-Prompt:
"Schreibe in backend/app/verification ein Skript, das die Segmentierung auf dem Val-Split
gegen die Ground-Truth misst (Dice pro Region) und die vom Agenten vergebenen FIGO-Typen
gegen die UMD-Labels vergleicht (Accuracy, Konfusionsmatrix). Gib die Ergebnisse als JSON
aus und zeige sie im Frontend als 'So gut trifft das Tool'-Panel."

### Phase 8: Politur, README, Demo
Ziel: README (Setup, BYO-Key, Lizenzhinweis der Daten), Beispielfaelle, kurzes Demo-Video
(2 bis 5 Minuten). Letzten Tag fuer das Video reservieren.

---

## 9. Scope-Disziplin und Risiken

- Wirbelsaeule zuerst. Wenn Zeit knapp wird, muss die Kette Masken zu FIGO zu Befund zu 3D
  auf wenigen Faellen sauber laufen. Das trainierte Modell ist Kuer, nicht Pflicht.
- MRT ist 3D und schwerer als 2D. Halte die Segmentierung schlicht, degradiere elegant
  (Klinikerin bestaetigt/korrigiert Messwerte, Agent rechnet weiter).
- Nicht ueberclaimen: Entscheidungsunterstuetzung mit Mensch in der Schleife, kein
  zugelassenes Geraet.
- Energie in Reasoning, Befundqualitaet und ein schoenes Frontend, nicht ins Plumbing.
