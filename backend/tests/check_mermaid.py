"""用前端实际使用的 mermaid 版本，在浏览器里解析课程中的全部图表。

用法：先启动服务，再运行
    uv run --with playwright python tests/check_mermaid.py
"""

import os
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

BASE = os.getenv("SMOKE_BASE", "http://127.0.0.1:8765")
CONTENT = Path(__file__).resolve().parents[2] / "content"
BLOCK = re.compile(r"```mermaid\s*\n(.*?)```", re.S)


def walk(obj, path):
    if isinstance(obj, str):
        for code in BLOCK.findall(obj):
            yield path, code.strip()
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


blocks = []
for f in sorted(CONTENT.rglob("*.yaml")):
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        print("跳过（YAML 语法错误，见 app.validate）:", f.name)
        continue
    blocks += [(f"{f.relative_to(CONTENT)}{p}", c) for p, c in walk(data, "")]
print(f"共 {len(blocks)} 张图", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page()
    page.goto(BASE + "/settings")
    page.wait_for_function("() => window.__loadMermaid !== undefined", timeout=30000)
    bad = []
    for where, code in blocks:
        err = page.evaluate(
            "async (c) => { try { const m = await window.__loadMermaid(); await m.parse(c); return null }"
            " catch (e) { return String(e.message || e) } }",
            code,
        )
        if err:
            bad.append((where, err.splitlines()[0][:200]))
    browser.close()

for where, err in bad:
    print("ERR", where, "→", err)
print(f"解析失败 {len(bad)} / {len(blocks)}")
sys.exit(1 if bad else 0)
