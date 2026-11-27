"""独立覆盖 build_release.build：成功打包与各类前置校验失败路径。

不复制上游 4000+ emoji 素材：用最小夹具替换模块级 ROOT，
让构建逻辑本身进入覆盖率门禁，同时保持测试轻量。
"""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from astrbot_plugin_manosaba_memes import build_release

NAME = "astrbot_plugin_manosaba_memes"

# build() 前置校验要求存在的全部相对路径
REQUIRED = (
    *build_release.MODULES,
    "metadata.yaml",
    "requirements.txt",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "build_release.py",
    "logo.png",
    "assets/anan/base.png",
    "assets/anan/base_overlay.png",
    "assets/trial/black.png",
    "assets/trial/background.png",
    "assets/trial/ema.png",
    "assets/trial/hiro.png",
    "assets/trial/option.png",
    "assets/fonts/SourceHanSansSC-Bold.otf",
    "assets/fonts/SourceHanSerifSC.otf",
    "assets/noto_emoji/index.json",
    "assets/noto_emoji/manifest.json",
    "assets/noto_emoji/NOTICE.txt",
    "assets/noto_emoji/LICENSE-IMAGES.txt",
    "assets/noto_emoji/LICENSE-APACHE-2.0.txt",
    "assets/noto_emoji/LICENSE-FLAGS.txt",
)
EMOJI_FILE = "emoji_u0023.png"
EMOJI_BYTES = b"fake-png-payload"


@pytest.fixture
def project(tmp_path, monkeypatch):
    """建立最小可构建夹具，并把 build_release.ROOT 指向它。"""
    for rel in REQUIRED:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    (tmp_path / "metadata.yaml").write_text(
        f"name: {NAME}\nversion: 0.0.5\n", encoding="utf-8"
    )
    png = tmp_path / "assets" / "noto_emoji" / "png" / EMOJI_FILE
    png.parent.mkdir(parents=True, exist_ok=True)
    png.write_bytes(EMOJI_BYTES)
    digest = hashlib.sha256(EMOJI_BYTES).hexdigest()
    (tmp_path / "assets" / "noto_emoji" / "manifest.json").write_text(
        json.dumps({"sha256": {EMOJI_FILE: digest}}), encoding="utf-8"
    )
    (tmp_path / "assets" / "noto_emoji" / "index.json").write_text(
        json.dumps({"0023": EMOJI_FILE}), encoding="utf-8"
    )
    monkeypatch.setattr(build_release, "ROOT", tmp_path)
    return tmp_path


def test_build_produces_valid_archive(project, tmp_path):
    archive = build_release.build(tmp_path / "out.zip")
    assert archive.is_file()
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        names = set(bundle.namelist())
        assert f"{NAME}/main.py" in names
        assert f"{NAME}/assets/noto_emoji/png/{EMOJI_FILE}" in names
        assert all(name.startswith(f"{NAME}/") for name in names)


def test_build_rejects_illegal_module_name(project):
    (project / "metadata.yaml").write_text("name: bad-name\n", encoding="utf-8")
    with pytest.raises(ValueError, match="模块名"):
        build_release.build(project / "out.zip")


def test_build_requires_all_files(project):
    (project / "main.py").unlink()
    with pytest.raises(FileNotFoundError, match="main.py"):
        build_release.build(project / "out.zip")


def test_build_rejects_bad_emoji_hash(project):
    (project / "assets" / "noto_emoji" / "png" / EMOJI_FILE).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="校验失败"):
        build_release.build(project / "out.zip")


def test_build_rejects_illegal_emoji_path(project):
    manifest_path = project / "assets" / "noto_emoji" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"]["../evil.png"] = manifest["sha256"].pop(EMOJI_FILE)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="非法的 emoji 素材路径"):
        build_release.build(project / "out.zip")


def test_build_rejects_index_reference_to_missing_asset(project):
    index_path = project / "assets" / "noto_emoji" / "index.json"
    index_path.write_text(json.dumps({"1f004": "missing.png"}), encoding="utf-8")
    with pytest.raises(ValueError, match="缺失素材"):
        build_release.build(project / "out.zip")
