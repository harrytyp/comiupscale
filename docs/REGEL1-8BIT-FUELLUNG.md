# Regel 1 im Kostuem-Blitz: Zahlen fuer die Entscheidung

Aufgabe t_783d896a, Stand 25.10.2026. Es wurde kein Code und kein Bild geaendert.
Alle Zahlen unten kommen aus vorhandenen Messlaeufen, nicht aus einem neuen Build.

## Was zur Entscheidung steht

Der Kostuem-Blitz wertet den Alpha-Byte aus. Sichtbar bleibt 8 Bit an durchsichtigen
Stellen trotzdem, aus zwei Regeln, die die 8-Bit-Ebene als Fuellung nehmen:

- Regel 1, `gfx.cpp:3049`: Alpha 0 und darunter 8-Bit-Vordergrund
  (`foregroundBelow`) heisst, der 8-Bit-Punkt bleibt stehen. Eingebaut fuer Raum 89
  (Figur unter der durchsichtigen Flaeche der HD-Hand).
- Regel 2, Stufe 2.6b ab `gfx.cpp:3157`: legt 8 Bit in Palettenfarben neu ab, ueberall
  wo die HD-Maske leer ist und der Punkt ausserhalb der Kaesten bereits gezeichneter
  Akteure liegt (16.852 Punkte je Bild in Raum 44).

Vorschlag aus der Vorgaengeraufgabe: Regel 1 nur greifen lassen, wenn der 8-Bit-Punkt
zu einem **anderen** Akteur gehoert als dem, dessen Kostuem gerade gezeichnet wird.

## Neue Messung: in Raum 44 gibt es keinen anderen Akteur im Kasten

Grundlage: `projects/comi-hd/work/raum44_alpha/hd_state_alpha_spy.log`, 80 Bilder,
5 Kostuem-Eintraege je Bild (400 Zeilen, `HD_ALPHA_SPY=1`). Auswertung:
`/opt/data/tmp/keep8_geometrie.py`.

```
Eintrag                     Kasten (Komposit)    Kasten (8 Bit)      keep8 gesamt   je Bild   % Bild
ai=17 akos 253             712x1388 @ 0,532     x   0..178 y 133..480    930.147      2.907    0,24
ai=1  akos 2  cel 22       260x671  @1156,576   x 289..354 y 144..312    748.240      2.338    0,19
ai=4  akos 251 cel 11      616x432  @1568,896   x 392..546 y 224..332    108.000        338    0,03
ai=4  akos 251 cel 8       204x220  @1944,724   x 486..537 y 181..236    166.240        520    0,04
Summe                                                                  1.952.627      6.102    0,50
```

Die Kaesten schneiden sich nicht, auch nicht mit den 40 Punkten Rand, die Stufe 2.6b
als Sicherheitsabstand nimmt: zwischen dem rechten Rand von ai=17 (x 178) und dem
linken Rand von ai=1 (x 289) liegen 111 Achtbitpunkte.

Damit liegen **100 Prozent** der 1.952.627 keep8-Punkte in einem Kasten, in dem kein
anderer Akteur steht. Fuer Raum 44 ist die vorgeschlagene Einschraenkung also nicht
eine Abschwaechung von Regel 1, sondern **Regel 1 aus**. Die Akteur-Pruefung kostet
dort Maschinerie und aendert nichts am Ergebnis.

## Was abgeschaltet wird, und was daran weh tut

