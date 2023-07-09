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

from pathlib import Path

import time
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

time_config_file = path / "time_config.json"

if time_config_file.exists():
    with open(time_config_file, "r", encoding="utf8") as f:
        time_config = json.load(f)
else:
    time_config = {}

group_config_file = path / "group_config.json"

if group_config_file.exists():
    with open(group_config_file, "r", encoding="utf8") as f:
        group_config = json.load(f)
else:
    group_config = {}

def is_block_group(event:GroupMessageEvent) -> bool:
    msg = event.message.extract_plain_text().strip()
    group_id = str(event.group_id)
    if group_id not in group_config:
        return False
    commands = group_config[group_id]
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            return True
        elif msg.startswith(command):
            return True
    else:
        return False

cache = {}

def is_block_time(event:GroupMessageEvent) -> bool:
    msg = event.message.extract_plain_text().strip()
    group_id = str(event.group_id)
    if group_id not in time_config:
        return False
    commands = time_config[group_id]
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            break
        elif msg.startswith(command):
            break
    else:
        return False

    user_id = event.user_id
    usercache = cache.setdefault(group_id, {}).setdefault(user_id, {})
    cd = time.time() - usercache.get(command, 0)
    if cd > commands[command]:
        usercache[command] = time.time()
        return False
    else:
        return f"你的【{msg}】冷却还有{int(commands[command] - cd) + 1}秒"

from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

@event_preprocessor
async def do_something(bot:Bot, event:GroupMessageEvent , permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER):
    if not await permission(bot,event):
        if is_block_group(event):
            raise IgnoredException("本群已屏蔽此指令")
        elif echo := is_block_time(event):
            await bot.send(event = event, message = echo)
            raise IgnoredException("用户指令正在冷却")

add_block = on_command("添加阻断", permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@add_block.handle()
async def _(event:GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg and len(msg) >= 2:
        group_id = str(event.group_id)
        command = msg[0]
        if command in {"添加阻断","解除阻断","删除阻断"}:
            await add_block.finish("不可以这么做")
        block_type = msg[1]
        if len(msg) == 3 and block_type in {"时间","冷却"}:
            try:
                cd = int(msg[2])
            except:
                await add_block.finish(f"添加阻断接受了错误的时间参数：{msg[2]}")
            time_config.setdefault(group_id,{})[command] = cd
            with open(time_config_file, "w", encoding="utf8") as f:
                json.dump(time_config, f, ensure_ascii=False, indent=4)
            await add_block.finish(f"指令【{command}】已设置冷却：{cd}s")

        elif block_type == "群":
            tmp = group_config.setdefault(group_id,[])
            if command not in tmp:
                tmp.append(command)
                with open(group_config_file, "w", encoding="utf8") as f:
                    json.dump(group_config, f, ensure_ascii=False, indent=4)
            await add_block.finish(f"指令【{command}】已在本群屏蔽。")

    await add_block.finish("添加阻断指令格式错误。")


del_block = on_command("解除阻断",aliases={"删除阻断"}, permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@del_block.handle()
async def _(matcher: Matcher, event:GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().split()
    if msg and len(msg) == 2:
        group_id = str(event.group_id)
        command = msg[0]
        block_type = msg[1]
        if block_type in {"时间","冷却"}:
            if group_id in time_config and command in time_config[group_id]:
                del time_config[group_id][command]
                with open(time_config_file, "w", encoding="utf8") as f:
                    json.dump(time_config, f, ensure_ascii=False, indent=4)
                await del_block.finish(f"指令【{command}】已解除冷却限制。")
            else:
                await del_block.finish(f"指令【{command}】没有设置冷却。")
        if block_type == "群":
            if group_id in group_config and command in group_config[group_id]:
                group_config[group_id].remove(command)
                with open(group_config_file, "w", encoding="utf8") as f:
                    json.dump(group_config, f, ensure_ascii=False, indent=4)
                await del_block.finish(f"指令【{command}】已解除屏蔽。")
            else:
                await del_block.finish(f"指令【{command}】未屏蔽。")

    await del_block.finish("解除阻断指令格式错误。")

show_block = on_command("查看阻断", permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5, block = True)

@show_block.handle()
async def _(matcher: Matcher, event:GroupMessageEvent):
    group_id = str(event.group_id)
    msg = ""
    if group_id in group_config:
        msg += "".join([f"【{command}】：屏蔽\n" for command in group_config[group_id]])
    if group_id in time_config:
        msg += "".join([f"【{command}】：{cd}s\n" for command,cd in time_config[group_id].items()])
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