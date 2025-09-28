"""
西班牙语Roguelike游戏核心逻辑模块

这个模块包含了游戏的主要逻辑，包括：
- 游戏状态管理
- 玩家和Boss交互
- 动词变位验证
- 商店系统
- 升级系统
"""

from __future__ import annotations
import random
import unicodedata
from typing import List, Tuple, Dict, Any

from .models import GameState, Player, Boss, Question, VerbCard, RuleCard, SkillCard
from .rules import present_indicative_rules, apply_rule_to_verb, random_question, expected_present_form
from .lexicon import VerbLexicon


def _normalize_form(s: str) -> str:
    """
    标准化字符串格式，用于比较动词变位
    
    Args:
        s: 需要标准化的字符串
        
    Returns:
        标准化后的字符串（NFC格式，去除首尾空格，转为小写）
    """
    if s is None:
        return ""
    return unicodedata.normalize("NFC", s).strip().casefold()


def start_new_game() -> GameState:
    """
    开始新游戏，初始化游戏状态
    
    Returns:
        初始化的游戏状态对象
    """
    # 不固定随机种子，允许真正的随机性
    lex = VerbLexicon()
    try:
        # 尝试加载动词词典
        lex.load()
        verb_pool = lex.list_infinitives()
        if not verb_pool:
            raise ValueError("empty lexicon")
    except Exception:
        # 如果加载失败，使用默认动词列表
        verb_pool = [
            "hablar", "comer", "vivir", "estudiar", "leer", "escribir",
            "amar", "beber", "abrir", "correr", "saltar", "cantar",
        ]
        lex = None  # type: ignore

    # 创建玩家和Boss
    player = Player()
    boss = Boss(name="初级Boss", hp=20, base_hp_per_subround=5)
    question = random_question()
    
    # 创建游戏状态
    state = GameState(player=player, boss=boss, major_round=1, subround=1, question=question, verb_pool=verb_pool)
    setattr(state, "lexicon", lex)
    
    # 刷新手牌
    refresh_hands(state)
    return state


def refresh_hands(state: GameState) -> None:
    """
    刷新玩家手牌，包括动词卡和变化卡
    
    Args:
        state: 当前游戏状态
    """
    player = state.player
    
    # 洗牌并选择动词卡
    pool_copy = list(state.verb_pool)
    random.shuffle(pool_copy)
    player.hand_verbs = [VerbCard(infinitive=pool_copy[i % len(pool_copy)]) for i in range(player.base_hand_verbs)]
    current_verbs = {v.infinitive for v in player.hand_verbs}

    # 获取变化卡规则
    lex = getattr(state, "lexicon", None)
    all_rules = present_indicative_rules(lex)
    random.shuffle(all_rules)
    
    # 分离通用规则和特定动词规则
    generic_rules: List[RuleCard] = [r for r in all_rules if not r.verb_infinitive]
    irregular_rules: List[RuleCard] = [r for r in all_rules if r.verb_infinitive and r.verb_infinitive in current_verbs]

    # 优先选择与当前动词相关的规则
    pool: List[RuleCard] = irregular_rules + generic_rules
    if len(pool) < player.base_hand_rules:
        pool = generic_rules
    random.shuffle(pool)

    # 选择变化卡
    player.hand_rules = [pool[i % len(pool)] for i in range(player.base_hand_rules)]

    # 生成新的题目
    state.question = random_question()


# ===================== UI友好的API =====================

def get_view(state: GameState) -> Dict[str, Any]:
    """
    获取游戏状态的UI显示信息
    
    Args:
        state: 当前游戏状态
        
    Returns:
        包含游戏状态信息的字典，用于UI显示
    """
    return {
        "major_round": state.major_round,  # 大回合数
        "subround": state.subround,        # 子回合数
        "boss": {"name": state.boss.name, "hp": state.boss.hp},  # Boss信息
        "player": {
            "hp": state.player.hp,         # 玩家生命值
            "coins": state.player.coins,   # 玩家金币
            "skills": [s.name for s in state.player.skills],  # 玩家技能
            "verbs": [v.infinitive for v in state.player.hand_verbs],  # 手牌动词
            "rules": [  # 手牌变化规则
                f"{r.pattern}" + (f" (仅{r.verb_infinitive})" if r.verb_infinitive else "")
                for r in state.player.hand_rules
            ],
        },
        "question": state.question.person,  # 当前题目的人称
    }


