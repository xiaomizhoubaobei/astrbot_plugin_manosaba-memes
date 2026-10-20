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
在 AstrBot 插件市场中搜索并安装 `astrbot_plugin_manosaba_memes`

### 手动安装
1. 下载 Release 中的插件 ZIP，在 AstrBot 的插件管理页面选择从文件安装
2. ZIP 内目录名及 metadata 名称均为 `astrbot_plugin_manosaba_memes`
3. 如已有同名插件，先保留备份，并按 AstrBot 管理界面流程处理重复目录


## 小贴士

- 在文本中输入 `\n` 可以换行
- 中括号 `【】` 中的内容会被渲染成紫色
- 审判表情包支持多行输入生成多个选项
- 最多 10 个选项，每张图片最多 3 项，超过后按顺序自动分页
- 角色按平台、会话和用户分别保存；兼容旧版会话偏好文件中的 Ema/Hiro 值
- 安安文本最多 300 字，每个审判选项最多 200 字；空白或错误行会提示错误
- 安安命令后的表情名支持普通空格、全角空格和制表符分隔
- 审判格式每行一项，行内换行请使用字面量 `\n`；直接发送以 `【疑问】` 等开头的消息即可

## 依赖

- `sketchbook-py>=0.2.1,<1.0.0`
- `Pillow>=10.4.0,<13`
- `regex>=2024.11.6`

## 开发信息

- **插件名称**: astrbot_plugin_manosaba_memes
- **版本**: v0.0.5
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

## 构建与测试

`build_release.py` 会检查模块名、必需文件、emoji 索引与素材哈希，生成包含绘图模块、图片、字体及许可文件的完整安装包：

```shell
python build_release.py --output dist/astrbot_plugin_manosaba_memes.zip
```

在独立环境中安装运行依赖和测试依赖后执行回归测试：

```shell
python -m pip install -r requirements.txt pytest PyYAML
python -m pytest -q
```

测试真实调用 sketchbook/Pillow 绘图，AstrBot 事件和消息组件使用接口替身；
测试覆盖角色偏好、分页、输入校验、图片结果生命周期、emoji 混排及 Windows 字体文件释放。
这些测试不替代 AstrBot 平台适配器的真实消息发送测试。

## Noto 2D emoji

安安举牌与审判选项均支持中文和 Unicode emoji 混排，例如：

```text
/安安说 我喜欢你🐖 开心
/安安说 🐖❤️👍🏻\n🇨🇳👨‍👩‍👧‍👦1️⃣
【赞同】我喜欢你🐖
【疑问】今天【开心🥰】
```

emoji 固定使用 Google Noto 2D 彩色图像，生成后的图片在手机和电脑显示一致。
中文字体沿用原素材；纯文字仍走原来的 sketchbook 渲染路径。
带 emoji 的文字由 Pillow 进行字形测量、自动缩放、换行、基线对齐和透明图片混排，
高亮只改变文字颜色，emoji 保留原来的彩色外观。安安混排最大字号为 60 像素。
ZWJ 家庭、肤色、国旗和键帽按完整字素处理，未收录组合显示 `[表情]`。

- 内置 4004 张图片，4012 个序列映射（含别名），运行时不请求 CDN 或其他网络服务。
- 素材固定于 `googlefonts/noto-emoji` 提交 `e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e`。
- 使用 `2D/png/128`；地区旗帜从同提交的 waved SVG 预先转换为 PNG。
- 图片及旗帜来源说明、许可、逐文件 SHA-256 和映射在 `assets/noto_emoji/`。
- 构建前核对素材清单和哈希，避免发布包丢失 emoji 文件。
- 本次支持 Unicode emoji；QQ 专属 `face` 消息段和收藏贴纸不是这套素材，未新增支持。

重新导入素材时，在开发环境额外安装 `resvg-py==0.5.0`，再运行：

```powershell
python tools/vendor_noto.py <上述提交的本地Noto源码目录>
```

该工具只用于构建素材，不是运行依赖。发布包已包含转换好的图片。
