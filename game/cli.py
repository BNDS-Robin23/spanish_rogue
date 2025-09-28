from .models import GameState
from .logic import start_new_game, play_subround, between_subround_shop, end_of_major_round


def run_game() -> None:
    print("西班牙语动词变位战斗 - CLI 版本")

    state: GameState = start_new_game()

    while True:
        print(f"\n=== 第{state.major_round}大回合 第{state.subround}小回合 ===")
        print(f"Boss 生命: {state.boss.hp}    金币: {state.player.coins}")

        survived, defeated = play_subround(state)
        if not survived:
            print("你阵亡了！游戏结束。")
            break
        if defeated:
            print("Boss 被击败！进入下一大回合！")
            end_of_major_round(state)
            continue

        between_subround_shop(state)
