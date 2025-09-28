import sys
from game.cli import run_game as run_cli
from game.ui import run_gui


if __name__ == "__main__":
    try:
        if "--cli" in sys.argv:
            print("启动CLI模式...")
            run_cli()
        else:
            print("启动GUI模式...")
            run_gui()
    except Exception as e:
        print(f"启动游戏时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已退出游戏。")
        sys.exit(0)
