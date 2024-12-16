from collections import Counter
import random
import time
import json


from nonebot.plugin.on import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    GroupMessageEvent,
    Message,
)
from nonebot.permission import SUPERUSER
from nonebot.log import logger
from nonebot import get_driver, get_plugin_config
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException


from . import config as cfg
from .core import Manager as BaseManager

driver = get_driver()
nickname = driver.config.nickname
command_start = driver.config.command_start
config = get_plugin_config(cfg.Config)

type GroupID = int
type UserID = int


class Manager(BaseManager[GroupID, UserID]):
    """阻断管理实例"""

    def __init__(self):
        super().__init__()
        self.naughtylist: dict[GroupID, Counter[UserID]] = {}
        """淘气鬼名单: {用户:刷屏次数}"""
        self.brig: dict[UserID, float] = {}
        """小黑屋: {用户:解除时间}"""

        if nickname:
            self.Bot_Nickname = property(lambda self: random.choice(nickname))
        else:
            self.Bot_Nickname = "【指令阻断bot】"

        if command_start and config.block_match_start:

            def get_plaintext(msg: str):
                for start in command_start:
                    if msg.startswith(start):
                        return msg.lstrip(start)
                # 如果配置了指令前缀并且不存在指令前缀为空字符时还没有匹配到指令
                # 则说明这条指令不会触发 on_command 响应器
                # 但并不排除这是一条 on_message 指令
                return msg

            self.get_plaintext = staticmethod(get_plaintext)

        personalized_replylist = config.personalized_replylist
        self.personalized_replylist = [(int(t), reply) for t, reply in map(lambda x: x.split(" ", 1), personalized_replylist)]

    async def act(self, bot: Bot, event: GroupMessageEvent, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER):
        if await permission(bot, event):
            return
        group_id = event.group_id
        user_id = event.user_id
        message = event.get_plaintext()
        info = self.check(message, group_id, user_id)
        if not info:
            return
        checkpoint = info["checkpoint"]
        if checkpoint == "block":
            raise IgnoredException("block")
        count = self.naughtylist[group_id][user_id]
        msg = message if len(message) < 7 else message[:4] + "..."
        cd = int(info["cd"] - time.time() + 1)
        if checkpoint == "cooldown":
            self.naughtylist.setdefault(group_id, Counter())[user_id] += 1
            if count == 1:
                await bot.send(event=event, message=f"你的{msg}冷却还有{cd}秒~")
            elif count > len(self.personalized_replylist):
                if random.randint(1, 9) == 5:
                    await bot.send(event=event, message="哼！")
            else:
                t, resp = self.personalized_replylist[count]
                self.cooldown_rec[group_id][info["cmd"]][user_id] + t
                await bot.send(event=event, message=resp.format(bot=self.Bot_Nickname, msg=msg, cd=cd + t))
        else:
            await bot.send(event=event, message=f"本群{msg}冷却还有{cd}秒~")
        raise IgnoredException(checkpoint)


manager = Manager()

event_preprocessor(manager.act)


add_block = on_command("添加阻断", aliases={"设置阻断"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5, block=True)


@add_block.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if not msg:
        return
    command = msg[0]
    if command in {"添加阻断", "设置阻断", "解除阻断", "删除阻断"}:
        await add_block.finish("不可以这么做")
    args = set(msg[1:])
    if command.startswith("^"):
        regex = True
        command = command[1:]
    else:
        regex = False
    if await SUPERUSER(bot, event) and "全局" in args:
        group_id = None
    else:
        group_id = event.group_id
    args.discard("全局")
    if {"群", "屏蔽"} & args:
        manager.add_block(command, group_id, regex)
        echo = f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}屏蔽。"
        logger.success(echo)
    elif block_type := {"时间", "冷却"} & args:
        args = args - block_type
        cd = args.pop()
        try:
            cd = int(cd)
        except:
            echo = f"添加阻断接受了错误的时间参数：{cd}"
            logger.warning(echo)
        manager.add_cooldown(command, cd, group_id, regex)
        echo = f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}设置冷却：{cd}s"
        logger.success(echo)
    elif block_type := {"共享", "共享冷却"} & args:
        args = args - block_type
        cd = args.pop()
        try:
            cd = int(cd)
        except:
            echo = f"添加阻断接受了错误的时间参数：{cd}"
            logger.warning(echo)
        manager.add_shared_cooldown(command, cd, group_id, regex)
        echo = f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}设置共享冷却：{cd}s"
        logger.success(echo)

    await add_block.finish(echo)


del_block = on_command("解除阻断", aliases={"删除阻断"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5, block=True)


@del_block.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if not msg:
        return
    command = msg[0]
    args = set(msg[1:])
    if command.startswith("^"):
        regex = True
        command = command[1:]
    else:
        regex = False
    if await SUPERUSER(bot, event) and "全局" in args:
        group_id = None
    else:
        group_id = event.group_id
    echo = []
    try:
        manager.del_block(command, group_id, regex)
        echo.append(f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}已解除屏蔽")
    except KeyError:
        pass
    try:
        manager.del_cooldown(command, group_id, regex)
        echo.append(f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}已解除冷却")
    except KeyError:
        pass
    try:
        manager.del_shared_cooldown(command, group_id, regex)
        echo.append(f"指令【{command}】已在{f'群{group_id}' if group_id else '全局'}已解除共享冷却")
    except KeyError:
        pass
    await del_block.finish("\n".join(echo) if echo else f"指令【{command}】未被阻断")


show_block = on_command("查看阻断", permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5, block=True)


@show_block.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    if group_id not in manager.config_data.configs:
        msg = "本群没有阻断配置。"
    else:
        group_config = manager.config_data.configs[group_id]
        msg = f"本群阻断配置：\n"
        msg += "".join(f"【{command}】：屏蔽\n" for command in group_config.block)
        msg += "".join(f"【{command}】：屏蔽（正则）\n" for command in group_config.block_regex)
        msg += "".join(f"【{command}】：{cd}秒冷却\n" for command, cd in group_config.cooldown.items())
        msg += "".join(f"【{command}】：{cd}秒冷却（正则）\n" for command, cd in group_config.cooldown_regex.items())
        msg += "".join(f"【{command}】：{cd}秒共享冷却\n" for command, cd in group_config.shared_cooldown.items())
        msg += "".join(f"【{command}】：{cd}秒共享冷却（正则）\n" for command, cd in group_config.shared_cooldown_regex.items())
    await show_block.finish(msg)
