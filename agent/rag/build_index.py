"""Runbook index CLI and library wrapper."""

from __future__ import annotations

import argparse
from pathlib import Path

from rag.indexer import index_runbooks, runbooks_dir


def build_index(persist_dir: Path | None = None, *, mode: str = "full") -> str:
    result = index_runbooks(
        source_dir=runbooks_dir(),
        persist_dir=persist_dir,
        mode="incremental" if mode == "incremental" else "full",
    )
    return result.index_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma runbook index")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    args = parser.parse_args()
    version = build_index(mode=args.mode)
    print(f"Index built: {version}")


if __name__ == "__main__":
    main()
