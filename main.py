import re
import tempfile
from collections import defaultdict
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .models import Option
from .drawer import draw_anan, draw_trial
from .utils import get_statement, get_character


@register("manosaba-memes", "祁筱欣", "生成「魔法少女的魔法审判」的表情包", "0.0.1", "https://github.com/xiaomizhoubaobei/astrbot_plugin_manosaba-memes")
class ManosabaMemesPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.character_map = defaultdict(lambda: get_character("艾玛"))

    async def initialize(self):
        """插件初始化方法"""
        logger.info("魔裁 Memes 插件已加载")

    @filter.command("安安说", alias={"anan说", "anansays"})
    async def handle_anan_says(self, event: AstrMessageEvent):
        """让安安说话的插件
        
        用法: 安安说 [文本] [表情]
        表情可选: 害羞, 生气, 病娇, 无语, 开心
        """
        message_str = event.message_str
        parts = message_str.split(maxsplit=2)
        
        if len(parts) < 2:
            yield event.plain_result("请输入文本。用法: 安安说 [文本] [表情]")
            return
        
        text = parts[1]
        face = parts[2] if len(parts) > 2 else None
        text = text.replace("\\n", "\n")
        
        try:
            image_bytes = draw_anan(text, face)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(image_bytes)
                temp_path = f.name
            yield event.image_result(temp_path)
            Path(temp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"生成安安说话图片失败: {e}")
            yield event.plain_result(f"生成图片失败: {str(e)}")

    @filter.regex(r"^【(疑问|反驳|伪证|赞同|魔法)(?:[:：]([^】]*))?】(.+)$", flags=re.MULTILINE)
    async def handle_trail(self, event: AstrMessageEvent):
        """生成审判表情包
        
        用法: 【疑问/反驳/伪证/赞同/魔法:[角色名]】这是一个选项文本
        角色名可选: 梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅
        可发送多行以添加多个选项
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
            except (KeyError, AssertionError):
                if arg:
                    yield event.plain_result(
                        f"角色 {arg} 无效，请从以下选项中选择："
                        "梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅"
                    )
                    return
                else:
                    yield event.plain_result(
                        "魔法类型无效，请输入【魔法:角色】格式。可选的角色有："
                        "梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅"
                    )
                    return
            options.append(Option(statement_enum, text))

        try:
            image_bytes = draw_trial(self.character_map[event.get_session_id()], options)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
                f.write(image_bytes)
                temp_path = f.name
            yield event.image_result(temp_path)
            Path(temp_path).unlink(missing_ok=True)
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
            self.character_map[event.get_session_id()] = get_character(character_name)
            yield event.plain_result(f"已切换角色为 {character_name}")
        except KeyError:
            yield event.plain_result(
                f"角色名 {character_name} 无效，请选择 艾玛 或 希罗"
            )

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
示例: 【伪证】我和艾玛不是恋人
示例: 【魔法:诺亚】液体操控

3️⃣ 切换角色
用法: 切换角色 [角色名]
说明: 切换审判表情包中的角色
角色可选: 艾玛, 希罗
示例: 切换角色 希罗

💡 小贴士:
• 在文本中输入 \\n 可以换行
• 中括号【】中的内容会被渲染成紫色
• 选项数量建议 3 条以内效果最佳"""
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法"""
        logger.info("魔裁 Memes 插件已卸载")
