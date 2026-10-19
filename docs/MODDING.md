# Eigene HD-Upscales einbauen und pruefen

Der Fork laedt seine HD-Bilder aus dem Ordner `hd/` neben dem Spiel. Alles, was dort liegt,
ersetzt das jeweilige 8-Bit-Bild. Eigene Upscales sind deshalb nur eine Frage von Ordnernamen
und Dateinamen.

## Aufbau

    hd/backgrounds/NNNN_name.png              Hintergrund eines Raums
    hd/costumes/LFLF_NNNN_AKOS_NNNN_aframe_N.png   Kostuem, NNNN = Raum, AKOS = Kostuemnummer
    hd/objects/NNNN_name_NNNN.png             Raumobjekt
    hd/objects_layers/NNNN_name_NNNN.png      Objektschicht
    hd/fonts/                                 Schriften

Die Namen entsprechen der Extraktion (`nutcracker sputm room decode`), damit sich eigene
Upscales ohne Umbenennen einsetzen lassen.

## Pruefen statt raten

    python3 scripts/validate_hd_mod.py --dir /pfad/zu/meinem/hd
    python3 scripts/validate_hd_mod.py --dir /pfad/zu/meinem/hd --referenz release/linux/hd

Geprueft werden Ordnernamen, Dateinamen, PNG-Format und Lesbarkeit. Mit `--referenz` kommt
dazu, welche Dateien gegenueber dem vollstaendigen Satz fehlen, also ob der Mod vollstaendig
ist. Rueckgabewert 0 heisst: keine Fehler.

## Masstaebe

Der Hintergrund wird mit dem Faktor 4 hochskaliert (640x480 wird 2560x1920), Kostueme und
Objekte ebenfalls 4x. Ein anderer Faktor funktioniert, solange alle Bilder eines Raums
denselben Faktor haben; gemischt geht nicht.

## Wenn ein Bild fehlt

Fehlt ein Bild im HD-Ordner, zeichnet die Engine an dieser Stelle die 8-Bit-Fassung. Das ist
kein Fehler, sondern der Rueckfall. Wirklich fehlend ist nur, was auch im Original fehlt.
