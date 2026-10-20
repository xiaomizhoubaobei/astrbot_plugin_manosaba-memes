import asyncio
import json
import os
import tempfile
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Image
from astrbot.api.star import Context, Star, StarTools
from astrbot.api import logger

from .models import Character
from .drawer import draw_anan, draw_trial
from .utils import get_character, parse_anan, parse_trial, TRIAL_TRIGGER
from .constants import OPTIONS_PER_PAGE


class ManosabaMemesPlugin(Star):
    """生成魔裁表情包；角色偏好按平台、会话及用户独立保存。"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.character_map: dict[str, Character] = {}
        self.data_file: Path | None = None
        self._preference_lock = asyncio.Lock()
        self._render_lock = asyncio.Lock()

    async def initialize(self):
        data_dir = StarTools.get_data_dir("astrbot_plugin_manosaba_memes")
        self.data_file = data_dir / "character_preferences.json"
        await self._load_character_preferences()
        logger.info("魔裁 Memes 插件已加载")

    @staticmethod
    def _preference_key(event: AstrMessageEvent) -> str:
        # JSON avoids ambiguous separators in platform/session/user identifiers.
        return json.dumps([event.unified_msg_origin, event.get_sender_id()], ensure_ascii=False)

    def _character_for(self, event: AstrMessageEvent) -> Character:
        key = self._preference_key(event)
        # Read legacy session-wide settings until this user makes a new choice.
        return self.character_map.get(key, self.character_map.get(event.get_session_id(), Character.EMA))

    async def _load_character_preferences(self):
        if self.data_file is None or not self.data_file.exists():
            return
        try:
            content = await asyncio.to_thread(self.data_file.read_text, encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("角色偏好文件应为 JSON 对象")
            for key, value in data.items():
                if not isinstance(value, str):
                    logger.warning("忽略无效的角色偏好记录")
                    continue
                try:
                    self.character_map[key] = get_character(value)
                except ValueError:
                    logger.warning("忽略无效的角色偏好记录")
        except Exception:
            logger.exception("读取角色偏好失败，原文件未修改")

    def _write_preferences(self, data: dict[str, str]):
        if self.data_file is None:
            raise RuntimeError("插件尚未初始化")
        # Same-directory replacement is atomic and preserves the previous file
        # if serialization/write/replace fails. Close before replace on Windows.
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.data_file.parent,
                prefix="character_preferences-", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temp_path.replace(self.data_file)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    @filter.command("安安说", alias={"anan说", "anansays"})
    async def handle_anan_says(self, event: AstrMessageEvent):
        parts = event.message_str.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("请输入文本。用法: 安安说 [文本] [表情]")
            return
        try:
            text, face = parse_anan(parts[1])
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return
        try:
            async with self._render_lock:
                image_bytes = await asyncio.to_thread(draw_anan, text, face)
        except Exception:
            logger.exception("生成安安图片失败")
            yield event.plain_result("生成图片失败，请查看控制台日志")
            return
        # The result owns the image bytes, so it remains usable after this
        # generator finishes and no file is removed before the adapter sends it.
        yield event.chain_result([Image.fromBytes(image_bytes)])

    @filter.regex(TRIAL_TRIGGER)
    async def handle_trial(self, event: AstrMessageEvent):
        try:
            options = parse_trial(event.message_str)
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return
        try:
            character = self._character_for(event)
            chain = []
            async with self._render_lock:
                for offset in range(0, len(options), OPTIONS_PER_PAGE):
                    data = await asyncio.to_thread(
                        draw_trial, character, options[offset:offset + OPTIONS_PER_PAGE]
                    )
                    chain.append(Image.fromBytes(data))
        except Exception:
            logger.exception("生成审判图片失败")
            yield event.plain_result("生成图片失败，请查看控制台日志")
            return
        yield event.chain_result(chain)

    @filter.command("切换角色")
    async def handle_switch_character(self, event: AstrMessageEvent):
        parts = event.message_str.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("请输入角色名。用法: 切换角色 [角色名]")
            return
        try:
            character = get_character(parts[1])
        except ValueError as exc:
            yield event.plain_result(str(exc))
            return
        try:
            async with self._preference_lock:
                data = {key: value.value for key, value in self.character_map.items()}
                data[self._preference_key(event)] = character.value
                await asyncio.to_thread(self._write_preferences, data)
                self.character_map[self._preference_key(event)] = character
        except Exception:
            logger.exception("保存角色偏好失败")
            yield event.plain_result("角色切换失败：无法保存偏好，请检查插件数据目录权限")
            return
        name = "艾玛" if character == Character.EMA else "希罗"
        yield event.plain_result(f"已切换角色为 {name}（仅当前会话中的你生效，已保存）")

    @filter.command("魔裁帮助", alias={"manosaba帮助", "魔裁help"})
    async def handle_help(self, event: AstrMessageEvent):
        """显示插件帮助信息"""
        help_text = """🌸 魔裁 Memes 插件使用说明 🌸

📖 指令列表：

1️⃣ 安安说
用法: 安安说 [文本] [表情]
说明: 让安安举着写了你想说的话的素描本
表情可选: 害羞, 生气, 病娇, 无语, 开心
别名: anan说, anansays
示例: 安安说 吾辈现在不想说话
示例: 安安说 吾辈命令你现在【猛击自己的魔丸一百下】 生气

2️⃣ 审判表情包
用法: 【疑问/反驳/伪证/赞同/魔法:[角色名]】[文本]
说明: 生成审判时的选项图片，支持多行输入生成多个选项
类型: 疑问, 反驳, 伪证, 赞同, 魔法
魔法角色: 梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅
注意：最多支持 10 个选项，每张图片最多 3 项，超出自动分页
示例: 【伪证】我和艾玛不是恋人
示例: 【魔法: 诺亚】液体操控  （冒号后可以有空格）

3️⃣ 切换角色
用法: 切换角色 [角色名]
说明: 切换审判表情包中的角色（自动保存）
角色可选: 艾玛, 希罗
示例: 切换角色 希罗

💡 小贴士:
• 在文本中输入 \\n 可以换行
• 中括号【】中的文字会被渲染成紫色
• 支持 🐖、❤️、👍🏻 等 Noto 2D 彩色 emoji，未收录组合显示 [表情]
• 最多支持 10 个选项，超过 3 个时自动分页，保留清晰字号
• 安安文本最多 300 字，每个审判选项最多 200 字
• 角色按平台、会话、用户独立保存，重启后依然有效
• 角色名和表情名会自动去除首尾空格，支持常见输入格式"""
        yield event.plain_result(help_text)

    async def terminate(self):
        logger.info("魔裁 Memes 插件已卸载")
