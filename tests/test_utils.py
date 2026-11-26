"""utils.py 文本标准化与枚举转换单测。"""

import pytest

from astrbot_plugin_manosaba_memes.models import Character, Statement
from astrbot_plugin_manosaba_memes.utils import (
    _normalize_text,
    get_character,
    get_magic_statement,
    get_statement,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        (None, None),
        ("  hello  ", "hello"),
        ("a\u3000\u3000b", "a b"),
        ("a   b\tc", "a b c"),
    ],
)
def test_normalize_text(raw: object, expected: object) -> None:
    assert _normalize_text(raw) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("赞同", Statement.AGREEMENT),
        ("疑问", Statement.DOUBT),
        ("伪证", Statement.PERJURY),
        ("反驳", Statement.REFUTATION),
        ("  赞同  ", Statement.AGREEMENT),
    ],
)
def test_get_statement_basic(raw: str, expected: Statement) -> None:
    assert get_statement(raw) is expected


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("梅露露", Statement.MAGIC_CHIYUSAISEI),
        ("诺亚", Statement.MAGIC_EKITAISOUSA),
        ("汉娜", Statement.MAGIC_FUYUU),
        ("奈叶香", Statement.MAGIC_GENSHI),
        ("亚里沙", Statement.MAGIC_HAKKA),
        ("米莉亚", Statement.MAGIC_IREKAWARI),
        ("雪莉", Statement.MAGIC_KAIRIKI),
        ("艾玛", Statement.MAGIC_MAJOGOROSHI),
        ("玛格", Statement.MAGIC_MONOMANE),
        ("安安", Statement.MAGIC_SENNOU),
        ("可可", Statement.MAGIC_SENRIGAN),
        ("希罗", Statement.MAGIC_SHINIMODORI),
        ("蕾雅", Statement.MAGIC_SHISENYUUDOU),
    ],
)
def test_get_magic_statement_all_roles(arg: str, expected: Statement) -> None:
    assert get_magic_statement(arg) is expected
    assert get_statement("魔法", arg) is expected


def test_get_statement_magic_fullwidth_colon_arg() -> None:
    assert get_statement("魔法", "  诺亚  ") is Statement.MAGIC_EKITAISOUSA


def test_get_statement_invalid_type() -> None:
    with pytest.raises(ValueError, match="无效的陈述类型"):
        get_statement("未知")


@pytest.mark.parametrize("arg", [None, "", "   "])
def test_get_statement_magic_requires_arg(arg: object) -> None:
    with pytest.raises(ValueError, match="需要指定角色名"):
        get_statement("魔法", arg)  # type: ignore[arg-type]


@pytest.mark.parametrize("raw", ["", "   ", "\u3000"])
def test_get_magic_statement_blank(raw: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        get_magic_statement(raw)


def test_get_magic_statement_unknown_role() -> None:
    with pytest.raises(ValueError, match="无效的角色"):
        get_magic_statement("路人甲")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("艾玛", Character.EMA), ("希罗", Character.HIRO), ("  希罗 ", Character.HIRO)],
)
def test_get_character(raw: str, expected: Character) -> None:
    assert get_character(raw) is expected


@pytest.mark.parametrize("raw", ["", "  ", "\u3000"])
def test_get_character_blank(raw: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        get_character(raw)


def test_get_character_unknown() -> None:
    with pytest.raises(ValueError, match="无效的角色"):
        get_character(" unspecified ")
