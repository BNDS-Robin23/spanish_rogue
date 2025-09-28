import sys
from game.cli import run_game as run_cli
from game.ui import run_gui


if __name__ == "__main__":
    try:
        if "--cli" in sys.argv:
            run_cli()
        else:
            run_gui()
    except KeyboardInterrupt:
        print("\n已退出游戏。")
        sys.exit(0)
