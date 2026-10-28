---
name: data/linear-a/protocol-c/builds/hurrian/notes
title: "Transkriptionsnotizen"
desc: "The hurrian builder's notes on the units, forms, segmentations and doubts, as written."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Transkriptionsnotizen

Grundlage ist ausschließlich Wegners Grammatik (2000) in den in `units.md` bezeichneten Einheiten. Alle 33 Einheiten wurden vollständig gelesen. Die vorhandene OCR wurde mit den betreffenden PDF-Seiten abgeglichen; bei Abweichungen gilt das PDF. Gedruckte Seitenzahlen sind von den PDF-Seitenzahlen unterschieden. Die in `units.md` erwähnte zusätzliche `.ocr.json` liegt hier nicht vor und wurde nicht benutzt.

## Umfang und Quellenbezeichnung

Als eindeutige Einheitenbezeichnung dient der unveränderte Eintrag der Spalte „Section / table no.“. Für die drei mit `II.C.5` bezeichneten Einheiten dient stattdessen die jeweils unterschiedliche, unverändert übernommene Überschrift aus der Titelspalte. `source.section` bezeichnet den Abschnitt; `source.page` die gedruckte Seite.

Identische Kombinationen aus Morphem, Schreibung, Segmentfolge und Slot werden nur einmal eingetragen. Weitere Einheiten, die dieselbe Kombination liefern, stehen unter `notes` des Eintrags. Eine Einheit, deren Formen schon anderweitig eingetragen sind, gilt deshalb ebenfalls als Quelle von Einträgen. Alle Einheiten liefern mindestens einen Eintrag; `units_without_entries` ist leer. Die Übersicht II.C.4, 11. liefert den ausdrücklich benannten Jussivanzeiger -i- in Anm. 79, nicht ein zusätzlich rekonstruiertes Paradigma.

Die vollständigen deklarierten Paradigmenausgänge werden auch dann bewahrt, wenn die Grammatik sie intern mit `+` oder `=` zerlegt. Daneben stehen die in einer Einheit selbständig genannten Bestandteile. Zusammengesetzte Ausgänge haben eigene Morphemkennungen; die Kennung behauptet hier keine Unteilbarkeit. Gleiche Lautfolgen mit verschiedenen Funktionen sind nicht gleichgesetzt. Unterschiedliche Schreibungen eines identifizierten Formanten teilen eine Morphemkennung. Abweichende Grenzzeichen bleiben in `form` erhalten und können daher mehrere Einträge derselben Segmentfolge ergeben.

## Abgrenzung

- Freie Postpositionen und selbständige Partikeln werden nicht zu Affixen gemacht. Insbesondere sind die in II.C.5 beschriebenen Wörter für Körper, Gesicht, Blick und Mitte trotz ihrer grammatischen Verwendung eigenständige Wörter; ihre ausgeschriebenen Possessivsuffixe und Kasuskennzeichen sowie die ausdrücklich enklitischen Partikeln und Pronominalallomorphe sind berücksichtigt.
- Die Satzanfangskonjunktionen auf S. 99 bleiben frei. Ein im Wörterbuchstil angehängter Bindestrich allein macht sie nicht gebunden. Die dort ausdrücklich angeführten Allomorphe /lle/, /lla/, /me/, /nna/ sind dagegen aufgenommen.
- Die Wortbildungsbestandteile -hhe, -šše und -arde in der Spalte „Wurzel+WEn“ der nominalen Tabellen 1 und 2 werden nicht als nominale Flexionssuffixe eingetragen. Die zugelassenen nominalen Kategorien umfassen keine allgemeine nominale Derivation. Aus der bloßen Tabellenzelle wird auch keine zusätzliche verbale Funktion erschlossen.
- Die Bindevokale -u-, -o- und -i- sind keine selbständigen Kasus-, Personen-, Numerus- oder Modalzeichen. Sie erhalten keinen erfundenen Slot. In ausdrücklich gedruckten Kombinationen wie -iff=u-, -aš=u=š und -u-da bleiben sie enthalten. Ihre Tabellenpositionen sind gelesen, aber nicht als zusätzliche Morpheme behandelt. Das ist eine schwierige Grenze zwischen „alle Formen“ und den ausdrücklich zugelassenen Kategorien.
- Orthographische Angaben unter „Graphie“ sind keine zusätzlichen phonemischen Allomorphe. Die daneben ausdrücklich gegebenen Lautvarianten in eckigen Klammern oder Schrägstrichen werden aufgenommen. Ganze Beispielwörter, lexikalische Wurzeln, Literaturtitel und Vergleichsmaterial sind keine Einträge. Die in `units.md` ausgeschlossenen personenspezifischen Beispielparadigmen auf S. 88–89 werden nicht als weitere Inventarquelle ausgeschöpft; die ausdrücklich benannten Formanten im erklärenden Text des zugelassenen Abschnitts bleiben berücksichtigt.
- In den Listen und erklärenden Abschnitten bleiben unsichere, aber ausdrücklich gedruckte Formen erhalten. Nicht ausgeschriebene Ergebnisse von Assimilationsregeln werden nicht neu erzeugt: etwa wird aus der Erklärung zu -kko und -kki in Tabelle 5/6 kein zusätzliches -kka erfunden.

