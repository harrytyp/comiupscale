#!/usr/bin/env python3
"""Macht aus befunde.csv eine lesbare Liste mit echten Problemen.

Aufruf: python3 harness/ab_report.py <ordner> [min-schwere]

Gelesen wird befunde.csv (aus ab_analyse.py) und, falls vorhanden, scroll.csv
(aus ab_scroll.py). Ausgegeben wird eine Liste mit einer Zeile je Raum, sortiert nach
Schwere, plus der Angabe, welche Pruefung angesprungen ist.
"""
import csv
import os
import sys


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/projects/comi-hd/reports/ab"
    minimum = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    rows = load(os.path.join(folder, "befunde.csv"))
    scroll = {r["raum"]: r for r in load(os.path.join(folder, "scroll.csv"))}

    out = []
    for r in rows:
        try:
            sev = float(r["schwere"])
        except (KeyError, ValueError):
            continue
        if sev < minimum or r["befund"] == "unauffaellig":
            continue
        parts = [f"Raum {r['raum']}"]
        if "ausrichtung" in r["befund"]:
            parts.append(f"Ausrichtung {int(r['versatz_x'])},{int(r['versatz_y'])} px gegen das Original")
        if "verdeckt" in r["befund"]:
            parts.append(f"{r['verdeckt']}% der Flaeche ist im HD-Bild leer, das Original hat dort Struktur")
        if "ohne_hd" in r["befund"]:
            parts.append(f"{r['ohne_hd']}% ohne HD-Asset (hochskaliertes Original)")
        boxes = [r.get("flaeche1", "-"), r.get("flaeche2", "-"), r.get("flaeche3", "-")]
        boxes = [b for b in boxes if b and b != "-"]
        if boxes:
            parts.append("groesste Stellen: " + ", ".join(boxes))
        s = scroll.get(r["raum"])
        if s:
            parts.append(f"Kamerafahrt: Drift x {s['drift_x']} y {s['drift_y']}, Versatz max {s['versatz_max']}")
        parts.append(f"Schwere {r['schwere']}")
        out.append(" | ".join(parts))

    print(f"{len(out)} Raeume ueber der Schwelle {minimum}")
    for line in out:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
