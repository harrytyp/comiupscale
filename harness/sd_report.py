#!/usr/bin/env python3
"""Gesamtliste: Ausrichtung (Fork gegen sich) und Inhalt (HD gegen SD-Engine).

Liest befunde.csv (Ausrichtung, aus ab_analyse.py) und sd_befunde.csv (Inhalt, aus
sd_compare.py) und schreibt eine sortierte Liste je Raum.

Aufruf: python3 harness/sd_report.py [ordner]
"""
import csv
import os
import sys


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def num(value, default=0.0):
    try:
        return float(str(value).strip("()").split(",")[0])
    except (TypeError, ValueError):
        return default


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/projects/comi-hd/reports"
    fork = {r["raum"]: r for r in load(os.path.join(folder, "ab", "befunde.csv"))}
    sd = {}
    for r in load(os.path.join(folder, "sd", "sd_befunde.csv")):
        room = r["name"].split("_")[0]
        prev = sd.get(room)
        score = float(r["fehlt%"]) * 2 + float(r["verrutscht%"]) + float(r["abweichend%"])
        if prev is None or score > prev[0]:
            sd[room] = (score, r)

    rows = []
    for room in sorted(set(fork) | set(sd), key=lambda s: int(s) if s.isdigit() else 0):
        f = fork.get(room, {})
        s = sd.get(room, (0.0, None))
        sx, sy = 0, 0
        if f:
            sx = int(float(f.get("versatz_x", 0) or 0))
            sy = int(float(f.get("versatz_y", 0) or 0))
        fehlt = float(s[1]["fehlt%"]) if s[1] else 0.0
        verr = float(s[1]["verrutscht%"]) if s[1] else 0.0
        abw = float(s[1]["abweichend%"]) if s[1] else 0.0
        severity = 10 * max(abs(sx), abs(sy)) + 2.5 * fehlt + 1.2 * verr + 1.0 * abw
        rows.append((severity, room, sx, sy, fehlt, verr, abw))

    rows.sort(key=lambda r: -r[0])
    out = os.path.join(folder, "gesamtiliste.csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("raum;schwere;versatz_x;versatz_y;fehlt%;verrutscht%;abweichend%\n")
        for r in rows:
            fh.write("%s;%.1f;%d;%d;%.1f;%.1f;%.1f\n" % (r[1], r[0], r[2], r[3], r[4], r[5], r[6]))
    print(f"{len(rows)} Raeume -> {out}")
    print("raum schwere versatz      fehlt% verr% abw%")
    for r in rows[:25]:
        print("%-5s %8.1f  (%4d,%4d)  %5.1f %5.1f %5.1f" % (r[1], r[0], r[2], r[3], r[4], r[5], r[6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
