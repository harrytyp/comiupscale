#!/usr/bin/env python3
"""Convert the archive.org COMI soundtrack to in-game music replacement WAVs.

Reads hq_music_map.json (IMX cue -> OST track + offset), converts each
matched OST FLAC to a 16-bit PCM WAV named after the game cue, and writes
it into the game directory. Cues without a match keep the original music.

Usage:
    python3 convert_ost.py <ost_dir> <game_dir> [--offset]

    ost_dir   : folder with the archive.org FLACs (e.g. "NN Title.flac")
    game_dir  : your COMI game folder (where COMI.LA0 lives)
    --offset  : also apply the offset from hq_music_map.json (trim leading
                seconds from the OST track so it aligns with the in-game cue)

Requires ffmpeg in PATH.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, "hq_music_map.json")))

def find_flac(ost_dir, ost_wav_name):
    """ost_wav_name is like 'ost_04_Ye_Pining_of_a_Rotten_Heart.wav'.
    The FLAC is '04 Ye Pining of a Rotten Heart.flac'."""
    # strip 'ost_' prefix and '.wav'
    base = ost_wav_name[4:-4] if ost_wav_name.startswith("ost_") else ost_wav_name[:-4]
    # replace underscores back to spaces? The wav names came from FLACs with
    # spaces replaced by underscores. Try both.
    for candidate in (base, base.replace("_", " ")):
        for ext in (".flac", ".FLAC", ".mp3", ".MP3"):
            p = os.path.join(ost_dir, candidate + ext)
            if os.path.exists(p):
                return p
    return None

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    ost_dir, game_dir = sys.argv[1], sys.argv[2]
    use_offset = "--offset" in sys.argv

    converted = 0
    missing = []
    for cue, info in MAP.items():
        ost_wav = info["ost"]
        offset = info.get("offset_sec", 0)
        src = find_flac(ost_dir, ost_wav)
        if not src:
            missing.append((cue, ost_wav))
            continue
        # The game looks up "<IMX-name>.wav" where the IMX name has a dot
        # before "IMX" (e.g. "1099-M~1.IMX"). The map stores the bundle
        # short name without the dot — normalize it.
        game_cue = cue
        if "~1IMX" in game_cue and ".IMX" not in game_cue:
            game_cue = game_cue.replace("~1IMX", "~1.IMX")
        dst = os.path.join(game_dir, game_cue + ".wav")
        # Convert: 16-bit PCM stereo (keep original rate; game handles any)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "2",
               "-sample_fmt", "s16", "-vn"]
        if use_offset and offset > 0:
            # Trim the first `offset` seconds (where the in-game cue starts)
            cmd += ["-ss", f"{offset:.3f}"]
        cmd += [dst]
        subprocess.run(cmd, check=True)
        converted += 1
        print(f"  {game_cue}.wav <- {os.path.basename(src)} (offset {offset:+.1f}s)")

    print(f"\nConverted {converted} tracks into {game_dir}")
    if missing:
        print(f"  {len(missing)} cues: OST file not found (skipped, keep original music)")
        for cue, ost in missing[:10]:
            print(f"    {cue} -> {ost}")

if __name__ == "__main__":
    main()
