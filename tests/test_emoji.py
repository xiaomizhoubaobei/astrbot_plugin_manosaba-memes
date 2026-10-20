import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops
import pytest

from astrbot_plugin_manosaba_memes import emoji_renderer as er
from astrbot_plugin_manosaba_memes.drawer import draw_anan, draw_trial
from astrbot_plugin_manosaba_memes.models import Character, Option, Statement

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/SourceHanSansSC-Bold.otf")


@pytest.mark.parametrize("emoji", [
    "🐖", "😀", "😭", "🥰", "❤️", "❤", "👍🏻", "👍🏿", "🇨🇳", "🇺🇸", "🇧🇻",
    "👨‍👩‍👧‍👦", "👩🏽‍💻", "🏳️‍🌈", "1️⃣", "1⃣", "#️⃣", "🙅🏻‍♀️", "🤷🏿", "🧮",
])
def test_sequences_are_one_image(emoji):
    tokens = er.tokenize(emoji)
    assert len(tokens) == 1
    assert tokens[0].asset is not None
    assert (er.ASSET_ROOT / "png" / tokens[0].asset).is_file()


def test_digits_are_text_and_unknown_sequence_is_not_split():
    assert not er.has_emoji("123#*abc中文")
    assert all(token.asset is None for token in er.tokenize("123#*abc中文"))
    unknown = er.tokenize("🐖‍🐖")
    assert len(unknown) == 1 and unknown[0].text == "[表情]"
    assert unknown[0].asset is None


def test_variation_and_flag_aliases():
    assert er.tokenize("❤")[0].asset == er.tokenize("❤️")[0].asset
    assert er.tokenize("🇧🇻")[0].asset == er.tokenize("🇳🇴")[0].asset


def test_highlight_and_newlines_preserved():
    tokens = er.tokenize("a【好🐖】b\r\n[❤️]c")
    assert [t.text for t in tokens if t.highlighted] == ["【", "好", "🐖", "】", "[", "❤️", "]"]
    assert sum(t.text == "\n" for t in tokens) == 1


def test_source_pig_is_exact_approved_noto_asset():
    # Hash of the official pig visually compared with the user's first image.
    original = ROOT.parent / "reference/emoji-style/noto-current-pig.png"
    if original.exists():
        bundled = er.ASSET_ROOT / "png/emoji_u1f416.png"
        assert bundled.read_bytes() == original.read_bytes()


def test_asset_manifest_and_pngs():
    manifest = json.loads((er.ASSET_ROOT / "manifest.json").read_text())
    assert manifest["image_count"] == len(manifest["sha256"]) == 4004
    assert len(er.asset_index()) == manifest["sequence_count"] == 4012
    assert set(er.asset_index().values()).issubset(manifest["sha256"])
    for name, digest in manifest["sha256"].items():
        data = (er.ASSET_ROOT / "png" / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        with Image.open(BytesIO(data)) as image:
            image.verify()


def test_all_indexed_emoji_sequences_tokenize_without_splitting():
    for key, expected in er.asset_index().items():
        sequence = "".join(chr(int(code, 16)) for code in key.split("_"))
        if not er.has_emoji(sequence):  # Legacy ASCII artwork is not substituted.
            continue
        tokens = er.tokenize(sequence)
        assert len(tokens) == 1 and tokens[0].asset == expected, key


@pytest.mark.parametrize("text", [
    "我喜欢你🐖", "🐖❤️👍🏻\n🇨🇳👨‍👩‍👧‍👦1️⃣", "今天【开心🥰】", "🐖‍🐖",
    "混排Ab🐖❤️👍🏻" * 20, "🐖\n\n👍🏻", "😃" * 100,
])
def test_mixed_layout_is_inside_region(text):
    image = er.render_mixed(text, FONT, 319, 204, max_font_size=60)
    assert image.size == (319, 204)
    left, top, right, bottom = image.getbbox()
    assert 0 < left < right < 319
    assert 0 < top < bottom < 204


def test_too_many_newlines_is_a_controlled_error():
    with pytest.raises(ValueError, match="换行过多"):
        er.render_mixed("🐖\n" * 100, FONT, 319, 204)


def test_cached_fonts_do_not_lock_files_on_windows(tmp_path):
    temporary_font = tmp_path / "font.otf"
    temporary_font.write_bytes(Path(FONT).read_bytes())
    er.render_mixed("字体🐖", str(temporary_font), 319, 204, max_font_size=60)
    temporary_font.unlink()
    assert not temporary_font.exists()


def test_emoji_pixels_really_come_from_pig_image():
    result = er.render_mixed("🐖", FONT, 100, 100, max_font_size=60)
    with Image.open(er.ASSET_ROOT / "png/emoji_u1f416.png") as pig:
        expected = Image.new("RGBA", (100, 100))
        expected.alpha_composite(pig.convert("RGBA").resize((60, 60), Image.Resampling.LANCZOS), (20, 20))
    assert result.tobytes() == expected.tobytes()


@pytest.mark.parametrize("face", [None, "开心", "生气", "害羞", "无语", "病娇"])
def test_anan_emoji_render_leaves_artwork_untouched(face):
    image = Image.open(BytesIO(draw_anan("我喜欢你🐖", face))).convert("RGBA")
    with Image.open(ROOT / "assets/anan" / (f"{face}.png" if face else "base.png")) as base:
        expected = base.convert("RGBA")
    with Image.open(ROOT / "assets/anan/base_overlay.png") as overlay:
        expected.alpha_composite(overlay.convert("RGBA"))
    difference = ImageChops.difference(image, expected).convert("RGB").getbbox()
    assert difference is not None
    left, top, right, bottom = difference
    assert 100 <= left < right <= 419
    assert 432 <= top < bottom <= 636


@pytest.mark.parametrize("character", list(Character))
def test_trial_mixed_real_render(character):
    options = [Option(Statement.AGREEMENT, "我喜欢你🐖"),
               Option(Statement.DOUBT, "【开心🥰】❤️👍🏻🇨🇳"),
               Option(Statement.PERJURY, "一家人👨‍👩‍👧‍👦\n数字1️⃣")]
    with Image.open(BytesIO(draw_trial(character, options))) as image:
        image.load()
        assert image.size == (1260, 1080)
