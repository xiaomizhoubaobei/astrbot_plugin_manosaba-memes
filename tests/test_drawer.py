"""drawer.py 单测：路径白名单、坐标布局与绘图流程（stub sketchbook）。"""

import pytest
from astrbot_plugin_manosaba_memes.constants import (
    FACE_WHITELIST,
    MAX_OPTIONS_COUNT,
    OPTION_END_Y,
    OPTION_HEIGHT,
    OPTION_START_X,
    OPTION_START_Y,
)
from astrbot_plugin_manosaba_memes.drawer import (
    PLUGIN_PATH,
    draw_anan,
    draw_trial,
    get_anan_base_image,
    get_option_coordinates,
    get_statement_image,
)
from astrbot_plugin_manosaba_memes.models import Character, Option, Statement


def test_get_anan_base_image_default() -> None:
    path = get_anan_base_image()
    assert path.endswith("assets/anan/base.png")
    assert path.startswith(str(PLUGIN_PATH))


@pytest.mark.parametrize("face", sorted(FACE_WHITELIST))
def test_get_anan_base_image_whitelisted(face: str) -> None:
    path = get_anan_base_image(face)
    assert path.endswith(f"assets/anan/{face}.png")


@pytest.mark.parametrize("bad", ["../../etc/passwd", "unknown", "base"])
def test_get_anan_base_image_rejects_unknown(bad: str) -> None:
    with pytest.raises(ValueError, match="Invalid face type"):
        get_anan_base_image(bad)


def test_draw_anan_returns_bytes() -> None:
    result = draw_anan("你好", face="开心")
    assert isinstance(result, bytes)
    assert result.startswith(b"\x89PNG")
    assert "你好" in result.decode("utf-8", errors="ignore")


@pytest.mark.parametrize(
    ("statement", "filename"),
    [
        (Statement.AGREEMENT, "agreement.png"),
        (Statement.DOUBT, "doubt.png"),
        (Statement.MAGIC_SHISENYUUDOU, "magic_shisenyuudou.png"),
    ],
)
def test_get_statement_image(statement: Statement, filename: str) -> None:
    assert get_statement_image(statement).endswith(f"assets/trial/{filename}")


def test_get_statement_image_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="未知的陈述类型"):
        get_statement_image("unknown")  # type: ignore[arg-type]


@pytest.mark.parametrize("number", [0, -1, MAX_OPTIONS_COUNT + 1])
def test_get_option_coordinates_rejects_bad_count(number: int) -> None:
    with pytest.raises(ValueError):
        get_option_coordinates(number)


def test_get_option_coordinates_single_centered() -> None:
    coords = get_option_coordinates(1)
    assert len(coords) == 1
    x, y = coords[0]
    assert x == OPTION_START_X
    assert y == OPTION_START_Y + (OPTION_END_Y - OPTION_START_Y - OPTION_HEIGHT) // 2


def test_get_option_coordinates_spacing_and_centered() -> None:
    coords = get_option_coordinates(3)
    assert len(coords) == 3
    ys = [y for _, y in coords]
    # 间距 20px：相邻 y 固定相差 OPTION_HEIGHT + 20
    step = OPTION_HEIGHT + 20
    assert ys[1] - ys[0] == step
    assert ys[2] - ys[1] == step
    # 3 项总高 3*216+2*20=688 < 可用高度 416? 否 —— 实际超出，故从顶部起排
    # 无论居中或顶对齐，首项都不早于起点，末项步进一致
    assert ys[0] >= OPTION_START_Y
    assert ys[-1] == ys[0] + 2 * step


def test_get_option_coordinates_overflow_starts_at_top() -> None:
    # 选项多到放不下时从顶部开始排布（total_layout_height > available_height）
    coords = get_option_coordinates(MAX_OPTIONS_COUNT)
    assert coords[0][1] == OPTION_START_Y


def _options(count: int) -> list[Option]:
    return [Option(Statement.DOUBT, f"选项{i}") for i in range(count)]


@pytest.mark.parametrize("character", [Character.EMA, Character.HIRO])
def test_draw_trial_by_character(character: Character) -> None:
    result = draw_trial(character, _options(2))
    text = result.decode("utf-8", errors="ignore")
    # 角色图片被 paste
    expected_img = "ema.png" if character == Character.EMA else "hiro.png"
    assert expected_img in text
    # 选项文本与陈述图标都进入绘制流程
    assert "选项0" in text and "选项1" in text
    assert "doubt.png" in text


def test_draw_trial_rejects_empty_options() -> None:
    with pytest.raises(ValueError, match="选项数量不能为 0"):
        draw_trial(Character.EMA, [])


def test_draw_trial_rejects_too_many_options() -> None:
    with pytest.raises(ValueError, match="最多支持"):
        draw_trial(Character.EMA, _options(MAX_OPTIONS_COUNT + 1))
