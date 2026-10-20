#!/usr/bin/env python3
"""Fuehrt mehrere Messlaeufe zu einem Ergebnis zusammen.

Aufruf: python3 harness/merge_sweeps.py <ziel.csv> <quelle1.csv> [<quelle2.csv> ...]

Raeume aus spaeteren Quellen ueberschreiben frueher gemessene. Das ist noetig, wenn ein Lauf
einen Teil der Raeume nicht messen konnte und der Rest nachgeholt wurde.
"""
import csv
import os
import sys


def main():
    ziel = sys.argv[1]
    quellen = sys.argv[2:]
    werte = {}
    for quelle in quellen:
        if not os.path.exists(quelle):
            print("fehlt: %s" % quelle)
            continue
        with open(quelle, newline="") as f:
            for row in csv.DictReader(f, delimiter=";"):
                raum = (row.get("raum") or "").strip()
                if raum:
                    werte[raum] = (row.get("abweichung", ""), row.get("ueber40_prozent", ""))
        print("%-52s %3d Raeume" % (os.path.basename(os.path.dirname(quelle)), len(werte)))

    with open(ziel, "w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["raum", "abweichung", "ueber40_prozent"])
        for raum in sorted(werte, key=lambda r: int(r) if r.isdigit() else 0):
            w.writerow([raum, werte[raum][0], werte[raum][1]])
    print("zusammengefuehrt: %d Raeume -> %s" % (len(werte), ziel))


if __name__ == "__main__":
    main()
