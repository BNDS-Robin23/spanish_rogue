from __future__ import annotations
import random
import unicodedata
from typing import List, Tuple, Dict, Any

from .models import GameState, Player, Boss, Question, VerbCard, RuleCard, SkillCard
from .rules import present_indicative_rules, apply_rule_to_verb, random_question, expected_present_form
from .lexicon import VerbLexicon


def _normalize_form(s: str) -> str:
    if s is None:
        return ""
    return unicodedata.normalize("NFC", s).strip().casefold()


def start_new_game() -> GameState:
    # Don't fix seed here to allow real randomness in gameplay
    lex = VerbLexicon()
    try:
        lex.load()
        verb_pool = lex.list_infinitives()
        if not verb_pool:
            raise ValueError("empty lexicon")
    except Exception:
        verb_pool = [
            "hablar", "comer", "vivir", "estudiar", "leer", "escribir",
            "amar", "beber", "abrir", "correr", "saltar", "cantar",
        ]
        lex = None  # type: ignore

    player = Player()
    boss = Boss(name="初级Boss", hp=20, base_hp_per_subround=5)
    question = random_question()
    state = GameState(player=player, boss=boss, major_round=1, subround=1, question=question, verb_pool=verb_pool)
    setattr(state, "lexicon", lex)
    refresh_hands(state)
    return state


def refresh_hands(state: GameState) -> None:
    player = state.player
    # Shuffle pool and select verbs
    pool_copy = list(state.verb_pool)
    random.shuffle(pool_copy)
    player.hand_verbs = [VerbCard(infinitive=pool_copy[i % len(pool_copy)]) for i in range(player.base_hand_verbs)]
    current_verbs = {v.infinitive for v in player.hand_verbs}

    lex = getattr(state, "lexicon", None)
    all_rules = present_indicative_rules(lex)
    random.shuffle(all_rules)
    generic_rules: List[RuleCard] = [r for r in all_rules if not r.verb_infinitive]
    irregular_rules: List[RuleCard] = [r for r in all_rules if r.verb_infinitive and r.verb_infinitive in current_verbs]

    pool: List[RuleCard] = irregular_rules + generic_rules
    if len(pool) < player.base_hand_rules:
        pool = generic_rules
    random.shuffle(pool)

    player.hand_rules = [pool[i % len(pool)] for i in range(player.base_hand_rules)]

    state.question = random_question()


# ===================== UI-friendly API =====================

def get_view(state: GameState) -> Dict[str, Any]:
    return {
        "major_round": state.major_round,
        "subround": state.subround,
        "boss": {"name": state.boss.name, "hp": state.boss.hp},
        "player": {
            "hp": state.player.hp,
            "coins": state.player.coins,
            "skills": [s.name for s in state.player.skills],
            "verbs": [v.infinitive for v in state.player.hand_verbs],
            "rules": [
                f"{r.pattern}" + (f" (仅{r.verb_infinitive})" if r.verb_infinitive else "")
                for r in state.player.hand_rules
            ],
        },
        "question": state.question.person,
    }


