from nonebot.plugin.on import on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    GroupMessageEvent,
    Message,
    )
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.log import logger

from pathlib import Path
import os
import re

try:
    import ujson as json
except ModuleNotFoundError:
    import json

# 加载阻断配置
path = Path() / "data" / "block"
if not path.exists():
    os.makedirs(path)

def load(file:Path) -> dict:
    if file.exists():
        with open(file, "r", encoding="utf8") as f:
            return json.load(f)
    return {}

# 屏蔽
group_config_file = path / "group_config.json"
group_config = load(group_config_file)

# 冷却
time_config_file = path / "time_config.json"
time_config = load(time_config_file)

# 共享
share_config_file = path / "share_config.json"
share_config = load(share_config_file)


def is_block_group(event:GroupMessageEvent) -> bool:
    """
    规则：屏蔽
    """
    msg = event.message.extract_plain_text().strip()
    global_group_config = group_config.get("global",[]) 
    commands = group_config.setdefault(str(event.group_id),global_group_config)
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            return True
        elif msg.startswith(command):
            return True
    else:
        return False

cache = {}

def is_block_time(event:GroupMessageEvent) -> bool:
    """
    规则：冷却
    """
    msg = event.message.extract_plain_text().strip()
    group_id = str(event.group_id)
    global_time_config = time_config.get("global",{})
    commands = time_config.setdefault(group_id,global_time_config)
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            break
        elif msg.startswith(command):
            break
    else:
        return False

    user_id = event.user_id
    usercache = cache.setdefault(group_id, {}).setdefault(user_id, {})
    cd = event.time - usercache.get(command, 0)
    if cd > commands[command]:
        usercache[command] = event.time
        return False
    else:
        return f"你的【{msg}】冷却还有{int(commands[command] - cd) + 1}秒"

def is_block_share(event:GroupMessageEvent) -> bool:
    """
    规则：共享冷却
    """
    msg = event.message.extract_plain_text().strip()
    group_id = str(event.group_id)
    global_share_config = share_config.get("global",{})
    commands = share_config.setdefault(group_id,global_share_config)
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            break
        elif msg.startswith(command):
            break
    else:
        return False
    sharecache = cache.setdefault(group_id, {}).setdefault("share", {})
    cd = event.time - sharecache.get(command, 0)
    if cd > commands[command]:
        sharecache[command] = event.time
        return False
    else:
        return f"本群【{msg}】冷却还有{int(commands[command] - cd) + 1}秒"

from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

@event_preprocessor
async def do_something(bot:Bot, event:GroupMessageEvent , permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER):
    if not await permission(bot,event):
        if is_block_group(event):
            raise IgnoredException("本群已屏蔽此指令")
        elif echo := is_block_share(event):
            await bot.send(event = event, message = echo)
            raise IgnoredException("本群指令正在冷却")
        elif echo := is_block_time(event):
            await bot.send(event = event, message = echo)
            raise IgnoredException("用户指令正在冷却")

