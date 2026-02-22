import re
import tempfile
import asyncio
import json
from collections import defaultdict
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, StarTools
from astrbot.api import logger

from .models import Option, Character
from .drawer import draw_anan, draw_trial, MAX_OPTIONS_COUNT
from .utils import get_statement, get_character
from .constants import FACE_WHITELIST


class ManosabaMemesPlugin(Star):
    """生成「魔法少女的魔法审判」的表情包插件
    
    指令列表：
    • 安安说 - 让安安举着写了你想说的话的素描本
      用法: 安安说 [文本] [表情]
      表情可选: 害羞, 生气, 病娇, 无语, 开心
      别名: anan说, anansays
    
    • 审判表情包 - 生成审判时的选项图片
      用法: 【疑问/反驳/伪证/赞同/魔法:[角色名]】[文本]
      类型: 疑问, 反驳, 伪证, 赞同, 魔法
      魔法角色: 梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅
    
    • 切换角色 - 切换审判表情包中的角色（自动保存）
      用法: 切换角色 [角色名]
      角色可选: 艾玛, 希罗
    
    • 魔裁帮助 - 显示插件帮助信息
      别名: manosaba帮助, 魔裁help
    """
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.character_map = defaultdict(lambda: Character.EMA)
        self.data_file = None  # 将在 initialize 中设置

    async def initialize(self):
        """插件初始化方法"""
        # 获取插件数据目录
        data_dir = StarTools.get_data_dir()
        self.data_file = data_dir / "character_preferences.json"
        
        # 确保数据目录存在
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载用户角色偏好
        await self._load_character_preferences()
        
        logger.info("魔裁 Memes 插件已加载")

    async def _load_character_preferences(self):
        """从文件加载用户角色偏好"""
        try:
            if self.data_file and self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for session_id, character_name in data.items():
                        try:
                            self.character_map[session_id] = get_character(character_name)
                        except ValueError:
                            # 忽略无效的角色名，使用默认值
                            logger.warning(f"加载角色偏好失败: 无效的角色名 {character_name}")
                logger.info(f"已加载 {len(self.character_map)} 个用户的角色偏好")
        except Exception as e:
            logger.error(f"加载角色偏好失败: {e}")

    async def _save_character_preferences(self):
        """保存用户角色偏好到文件"""
        try:
            if self.data_file:
                # 将 Character 枚举转换为字符串
                data = {
                    session_id: character.value
                    for session_id, character in self.character_map.items()
                }
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug(f"已保存 {len(self.character_map)} 个用户的角色偏好")
        except Exception as e:
            logger.error(f"保存角色偏好失败: {e}")

    @filter.command("安安说", alias={"anan说", "anansays"})
    async def handle_anan_says(self, event: AstrMessageEvent):
        """让安安说话的插件

        用法: 安安说 [文本] [表情]
        表情可选: 害羞, 生气, 病娇, 无语, 开心
        """
        message_str = event.message_str
        parts = message_str.split(maxsplit=1)

        if len(parts) < 2:
            yield event.plain_result("请输入文本。用法: 安安说 [文本] [表情]")
            return

        content = parts[1].strip()
        # 尝试从右向左查找最后一个空格作为表情的分隔符
        last_space_idx = content.rfind(' ')
        if last_space_idx != -1:
            potential_face = content[last_space_idx + 1:].strip()
            if potential_face in FACE_WHITELIST:
                text = content[:last_space_idx]
                face = potential_face
            else:
                text = content
                face = None
        else:
            text = content
            face = None

        text = text.replace("\\n", "\n")
        
        try:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(None, draw_anan, text, face)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(image_bytes)
                temp_path = f.name
            try:
                yield event.image_result(temp_path)
            finally:
                Path(temp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"生成安安说话图片失败: {e}")
            yield event.plain_result(f"生成图片失败: {str(e)}")

    @filter.regex(r"^【(疑问|反驳|伪证|赞同|魔法)(?:[:：]([^】]*))?】(.+)$", flags=re.MULTILINE)
    async def handle_trial(self, event: AstrMessageEvent):
        """生成审判表情包

        用法: 【疑问/反驳/伪证/赞同/魔法:[角色名]】这是一个选项文本
        角色名可选: 梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅
        可发送多行以添加多个选项

        注意：最多支持 10 个选项
        """
        message_str = event.message_str
        matches = re.findall(
            r"^【(疑问|反驳|伪证|赞同|魔法)(?:[:：]([^】]*))?】(.+)$",
            message_str,
            flags=re.M,
        )

        options = []
        for statement_type, arg, text in matches:
            try:
                statement_enum = get_statement(statement_type, arg)
                options.append(Option(statement_enum, text))
            except ValueError as e:
                # 直接显示 utils.py 返回的清晰错误信息
                yield event.plain_result(str(e))
                return

        # 前置校验：检查选项数量
        if len(options) > MAX_OPTIONS_COUNT:
            yield event.plain_result(f"选项数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")
            return
        
        if len(options) == 0:
            yield event.plain_result("请至少输入一个选项")
            return

        try:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None, draw_trial, self.character_map[event.get_session_id()], options
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(image_bytes)
                temp_path = f.name
            try:
                yield event.image_result(temp_path)
            finally:
                Path(temp_path).unlink(missing_ok=True)
        except ValueError as e:
            # 捕获选项数量等业务级错误
            yield event.plain_result(str(e))
        except OverflowError:
            yield event.plain_result("选项过多，请减少选项数量")
        except Exception as e:
            logger.error(f"生成审判图片失败: {e}")
            yield event.plain_result(f"生成图片失败: {str(e)}")

    @filter.command("切换角色")
    async def handle_switch_character(self, event: AstrMessageEvent):
        """切换审判选择中的角色
        
        用法: 切换角色 [角色名]
        角色名可选: 艾玛, 希罗
        """
        message_str = event.message_str
        parts = message_str.split(maxsplit=2)
        
        if len(parts) < 2:
            yield event.plain_result("请输入角色名。用法: 切换角色 [角色名]")
            return
        
        character_name = parts[1]
        try:
            character = get_character(character_name)
            self.character_map[event.get_session_id()] = character
            # 保存用户偏好
            await self._save_character_preferences()
            yield event.plain_result(f"已切换角色为 {character_name}")
        except ValueError as e:
            # 直接显示 utils.py 返回的清晰错误信息
            yield event.plain_result(str(e))

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
注意：最多支持 10 个选项
示例: 【伪证】我和艾玛不是恋人
示例: 【魔法: 诺亚】液体操控  （冒号后可以有空格）

3️⃣ 切换角色
用法: 切换角色 [角色名]
说明: 切换审判表情包中的角色（自动保存）
角色可选: 艾玛, 希罗
示例: 切换角色 希罗

💡 小贴士:
• 在文本中输入 \\n 可以换行
• 中括号【】中的内容会被渲染成紫色
• 选项数量建议 3 条以内效果最佳，最多支持 10 条
• 角色选择会自动保存，重启后依然有效
• 角色名和表情名会自动去除首尾空格，支持常见输入格式"""
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法"""
        # 保存用户偏好
        await self._save_character_preferences()
        logger.info("魔裁 Memes 插件已卸载")
