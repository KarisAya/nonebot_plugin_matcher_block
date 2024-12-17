from pydantic import BaseModel
import re
import time
from pathlib import Path


class BlockConfig(BaseModel):
    """
    指令阻断配置
    """

    block: set[str] = set()
    """指令屏蔽 {指令}"""
    block_regex: set[str] = set()
    """正则指令屏蔽 {指令}"""
    cooldown: dict[str, int] = {}
    """指令冷却 {指令:冷却时间}"""
    cooldown_regex: dict[str, int] = {}
    """正则指令冷却 {指令:冷却时间}"""
    shared_cooldown: dict[str, int] = {}
    """群共用指令冷却 {指令:冷却时间}"""
    shared_cooldown_regex: dict[str, int] = {}
    """群共用正则指令冷却 {指令:冷却时间}"""

    @property
    def block_data(self) -> tuple[set[str], set[str]]:
        return self.block, self.block_regex

    @property
    def cooldown_data(self) -> tuple[dict[str, int], dict[str, int]]:
        return self.cooldown, self.cooldown_regex

    @property
    def shared_cooldown_data(self) -> tuple[dict[str, int], dict[str, int]]:
        return self.shared_cooldown, self.shared_cooldown_regex


class ConfigData[GroupID](BaseModel):
    """
    指令配置数据
    """

    configs: dict[GroupID, BlockConfig]
    """群配置 {群号:配置}"""
    global_config: BlockConfig
    """全局配置"""

    @classmethod
    def load(cls, data_path: str):
        path = Path(data_path)
        if path.exists():
            with open(path, "r", encoding="utf8") as f:
                return cls.model_validate_json(f.read())
        else:
            return cls(configs={}, global_config=BlockConfig())

    def save(self, data_path: str):
        with open(data_path, "w", encoding="utf8") as f:
            f.write(self.model_dump_json(indent=4))


class Manager[GroupID, UserID]():
    """阻断管理实例"""

    cooldown_rec: dict[GroupID, dict[str, dict[UserID, float]]]
    """指令冷却记录 {群号:{指令:{用户:解除冷却时间戳}}}"""
    shared_cooldown_rec: dict[GroupID, dict[str, float]]
    """群共用冷却记录 {群号:{指令:解除冷却时间戳}}"""

    config_path = "data/block.json"

    def __init__(self):
        self.config_data = ConfigData[GroupID].load(self.config_path)
        self.cooldown_rec = {}
        self.shared_cooldown_rec = {}

    def savedata(self):
        self.config_data.save(self.config_path)

    @staticmethod
    def is_cooldown_command(message: str, cooldown: dict[str, int], cooldown_regex: dict[str, int]) -> tuple[str, int] | None:
        if cooldown:
            for x in cooldown:
                if message.startswith(x):
                    return x, cooldown[x]
        if cooldown_regex:
            for x in cooldown_regex:
                if re.match(x, message):
                    return x, cooldown_regex[x]

    @staticmethod
    def check_block(message: str, block: set[str], block_regex: set[str]):
        info = {"checkpoint": "block"}
        if block:
            if any(message.startswith(x) for x in block):
                return info
        if block_regex:
            if any(re.match(x, message) for x in block):
                return info

    def check_cooldown(self, group_id: GroupID, user_id: UserID, command: str, cooldown: float):
        cmd_cd_rec = self.cooldown_rec.setdefault(group_id, {}).setdefault(command, {})
        now = time.time()
        if user_id in cmd_cd_rec:
            if now < cmd_cd_rec[user_id]:
                return {"checkpoint": "cooldown", "cd": cmd_cd_rec[user_id] - now, "cmd": command}
        cmd_cd_rec[user_id] = now + cooldown

    def check_shared_cooldown(self, group_id: GroupID, command: str, cooldown: float):
        cmd_cd_rec = self.shared_cooldown_rec.setdefault(group_id, {})
        now = time.time()
        if command in cmd_cd_rec:
            if now < cmd_cd_rec[command]:
                return {"checkpoint": "shared_cooldown", "cd": cmd_cd_rec[command] - now, "cmd": command}
        cmd_cd_rec[command] = now + cooldown

    def check(self, message: str, group_id: GroupID, user_id: UserID):
        """
        检查指令是否通过
            如果未通过，返回检查点信息
        """
        message = self.get_plaintext(message)
        global_config = self.config_data.global_config
        if group_id in self.config_data.configs:
            config = self.config_data.configs[group_id]
            if info := self.check_block(message, *config.block_data):
                return info
            if info := self.check_block(message, *global_config.block_data):
                return info
            if info := self.is_cooldown_command(message, *config.cooldown_data):
                return self.check_cooldown(group_id, user_id, *info)
            if info := self.is_cooldown_command(message, *global_config.cooldown_data):
                return self.check_cooldown(group_id, user_id, *info)
            if info := self.is_cooldown_command(message, *config.shared_cooldown_data):
                return self.check_shared_cooldown(group_id, *info)
            if info := self.is_cooldown_command(message, *global_config.shared_cooldown_data):
                return self.check_shared_cooldown(group_id, *info)
        else:
            if info := self.check_block(message, global_config.block, global_config.block_regex):
                return info
            if info := self.is_cooldown_command(message, *global_config.cooldown_data):
                return self.check_cooldown(group_id, user_id, *info)
            if info := self.is_cooldown_command(message, *global_config.shared_cooldown_data):
                return self.check_shared_cooldown(group_id, *info)

    @staticmethod
    def get_plaintext(message: str) -> str:
        return message

    def get_config(self, group_id: int | None = None):
        if group_id is None:
            config = self.config_data.global_config
        else:
            if group_id in self.config_data.configs:
                config = self.config_data.configs[group_id]
            else:
                config = self.config_data.configs[group_id] = BlockConfig()
        return config

    def add_block(self, command: str, group_id: int | None = None, regex: bool = False):
        """添加屏蔽词"""
        config = self.get_config(group_id)
        if regex:
            config.block_regex.add(command)
        else:
            config.block.add(command)

        self.savedata()

    def del_block(self, command: str, group_id: int | None = None, regex: bool = False):
        """删除屏蔽词"""
        config = self.get_config(group_id)
        if regex:
            config.block_regex.remove(command)
        else:
            config.block.remove(command)

        self.savedata()

    def add_cooldown(self, command: str, cd: int, group_id: int | None = None, regex: bool = False):
        """添加冷却词"""
        config = self.get_config(group_id)
        if regex:
            config.cooldown_regex[command] = cd
        else:
            config.cooldown[command] = cd
        self.savedata()

    def del_cooldown(self, command: str, group_id: int | None = None, regex: bool = False):
        """删除冷却词"""
        config = self.get_config(group_id)
        if regex:
            del config.cooldown_regex[command]
        else:
            del config.cooldown[command]

        self.savedata()

    def add_shared_cooldown(self, command: str, cd: int, group_id: int | None = None, regex: bool = False):
        """添加共享冷却词"""
        config = self.get_config(group_id)
        if regex:
            config.shared_cooldown_regex[command] = cd
        else:
            config.shared_cooldown[command] = cd
        self.savedata()

    def del_shared_cooldown(self, command: str, group_id: int | None = None, regex: bool = False):
        """删除共享冷却词"""
        config = self.get_config(group_id)
        if regex:
            del config.shared_cooldown_regex[command]
        else:
            del config.shared_cooldown[command]

        self.savedata()
