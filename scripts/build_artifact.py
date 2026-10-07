#!/usr/bin/env python3
"""
把 index.html 打包成单文件版本，用于发布为 Claude Artifact（在线链接版）。

做的事：
  1. 取出 <head> 和 <body> 里面的内容（Artifact 发布时会自己加 <html>/<head>/<body> 外壳）
  2. 去掉 <meta charset>（外壳里已经有）
  3. 把 assets/ 里引用的图片转成 base64 内嵌（Artifact 页面不能加载外部图片）

用法（在仓库根目录运行）：
  python3 scripts/build_artifact.py
输出：
  dist/aeration-calculator.artifact.html
"""
import base64
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
OUT = ROOT / "dist" / "aeration-calculator.artifact.html"


def inline_assets(html: str) -> str:
    def repl(m):
        path = ROOT / m.group(1)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:{mime};base64,{data}"'
    return re.sub(r'src="(assets/[^"]+)"', repl, html)


def main():
    html = SRC.read_text(encoding="utf-8")
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    head = re.sub(r'\s*<meta charset="utf-8">', "", head)
    out = inline_assets(head.strip() + "\n\n" + body.strip() + "\n")
    if "assets/" in out:
        raise SystemExit("还有未内嵌的 assets/ 引用，请检查 index.html")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"OK -> {OUT.relative_to(ROOT)}  ({len(out):,} chars)")


if __name__ == "__main__":
    main()
