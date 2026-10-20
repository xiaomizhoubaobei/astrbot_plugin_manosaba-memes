import asyncio
import base64
from io import BytesIO
import json
import keyword
from pathlib import Path
import zipfile

from PIL import Image
import pytest
import yaml

from astrbot_plugin_manosaba_memes import main
from astrbot_plugin_manosaba_memes.build_release import build
from astrbot_plugin_manosaba_memes.constants import FACE_WHITELIST, BRACKET_COLOR
from astrbot_plugin_manosaba_memes.drawer import draw_anan, draw_trial, get_option_coordinates
from astrbot_plugin_manosaba_memes.models import Character, Option, Statement
from astrbot_plugin_manosaba_memes.utils import parse_anan, parse_trial, TRIAL_TRIGGER

ROOT = Path(__file__).resolve().parents[1]


class Event:
    def __init__(self, message="", user="one", platform="qq", session="group"):
        self.message_str = message
        self.user, self.session = user, session
        self.unified_msg_origin = f"{platform}:GroupMessage:{session}"

    def get_sender_id(self):
        return self.user

    def get_session_id(self):
        return self.session

    def plain_result(self, text):
        return text

    def chain_result(self, chain):
        return chain


async def collect(generator):
    return [item async for item in generator]


def test_install_metadata():
    data = yaml.safe_load((ROOT / "metadata.yaml").read_text(encoding="utf-8"))
    assert data["name"] == "astrbot_plugin_manosaba_memes"
    assert data["name"].isidentifier() and not keyword.iskeyword(data["name"])
    assert all(data.get(key) for key in ("name", "desc", "version", "author", "repo"))


def test_release_contains_every_runtime_file(tmp_path):
    archive = build(tmp_path / "plugin.zip")
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        files = set(bundle.namelist())
        prefix = "astrbot_plugin_manosaba_memes/"
        for path in list(ROOT.glob("*.py")) + list((ROOT / "assets").rglob("*")):
            if path.is_file():
                assert prefix + path.relative_to(ROOT).as_posix() in files
        assert all(name.startswith(prefix) for name in files)
        assert not any("__pycache__" in name or ".git/" in name for name in files)


def test_long_trial_text_clear_of_icon():
    from astrbot_plugin_manosaba_memes import constants as c
    assert c.TEXT_OFFSET_X > c.STATEMENT_OFFSET_X + c.STATEMENT_ICON_WIDTH
    assert c.TEXT_OFFSET_X + c.TEXT_WIDTH < c.OPTION_WIDTH


def test_anan_input():
    assert parse_anan("第一行\\n第二行\u3000开心 ") == ("第一行\n第二行", "开心")
    assert parse_anan("今天很 开心呀") == ("今天很 开心呀", None)
    with pytest.raises(ValueError):
        parse_anan("\\n 开心")
    with pytest.raises(ValueError):
        parse_anan("字" * 301)


def test_trial_input():
    options = parse_trial("  【疑问】第一行\\n第二行\r\n\r\n【魔法： 诺亚 】液体操控 ")
    assert options[0].text == "第一行\n第二行"
    assert options[1].statement == Statement.MAGIC_EKITAISOUSA
    assert TRIAL_TRIGGER.search("  【疑问】测试")
    assert not TRIAL_TRIGGER.search("聊天里引用【疑问】测试")


@pytest.mark.parametrize("text", [
    "【疑问】", "【疑问】   ", "【魔法】文本", "【魔法:未知】文本",
    "【疑问:艾玛】文本", "【疑问】正确\n错误的一行",
    "【疑问】" + "字" * 201, "\n".join(["【疑问】测试"] * 11),
])
def test_trial_invalid_not_silently_dropped(text):
    with pytest.raises(ValueError):
        parse_trial(text)


@pytest.mark.parametrize("face", [None, *sorted(FACE_WHITELIST)])
def test_actual_anan_render(face):
    data = draw_anan("今天也要【加油】\n第二行", face)
    with Image.open(BytesIO(data)) as image:
        image.load()
        assert image.size == (541, 648)
        assert any(pixel[:3] == BRACKET_COLOR[:3] for pixel in image.getdata())


