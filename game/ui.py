from __future__ import annotations
import tkinter as tk
from tkinter import messagebox

from .logic import start_new_game, get_view, resolve_play, shop_buy_direction_skill, choose_upgrade
from .models import GameState


class GameApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("西语变位战斗")
        self.state: GameState = start_new_game()

        self.info_frame = tk.Frame(self)
        self.info_frame.pack(fill=tk.X, padx=10, pady=8)

        self.lbl_round = tk.Label(self.info_frame, text="")
        self.lbl_round.pack(side=tk.LEFT)
        self.lbl_boss = tk.Label(self.info_frame, text="")
        self.lbl_boss.pack(side=tk.LEFT, padx=16)
        self.lbl_player = tk.Label(self.info_frame, text="")
        self.lbl_player.pack(side=tk.LEFT, padx=16)
        self.lbl_hp = tk.Label(self.info_frame, text="")
        self.lbl_hp.pack(side=tk.LEFT, padx=16)

        self.lbl_question = tk.Label(self, text="", font=("Arial", 12, "bold"))
        self.lbl_question.pack(pady=6)

        self.cards_frame = tk.Frame(self)
        self.cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self.verb_frame = tk.LabelFrame(self.cards_frame, text="动词卡")
        self.verb_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        self.rule_frame = tk.LabelFrame(self.cards_frame, text="变化卡")
        self.rule_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        self.action_frame = tk.Frame(self)
        self.action_frame.pack(fill=tk.X, padx=10, pady=6)
        self.btn_shop = tk.Button(self.action_frame, text="商店", command=self.open_shop)
        self.btn_shop.pack(side=tk.RIGHT)

        self.status = tk.StringVar()
        self.lbl_status = tk.Label(self, textvariable=self.status, fg="#333")
        self.lbl_status.pack(fill=tk.X, padx=10, pady=6)

        self.selected_verb = None
        self.selected_rule = None

        self.refresh_view()

    def refresh_view(self) -> None:
        view = get_view(self.state)
        self.lbl_round.config(text=f"R{view['major_round']}-S{view['subround']}")
        self.lbl_boss.config(text=f"Boss {view['boss']['name']} HP:{view['boss']['hp']}")
        self.lbl_player.config(text=f"金币:{view['player']['coins']} 技能:{','.join(view['player']['skills']) if view['player']['skills'] else '无'}")
        self.lbl_hp.config(text=f"HP:{view['player']['hp']}")
        self.lbl_question.config(text=f"题目：{view['question']}")

        for w in self.verb_frame.winfo_children():
            w.destroy()
        for w in self.rule_frame.winfo_children():
            w.destroy()

        for i, v in enumerate(view['player']['verbs']):
            btn = tk.Button(self.verb_frame, text=f"{i+1}. {v}", command=lambda idx=i: self.pick_verb(idx))
            btn.pack(fill=tk.X, padx=6, pady=3)
        for i, r in enumerate(view['player']['rules']):
            btn = tk.Button(self.rule_frame, text=f"{i+1}. {r}", command=lambda idx=i: self.pick_rule(idx))
            btn.pack(fill=tk.X, padx=6, pady=3)

        self.status.set("提示：先选择动词，再选择变化卡，系统自动出牌。")

    def pick_verb(self, idx: int) -> None:
        self.selected_verb = idx
        self.status.set(f"已选动词卡 {idx+1}，请选择变化卡。")

    def pick_rule(self, idx: int) -> None:
        self.selected_rule = idx
        if self.selected_verb is None:
            self.status.set("请先选择动词卡。")
            return
        self.play_selected()

    def play_selected(self) -> None:
        v_idx = int(self.selected_verb)
        r_idx = int(self.selected_rule)
        outcome = resolve_play(self.state, v_idx, r_idx)
        if not outcome["ok"]:
            messagebox.showwarning("无效", outcome["message"])
            return
        msg = outcome["message"]
        produced = outcome.get("produced", "")
        expected = outcome.get("expected", "")
        detail = f"\n你打出的结果: {produced}\n正确结果: {expected}"
        if outcome["damage"] > 0:
            msg += f"\n伤害 {outcome['damage']}，+{outcome['coins_gained']} 金币" + detail
        else:
            msg += f"\n被Boss反击 {outcome['player_damage']}，剩余HP {outcome['player_hp']}" + detail
        if outcome["player_dead"]:
            messagebox.showerror("失败", msg + "\n你阵亡了！")
            self.destroy()
            return
        if outcome["boss_defeated"]:
            messagebox.showinfo("胜利", msg)
            self.open_upgrade()
        else:
            messagebox.showinfo("提示", msg)
            self.status.set(msg)
            self.refresh_view()

        self.selected_verb = None
        self.selected_rule = None

    def open_shop(self) -> None:
        shop = tk.Toplevel(self)
        shop.title("商店")
        tk.Label(shop, text="10 金币：方向加成（含->的变化卡伤害×3)").pack(padx=10, pady=8)
        def buy():
            if shop_buy_direction_skill(self.state):
                messagebox.showinfo("成功", "已购买：方向加成")
                self.refresh_view()
            else:
                messagebox.showwarning("失败", "金币不足")
        tk.Button(shop, text="购买", command=buy).pack(pady=4)
        tk.Button(shop, text="关闭", command=shop.destroy).pack(pady=4)

    def open_upgrade(self) -> None:
        up = tk.Toplevel(self)
        up.title("大回合强化")
        tk.Label(up, text="选择一个强化：").pack(padx=10, pady=8)
        def choose(opt: int):
            choose_upgrade(self.state, opt)
            self.refresh_view()
            up.destroy()
        tk.Button(up, text="1) 动词卡+1", command=lambda: choose(1)).pack(fill=tk.X, padx=10, pady=4)
        tk.Button(up, text="2) 变化卡+1", command=lambda: choose(2)).pack(fill=tk.X, padx=10, pady=4)
        tk.Button(up, text="3) 50%保留打出的卡", command=lambda: choose(3)).pack(fill=tk.X, padx=10, pady=4)


def run_gui() -> None:
    app = GameApp()
    app.mainloop()
