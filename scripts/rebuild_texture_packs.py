"""Baut die drei Texture-Packs neu, vollstaendig und ohne Doppelungen.

Zuordnung (reproduzierbar, gleiche Datei landet immer im gleichen Pack):

    part1  backgrounds/ audio/ und Kostueme der Gruppe 0
    part2  Kostueme der Gruppe 1
    part3  objects/ objects_layers/ fonts/ object_map.json und Kostueme der Gruppe 2

Die Gruppe ergibt sich aus dem SHA-1 des Dateinamens modulo 3, damit die drei Packs
ungefaehr gleich gross werden und ein neuer Lauf dieselbe Aufteilung erzeugt.

Aufruf: python3 scripts/rebuild_texture_packs.py
"""
import hashlib
import os
import zipfile

ROOT = "/opt/data/local/comi-hd-repo"
HD = os.path.join(ROOT, "release", "linux", "hd")
PACKS = {
    "hd_assets_part1.zip": ["backgrounds", "audio"],
    "hd_assets_part2.zip": [],
    "hd_assets_part3.zip": ["objects", "objects_layers", "fonts", "object_map.json"],
}


def gruppe(rel):
    return int(hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8], 16) % 3


def lies():
    dateien = []
    for base, _dirs, files in os.walk(HD):
        for name in files:
            full = os.path.join(base, name)
            dateien.append((os.path.relpath(full, HD).replace(os.sep, "/"), full))
    return sorted(dateien)


def ziel(rel):
    top = rel.split("/")[0]
    for pack, ordner in PACKS.items():
        if top in ordner:
            return pack
    if top == "costumes":
        return ["hd_assets_part1.zip", "hd_assets_part2.zip", "hd_assets_part3.zip"][gruppe(rel)]
    return "hd_assets_part3.zip"


def main():
    dateien = lies()
    print("%d Dateien im HD-Ordner" % len(dateien))

    nach_pack = {}
    for rel, full in dateien:
        nach_pack.setdefault(ziel(rel), []).append((rel, full))
    for pack, items in sorted(nach_pack.items()):
        print("  %s: %d Dateien" % (pack, len(items)))

    for pack, items in sorted(nach_pack.items()):
        ziel_path = os.path.join(ROOT, "release", pack)
        tmp_path = ziel_path + ".neu"
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel, full in items:
                z.write(full, "hd/" + rel)
        # Vorherigen Stand sichern, nicht ueberschreiben: der alte Pack wandert nach .prev.
        if os.path.exists(ziel_path):
            vorher = ziel_path + ".prev"
            if os.path.exists(vorher):
                os.unlink(vorher)
            os.replace(ziel_path, vorher)
        os.replace(tmp_path, ziel_path)
        print("  geschrieben: %s (%.2f GB)" % (pack, os.path.getsize(ziel_path) / 1e9))

    # Kontrolle: jedes Bild aus dem HD-Ordner genau einmal in den Packs
    gesehen = {}
    for pack in sorted(nach_pack):
        with zipfile.ZipFile(os.path.join(ROOT, "release", pack)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("./", "")
                if name.startswith("hd/"):
                    name = name[3:]
                gesehen[name] = gesehen.get(name, 0) + 1

    fehlt = [rel for rel, _full in dateien if rel not in gesehen]
    doppelt = [name for name, n in gesehen.items() if n > 1]
    fremd = [name for name in gesehen if name not in {rel for rel, _f in dateien}]
    print("Kontrolle: %d Eintraege, fehlt %d, doppelt %d, fremd %d" %
          (sum(gesehen.values()), len(fehlt), len(doppelt), len(fremd)))
    for rel in fehlt[:5]:
        print("   fehlt:", rel)
    for name in doppelt[:5]:
        print("   doppelt:", name)


if __name__ == "__main__":
    main()
