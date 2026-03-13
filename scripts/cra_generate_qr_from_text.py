from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: cra_generate_qr_from_text.py <content> <output-path>", file=sys.stderr)
        return 2

    content = sys.argv[1]
    output_path = Path(sys.argv[2]).expanduser().resolve()
    repo_root = Path(__file__).resolve().parent.parent
    cache_dir = output_path.parent / ".swift-module-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["CLANG_MODULE_CACHE_PATH"] = str(cache_dir)
    env["SWIFT_MODULE_CACHE_PATH"] = str(cache_dir)

    result = subprocess.run(
        ["swift", str(repo_root / "scripts" / "cra_generate_qr.swift"), content, str(output_path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown QR generation failure."
        print(message, file=sys.stderr)
        return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

