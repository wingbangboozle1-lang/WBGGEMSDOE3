#!/usr/bin/env python3
"""Insert (idempotently) the repository-wide decision banner into every lane page.

Lane pages (docs/hce, docs/cspes, docs/lst1) keep their own lane verdicts; this
banner only states the single repository-wide decision from evidence/decision.json
so no page can be read as a submit instruction that contradicts it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- REPO-DECISION:START -->", "<!-- REPO-DECISION:END -->"


def main() -> int:
    d = json.loads((ROOT / "evidence" / "decision.json").read_text())
    word = "SUBMIT (selector decides the slot)" if d["verdict"] == "promote" else "DO NOT SUBMIT"
    banner = (f'{START}<div style="background:#2a1214;color:#ffe9e9;border-bottom:2px solid #da3633;padding:10px 20px;'
              f'font:14px/1.5 system-ui,sans-serif"><b>Repository-wide decision ({d["generated_utc"][:10]}): {word}.</b> '
              f'No file in WBGGEMSDOE3 is cleared for upload; this lane page keeps its own research verdict. '
              f'<a style="color:#ffb3b3" href="../index.html">Decision and gate table</a></div>{END}')
    n = 0
    for lane in ("hce", "cspes", "lst1"):
        for page in sorted((ROOT / "docs" / lane).glob("*.html")):
            s = page.read_text()
            if START in s:
                s = re.sub(re.escape(START) + ".*?" + re.escape(END), banner, s, flags=re.S)
            else:
                m = re.search(r"<body[^>]*>", s)
                if not m:
                    continue
                s = s[:m.end()] + banner + s[m.end():]
            page.write_text(s)
            n += 1
    print(f"[lane-banner] {n} lane pages carry the repository decision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
