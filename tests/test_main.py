"""main.py 指令处理单测（stub astrbot）。"""

import json
from pathlib import Path
from typing import Any, List

import pytest
from astrbot_plugin_manosaba_memes import main as main_mod
from astrbot_plugin_manosaba_memes.constants import FACE_WHITELIST
from astrbot_plugin_manosaba_memes.main import ManosabaMemesPlugin
from astrbot_plugin_manosaba_memes.models import Character


class FakeEvent:
    """最小事件替身：记录 plain/chain 结果。"""

    def __init__(
        self,
        message_str: str,
        session: str = "session-1",
        user: str = "u1",
        platform: str = "qq",
    ) -> None:
        self.message_str = message_str
        self._session = session
        self._user = user
        self.unified_msg_origin = f"{platform}:GroupMessage:{session}"
        self.results: List[Any] = []

    def plain_result(self, text: str) -> Any:
        self.results.append(("plain", text))
        return self.results[-1]

    def chain_result(self, chain: Any) -> Any:
        self.results.append(("chain", chain))
        return self.results[-1]

    def get_session_id(self) -> str:
        return self._session

    def get_sender_id(self) -> str:
        return self._user

    @property
    def key(self) -> str:
        return json.dumps([self.unified_msg_origin, self._user], ensure_ascii=False)

    @property
    def last(self) -> Any:
        return self.results[-1] if self.results else None


async def _drain(agen: Any) -> List[Any]:
    """消费异步生成器。"""
    return [item async for item in agen]


@pytest.fixture
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ManosabaMemesPlugin:
    monkeypatch.setattr(main_mod.StarTools, "get_data_dir", lambda name: tmp_path)
    p = ManosabaMemesPlugin(None)
    p.data_file = tmp_path / "character_preferences.json"
    return p


# ── 初始化与偏好持久化 ────────────────────────────────────────────────────


async def test_initialize_creates_data_file(plugin: ManosabaMemesPlugin) -> None:
    await plugin.initialize()
    assert plugin.data_file is not None
    assert plugin.data_file.parent.exists()


async def test_load_preferences_ignores_invalid_names(
    plugin: ManosabaMemesPlugin,
) -> None:
    event = FakeEvent("", session="s1")
    other = FakeEvent("", session="s2")
    assert plugin.data_file is not None
    plugin.data_file.write_text(
        json.dumps({event.key: "希罗", other.key: "不存在的角色"}, ensure_ascii=False),
        encoding="utf-8",
    )
    await plugin._load_character_preferences()
    assert plugin.character_map[event.key] is Character.HIRO
    # 无效名字被忽略，不写入 map
    assert other.key not in plugin.character_map


async def test_load_preferences_handles_broken_json(
    plugin: ManosabaMemesPlugin,
) -> None:
    assert plugin.data_file is not None
    plugin.data_file.write_text("{not json", encoding="utf-8")
    # 不应抛异常
    await plugin._load_character_preferences()


async def test_save_and_reload_preferences(plugin: ManosabaMemesPlugin) -> None:
    event = FakeEvent("", session="s1")
    plugin._write_preferences({event.key: Character.HIRO.value})
    assert plugin.data_file is not None
    assert json.loads(plugin.data_file.read_text(encoding="utf-8")) == {
        event.key: "Hiro"
    }

    plugin.character_map.clear()
    await plugin._load_character_preferences()
    # get_character 兼容旧的英文 value
    assert plugin.character_map[event.key] is Character.HIRO


# ── 安安说 ─────────────────────────────────────────────────────────────────


async def test_handle_anan_says_requires_text(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_anan_says(FakeEvent("安安说")))
    assert out[0][0] == "plain" and "请输入文本" in out[0][1]


@pytest.mark.parametrize("face", sorted(FACE_WHITELIST))
async def test_handle_anan_says_with_face(
    plugin: ManosabaMemesPlugin, face: str
) -> None:
    event = FakeEvent(f"安安说 你好 {face}")
    out = await _drain(plugin.handle_anan_says(event))
    assert out[0][0] == "chain" and len(out[0][1]) == 1


async def test_handle_anan_says_unknown_face_treated_as_text(
    plugin: ManosabaMemesPlugin,
) -> None:
    event = FakeEvent("安安说 你好 随便")
    out = await _drain(plugin.handle_anan_says(event))
    assert out[0][0] == "chain"


