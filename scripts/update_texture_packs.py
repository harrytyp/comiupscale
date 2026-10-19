"""Ergaenzt die Texture-Packs um Dateien, die im HD-Ordner liegen, aber im Pack fehlen.

Die Packs vom 18.07.2026 enthalten 436 Dateien nicht, die inzwischen dazugekommen sind
(Hintergruende 0039 bis 0094, Audio). Zugeordnet wird nach Ordner, wie in den Packs bereits
angelegt: Hintergruende und Audio nach part1, Objekte, Objektschichten, Schriften und
object_map.json nach part3, Kostueme nach part2. Vorhandene Eintraege bleiben unberuehrt.
"""
import os
import zipfile

ROOT = "/opt/data/local/comi-hd-repo"
HD = os.path.join(ROOT, "release", "linux", "hd")
ZIEL = {
    "backgrounds": "hd_assets_part1.zip",
    "audio": "hd_assets_part1.zip",
    "objects": "hd_assets_part3.zip",
    "objects_layers": "hd_assets_part3.zip",
    "fonts": "hd_assets_part3.zip",
    "costumes": "hd_assets_part2.zip",
}


def pack_paths():
    return {name: os.path.join(ROOT, "release", name) for name in set(ZIEL.values())}


def inhalt(pack):
    with zipfile.ZipFile(pack) as z:
        return {i.filename.replace("./", "") for i in z.infolist() if not i.is_dir()}


def main():
    packs = pack_paths()
    vorhanden = {name: inhalt(path) for name, path in packs.items()}
    for name, entries in vorhanden.items():
        print("%s: %d Eintraege" % (name, len(entries)))

    hd_files = []
    for base, _dirs, files in os.walk(HD):
        for name in files:
            full = os.path.join(base, name)
            hd_files.append((os.path.relpath(full, HD).replace(os.sep, "/"), full))

    offen = []
    for rel, full in sorted(hd_files):
        top = rel.split("/")[0]
        ziel = ZIEL.get(top, "hd_assets_part3.zip")
        if rel in vorhanden[ziel] or ("hd/" + rel) in vorhanden[ziel]:
            continue
        offen.append((ziel, rel, full))

    print("fehlend in den Packs: %d" % len(offen))
    nach_pack = {}
    for ziel, rel, full in offen:
        nach_pack.setdefault(ziel, []).append((rel, full))

    for ziel, items in nach_pack.items():
        path = packs[ziel]
        print("%s: %d Dateien ergaenzen" % (ziel, len(items)))
        with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as z:
            for rel, full in items:
                z.write(full, "hd/" + rel)

    print("--- Kontrolle")
    for name, path in packs.items():
        entries = inhalt(path)
        fehlt = [rel for rel, _full in hd_files if ("hd/" + rel) not in entries and rel not in entries]
        print("%s: %d Eintraege, fehlt noch %d" % (name, len(entries), len(fehlt)))
        for rel in fehlt[:5]:
            print("   ", rel)


if __name__ == "__main__":
    main()