## Schreibung und Segmentierung

- -iffə auf S. 54 und in Tabelle 2 hat tatsächlich das besondere Auslautzeichen ə. Anm. 59 erklärt es als Zeichen unsicherer Lautung. Es wurde weder zu a noch zu e normalisiert. Die tatsächliche phonemische Bestimmung bleibt offen.
- Hyphen, Pluszeichen, Gleichheitszeichen, Klammern, Sternchen und Fragezeichen bleiben in `form`, aber nicht in `segments`. Hochgestellte Fußnotenziffern sind Verweise, keine Bestandteile der Form. Schriftart und Kapitälchengröße können im JSON nicht wiedergegeben werden; die Kapitälchen NE und NA bleiben als Großbuchstaben erhalten.
- Bei fakultativen Lauten werden beide ausdrücklich zugelassenen Segmentfolgen eingetragen: z.B. -an(n)-, -š(a), -(i)t-, +(a)ffu und -u(w). Ist ein ganzer Formant eingeklammert, wird nur seine nichtleere Realisierung eingetragen. `(?)` bezeichnet Unsicherheit, keinen fakultativen Laut. Die Klammern um die Varianten (-b/p) bezeichnen ebenfalls keine Nullrealisierung.
- Bei kompakten Alternativschreibungen bleibt die ganze gedruckte Kurzschreibung im Feld `form`; unterschiedliche Segmentfolgen zeigen die Alternativen an. Gemeinsame Teile werden dabei mitgelesen: -t/da → ta/da, -t/dan → tan/dan, -ni/e? → ni/ne, -u/ol- → ul/ol, *-o/ur- → or/ur. Das ist eine Interpretation der abgekürzten Drucknotation; ihre genaue Reichweite ist nicht eigens definiert und bleibt als Segmentierungsunsicherheit vermerkt. Explizite Lautalternativen wie =u [o] werden getrennt als u und o wiedergegeben, ohne die erste Schreibung zu tilgen.
- Doppelkonsonanten sind in `segments` konservativ als zwei aufeinanderfolgende gleiche Zeichen bewahrt. Die zugelassenen Einheiten entscheiden nicht systematisch, ob jede einzelne Verdopplung als ein Längenphonem oder als zwei Konsonantensegmente zu analysieren ist. Diese phonologische Frage wird nicht durch zusätzliche Normalisierung entschieden. Auch ae und ai bleiben zwei Vokalzeichen; Längenzeichen wie ā in iffāš und /mān/ bleiben am Vokal.
- V in -Všt- und -kkV- ist ein Decksymbol und bleibt genau **ein** Segment `V`. Es wird nicht durch erschlossene Vokale ersetzt. In -Všt- genannte konkrete Beispielrealisierungen ašt-, ešt- und ušt- sind zusätzlich aufgenommen. NE und NA sind dagegen keine Vokaldecksymbole: die Segmentfolgen sind N+E und N+A.
- Die Endungen =i= (i)d en und =i= (i)d= anni auf S. 116 werden mechanisch mit und ohne das ausdrücklich eingeklammerte i wiedergegeben. Dabei kann ii entstehen. Eine Kontraktion oder phonologische Längeninterpretation wird nicht ergänzt.
- Leerraum zwischen Bestandteilen einer Tabellenzeile wird als einfacher Leerraum wiedergegeben; die breite typographische Spaltenausrichtung wird nicht imitiert.

## Nullen und fehlende Formen

Folgende Nullen erhalten keine Einträge:

