#!/usr/bin/env python3
"""Pruefsummen der ausgelieferten HD-Assets.

Die Assets liegen nicht in git (5,3 GB). Damit trotzdem nachweisbar ist, ob ein neuer
Pipeline-Lauf denselben Stand erzeugt, schreibt dieses Werkzeug Pfad, Groesse und SHA-256
jeder Datei in eine Liste. `--check` vergleicht den aktuellen Stand damit.

    python3 scripts/asset_manifest.py            # Liste schreiben
    python3 scripts/asset_manifest.py --check    # Stand vergleichen
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HD = os.path.join(ROOT, "release", "linux", "hd")
MANIFEST = os.path.join(ROOT, "docs", "asset-manifest.txt")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def walk():
    for base, _dirs, files in os.walk(HD):
        for name in sorted(files):
            full = os.path.join(base, name)
            yield os.path.relpath(full, HD).replace(os.sep, "/"), full


def main():
    check = "--check" in sys.argv
    current = {}
    for rel, full in walk():
        current[rel] = (os.path.getsize(full), sha256(full))

    if not check:
        with open(MANIFEST, "w", encoding="utf-8") as f:
            f.write("# Pfad\tGroesse\tSHA-256  (release/linux/hd)\n")
            for rel in sorted(current):
                size, digest = current[rel]
                f.write("%s\t%d\t%s\n" % (rel, size, digest))
        print("%d Dateien in %s geschrieben" % (len(current), os.path.relpath(MANIFEST, ROOT)))
        return 0

    expected = {}
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            rel, size, digest = line.rstrip("\n").split("\t")
            expected[rel] = (int(size), digest)

    fehlt = [r for r in expected if r not in current]
    neu = [r for r in current if r not in expected]
    anders = [r for r in expected if r in current and current[r] != expected[r]]
    print("Dateien: %d erwartet, %d vorhanden" % (len(expected), len(current)))
    print("fehlt: %d, neu: %d, abweichend: %d" % (len(fehlt), len(neu), len(anders)))
    for label, items in (("fehlt", fehlt), ("neu", neu), ("abweichend", anders)):
        for rel in items[:10]:
            print("  %s: %s" % (label, rel))
    return 0 if not (fehlt or neu or anders) else 1


if __name__ == "__main__":
    sys.exit(main())
