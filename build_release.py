"""Build a complete AstrBot upload archive without installing anything."""
import argparse
import hashlib
import json
import keyword
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
MODULES = ("__init__.py", "main.py", "drawer.py", "models.py", "utils.py", "constants.py", "emoji_renderer.py")


def build(output: Path | None = None) -> Path:
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    match = re.search(r"^name:\s*([^\s#]+)", metadata, re.MULTILINE)
    if not match:
        raise ValueError("metadata.yaml 缺少 name")
    name = match[1]
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError("metadata name 必须为合法 Python 模块名")
    required = [ROOT / entry for entry in (*MODULES, "metadata.yaml", "requirements.txt", "LICENSE", "README.md", "CHANGELOG.md", "build_release.py")]
    required += [ROOT / "assets" / entry for entry in (
        "anan/base.png", "anan/base_overlay.png", "trial/black.png",
        "trial/background.png", "trial/ema.png", "trial/hiro.png", "trial/option.png",
        "fonts/SourceHanSansSC-Bold.otf", "fonts/SourceHanSerifSC.otf",
        "noto_emoji/index.json", "noto_emoji/manifest.json", "noto_emoji/NOTICE.txt",
        "noto_emoji/LICENSE-IMAGES.txt", "noto_emoji/LICENSE-APACHE-2.0.txt", "noto_emoji/LICENSE-FLAGS.txt",
    )]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"打包缺少必需文件: {path.relative_to(ROOT)}")
    emoji_root = ROOT / "assets/noto_emoji"
    manifest = json.loads((emoji_root / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((emoji_root / "index.json").read_text(encoding="utf-8"))
    for filename, digest in manifest["sha256"].items():
        if Path(filename).name != filename:
            raise ValueError("非法的 emoji 素材路径")
        data = (emoji_root / "png" / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"emoji 素材校验失败: {filename}")
    if not set(index.values()).issubset(manifest["sha256"]):
        raise ValueError("emoji 索引引用了缺失素材")
    files = set(required) | {p for p in (ROOT / "assets").rglob("*") if p.is_file()}
    files |= set((ROOT / "tests").glob("*.py"))
    files |= set((ROOT / "tools").glob("*.py"))
    output = Path(output) if output is not None else ROOT / f"{name}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, (Path(name) / path.relative_to(ROOT)).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP 完整性校验失败")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build(args.output))