- Absolutiv Singular in der Kasustabelle S. 57; Absolutiv in Tabellen 1 und 2, S. 65 und 69.
- Präsens / neutraler Aspekt im Tempusverzeichnis S. 77 sowie in Tabellen 3, 4, 5/6, 7 und 13 (S. 80, 82, 85, 86, 114).
- Subjektanzeiger 3. Sg. beim intransitiven und antipassivischen Verb in Tabelle 5/6, S. 85; die Tabelle sagt ausdrücklich „also nicht -nna“.
- Null des Subjektanzeigers 3. Pl. nach dem transitiv-ergativischen -o in Tabelle 12, S. 112; Null der 3. Sg. bei den dortigen Bewegungsverben auf -a und den unklaren Handlungsverben auf -u.
- Die weitere Null in der Spalte „3. und 4.“ von Tabelle 13, S. 114.
- Patiens im Absolutiv im Schema II.D.2, S. 102; Subjekt im Absolutiv und Personenanzeiger 3. Sg. im Schema II.D.3, S. 102.
- Die leere Alternative ganz fakultativer Klammerformen, insbesondere -(na), (-ol-), (-il-) und (-id-).

Leere Zellen, „unbesetzt“, Gedankenstriche und „usw.“ sind keine Formen. Das negative Paradigma S. 81 bezeichnet 2. Sg. und 3. Pl. ausdrücklich als nicht belegt; der Verweis zur 3. Sg. ersetzt dort keine gedruckte Form. Tabelle 8 hat keinen eigenen Jussivanzeiger in der 2. Sg./Pl. Diese Lücken werden nicht ergänzt.

## PDF-Korrekturen und innere Unterschiede

Die OCR verwechselt š in den nominalen Plural- und Kasusformen häufig mit f oder l, und liest die verbalen Tabellen mehrfach falsch. Im PDF bestätigt sind insbesondere -aš-, -š(a-), -Všt-, -tta/t, die Wurzelerweiterung -ol- in Tabelle 5/6 und -ill- in Tabelle 12. Die OCR-Lesungen -af-, -al-, -na/t, -oš- an der Wurzelerweiterungsstelle von Tabelle 5/6 und -il- in Tabelle 12 werden nicht übernommen. Tabelle 8 hat in der 1. Pl. **-š(?)**, in der 2. Pl. **e+š(?)**. Ihre Spalten wurden anhand des Bildes gelesen, nicht anhand der verrutschten OCR-Zeile.

Folgende Unterschiede bzw. Unsicherheiten sind im Druck selbst vorhanden und bleiben bestehen:

- S. 66 nennt für 2. Pl. -ppa mit [-ffa] (Fußnote: Bilingue), kurz -p [b/v]. Tabellen 1 und 5/6 drucken dagegen -ffa/f. Beide Bestände sind aufgenommen; -f wird nicht aus der anderen Tabelle herauskorrigiert.
- Die Kasustabelle S. 57 bezeichnet den Absolutiv Plural als -(na), während Tabellen 1 und 2 -na als „Artikel“ Plural führen. Die Schreibung bleibt verschieden; die Kennung ordnet beide dem pluralischen Artikel zu.
- Tabelle 8 versieht die pluralischen Jussivausgänge mit Fragezeichen; S. 91 nennt pluralische Imperative -eš bzw. -e+š ohne diese Zeichen. Beide Angaben bleiben erhalten.
- Tabelle 9 zeigt (-id-), erklärt aber in der Fußnote ausdrücklich, dass ein negierter Jussiv der 3. Pl. nicht belegt ist. Der gedruckte Formant ist eingetragen und als hypothetischer Paradigmenplatz gekennzeichnet; ein vollständiges unbelegtes Paradigma wird nicht erzeugt.
- S. 87 sagt, Modalformen besäßen keine „eigentlichen Personenzeichen“, während Tabellen 8 und 9 eine Spalte „Personenanzeiger des Jussivs“ führen. Für -l+e, -lli und -en gilt die konkrete Tabellenkategorie; ihre theoretische Analyse bleibt offen.
- Tabelle 12 führt Wurzelerweiterungen teilweise unter „wahrscheinlich aber Aspekt/Aktionsart“; die Funktion wird nicht präziser bestimmt, als die Tabelle erlaubt. Die doppelte Platzierung von -Všt-? wird nicht als zwei verschiedene Morpheme gezählt.
- Die 2. Pl. des Possessivums -šu? bleibt unsicher. Die Kasus -ni/e? und -e? bleiben unsicher. Die Deutungen der Ausgänge -o/uw(a)en, -o/uwen und -owen (S. 92–93), der Formanten -il-/-ol- sowie der Wunschformen auf S. 96–97 werden nicht harmonisiert.
- Die auf S. 77 in Anm. 76 referierte Deutung von -ud- als Negativmorphem steht neben dem unklaren Wurzelerweiterungsformanten -ut-. Beide schriftlich ausgewiesenen Formen sind aufgenommen; die alternative Deutung steht beim Eintrag.

