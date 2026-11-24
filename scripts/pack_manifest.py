#!/usr/bin/env python3
"""HD-Pack-Manifest schreiben und pruefen.

    pack_manifest.py --pack <verzeichnis> [--out hd.json] [--name esrgan-anime]
    pack_manifest.py --pack <verzeichnis> --check

Schreibt hd.json nach Spec docs/HD_PACKS.md: Name, Version, Skalierung, Zahl der Raeume und
Objekte, Sprachliste der Videos, Pruefsumme ueber das Manifest selbst. --check prueft ein
vorhandenes Manifest gegen den Verzeichnisinhalt und meldet Abweichungen, ohne etwas zu aendern.
"""
import argparse, glob, hashlib, json, os, re, sys
from datetime import date

SCHEMA = 1

def rows(pack, sub, pattern='*.png'):
    return sorted(glob.glob(os.path.join(pack, sub, pattern)))

def bg_rooms(pack):
    return sorted(int(os.path.basename(p).split('_')[0]) for p in rows(pack, 'backgrounds')
                  if re.match(r'^\d{4}_', os.path.basename(p)))

def detect_scale(pack, sample=3):
    """Skalierung aus Hintergrundgroesse gegen die naechstkleinere gerade Teilung raten."""
    try:
        from PIL import Image
    except ImportError:
        return None
    files = rows(pack, 'backgrounds')[:sample]
    if not files:
        return None
    for p in files:
        w = Image.open(p).size[0]
        for s in (4, 3, 2):
            if w % s == 0 and w // s in (320, 640, 1280):
                return s
    return None

def video_info(pack):
    """Videos werden ueber den SAN-Basisnamen gefunden (hd_video_player.cpp), nicht ueber
    Sprachsuffixe. Dateien mit Sprachmuster sind verdaechtig und werden gemeldet."""
    files = rows(pack, 'videos', '*.*')
    verdacht = sorted(os.path.basename(p) for p in files
                      if re.search(r'[-_](de|en|es|fr|it)(?:[-_][0-9]+)?\.mp4$', os.path.basename(p), re.I))
    return {'files': len(files), 'naming': 'san', 'suspect': verdacht}

def build(pack, name, title, version, engine_min):
    rooms = bg_rooms(pack)
    man = {
        'schema': SCHEMA,
        'name': name or os.path.basename(os.path.normpath(pack)),
        'title': title or (name or os.path.basename(os.path.normpath(pack))),
        'version': version or '0.0.0',
        'engine_min': engine_min or '',
        'scale': detect_scale(pack),
        'created': date.today().isoformat(),
        'rooms': len(rooms),
        'objects': len(rows(pack, 'objects')),
        'videos': video_info(pack),
    }
    blob = json.dumps(man, sort_keys=True, separators=(',', ':')).encode()
    man['manifest_sha256'] = hashlib.sha256(blob).hexdigest()
    return man

def check(pack, man_path):
    if not os.path.exists(man_path):
        print('FEHLT: %s' % man_path); return 1
    man = json.load(open(man_path))
    problems = []
    for key in ('name', 'title', 'version', 'scale'):
        if key not in man:
            problems.append('Pflichtfeld fehlt: %s' % key)
    if not rows(pack, 'backgrounds'):
        problems.append('keine Hintergruende')
    if not rows(pack, 'objects'):
        problems.append('keine Objekte')
    ist = len(bg_rooms(pack))
    if man.get('rooms') and ist != man['rooms']:
        problems.append('Raeume: Manifest %d, Verzeichnis %d' % (man['rooms'], ist))
    soll_obj = man.get('objects')
    if soll_obj and soll_obj != len(rows(pack, 'objects')):
        problems.append('Objekte: Manifest %d, Verzeichnis %d' % (soll_obj, len(rows(pack, 'objects'))))
    fehlend = [d for d in ('backgrounds', 'objects') if not os.path.isdir(os.path.join(pack, d))]
    problems += ['Ordner fehlt: %s' % d for d in fehlend]
    vid = man.get('videos', {})
    print('%s: %d Raeume, %d Objekte, Skalierung %s, Videos %d' % (
        man.get('name'), ist, len(rows(pack, 'objects')), man.get('scale'), vid.get('files', 0)))
    for f in vid.get('suspect', []):
        problems.append('Videoname mit Sprachsuffix (Fork sucht SAN-Namen): %s' % f)
    if problems:
        print('BEFUNDE:'); [print('  - ' + p) for p in problems]; return 1
    print('OK, keine Abweichung'); return 0

def list_packs(root):
    """Alle Packs unter einem Verzeichnis auflisten und pruefen."""
    found = 0
    for d in sorted(glob.glob(os.path.join(root, '*'))):
        if not os.path.isdir(d):
            continue
        man = os.path.join(d, 'hd.json')
        if not os.path.exists(man):
            print('%-24s %-10s %s' % (os.path.basename(d), '-', 'kein hd.json (unbekanntes Pack)'))
            found += 1
            continue
        try:
            m = json.load(open(man))
        except ValueError:
            print('%-24s %-10s %s' % (os.path.basename(d), '-', 'hd.json nicht lesbar'))
            found += 1
            continue
        rooms = len(bg_rooms(d)); objs = len(rows(d, 'objects'))
        ok = (m.get('rooms') in (None, rooms)) and (m.get('objects') in (None, objs))
        print('%-24s %-10s %5d Raeume %5d Objekte  Skal %s  %s' % (
            m.get('name', os.path.basename(d)), m.get('version', '-'), rooms, objs,
            m.get('scale', '-'), 'ok' if ok else 'ABWEICHUNG'))
        found += 1
    if not found:
        print('keine Packs unter %s' % root)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', required=True)
    ap.add_argument('--out', default=None, help='Zielpfad, Vorgabe <pack>/hd.json')
    ap.add_argument('--name'); ap.add_argument('--title'); ap.add_argument('--version')
    ap.add_argument('--engine-min', default='')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--list', dest='listen', action='store_true',
                    help='alle Packs unter --pack auflisten')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    out = a.out or os.path.join(a.pack, 'hd.json')
    if a.listen:
        sys.exit(0 if list_packs(a.pack) else 1)
    if a.check:
        sys.exit(check(a.pack, out))
    man = build(a.pack, a.name, a.title, a.version, a.engine_min)
    text = json.dumps(man, indent=2, ensure_ascii=False) + '\n'
    if a.dry_run:
        sys.stdout.write(text); return
    open(out, 'w').write(text)
    print('geschrieben: %s (%d Raeume, %d Objekte, Skalierung %s)' % (
        out, man['rooms'], man['objects'], man['scale']))

if __name__ == '__main__':
    main()
