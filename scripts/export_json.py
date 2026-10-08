"""Write web/src/data/node-verdict-data.json from the real engine and simulator.

Run from the repo root after any change to the engine, policy, simulator or data:

    python scripts/export_json.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

from node_verdict.export import DEFAULT_OUT, write


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    path = write(parser.parse_args().out)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
