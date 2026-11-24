#!/usr/bin/env python3
"""Selbsttest fuer scripts/pack_manifest.py (stdlib unittest, kein pytest noetig).

Aufruf:  python3 tests/test_pack_manifest.py
Braucht Pillow (steht in requirements.txt).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "pack_manifest.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pack_manifest as pm  # noqa: E402


def make_pack(path, rooms=2, objects=3):
    """Minimalpack: winzige PNGs mit gueltigen Raumnamen."""
    from PIL import Image
    os.makedirs(os.path.join(path, "backgrounds"), exist_ok=True)
    os.makedirs(os.path.join(path, "objects"), exist_ok=True)
    for r in range(1, rooms + 1):
        Image.new("RGB", (2560, 1920), (10, 20, 30)).save(
            os.path.join(path, "backgrounds", "%04d_bg.png" % r))
        for o in range(objects):
            Image.new("RGBA", (64, 64), (1, 2, 3, 255)).save(
                os.path.join(path, "objects", "%04d_obj_%04d.png" % (r, o)))
    return path


class PackManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="packman-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_counts_and_scale(self):
        pack = make_pack(os.path.join(self.tmp, "p"), rooms=2, objects=3)
        man = pm.build(pack, "testpack", "Test Pack", "1.2.3", "2026.1.0")
        self.assertEqual(man["rooms"], 2)
        self.assertEqual(man["objects"], 6)
        self.assertEqual(man["scale"], 4)
        self.assertEqual(man["name"], "testpack")
        self.assertIn("manifest_sha256", man)

    def test_check_accepts_matching_manifest(self):
        pack = make_pack(os.path.join(self.tmp, "p"))
        man = pm.build(pack, "testpack", "Test Pack", "1.0", "")
        mp = os.path.join(pack, "hd.json")
        json.dump(man, open(mp, "w"))
        self.assertEqual(pm.check(pack, mp), 0)

    def test_check_rejects_wrong_room_count(self):
        pack = make_pack(os.path.join(self.tmp, "p"), rooms=2)
        man = pm.build(pack, "testpack", "T", "1.0", "")
        man["rooms"] = 99
        mp = os.path.join(pack, "hd.json")
        json.dump(man, open(mp, "w"))
        self.assertEqual(pm.check(pack, mp), 1)

    def test_check_flags_missing_objects_dir(self):
        pack = make_pack(os.path.join(self.tmp, "p"))
        shutil.rmtree(os.path.join(pack, "objects"))
        man = pm.build(pack, "testpack", "T", "1.0", "")
        mp = os.path.join(pack, "hd.json")
        man["objects"] = 0
        json.dump(man, open(mp, "w"))
        self.assertEqual(pm.check(pack, mp), 1)

    def test_list_flags_deviation(self):
        base = os.path.join(self.tmp, "packs")
        a = make_pack(os.path.join(base, "gut"), rooms=1, objects=1)
        json.dump(pm.build(a, "gut", "Gut", "1.0", ""), open(os.path.join(a, "hd.json"), "w"))
        b = make_pack(os.path.join(base, "halb"), rooms=1, objects=1)
        man = pm.build(b, "halb", "Halb", "0.1", "")
        man["objects"] = 500
        json.dump(man, open(os.path.join(b, "hd.json"), "w"))
        out = subprocess.run([sys.executable, SCRIPT, "--list", "--pack", base],
                             capture_output=True, text=True)
        self.assertIn("ok", out.stdout)
        self.assertIn("ABWEICHUNG", out.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
