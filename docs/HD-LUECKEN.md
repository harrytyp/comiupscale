# Fehlende HD-Texturen: vier Ursachenklassen und der aktuelle Befund

Ziel: im fertigen Bild keine 8-Bit-Grafik mehr. Dafür muss jede sichtbare 8-Bit-Textur
einer Ursache zugeordnet werden können. Diese vier Klassen sind zu unterscheiden:

| Klasse | Erkennungsmerkmal | Werkzeug |
|---|---|---|
| 1 fehlt | keine Datei im Asset-Verzeichnis | `hd_missing.log`, `NOMAP`/`MISSING` |
| 2 wird nicht geladen | Datei vorhanden, Engine fragt sie nie an | `hd_spy.log` + Verzeichnisvergleich |
| 3 falsche Position | HD gezeichnet, aber versetzt | 8-Bit- und HD-Kasten je Bild vergleichen |
| 4 scrollt/skaliert falsch | Versatz oder Maßstab driftet über die Bildfolge | Vergleich über die Folge, `shift_probe.py` |

## Befund vom 24.10.2026

**Klasse 1 ist flächendeckend.** Vergleich der Asset-Verzeichnisse:

```
94 Räume mit HD-Hintergrund
65 Räume mit HD-Objekten
29 Räume mit Hintergrund, aber ohne jedes Objekt-Asset:
   2, 4, 5, 6, 7, 8, 11, 17, 25, 27, 29, 38,
   40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 57, 79, 88, 89, 90, 93, 94
```

**Klasse 2 in den Schiffsszenen.** Die Texturspur (`HD_SPY=1`) zeigt für Raum 47:

```
216 × AKOS nr=254 frame=8      (Figur)
  1 × OBJ  nr=1367 state=1 x=0 y=0 w=640 h=480
```

Ein einzelnes Objekt deckt den ganzen Bildschirm ab und wird in 8 Bit gezeichnet. Die
Engine fragt dafür **kein** HD-Bild an (`hd_missing.log` bleibt leer), weil Vollbild-Objekte
im Objektpfad als „nicht zum Laufzeit-Kompositing geeignet" gelten. In Räumen wie 40–50 ist
der Raumhintergrund selbst ein solches Objekt: das HD-Bild ist geladen, wird aber in 8 Bit
überzeichnet.

Nachweis der Sichtbarkeit: mit `HD_TINT_8BIT=1` sind 97,4 Prozent des Bildes magenta, und
der Vordergrundzähler meldet 302080 von 307200 Pixeln (98,3 Prozent).

## Nächste Schritte

1. **Objekte für die 29 Räume extrahieren** und in die Textur-Packs aufnehmen
   (Pipeline, nicht Einzelfall). Danach `config/object_map.json` neu bauen.
2. **Vollbild-Objekte als Hintergrund behandeln**: Ist ein Objekt so groß wie der
   Bildschirm und existiert eine HD-Fassung, darf die 8-Bit-Version nicht darüber
   gezeichnet werden. Das ist eine Regel in der Zeichenlogik.
3. Klassen 3 und 4 danach prüfen; sie brauchen Bildfolgen, keine Einzelbilder.

## Warum frühere Messungen das nicht fanden

Verglichen wurden Hintergründe, nie die einzelnen Texturen. Ein Vollbild-Objekt, das den
HD-Hintergrund überdeckt, sieht in jeder Kennzahl „unauffällig" aus, weil das Bild ja zum
Original passt — nur eben in der falschen Auflösung.
