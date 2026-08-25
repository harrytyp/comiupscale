#!/usr/bin/env python3
"""Convert the archive.org COMI soundtrack to CD-quality music WAVs.

Reads hq_music_map.json to know which OST tracks the game uses, converts
each matched OST FLAC to a 16-bit PCM WAV keeping the ORIGINAL archive.org
name, and writes it into <game>/hd/audio/. The game maps the files to the
in-game cues automatically via the built-in table.

Usage:
    python3 convert_ost.py <ost_dir> <game_dir>

    ost_dir  : folder with the archive.org FLACs (e.g. "NN Title.flac")
    game_dir : your COMI game folder (the one containing hd/ or game data)

Requires ffmpeg in PATH.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, "hq_music_map.json")))

def find_flac(ost_dir, ost_wav_name):
    """ost_wav_name is like 'ost_04_Ye_Pining_of_a_Rotten_Heart.wav'.
    The original archive.org FLAC is '04 Ye Pining of a Rotten Heart.flac'.
    Returns (path, original_base_name_with_spaces)."""
    base = ost_wav_name[4:-4] if ost_wav_name.startswith("ost_") else ost_wav_name[:-4]
    underscore = base
    spaced = base.replace("_", " ")
    # Try underscore version first (what the wav names were derived from),
    # then the spaced original.
    for candidate in (underscore, spaced):
        for ext in (".flac", ".FLAC", ".mp3", ".MP3"):
            p = os.path.join(ost_dir, candidate + ext)
            if os.path.exists(p):
                # Output name: the ORIGINAL archive.org name (spaces)
                return p, spaced
    return None, None

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    ost_dir, game_dir = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(game_dir, "hd", "audio")
    os.makedirs(out_dir, exist_ok=True)

    converted = 0
    missing = []
    seen = set()
    for cue, info in MAP.items():
        ost_wav = info["ost"]
        src, orig_name = find_flac(ost_dir, ost_wav)
        if not src or not orig_name:
            missing.append((cue, ost_wav))
            continue
        if orig_name in seen:
            continue  # same OST track mapped to multiple cues -> one file
        seen.add(orig_name)
        dst = os.path.join(out_dir, orig_name + ".wav")
        if os.path.exists(dst):
            converted += 1
            continue
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "2",
               "-sample_fmt", "s16", "-vn", dst]
        subprocess.run(cmd, check=True)
        converted += 1
        print(f"  {orig_name}.wav <- {os.path.basename(src)}")

    print(f"\nConverted {converted} tracks into {out_dir}")
    if missing:
        print(f"  {len(missing)} cues: OST file not found (skipped, keep original music)")
        for cue, ost in missing[:10]:
            print(f"    {cue} -> {ost}")

if __name__ == "__main__":
    main()
