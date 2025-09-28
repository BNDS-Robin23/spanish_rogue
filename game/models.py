"""
游戏数据模型定义

这个模块包含了游戏中使用的所有数据类，包括：
- 游戏状态
- 玩家信息
- Boss信息
- 卡牌类型
- 题目信息
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GameState:
    """
    游戏状态类，包含整个游戏的状态信息
    """
    player: Player
    boss: Boss
    major_round: int  # 大回合数
    subround: int     # 子回合数
    question: Question
    verb_pool: List[str]  # 动词池
    
    def next_subround(self) -> None:
        """进入下一子回合"""
        self.subround += 1


@dataclass
class Player:
    """
    玩家类，包含玩家的所有信息
    """
    hp: int = 20                    # 生命值
    coins: int = 0                  # 金币数量
    skills: List[SkillCard] = None  # 技能列表
    hand_verbs: List[VerbCard] = None      # 手牌动词
    hand_rules: List[RuleCard] = None      # 手牌变化规则
    base_hand_verbs: int = 3        # 基础手牌动词数量
    base_hand_rules: int = 3        # 基础手牌变化卡数量
    
    def __post_init__(self):
        """初始化后处理，确保列表不为None"""
        if self.skills is None:
            self.skills = []
        if self.hand_verbs is None:
            self.hand_verbs = []
        if self.hand_rules is None:
            self.hand_rules = []


@dataclass
class Boss:
    """
    Boss类，包含Boss的信息
    """
    name: str                       # Boss名称
    hp: int                         # 生命值
    base_hp_per_subround: int       # 每子回合基础生命值


@dataclass
class Question:
    """
    题目类，包含当前题目信息
    """
    person: str  # 人称（如"直陈式现在时+第一人称单数"）


@dataclass
class VerbCard:
    """
    动词卡类，代表一张动词卡
    """
    infinitive: str  # 动词原形


@dataclass
class RuleCard:
    """
    变化规则卡类，代表一张变化规则卡
    """
    person: str                           # 人称
    stem_from: Optional[str] = None       # 词干变化前
    stem_to: Optional[str] = None         # 词干变化后
    ending_from: Optional[str] = None     # 词尾变化前
    ending_to: Optional[str] = None       # 词尾变化后
    verb_infinitive: Optional[str] = None # 特定动词（如果只适用于某个动词）
    
    @property
    def pattern(self) -> str:
        """
        获取变化模式的字符串表示
        """
        parts = []
        if self.stem_from is not None or self.stem_to is not None:
            parts.append(f"{self.stem_from or ''}->{self.stem_to or ''}")
        if self.ending_from is not None or self.ending_to is not None:
            parts.append(f"{self.ending_from or ''}->{self.ending_to or ''}")
        return " + ".join(parts)


@dataclass
class SkillCard:
    """
    技能卡类，代表玩家的技能
    """
    name: str                                    # 技能名称
    description: str                             # 技能描述
    cost: int                                    # 技能成本
    triple_damage_on_directional: bool = False   # 方向加成效果
    retain_on_play_50: bool = False             # 50%保留效果


