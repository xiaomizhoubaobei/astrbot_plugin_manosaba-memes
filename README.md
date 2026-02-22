# 魔裁 Memes - AstrBot 插件

生成「魔法少女的魔法审判」相关表情包的 AstrBot 插件。

## 功能特性

### 安安说
让不同表情的安安举着写了你想说的话的素描本

**用法**: `安安说 [文本] [表情]`

**可用表情**: 害羞, 生气, 病娇, 无语, 开心

**别名**: `anan说`, `anansays`

**示例**:
```
安安说 吾辈现在不想说话
安安说 吾辈命令你现在【猛击自己的魔丸一百下】 生气
```

### 审判表情包
生成审判时的选项图片

**用法**: `【疑问/反驳/伪证/赞同/魔法:[角色名]】[文本]`

**类型**: 疑问, 反驳, 伪证, 赞同, 魔法

**魔法角色**: 梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅

**示例**:
```
【伪证】我和艾玛不是恋人
【赞同】我们初中的时候就确认关系了
【魔法:诺亚】液体操控
```

### 切换角色
切换审判表情包中的角色

**用法**: `切换角色 [角色名]`

**可选角色**: 艾玛, 希罗

**示例**:
```
切换角色 希罗
```

### 帮助命令
查看完整的使用说明

**用法**: `魔裁帮助`

**别名**: `manosaba帮助`, `魔裁help`

## 安装方法

### 从插件市场安装
在 AstrBot 插件市场中搜索并安装 `astrbot_plugin_manosaba-memes`

### 手动安装
1. 下载插件的最新版本
2. 将插件文件夹放入 AstrBot 的 `data/plugins/` 目录
3. 重启 AstrBot 或使用插件管理器加载插件

## 小贴士

- 在文本中输入 `\n` 可以换行
- 中括号 `【】` 中的内容会被渲染成紫色
- 审判表情包支持多行输入生成多个选项
- 选项数量建议 3 条以内效果最佳
- 角色与用户绑定，每个用户可以独立设置

## 依赖

- `sketchbook-py>=0.2.1`

## 开发信息

- **插件名称**: astrbot_plugin_manosaba-memes
- **版本**: v0.0.1
- **作者**: 祁筱欣
- **仓库**: https://github.com/xiaomizhoubaobei/astrbot_plugin_manosaba-memes
- **基于**: [nonebot-plugin-manosaba-memes](https://github.com/zhaomaoniu/nonebot-plugin-manosaba-memes)

## 致谢

- 感谢 [TY_Ling](https://github.com/TY_Ling) 提出了写这个插件的想法
- 感谢 [Mythos_404](https://github.com/Mythos-404) 编写了高效又好用的绘图库 sketchbook-py
- 感谢 [Acacia](https://github.com/Acacia-997) 制作了魔法少女ノ魔女裁判

## 许可证

本项目基于 GNU Affero General Public License v3.0 (AGPL-3.0) 开源。

## 相关链接

- [AstrBot 官方文档](https://docs.astrbot.app/)
- [原版 NoneBot 插件](https://github.com/zhaomaoniu/nonebot-plugin-manosaba-memes)