Es blieb kein ganzer obligatorischer Tabelleneintrag aufgrund unleserlicher Druckgestalt ausgelassen. Die genannten Unsicherheiten betreffen die Analyse oder die besondere Notation, nicht stillschweigend ersetzte OCR-Lesungen.

## Grenze des Slotschemas

Die nominale Abfolge der Tabellen 1 und 2 ist Artikel → Possessiv-Pronomen → Pluralisator → Kasus → Suffixaufnahme → Pluralität des Bezugswortes → Kasus des Bezugswortes → enklitisches Pronomen → Partikel (S. 65, 69). Das Schema hat dagegen nur je einen einmalig verwendbaren Slot für sämtliche gebundenen Pronomina, sämtliche nominalen Numerus-/Artikelzeichen und sämtliche Kasuszeichen. Keine Permutation dieser Slots kann diese nominale Kette abbilden. Besonders stehen Possessivsuffixe vor Kasuszeichen, enklitische Personalpronomina aber danach.

Deshalb bleibt die Vorlagenreihenfolge als technische Projektion erhalten. Die tatsächliche Reihenfolge und ihre Unvereinbarkeit mit einer einzigen Slotliste sind zusätzlich in `class_order.basis` mit Seitenangabe festgehalten, obwohl keine vollständige neue Permutation eingetragen werden kann. Das ist eine ausdrücklich dokumentierte Grenze der verlangten Darstellung, keine Behauptung, dass die Grammatik die Vorlagenreihenfolge lehre.

Wurzelnahe Tempus-, Aspekt-, Valenz-, Negations- und Modalformanten stehen in `s_stem`; die verbalen Tabellen stellen sie vor die Personen-/Numeruszeichen. Selbständige finite Numeruszeichen und personentragende Gesamtausgänge stehen in `s_case_person`. Enklitische Absolutivpronomina behalten als gebundene Pronomina `s_pronoun`, auch wenn die Tabelle sie als Subjektanzeiger verwendet. Die Suffixaufnahmeträger NE/NA werden wegen ihrer Singular-/Pluralopposition unter `s_gender_number` geführt; ihre spätere Stellung in der realen Nominalkette kann dieser Slot nicht ausdrücken. Es wurde kein zusätzlicher Slot erfunden.

## Abdeckungsnachweis

Die letzte Spalte zählt die in der jeweiligen Einheit aufgenommenen Realisierungen, einschließlich bereits aus einer anderen Einheit belegter identischer Einträge. Sie ist deshalb keine additive Gesamtsumme.

| Einheit | Gedruckte Seite | Realisierungen |
|---|---|---:|
| II.C.2, 2. Position (list) | 54-55 | 13 |
| II.C.2, 4. Position (untitled table) | 57 | 36 |
| Tabelle 1 | 65 | 26 |
| II.C.2, 8. Position (untitled table) | 66 | 18 |
| II.C.2, 9. Position (list) | 68 | 5 |
| Tabelle 2 | 69 | 20 |
| II.C.4, 2. Position (untitled table) | 77 | 2 |
| II.C.4, 7. Position (list) | 78 | 16 |
| Tabelle 3 | 80 | 22 |
| II.C.4, 8. (list) | 81 | 3 |
| Tabelle 4 | 82 | 26 |
| Tabelle 5 und 6 | 85 | 22 |
| Tabelle 7 | 86 | 27 |
| Tabelle 8 | 88 | 20 |
| Tabelle 9 | 92 | 13 |
| Tabelle 10 | 93 | 7 |
| Tabelle 11 | 95 | 9 |
| Tabelle 12 | 112 | 12 |
| Tabelle 13 | 114 | 13 |
| II.E, "Der Jussiv und andere Modalformen der Bilingue" (untitled ruled lists) | 116-117 | 28 |
| II.D.2 (boxed schema) | 102 | 5 |
| II.D.3 (boxed schema) | 102 | 4 |
| II.C.4, Position 1 (Wurzelerweiterungen, itemised) | 75-77 | 32 |
| II.C.4, 11. | 87 | 1 |
| II.C.4, 12. | 87-91 | 19 |
| II.C.4, 13. | 92-93 | 15 |
| II.C.4, 14. | 93-94 | 11 |
| II.C.4, 15. | 94-96 | 14 |
| II.C.4, 16. | 96-97 | 13 |
| II.C.4, 17. | 97 | 2 |
| 5. Die Postpositionen und Partikeln | 97-100 | 12 |
| Die Partikeln | 99 | 4 |
| Die enklitischen Partikeln oder „Assoziative“ | 100 | 5 |
