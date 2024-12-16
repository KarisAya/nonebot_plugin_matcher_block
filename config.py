from pydantic import BaseModel


class Config(BaseModel):
    block_match_start: bool = True
    """默认阻断范围包括设置的指令前缀"""
    personalized_replylist: list[str] = [
        "0 嘛，还要{bot}帮你数...{msg}还有{cd}秒~",
        "0 诶？怎么肥四（盯...{msg}还有{cd}秒~",
        "0 再问{bot}要闹了！{msg}还有{cd}秒~",
        "30 你好吵...{bot}帮你冷静一下。{msg}冷却罚时 {cd} 秒（罚时+30）~",
        "30 啊拉，难道你还想要吗？{msg}冷却罚时 {cd} 秒（罚时+30）~",
        "60 呜——你冷却60秒（罚时+60）~",
        "0 好烦，{bot}不理你了！",
    ]