@pytest.mark.parametrize("character", list(Character))
@pytest.mark.parametrize("statement", list(Statement))
def test_actual_trial_assets_and_highlight(character, statement):
    data = draw_trial(character, [Option(statement, "这是【重点】\n中文与 English")])
    with Image.open(BytesIO(data)) as image:
        image.load()
        assert image.size == (1260, 1080)
        assert any(pixel[:3] == BRACKET_COLOR[:3] for pixel in image.getdata())


@pytest.mark.parametrize("count", [1, 2, 3])
def test_page_layout_fully_visible(count):
    coords = get_option_coordinates(count)
    previous_bottom = 0
    for x, y in coords:
        assert x >= 0 and x + 802 <= 1260
        assert y - 43 >= previous_bottom
        assert y + 216 <= 1080
        previous_bottom = y + 216


def test_preference_restart_and_isolation(tmp_path):
    async def scenario():
        plugin = main.ManosabaMemesPlugin(None)
        plugin.data_file = tmp_path / "preferences.json"
        plugin.data_file.write_text(json.dumps({"legacy": "Hiro", "bad": 17}), encoding="utf-8")
        await plugin._load_character_preferences()
        assert plugin._character_for(Event(session="legacy")) == Character.HIRO
        reply = await collect(plugin.handle_switch_character(Event("切换角色 希罗")))
        assert "已保存" in reply[0]
        reloaded = main.ManosabaMemesPlugin(None)
        reloaded.data_file = plugin.data_file
        await reloaded._load_character_preferences()
        assert reloaded._character_for(Event()) == Character.HIRO
        assert reloaded._character_for(Event(user="two")) == Character.EMA
        assert reloaded._character_for(Event(platform="other")) == Character.EMA
        assert reloaded._character_for(Event(session="other")) == Character.EMA
    asyncio.run(scenario())


def test_save_failure_keeps_file_and_memory(tmp_path, monkeypatch):
    async def scenario():
        plugin = main.ManosabaMemesPlugin(None)
        plugin.data_file = tmp_path / "prefs.json"
        plugin.data_file.write_text("{}", encoding="utf-8")
        def fail(*args, **kwargs):
            raise OSError("simulated disk failure")
        monkeypatch.setattr(Path, "replace", fail)
        reply = await collect(plugin.handle_switch_character(Event("切换角色 希罗")))
        assert "失败" in reply[0]
        assert plugin._character_for(Event()) == Character.EMA
        assert plugin.data_file.read_text() == "{}"
        assert not list(tmp_path.glob("*.tmp"))
    asyncio.run(scenario())


@pytest.mark.parametrize("count", range(1, 11))
def test_handler_pagination_and_result_lifetime(count, monkeypatch):
    async def scenario():
        seen = []
        def render(character, options):
            seen.extend(option.text for option in options)
            assert 1 <= len(options) <= 3
            return b"PNG-test-payload"
        monkeypatch.setattr(main, "draw_trial", render)
        plugin = main.ManosabaMemesPlugin(None)
        text = "\n".join(f"【疑问】第 {i} 项" for i in range(count))
        results = await collect(plugin.handle_trial(Event(text)))
        assert seen == [f"第 {i} 项" for i in range(count)]
        assert len(results) == 1
        assert len(results[0]) == (count + 2) // 3
        for component in results[0]:
            assert base64.b64decode(component.file.removeprefix("base64://")) == b"PNG-test-payload"
    asyncio.run(scenario())


def test_invalid_input_does_not_render(monkeypatch):
    async def scenario():
        def fail(*args):
            pytest.fail("invalid request reached renderer")
        monkeypatch.setattr(main, "draw_trial", fail)
        plugin = main.ManosabaMemesPlugin(None)
        result = await collect(plugin.handle_trial(Event("【疑问】正确\n错误")))
        assert "第 2 行格式错误" in result[0]
    asyncio.run(scenario())
