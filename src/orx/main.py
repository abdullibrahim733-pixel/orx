from __future__ import annotations

import argparse

from orx.game import Game


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orx", add_help=True)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run a short headless-friendly loop then exit.",
    )
    parser.add_argument(
        "--bench",
        action="store_true",
        help="Run with FPS benchmarking output.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug overlay with FPS and player position.",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run in windowed mode (default is fullscreen).",
    )
    args = parser.parse_args(argv)

    game = Game(smoke=args.smoke, bench=args.bench, debug=args.debug, windowed=args.windowed)
    return game.run()