async def test_handle_anan_says_newline_escape(plugin: ManosabaMemesPlugin) -> None:
    event = FakeEvent(r"安安说 第一行\n第二行")
    out = await _drain(plugin.handle_anan_says(event))
    assert out[0][0] == "chain"


async def test_handle_anan_says_reports_draw_failure(
    plugin: ManosabaMemesPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: Any, **kwargs: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(main_mod, "draw_anan", boom)
    out = await _drain(plugin.handle_anan_says(FakeEvent("安安说 你好")))
    assert out[0][0] == "plain" and "生成图片失败" in out[0][1]


# ── 审判表情包 ─────────────────────────────────────────────────────────────


async def test_handle_trial_single_option(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_trial(FakeEvent("【疑问】这是疑问")))
    assert out[0][0] == "chain" and len(out[0][1]) == 1


async def test_handle_trial_multiple_options(plugin: ManosabaMemesPlugin) -> None:
    event = FakeEvent("【疑问】第一\n【反驳】第二\n【赞同】第三")
    out = await _drain(plugin.handle_trial(event))
    assert out[0][0] == "chain" and len(out[0][1]) == 1


async def test_handle_trial_paginates(plugin: ManosabaMemesPlugin) -> None:
    msg = "\n".join(f"【疑问】选项{i}" for i in range(5))
    out = await _drain(plugin.handle_trial(FakeEvent(msg)))
    # 每页最多 3 项，5 项分成 2 页
    assert out[0][0] == "chain" and len(out[0][1]) == 2


async def test_handle_trial_magic_with_arg(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_trial(FakeEvent("【魔法: 诺亚】液体操控")))
    assert out[0][0] == "chain"


async def test_handle_trial_bad_statement_reports_error(
    plugin: ManosabaMemesPlugin,
) -> None:
    out = await _drain(plugin.handle_trial(FakeEvent("随便说点什么")))
    assert out[0][0] == "plain" and "格式错误" in out[0][1]


async def test_handle_trial_invalid_magic_reports_error(
    plugin: ManosabaMemesPlugin,
) -> None:
    out = await _drain(plugin.handle_trial(FakeEvent("【魔法: 路人】某事")))
    assert out[0][0] == "plain" and "无效的角色" in out[0][1]


async def test_handle_trial_too_many_options(plugin: ManosabaMemesPlugin) -> None:
    msg = "\n".join(f"【疑问】选项{i}" for i in range(11))
    out = await _drain(plugin.handle_trial(FakeEvent(msg)))
    assert out[0][0] == "plain" and "最多支持" in out[0][1]


async def test_handle_trial_draw_failure_reports(
    plugin: ManosabaMemesPlugin, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: Any, **kwargs: Any) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr(main_mod, "draw_trial", boom)
    out = await _drain(plugin.handle_trial(FakeEvent("【疑问】文本")))
    assert out[0][0] == "plain" and "生成图片失败" in out[0][1]


# ── 切换角色 / 帮助 ────────────────────────────────────────────────────────


async def test_switch_character_requires_name(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_switch_character(FakeEvent("切换角色")))
    assert out[0][0] == "plain" and "请输入角色名" in out[0][1]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("艾玛", Character.EMA), ("希罗", Character.HIRO)],
)
async def test_switch_character_success(
    plugin: ManosabaMemesPlugin, name: str, expected: Character
) -> None:
    event = FakeEvent(f"切换角色 {name}", session="s9")
    out = await _drain(plugin.handle_switch_character(event))
    assert out[0][0] == "plain" and f"已切换角色为 {name}" in out[0][1]
    assert plugin.character_map[event.key] is expected
    assert plugin.data_file is not None
    assert (
        json.loads(plugin.data_file.read_text(encoding="utf-8"))[event.key]
        == expected.value
    )


async def test_switch_character_invalid(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_switch_character(FakeEvent("切换角色 路人")))
    assert out[0][0] == "plain" and "无效的角色" in out[0][1]


async def test_handle_help(plugin: ManosabaMemesPlugin) -> None:
    out = await _drain(plugin.handle_help(FakeEvent("魔裁帮助")))
    assert out[0][0] == "plain" and "安安说" in out[0][1] and "审判表情包" in out[0][1]


async def test_terminate(plugin: ManosabaMemesPlugin) -> None:
    # terminate 仅记录卸载日志，不应抛异常
    await plugin.terminate()