6.102 Aufnahmepunkte je Bild, 0,50 Prozent des Bildes. Darin steckt der sichtbare
8-Bit-Rest am Fuss: im Schattenfenster (Aufnahme y 584 bis 622, x 676 bis 794) sind
nach dem Entfernen der HD-Schattenflaeche 36,9 Prozent der Punkte wieder 8 Bit
(`docs/HD-LUECKEN.md`, Abschnitt "Was offen bleibt: die 8-Bit-Ebene malt den Schatten
weiter"; je Bild 9.444 der 15.296 Schattenpunkte).

Drei Risiken, alle drei nur mit einem Lauf zu klaeren:

1. **Raum 89.** Ist die Figur unter der Hand ein anderer Akteur, bleibt sie mit der
   Einschraenkung stehen. Ist sie ein Objekt der 8-Bit-Ebene und kein Akteur, faellt
   sie weg. Genau dafuer wurde Regel 1 eingebaut.
2. **Die linke Bildhaelfte in Raum 44.** 48 Prozent der keep8-Punkte (930.147) liegen
   im Kasten von ai=17 (akos 253, 712x1388, linke Kante). Was dort in 8 Bit steht,
   ist nicht gemessen; vermutlich das Schiff. Wird Regel 1 abgeschaltet, holt der
   Zweig dort den HD-Hintergrund zurueck. Ob das richtig aussieht, entscheidet die
   Sicht, nicht die Zahl.
3. **Loecher in zusammenhaengenden HD-Flaechen.** `docs/OFFENE-FEHLER.md` Punkt 4
   beschreibt, dass die Rueckholung des HD-Hintergrunds im `alpha == 0`-Zweig Loecher
   in eine geschlossene HD-Flaeche stanzt (Segel). Jede Abschwaechung von Regel 1
   schickt mehr Punkte in genau diesen Zweig, macht dieses Risiko also groesser und
   nicht kleiner.

## Zwei Wege, ein Vergleich

**A, Regel 1 abschalten oder einschraenken.** Ein Schalter, ein Patch, eine Messung.
Der Patch liegt fertig bereit (unten), default aus, also ohne Wirkung, solange die
Variable nicht gesetzt ist. Fuer Raum 44 ist "abgeschaltet" dasselbe wie "nur bei
fremdem Akteur", siehe oben. Die Akteur-Pruefung gehoert erst dazu, wenn Raum 89 sie
verlangt.

**B, Marke im Asset.** Alpha 0 plus RGB 255,0,255 heisst "bewusst entfernt, immer
HD-Hintergrund zeigen". Steuert je Bildpunkt im Asset statt ueber Kaesten und ist
deshalb genauer, kostet aber Asset-Pflege. Die Schwesteraufgabe hat das gebaut und
wieder zurueckgenommen, mit der Begruendung, der Linux-Build koenne nicht linken
(`libXcursor`, `libXss` fehlen). Das ist in dieser Umgebung nicht reproduzierbar:

```
Test 1, mit den Verzeichnissen im LIBRARY_PATH:
  LIBRARY_PATH=/opt/data/local/staging/usr/lib/x86_64-linux-gnu:/opt/data/local/comi-hd-repo/build/x11link
  gcc -Wl,-t ... -lXcursor -lXss   -> rc=0, ld nimmt
  staging/libXcursor.a und staging/libXss.a

Test 2, ohne LIBRARY_PATH:
  gcc ... -lXcursor -lXss
  /usr/bin/ld: cannot find -lXcursor: No such file or directory
  /usr/bin/ld: cannot find -lXss: No such file or directory
```

Die Bibliotheken liegen also als statische Archive in `staging`; die `.so`-Zeiger in
`build/x11link` sind tot, deshalb braucht der Linker den `LIBRARY_PATH`. Der bewaehrte
Bauweg `/opt/data/tmp/build_fork_seq.sh` setzt genau diese Variable; ein `make scummvm`
ohne sie scheitert mit dem Fehlerbild aus Test 2. Das ist eine Umgebungsfrage, keine
fehlende Bibliothek. Weg B ist damit pruefbar.

**C, stehen lassen.** Kostet weiter den 8-Bit-Rest am Fuss und die braunen Stellen,
die Regel 1 und Stufe 2.6b in echten Palettenfarben schreiben.

## Empfehlung

Erst A als reiner Schalter messen, nicht gleich die Akteur-Pruefung bauen. Zwei Laeufe:

```
cd /opt/data/local/comi-hd-repo
git apply /opt/data/projects/comi-hd/patches/regel1_abschaltbar.patch
bash /opt/data/tmp/build_fork_seq.sh && bash scripts/install_build.sh
cd release/linux
HD_KEEP8=0 HD_JUMP_ROOM=44 HD_FIXED_DELTA=20 HD_EXIT_AFTER=240 HD_DUMP_SEQ=1 HD_ALPHA_SPY=1 \
  timeout -k 5 120 ./scummvm --config=scummvm_video.ini --path=game comi
HD_KEEP8=0 HD_JUMP_ROOM=89 ... (gleiches Muster, Sicht auf die Figur unter der Hand)
```

Auswertung: `harness/alpha_gegenprobe.py` (keep8 muss auf 0 gehen, `a0bg` entsprechend
steigen), `harness/magenta_check.py` und ein Bildpaar mit und ohne `HD_KEEP8=0`.

- Raum 89 haelt und Raum 44 wird besser: A einbauen, ohne Akteur-Pruefung.
  Weniger Code als der Vorschlag aus der Vorgaengeraufgabe, gleiche Wirkung.
- Raum 89 bricht: A ist tot, dann Weg B mit der Marke im Asset weiterverfolgen.

Ohne diese zwei Bilder ist keine der drei Varianten zu verantworten; alle drei
verschieben sichtbare Bildpunkte.

## Was hier nicht gemacht wurde

Kein Build, kein Lauf. Im selben Arbeitsbaum laufen zwei weitere Aufgaben, eine davon
in Raum 44 (`t_93c795bd`, magenta Randstreifen), und laut `AGENTS.md` darf nur ein
scummvm-Prozess gleichzeitig laufen. Ein eigener Build haette deren Messung
zerstoert und umgekehrt. Die Zahlen oben stammen deshalb aus dem vorhandenen
`HD_ALPHA_SPY`-Lauf, die Geometrie ist daraus gerechnet, nicht neu gemessen.

## Dateien

```
Patch (nicht angewendet)   projects/comi-hd/patches/regel1_abschaltbar.patch
Geometrie-Auswertung       /opt/data/tmp/keep8_geometrie.py
Messgrundlage              projects/comi-hd/work/raum44_alpha/hd_state_alpha_spy.log
Vorgaengerbefund           docs/HD-LUECKEN.md, "Alpha-Kanal im Kostuem-Blitz"
Loecher-Risiko             docs/OFFENE-FEHLER.md, Punkt 4
Schattenfenster            docs/HD-LUECKEN.md, "Was offen bleibt: die 8-Bit-Ebene ..."
```
