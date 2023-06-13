<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>
<div align="center">

# nonebot_plugin_matcher_block

通用指令阻断

</div>

## 安装

    pip install nonebot_plugin_matcher_block
	
## 使用

    nonebot.load_plugin('nonebot_plugin_matcher_block')
    
## 功能

`添加阻断 指令 群`

在本群屏蔽 `指令`

`添加阻断 指令 冷却 300`

在本群把 `指令` 设置成每个用户 300 秒冷却。

`解除阻断 指令 群`

在本群取消屏蔽该指令。

`解除阻断 指令 冷却`

在本群取消该指令的冷却。

`查看阻断`

查看本群被阻断的指令。

## 关于指令参数

### 不同指令前缀视为不同指令：

例如使用指令 `添加阻断 透群友 群` 在本群屏蔽了 `透群友` 指令。

但如果指令还可以用 `\透群友` 触发，那么 `\透群友` 事件并不会被屏蔽。

[~~插件广告：娶群友~~](https://github.com/KarisAya/nonebot_plugin_groupmate_waifu)


### 使用正则匹配：

如果指令以"^"开头，并以"$"结束，那么通用指令阻断将会认为本指令是一条正则匹配。

例如使用指令 `添加阻断 ^来.*张.+$ 冷却 300` 为 `来张xx色图` 添加阻断，

那么本条配置将会阻断诸如 `来张色图` `来三张白丝` 等 可以用 ^来.*张.+$ 匹配到的字符串。

[~~插件广告：我要一张xx涩图~~](https://github.com/KarisAya/nonebot_plugin_setu_collection)


## 其他


如有建议，bug反馈，以及讨论新玩法，新机制（或者单纯没有明白怎么用）可以来加群哦~

![群号](https://github.com/KarisAya/nonebot_plugin_game_collection/blob/master/%E9%99%84%E4%BB%B6/qrcode_1665028285876.jpg)
