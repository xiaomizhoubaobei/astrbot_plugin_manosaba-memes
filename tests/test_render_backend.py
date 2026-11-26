"""render_backend.py 单测：后端工厂选择 + Pillow fallback 渲染细节。"""

from __future__ import annotations

import builtins
import importlib
from pathlib import Path
from typing import Any

import pytest

from tests import pkg_view  # noqa: F401  确保桩路径与包视图已注册

PKG = "astrbot_plugin_manosaba_memes"
PLUGIN_ROOT = pkg_view.REPO_ROOT


def _font_path() -> str:
    return str(PLUGIN_ROOT / "assets/fonts/SourceHanSansSC-Bold.otf")


# ---------- 工厂选择 ----------


def test_load_backend_prefers_sketchbook(monkeypatch: pytest.MonkeyPatch) -> None:
    """sketchbook 可导入时优先使用它。"""
    import render_backend as rb

    monkeypatch.delenv("MANOSABA_RENDER_BACKEND", raising=False)
    monkeypatch.setattr(rb, "_BACKEND_OVERRIDE", "")
    assert rb._load_backend() == "sketchbook"


def test_load_backend_falls_back_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sketchbook 导入失败（缺 wheel/原生扩展）时回退 pillow。"""
    import render_backend as rb

    monkeypatch.setattr(rb, "_BACKEND_OVERRIDE", "")
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "sketchbook":
            raise ImportError("no wheel for this Python")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert rb._load_backend() == "pillow"


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ("sketchbook", "sketchbook"),
        ("pillow", "pillow"),
        ("", "sketchbook"),
        ("unknown", "sketchbook"),
    ],
)
def test_backend_env_override(
    monkeypatch: pytest.MonkeyPatch, override: str, expected: str
) -> None:
    """环境变量可强制指定后端，非法值回退自动探测。"""
    import render_backend as rb

    monkeypatch.setattr(rb, "_BACKEND_OVERRIDE", override)
    assert rb._load_backend() == expected


def test_module_exposes_pillow_classes_when_forced() -> None:
    """环境变量设为 pillow 时，模块导出 Pillow 实现。"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("MANOSABA_RENDER_BACKEND", "pillow")
        rb = importlib.reload(importlib.import_module("render_backend"))
        try:
            assert rb._BACKEND == "pillow"
            assert rb.Drawer is rb._PillowDrawer
            assert rb.TextFitDrawer is rb._PillowTextFitDrawer
        finally:
            mp.delenv("MANOSABA_RENDER_BACKEND", raising=False)
            importlib.reload(rb)


# ---------- 工具函数 ----------


def test_to_rgba() -> None:
    import render_backend as rb

    assert rb._to_rgba((1, 2, 3)) == (1, 2, 3, 255)
    assert rb._to_rgba([1, 2, 3, 4]) == (1, 2, 3, 4)
    assert rb._to_rgba(None) == (0, 0, 0, 255)
    with pytest.raises(ValueError):
        rb._to_rgba("red")


def test_region_size() -> None:
    import render_backend as rb

    region = rb.DrawerRegion(10, 20, 30, 60)
    assert region.width() == 20
    assert region.height() == 40


# ---------- 渲染细节 1：区域自适应字号 ----------


def test_fit_font_shrinks_for_long_text() -> None:
    """同样的区域，长文本自动选更小字号。"""
    import render_backend as rb

    short, _ = rb._fit_font("短", _font_path(), 48, 589, 150)
    long, _ = rb._fit_font("这是一段很长很长的文本" * 10, _font_path(), 48, 589, 150)
    assert short.size > long.size


def test_fit_font_respects_region_height() -> None:
    """字号与换行后的总行高不超过区域高度。"""
    import render_backend as rb

    font, lines = rb._fit_font("测试文本" * 20, _font_path(), 64, 100, 80)
    step = int(font.size * 1.15)
    assert step * len(lines) <= 80