def _boss_attack_damage(state: GameState) -> int:
    base = 3 + max(0, (state.major_round - 1) // 2)
    # +/-1 randomness
    return max(1, base + random.choice([-1, 0, 1]))


def resolve_play(state: GameState, verb_index: int, rule_index: int) -> Dict[str, Any]:
    player = state.player
    boss = state.boss
    outcome: Dict[str, Any] = {
        "ok": True,
        "message": "",
        "damage": 0,
        "coins_gained": 0,
        "boss_defeated": False,
        "player_damage": 0,
        "player_dead": False,
        "player_hp": player.hp,
        "produced": "",
        "expected": "",
    }

    if not (0 <= verb_index < len(player.hand_verbs)) or not (0 <= rule_index < len(player.hand_rules)):
        outcome.update({"ok": False, "message": "索引无效"})
        return outcome

    verb = player.hand_verbs[verb_index]
    rule = player.hand_rules[rule_index]

    lex = getattr(state, "lexicon", None)

    verb_specific_mismatch = bool(rule.verb_infinitive and rule.verb_infinitive != verb.infinitive)

    ok_by_rule, temp = apply_rule_to_verb(verb.infinitive, rule)

    expected = expected_present_form(verb.infinitive, state.question.person, lex)
    outcome["produced"] = temp
    outcome["expected"] = expected or ""

    produced_matches_expected = bool(expected) and (_normalize_form(temp) == _normalize_form(expected))

    if expected:
        success = produced_matches_expected
    else:
        success = ok_by_rule and (rule.person == state.question.person)

    if success:
        # random damage between 4-7
        damage = random.randint(4, 7)
        msg_prefix = f"{verb.infinitive} -> {temp}"
    else:
        correct_hint = expected or ""
        if verb_specific_mismatch:
            base_msg = f"该变化卡仅适用于 {rule.verb_infinitive}"
        elif rule.person != state.question.person and not produced_matches_expected:
            base_msg = "题目与变化卡不匹配"
        else:
            base_msg = "变位不正确"
        msg_prefix = f"{base_msg}；正确答案：{verb.infinitive} -> {correct_hint}"
        damage = 0

    for s in player.skills:
        if s.triple_damage_on_directional and ("->" in getattr(rule, "pattern", "")):
            damage *= 3

    boss.hp -= damage
    outcome["damage"] = damage

    if damage > 0:
        # random coins 1-3
        gain = random.randint(1, 3)
        player.coins += gain
        outcome["coins_gained"] = gain
        outcome["message"] = msg_prefix
    else:
        pdmg = _boss_attack_damage(state)
        player.hp -= pdmg
        outcome["player_damage"] = pdmg
        outcome["player_hp"] = max(0, player.hp)
        outcome["message"] = msg_prefix
        if player.hp <= 0:
            outcome["player_dead"] = True

    retain = False
    for s in player.skills:
        if s.retain_on_play_50 and random.random() < 0.5:
            retain = True
            break
    if not retain:
        del player.hand_verbs[verb_index]
        del player.hand_rules[rule_index]

    if boss.hp <= 0:
        # random bonus coins 8-12
        bonus = random.randint(8, 12)
        player.coins += bonus
        outcome["boss_defeated"] = True
        outcome["message"] += f"；击败Boss！+{bonus}金币"
        return outcome

    if outcome["player_dead"]:
        return outcome

    state.next_subround()
    refresh_hands(state)
    return outcome


def shop_buy_direction_skill(state: GameState) -> bool:
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
    state.major_round += 1
    state.subround = 1
    state.boss = Boss(
        name=f"Boss R{state.major_round}",
        hp=20 + 10 * (state.major_round - 1),
        base_hp_per_subround=5 + 2 * (state.major_round - 1),
    )
    # If option is 0 (invalid), pick randomly
    if option not in (1, 2, 3):
        option = random.choice([1, 2, 3])
    if option == 1:
        state.player.base_hand_verbs += 1
    elif option == 2:
        state.player.base_hand_rules += 1
    elif option == 3:
        skill = SkillCard(name="保留之力", description="50%不失去已打出卡", cost=0, retain_on_play_50=True)
        state.player.skills.append(skill)
    refresh_hands(state)


# ===================== CLI wrappers (keep playable) =====================

def play_subround(state: GameState) -> Tuple[bool, bool]:
    player = state.player
    boss = state.boss

    print("动词卡：")
    for idx, v in enumerate(player.hand_verbs, 1):
        print(f"  {idx}. {v.infinitive}")
    print("变化卡：")
    for idx, r in enumerate(player.hand_rules, 1):
        print(f"  {idx}. {r.person} {r.pattern}")

    print(f"题目：{state.question.person}")

    try:
        v_idx = int(input("选择一个动词卡编号: ")) - 1
        r_idx = int(input("选择一个变化卡编号: ")) - 1
    except Exception:
        print("输入无效，本回合失败。")
        return False, False

    outcome = resolve_play(state, v_idx, r_idx)
    if not outcome["ok"]:
        print("输入无效，本回合失败。")
        return False, False

    produced = outcome.get("produced", "")
    expected = outcome.get("expected", "")

    if outcome["damage"] > 0:
        print(f"{outcome['message']} | 造成 {outcome['damage']} 伤害，+{outcome['coins_gained']} 金币")
    else:
        extra = f" | 被Boss反击 {outcome['player_damage']}，剩余HP {outcome['player_hp']}"
        print(outcome["message"] + extra)

    print(f"你打出的结果: {produced} | 正确结果: {expected}")

    if outcome["player_dead"]:
        print("你阵亡了！游戏结束。")
        return False, False

    if outcome["boss_defeated"]:
        print("击败Boss！奖励10金币。")
        return True, True

    return True, False


def between_subround_shop(state: GameState) -> None:
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
    print("选择一个强化：1) 动词卡+1  2) 变化卡+1  3) 50%保留打出的卡")
    choice = input("选择: ").strip()
    mapping = {"1": 1, "2": 2, "3": 3}
    option = mapping.get(choice, 0)
    choose_upgrade(state, option)
