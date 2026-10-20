"""Rebuild bundled assets from a local Noto checkout (requires resvg-py 0.5.0).

The checkout must contain 2D/png/128, third_party/region-flags/waved-svg and
emoji_aliases.txt. License files are distributed separately in assets/noto_emoji.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import resvg_py


def normalized(sequence):
    return "_".join(f"{int(c, 16):x}" for c in sequence.split("_") if c.lower() not in ("fe0e", "fe0f"))


def vendor(source: Path):
    destination = Path(__file__).resolve().parents[1] / "assets/noto_emoji"
    (destination / "png").mkdir(parents=True, exist_ok=True)
    index, hashes, flags = {}, {}, {}
    for path in sorted((source / "2D/png/128").glob("*.png")):
        sequence = path.stem[7:] if path.stem.startswith("emoji_u") else path.stem[1:].replace("-u", "_")
        key = normalized(sequence)
        if key in index:
            continue
        shutil.copy2(path, destination / "png" / path.name)
        index[key] = path.name
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((source / "third_party/region-flags/waved-svg").glob("emoji_u*.svg")):
        svg = path.read_text(encoding="utf-8")
        # Git symlinks may appear as text files on Windows. The official alias
        # table below supplies these entries without interpreting arbitrary paths.
        if svg.strip().endswith(".svg") and "<svg" not in svg:
            continue
        key = normalized(path.stem[7:])
        if key in index:
            continue
        data = resvg_py.svg_to_bytes(svg_string=svg, width=128, height=128, skip_system_fonts=True)
        name = path.stem + ".png"
        (destination / "png" / name).write_bytes(data)
        index[key] = name
        hashes[name] = hashlib.sha256(data).hexdigest()
        flags[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for line in (source / "emoji_aliases.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        alias, target = line.split(";")
        if target != "unknown_flag" and normalized(target) in index:
            index[normalized(alias)] = index[normalized(target)]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    manifest = {
        "repository": "https://github.com/googlefonts/noto-emoji", "commit": commit,
        "source_directory": "2D/png/128", "style": "Noto 2D",
        "image_count": len(hashes), "sequence_count": len(index), "sha256": hashes,
        "flag_conversion": {"source": "third_party/region-flags/waved-svg",
                            "renderer": "resvg-py 0.5.0; 128x128", "source_svg_sha256": flags},
    }
    for name, data in (("index.json", index), ("manifest.json", manifest)):
        (destination / name).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (destination / "NOTICE.txt").write_text(
        "Noto Emoji 2D imagery. Copyright Google and contributors.\n"
        f"Source: googlefonts/noto-emoji, commit {commit}.\n"
        "Images: Apache-2.0; regional flag exceptions: LICENSE-FLAGS.txt.\n"
        "PNG images are copied unmodified. Regional flags were rasterized from\n"
        "the same commit waved SVG sources with resvg-py 0.5.0 at 128x128.\n"
        "See manifest.json for source and output hashes. No Noto fonts are bundled.\n",
        encoding="utf-8",
    )
    print(f"Bundled {len(hashes)} images for {len(index)} sequences at {commit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    vendor(parser.parse_args().checkout.resolve())
