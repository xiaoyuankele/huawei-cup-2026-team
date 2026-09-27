"""Print attachment C input hashes without copying private data into Git."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    for relative in ("leaderboard_cleaned.csv", "data/train-00000-of-00001.parquet",
                     "loss_benchmark_bridge.csv", "leaderboard_extended_timeseries.csv"):
        path = args.data_dir / relative
        if path.is_file():
            print(f"{relative},{path.stat().st_size},{sha256(path)}")
    root = args.data_dir / "detailed_results"
    files = sorted(root.rglob("*.json"), key=lambda item: item.relative_to(root).as_posix())
    tree = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        tree.update(relative.encode("utf-8") + b"\0" + sha256(path).encode("ascii") + b"\n")
    print(f"detailed_results/*.json,{len(files)},{tree.hexdigest()}")


if __name__ == "__main__":
    main()