# ---------- 渲染细节 2：【】染色 ----------


def test_bracket_coloring() -> None:
    """【】内的文字用 bracket_color，其余用 color。"""
    from PIL import Image, ImageDraw, ImageFont

    import render_backend as rb

    canvas = Image.new("RGBA", (400, 80), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(_font_path(), 40)
    style = rb.TextStyle(color=(0, 0, 0, 255), bracket_color=(255, 0, 0, 255))
    rb._draw_colored_line(draw, 0, 0, "普通【红字】", font, style)

    # 扫描像素：应同时存在接近纯黑与接近纯红的文字像素。
    pixels = list(canvas.get_flattened_data())
    has_black = any(r < 40 and g < 40 and b < 40 for r, g, b, _ in pixels)
    has_red = any(r > 200 and g < 60 and b < 60 for r, g, b, _ in pixels)
    assert has_black, "普通文字未用 color 渲染"
    assert has_red, "【】内文字未用 bracket_color 渲染"


# ---------- 渲染细节 3：alpha 合成策略 ----------


def test_paste_image_keep_alpha_false(tmp_path: Path) -> None:
    """keep_alpha=False 时透明像素与黑底合成，不透出下层。"""
    from PIL import Image

    import render_backend as rb

    base = tmp_path / "base.png"
    Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(base)
    overlay = tmp_path / "overlay.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(overlay)

    drawer = rb._PillowDrawer(str(base), _font_path()).paste_image(
        str(overlay), rb.DrawerRegion(0, 0, 10, 10), rb.PasteStyle(keep_alpha=False)
    )
    assert drawer.image.getpixel((5, 5))[:3] == (0, 0, 0)


def test_paste_image_keep_alpha_true(tmp_path: Path) -> None:
    """keep_alpha=True 时透明像素保留下层颜色。"""
    from PIL import Image

    import render_backend as rb

    base = tmp_path / "base.png"
    Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(base)
    overlay = tmp_path / "overlay.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(overlay)

    drawer = rb._PillowDrawer(str(base), _font_path()).paste_image(
        str(overlay), rb.DrawerRegion(0, 0, 10, 10), rb.PasteStyle(keep_alpha=True)
    )
    assert drawer.image.getpixel((5, 5))[:3] == (255, 255, 255)


# ---------- Pillow 后端端到端 ----------


def test_pillow_drawer_end_to_end() -> None:
    """Pillow 链式绘制返回合法 PNG 字节。"""
    import render_backend as rb

    drawer = rb._PillowDrawer(
        str(PLUGIN_ROOT / "assets/trial/black.png"),
        str(PLUGIN_ROOT / "assets/fonts/SourceHanSerifSC.otf"),
    )
    result = (
        drawer.paste_image(
            str(PLUGIN_ROOT / "assets/trial/background.png"),
            rb.DrawerRegion(0, 0, 1260, 1080),
            rb.PasteStyle(keep_alpha=False),
        )
        .draw_text(
            "【疑问】测试选项",
            rb.DrawerRegion(138, 396, 727, 546),
            rb.TextStyle(color=(39, 33, 30, 255), max_font_height=48),
        )
        .finish()
    )
    assert isinstance(result, bytes)
    assert result.startswith(b"\x89PNG\r\n\x1a\n")


def test_pillow_textfit_end_to_end() -> None:
    """Pillow 自适应文本渲染返回合法 PNG 字节。"""
    import render_backend as rb

    drawer = rb._PillowTextFitDrawer(
        str(PLUGIN_ROOT / "assets/anan/base.png"),
        _font_path(),
        str(PLUGIN_ROOT / "assets/anan/base_overlay.png"),
        rb.DrawerRegion(100, 432, 419, 636),
    )
    result = drawer.draw("吾辈不想说话【猛击】", rb.TextStyle())
    assert isinstance(result, bytes)
    assert result.startswith(b"\x89PNG\r\n\x1a\n")
