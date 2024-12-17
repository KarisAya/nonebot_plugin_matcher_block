<div align="center">

<a href="https://v2.nonebot.dev/store">
  <img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo">
</a>

<p>
  <img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText">
</p>

# nonebot-plugin-matcher-block

通用指令阻断

<img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="python">
<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/KarisAya/nonebot_plugin_matcher_block.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot_plugin_matcher_block">
  <img src="https://img.shields.io/pypi/v/nonebot_plugin_matcher_block.svg" alt="pypi">
</a>
<a href="https://pypi.python.org/pypi/nonebot_plugin_matcher_block">
  <img src="https://img.shields.io/pypi/dm/nonebot_plugin_matcher_block" alt="pypi download">
</a>

</div>

# 安装

推荐使用 nb-cli 安装

在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install nonebot_plugin_groupmate_waifu
```

# 功能

## 添加阻断

`添加阻断 指令 参数`

**参数列表：**

`屏蔽` `冷却` `共享冷却` `全局`

**指令解析：**

使用 `添加阻断 今日运势 屏蔽` 后，`今日运势` 在本群内被屏蔽

使用 `添加阻断 娶群友 冷却 120` 后，本群内成员各自的 `娶群友` 将会有 120 秒冷却

[~~插件广告：娶群友~~](https://github.com/KarisAya/nonebot_plugin_groupmate_waifu)

使用 `添加阻断 点歌 共享冷却 120` 后，本群内成员共享 `点歌` 的冷却时间

_注意:以上三个参数只生效 1 个。可以把某一指令设置多种阻断类型，也就是即屏蔽，又冷却，也共享冷却。~~但是这样做没有什么必要~~_

使用 `添加阻断 金币签到 冷却 120 全局` 后，在全局为 `金币签到` 设置 120 秒 CD

**使用正则匹配：**

如果指令以"^"开头，那么通用指令阻断将会认为本指令是一条正则匹配。

例如使用指令 `添加阻断 ^来.*张.+$ 冷却 300` 为 `来张xx色图` 添加阻断，

那么本条配置将会阻断诸如 `来张色图` `来三张白丝` 等 可以用 ^来.\*张.+$ 匹配到的字符串。

[~~插件广告：我要一张 xx 涩图~~](https://github.com/KarisAya/nonebot_plugin_setu_collection)

## 解除阻断

`解除阻断 指令`

在本群取消阻断该指令，如果此指令设置过多种阻断方式会全部解除。

`解除阻断 指令 全局`

在全局取消阻断该指令，如果此指令未设置过全局指令则会解除失败。

**注意:即使你在所有的群都阻断了某一指令，这个指令的阻断也不是全局阻断，无法用全局参数为所有的群解除阻断。**

## 查看阻断

`查看阻断`

查看本群被阻断的指令。

# 可选配置和功能：

```env

    block_match_start: bool = True
    personalized_replylist = [
        "0 嘛，还要{bot}帮你数...{msg}还有{cd}秒~",
        "0 诶？盯...你的 {msg} 指令冷却还有{cd}秒~",
        "0 再问{bot}要闹了！{msg} 还有{cd}秒~",
        "30 你好吵...{bot}帮你冷静一下。你的 {msg} 冷却罚时 {cd} 秒（罚时+30）~",
        "30 啊拉，难道你还想要吗？{msg} 冷却罚时 {cd} 秒（罚时+30）~",
        "60 呜——你冷却60秒（罚时+60）~",
        "0 好烦，{bot}不理你了！",
    ]

```

以上配置需要填写在 nonebot 的配置中

`block_match_start` 自动剔除你设置的 Bot 指令前缀（COMMAND_START）

此项值为 false，则不同指令前缀视为不同指令：

例如使用指令 `添加阻断 透群友 群` 在本群屏蔽了 `透群友` 指令。

但如果指令还可以用 `\透群友` 触发，那么 `\透群友` 事件并不会被屏蔽。

如你希望仅使用 `添加阻断 本群cp 屏蔽` 即可同时屏蔽 `\本群cp` `#本群cp` ...，请在你的.env 将此项值配置为 true。

`personalized_replylist` 冷却期内的个性化回复列表及多次刷屏罚时

列表中每行都是字符串，但是开头为数字与空格，数字代表触发此回复后给用户此指令增加的罚时。

列表是有序的，多次刷屏用户看到的回复是从上到下依次的。

字符串带有格式化标签，支持 `{bot}` Bot 名称，`{msg}` 被屏蔽的指令，`{cd}` 剩余冷却时间。

# 其他

如有建议，bug 反馈，以及讨论新玩法，新机制（或者单纯没有明白怎么用）可以来加群哦~

![群号](https://raw.githubusercontent.com/clovers-project/clovers/refs/heads/master/%E9%99%84%E4%BB%B6/qrcode_1676538742221.jpg)