add_block = on_command("添加阻断",aliases = {"设置阻断"}, permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@add_block.handle()
async def _(bot:Bot,event:GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if not msg:
        return
    command = msg[0]
    if command in {"添加阻断","设置阻断","解除阻断","删除阻断"}:
        await add_block.finish("不可以这么做")
    args = set(msg[1:])
    if await SUPERUSER(bot,event) and (global_type := {"全局"} & args):
        args = args - global_type
        group_id = "global"
    else:
        group_id = str(event.group_id)

    echo = "添加阻断指令格式错误。"
    if {"群","屏蔽"} & args:
        global group_config,group_config_file
        tmp = group_config.setdefault(group_id,[])
        if command not in tmp:
            tmp.append(command)
        if group_id == "global":
            group_config = {k:list(set(v)|set(group_config["global"])) for k,v in group_config.items()}
        with open(group_config_file, "w", encoding="utf8") as f:
            json.dump(group_config, f, ensure_ascii=False, indent=4)
        echo = f"指令【{command}】已在{'全局' if group_id == 'global' else group_id}屏蔽。"
        logger.info(echo)
    else:
        def set_config(data,file):
            data.setdefault(group_id,{})[command] = cd
            if group_id == "global":
                for v in data.values():
                    v.update(data["global"])
            with open(file, "w", encoding="utf8") as f:
                json.dump(data, f, ensure_ascii = False, indent = 4)

        if block_type := {"时间","冷却"} & args:
            args = args - block_type
            cd = args.pop()
            try:
                cd = int(cd)
            except:
                echo = f"添加阻断接受了错误的时间参数：{cd}"
                logger.warning(echo)
            global time_config,time_config_file
            set_config(time_config,time_config_file)
            echo = f"指令【{command}】已在{'全局' if group_id == 'global' else group_id}设置冷却：{cd}s"
            logger.info(echo)
        elif block_type := {"共享","共享冷却"} & args:
            args = args - block_type
            cd = args.pop()
            try:
                cd = int(cd)
            except:
                echo = f"添加阻断接受了错误的时间参数：{cd}"
                logger.warning(echo)
            global share_config,share_config_file
            set_config(share_config,share_config_file)
            echo = f"指令【{command}】已在{'全局' if group_id == 'global' else group_id}设置共享冷却：{cd}s"
            logger.info(echo)

    await add_block.finish(echo)


del_block = on_command("解除阻断",aliases={"删除阻断"}, permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@del_block.handle()
async def _(bot:Bot,event:GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if not msg:
        return
    command = msg[0]
    args = set(msg[1:])
    if await SUPERUSER(bot,event) and {"全局"} & args:
        group_id = "global"
    else:
        group_id = str(event.group_id)
    echo = []
    global group_config,group_config_file,share_config,share_config_file,time_config,time_config_file
    if group_id in group_config and command in group_config[group_id]:
        group_config[group_id].remove(command)
        if group_id == "global":
            group_config = {k:[x for x in v if x != command] for k,v in group_config.items()}
        with open(group_config_file, "w", encoding="utf8") as f:
            json.dump(group_config, f, ensure_ascii=False, indent=4)
        echo.append(f"指令【{command}】已解除屏蔽")


    if group_id in share_config and command in share_config[group_id]:
        del share_config[group_id][command]
        if group_id == "global":
            share_config = {k:{vk:vv for vk,vv in v.items() if vk != command} for k,v in share_config.items()}
        with open(share_config_file, "w", encoding="utf8") as f:
            json.dump(share_config, f, ensure_ascii=False, indent=4)
        echo.append(f"指令【{command}】已解除共享冷却限制")


    if group_id in time_config and command in time_config[group_id]:
        del time_config[group_id][command]
        if group_id == "global":
            time_config = {k:{vk:vv for vk,vv in v.items() if vk != command} for k,v in time_config.items()}
        with open(time_config_file, "w", encoding="utf8") as f:
            json.dump(time_config, f, ensure_ascii=False, indent=4)
        echo.append(f"指令【{command}】已解除冷却限制")
    await del_block.finish("\n".join(echo) if echo else f"指令【{command}】未被阻断")

show_block = on_command("查看阻断", permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@show_block.handle()
async def _(matcher: Matcher, event:GroupMessageEvent):
    group_id = str(event.group_id)
    msg = ""
    if group_id in group_config:
        msg += "".join(f"【{command}】：屏蔽\n" for command in group_config[group_id])
    if group_id in time_config:
        msg += "".join(f"【{command}】：{cd}s\n" for command,cd in time_config[group_id].items())
    if group_id in share_config:
        msg += "".join(f"【{command}】：共享{cd}s\n" for command,cd in share_config[group_id].items())
    msg = msg[:-1] if msg else "本群没有阻断。"
    await show_block.finish(msg)

from nonebot import get_driver

driver = get_driver()
bots = driver.bots

history = []

@event_preprocessor
async def do_something(event: GroupMessageEvent):
    if len(bots) > 1:
        if event.user_id in bots:
            raise IgnoredException("event来自其他bot")
        global history
        history = history[:20]
        message_id = event.message_id
        if message_id in history:
            raise IgnoredException("event已被其他bot处理")
        else:
            history.insert(0, message_id)