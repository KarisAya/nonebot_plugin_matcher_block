from nonebot.plugin.on import on_command
from nonebot.matcher import Matcher
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
from nonebot import get_plugin_config
from typing import Set
from pydantic import BaseModel
from pathlib import Path
import re
import random
try:
    import ujson as json
except ModuleNotFoundError:
    import json
    

class ConfigModel(BaseModel):
    nickname: Set[str]
    '''配置昵称'''
    command_start: Set[str] # = set()
    '''配置指令前缀'''
    block_prod: bool = False
    '''测试用 生产环境可改为 True'''
    block_match_start: bool = True
    '''默认阻断范围包括设置的指令前缀'''

config = get_plugin_config(ConfigModel)

nickname = next(iter(config.nickname)) if config.nickname else "本茶茶"
start = r'^\s*(' + '|'.join(re.escape(prefix) for prefix in sorted(config.command_start, key=len, reverse=True) if prefix) + r')\s*'

async def formatted_msg(msg: str) -> str:
    msg = msg.strip()
    if config.block_match_start:
        msg = re.sub(start, '', msg, count=1)
    return msg.strip()

# 加载阻断配置
path = Path() / "data" / "block"
if not path.exists():
    Path(path).mkdir(parents=True, exist_ok=True)
    # os.makedirs(path)

def load(file:Path) -> dict:
    if file.exists():
        with open(file, "r", encoding="utf8") as f:
            return json.load(f)
    return {}

# 单群屏蔽
group_config_file = path / "group_config.json"
group_config = load(group_config_file)

global_group_config = group_config.get("global",[])

# 用户冷却
time_config_file = path / "time_config.json"
time_config = load(time_config_file)

global_time_config = time_config.get("global",{})

# 群内共享冷却
share_config_file = path / "share_config.json"
share_config = load(share_config_file)

global_share_config = share_config.get("global",{})


async def is_block_group(event:GroupMessageEvent) -> bool:
    """
    规则：群内屏蔽指令
    """
    msg = await formatted_msg(event.message.extract_plain_text())
    commands = group_config.setdefault(str(event.group_id),global_group_config.copy())
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            return True
        elif msg.startswith(command):
            return True
    else:
        return False


cache = {} # CD

async def is_block_time(event:GroupMessageEvent) -> bool:
    """
    规则：不同用户冷却
    """
    global cache
    msg = await formatted_msg(event.message.extract_plain_text())
    group_id = str(event.group_id)
    commands = time_config.setdefault(group_id,global_time_config.copy())
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
    user_count = f'{command}_count'
    
    if cd > commands[command]:
        usercache[command] = event.time
        usercache.pop(user_count, None)
        return False
    else:
        usercache[user_count] = usercache.get(user_count, 0) + 1
        msg = (msg[:5] + '...') if len(msg) > 5 else msg
        penalty_cd, new_msg = await personalized_reply(
            usercache[user_count], f"【{msg}】", int(commands[command] - cd) + 1, False)
        if penalty_cd != 0:
            usercache[command] += penalty_cd
        return new_msg
    
        # return f"你的【{msg}】冷却还有{int(commands[command] - cd) + 1}秒"


async def is_block_share(event:GroupMessageEvent) -> bool:
    """
    规则：群内共享冷却
    """
    global cache
    msg = await formatted_msg(event.message.extract_plain_text())
    group_id = str(event.group_id)
    commands = share_config.setdefault(group_id,global_share_config.copy())
    for command in commands:
        if command.startswith("^") and re.match(re.compile(command),msg):
            break
        elif msg.startswith(command):
            break
    else:
        return False
    
    sharecache = cache.setdefault(group_id, {}).setdefault("share", {})
    cd = event.time - sharecache.get(command, 0)
    user_id = event.user_id
    user_cd = f'{command}_cd'
    user_count = f'{command}_count'
    cd -= sharecache.get(user_id, {}).get(user_cd, 0)
    
    if cd > commands[command]:
        sharecache[command] = event.time
        sharecache.pop(user_id, None)
        return False
    else:
        user_data = sharecache.setdefault(user_id, {user_cd: 0, user_count: 0})
        user_data[user_count] += 1
        msg = (msg[:5] + '...') if len(msg) > 5 else msg
        penalty_cd, new_msg = await personalized_reply(
            sharecache[user_id][user_count], f"【{msg}】", int(commands[command] - cd) + 1, True)
        if penalty_cd != 0:
            user_data[user_cd] += penalty_cd
        return new_msg
    
        # return f"本群【{msg}】冷却还有{int(commands[command] - cd) + 1}秒"


from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException

async def personalized_reply(count: int, msg: str, cd: int, share=False):
    """ 
    个性化CD回复与刷屏罚时功能
    如果是群内共享冷却则单独为刷屏用户添加罚时(全局)
    """
    global nickname
    base_msg = f"{'本群' if share else '你的'}{msg}冷却还有{cd}秒~"
    responses = {
        8: (0,  f"好烦，{nickname}不理你了！"),
        7: (60, f"呜——你冷却 {cd + 60} 秒（罚时+60）~"),
        6: (30, f"啊拉，难道你还想要吗？{msg}冷却罚时 {cd + 30} 秒（罚时+30）~"),
        5: (30, f"你好吵...{nickname}帮你冷静一下。{msg}冷却罚时 {cd + 30} 秒（罚时+30）~"),
        4: (0,  f"再问{nickname}要闹了！{msg}还有{cd}秒~"),
        3: (0,  f"诶？怎么肥四（盯...{msg}还有{cd}秒~"),
        2: (0,  f"嘛，还要{nickname}帮你数...{msg}还有{cd}秒~"),
        1: (0,  base_msg)
    }
    if count in responses:
        return responses[count]
    if random.randint(1, 9) == 5:
        return (0, "哼！")
    raise IgnoredException("指令冷却时刷屏超限，不予回应")


@event_preprocessor
async def do_something(bot:Bot, event:GroupMessageEvent , permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER):
    if await permission(bot,event) and config.block_prod:
        logger.info("已为规则制定者忽略冷却判定")
        return
    if await is_block_group(event):
        raise IgnoredException("本群已经屏蔽该指令啦")
    elif echo := await is_block_share(event):
        await bot.send(event = event, message = echo)
        raise IgnoredException("本群的指令正在冷却喔")
    elif echo := await is_block_time(event):
        await bot.send(event = event, message = echo)
        raise IgnoredException("该用户指令还在冷却嗷")

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
    if await SUPERUSER(bot,event) and {"全局"} & args:
        group_id = "global"
    else:
        group_id = str(event.group_id)
    args.discard("全局")
    echo = "添加阻断指令格式错误。"
    if {"群","屏蔽"} & args:
        global group_config,group_config_file
        commands = group_config.setdefault(group_id,global_group_config.copy())
        if command not in commands:
            commands.append(command)
        if group_id == "global":
            group_config = {k:list(set(v.append(command))) for k,v in group_config.items()}
        with open(group_config_file, "w", encoding="utf8") as f:
            json.dump(group_config, f, ensure_ascii=False, indent=4)
        echo = f"指令【{command}】已在{'全局' if group_id == 'global' else f'群{group_id}'}屏蔽。"
        logger.info(echo)
    else:
        def set_config(data,file):
            commands = data.setdefault(group_id,data.get("global",{}).copy())
            commands[command] = cd
            if group_id == "global":
                for v in data.values():
                    v[command] = cd
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