def _boss_attack_damage(state: GameState) -> int:
    """
    计算Boss攻击伤害
    
    Args:
        state: 当前游戏状态
        
    Returns:
        Boss造成的伤害值
    """
    # 基础伤害随大回合数增加
    base = 3 + max(0, (state.major_round - 1) // 2)
    # 添加随机性：-1, 0, +1
    return max(1, base + random.choice([-1, 0, 1]))


def resolve_play(state: GameState, verb_index: int, rule_index: int) -> Dict[str, Any]:
    """
    处理玩家出牌，验证变位正确性并计算结果
    
    Args:
        state: 当前游戏状态
        verb_index: 选择的动词卡索引
        rule_index: 选择的变化卡索引
        
    Returns:
        包含游戏结果的字典
    """
    player = state.player
    boss = state.boss
    
    # 初始化结果字典
    outcome: Dict[str, Any] = {
        "ok": True,              # 操作是否成功
        "message": "",           # 结果消息
        "damage": 0,             # 对Boss造成的伤害
        "coins_gained": 0,       # 获得的金币
        "boss_defeated": False,  # Boss是否被击败
        "player_damage": 0,      # 玩家受到的伤害
        "player_dead": False,    # 玩家是否死亡
        "player_hp": player.hp,  # 玩家当前生命值
        "produced": "",          # 玩家产生的变位
        "expected": "",          # 正确的变位
    }

    # 验证索引有效性
    if not (0 <= verb_index < len(player.hand_verbs)) or not (0 <= rule_index < len(player.hand_rules)):
        outcome.update({"ok": False, "message": "索引无效"})
        return outcome

    verb = player.hand_verbs[verb_index]
    rule = player.hand_rules[rule_index]

    lex = getattr(state, "lexicon", None)

    # 检查变化卡是否适用于当前动词
    verb_specific_mismatch = bool(rule.verb_infinitive and rule.verb_infinitive != verb.infinitive)

    # 应用变化规则
    ok_by_rule, temp = apply_rule_to_verb(verb.infinitive, rule)

    # 获取正确的变位形式
    expected = expected_present_form(verb.infinitive, state.question.person, lex)
    outcome["produced"] = temp
    outcome["expected"] = expected or ""

    # 检查变位是否正确
    produced_matches_expected = bool(expected) and (_normalize_form(temp) == _normalize_form(expected))

    # 判断是否成功
    if expected:
        success = produced_matches_expected
    else:
        success = ok_by_rule and (rule.person == state.question.person)

    if success:
        # 成功：随机伤害4-7
        damage = random.randint(4, 7)
        msg_prefix = f"{verb.infinitive} -> {temp}"
    else:
        # 失败：生成错误消息
        correct_hint = expected or ""
        if verb_specific_mismatch:
            base_msg = f"该变化卡仅适用于 {rule.verb_infinitive}"
        elif rule.person != state.question.person and not produced_matches_expected:
            base_msg = "题目与变化卡不匹配"
        else:
            base_msg = "变位不正确"
        msg_prefix = f"{base_msg}；正确答案：{verb.infinitive} -> {correct_hint}"
        damage = 0

    # 应用技能效果（方向加成）
    for s in player.skills:
        if s.triple_damage_on_directional and ("->" in getattr(rule, "pattern", "")):
            damage *= 3

    # 对Boss造成伤害
    boss.hp -= damage
    outcome["damage"] = damage

    if damage > 0:
        # 成功：获得金币1-3
        gain = random.randint(1, 3)
        player.coins += gain
        outcome["coins_gained"] = gain
        outcome["message"] = msg_prefix
    else:
        # 失败：受到Boss反击
        pdmg = _boss_attack_damage(state)
        player.hp -= pdmg
        outcome["player_damage"] = pdmg
        outcome["player_hp"] = max(0, player.hp)
        outcome["message"] = msg_prefix
        if player.hp <= 0:
            outcome["player_dead"] = True

    # 检查是否保留手牌（技能效果）
    retain = False
    for s in player.skills:
        if s.retain_on_play_50 and random.random() < 0.5:
            retain = True
            break
    if not retain:
        # 移除已使用的卡牌
        del player.hand_verbs[verb_index]
        del player.hand_rules[rule_index]

    # 检查Boss是否被击败
    if boss.hp <= 0:
        # 击败Boss：获得额外金币8-12
        bonus = random.randint(8, 12)
        player.coins += bonus
        outcome["boss_defeated"] = True
        outcome["message"] += f"；击败Boss！+{bonus}金币"
        return outcome

    # 检查玩家是否死亡
    if outcome["player_dead"]:
        return outcome

    # 进入下一子回合并刷新手牌
    state.next_subround()
    refresh_hands(state)
    return outcome


def shop_buy_direction_skill(state: GameState) -> bool:
    """
    在商店购买方向加成技能
    
    Args:
        state: 当前游戏状态
        
    Returns:
        是否成功购买
    """
    if state.player.coins >= 10:
        skill = SkillCard(
            name="方向加成",
            description="含->的变化卡伤害x3",
            cost=10,
            triple_damage_on_directional=True,
        )
        state.player.coins -= 10
        state.player.skills.append(skill)
        return True
    return False


def choose_upgrade(state: GameState, option: int) -> None:
    """
    选择升级选项，进入下一大回合
    
    Args:
        state: 当前游戏状态
        option: 升级选项 (1: 动词卡+1, 2: 变化卡+1, 3: 保留技能)
    """
    # 进入下一大回合
    state.major_round += 1
    state.subround = 1
    
    # 创建新的Boss，难度随回合增加
    state.boss = Boss(
        name=f"Boss R{state.major_round}",
        hp=20 + 10 * (state.major_round - 1),
        base_hp_per_subround=5 + 2 * (state.major_round - 1),
    )
    
    # 如果选项无效，随机选择
    if option not in (1, 2, 3):
        option = random.choice([1, 2, 3])
    
    # 应用升级效果
    if option == 1:
        state.player.base_hand_verbs += 1  # 增加手牌动词数量
    elif option == 2:
        state.player.base_hand_rules += 1  # 增加手牌变化卡数量
    elif option == 3:
        # 添加保留技能
        skill = SkillCard(name="保留之力", description="50%不失去已打出卡", cost=0, retain_on_play_50=True)
        state.player.skills.append(skill)
    
    # 刷新手牌
    refresh_hands(state)


# ===================== CLI包装器（保持可玩性） =====================

def play_subround(state: GameState) -> Tuple[bool, bool]:
    """
    执行一个子回合的CLI交互
    
    Args:
        state: 当前游戏状态
        
    Returns:
        (游戏是否继续, Boss是否被击败)
    """
    player = state.player
    boss = state.boss

    # 显示手牌
    print("动词卡：")
    for idx, v in enumerate(player.hand_verbs, 1):
        print(f"  {idx}. {v.infinitive}")
    print("变化卡：")
    for idx, r in enumerate(player.hand_rules, 1):
        print(f"  {idx}. {r.person} {r.pattern}")

    print(f"题目：{state.question.person}")

    # 获取玩家输入
    try:
        v_idx = int(input("选择一个动词卡编号: ")) - 1
        r_idx = int(input("选择一个变化卡编号: ")) - 1
    except Exception:
        print("输入无效，本回合失败。")
        return False, False

    # 处理出牌
    outcome = resolve_play(state, v_idx, r_idx)
    if not outcome["ok"]:
        print("输入无效，本回合失败。")
        return False, False

    produced = outcome.get("produced", "")
    expected = outcome.get("expected", "")

    # 显示结果
    if outcome["damage"] > 0:
        print(f"{outcome['message']} | 造成 {outcome['damage']} 伤害，+{outcome['coins_gained']} 金币")
    else:
        extra = f" | 被Boss反击 {outcome['player_damage']}，剩余HP {outcome['player_hp']}"
        print(outcome["message"] + extra)

    print(f"你打出的结果: {produced} | 正确结果: {expected}")

    # 检查游戏结束条件
    if outcome["player_dead"]:
        print("你阵亡了！游戏结束。")
        return False, False

    if outcome["boss_defeated"]:
        print("击败Boss！奖励10金币。")
        return True, True

    return True, False


def between_subround_shop(state: GameState) -> None:
    """
    子回合间的商店交互
    
    Args:
        state: 当前游戏状态
    """
    print("\n商店：1) 购买技能卡(10金)  2) 跳过")
    choice = input("选择: ").strip()
    if choice == "1":
        if shop_buy_direction_skill(state):
            print("已购买：方向加成")
        else:
            print("金币不足。")
    else:
        print("已跳过。")


def end_of_major_round(state: GameState) -> None:
    """
    大回合结束时的升级选择
    
    Args:
        state: 当前游戏状态
    """
    print("选择一个强化：1) 动词卡+1  2) 变化卡+1  3) 50%保留打出的卡")
    choice = input("选择: ").strip()
    mapping = {"1": 1, "2": 2, "3": 3}
    option = mapping.get(choice, 0)
    choose_upgrade(state, option)
