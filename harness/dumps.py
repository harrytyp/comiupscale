"""Aufnahmen pruefen und lesen.

Der Aufnahmelauf wird per timeout beendet und kann eine Datei mitten im Schreiben
abschneiden. PIL laedt solche Dateien teils ohne Fehler und liefert dann ein halbes Bild;
genau das hatte Raum 25 in der Messung 38,6 Prozent Abweichung gegeben statt 2,5. Deshalb
wird hier die Groesse gegen die Kopfzeile geprueft, bevor verglichen wird.
"""
import numpy as np


class DumpError(Exception):
    pass


def load_ppm(path):
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"P6"):
        raise DumpError("%s: kein Binaer-PPM" % path)
    teile = data.split(b"\n", 3)
    if len(teile) < 4:
        raise DumpError("%s: Kopf unvollstaendig" % path)
    try:
        w, h = [int(v) for v in teile[1].split()]
    except ValueError as exc:
        raise DumpError("%s: Kopf unlesbar (%s)" % (path, exc)) from exc
    pixel = teile[3]
    erwartet = w * h * 3
    if len(pixel) != erwartet:
        raise DumpError("%s: unvollstaendig (%d von %d Bytes)" % (path, len(pixel), erwartet))
    return np.frombuffer(pixel, dtype=np.uint8).reshape(h, w, 3)


def compare(a, b):
    """Mittlere Abweichung und Anteil starker Abweichungen zwischen zwei Bildern."""
    if a.shape != b.shape:
        raise DumpError("Bildgroessen passen nicht: %s gegen %s" % (a.shape, b.shape))
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    return float(d.mean()), float((d > 40).mean() * 100)


def scale_to(img, w, h):
    """Naechster Nachbar; die HD-Aufnahme ist ein ganzzahliges Vielfaches."""
    if img.shape[0] == h and img.shape[1] == w:
        return img
    fy, fx = img.shape[0] / h, img.shape[1] / w
    if abs(fy - round(fy)) < 1e-6 and abs(fx - round(fx)) < 1e-6:
        f = int(round(fy))
        return img[::f, ::f][:h, :w]
    return img
