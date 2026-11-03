#!/usr/bin/env python3
"""
把 index.html（厄瓜多尔版）和 indonesia.html（印尼版）打包成单文件版本，用于发布为 Claude Artifact（在线链接版）。

做的事：
  1. 取出 <head> 和 <body> 里面的内容（Artifact 发布时会自己加 <html>/<head>/<body> 外壳）
  2. 去掉 <meta charset>（外壳里已经有）
  3. 把 assets/ 里引用的图片转成 base64 内嵌（Artifact 页面不能加载外部图片）
  4. 印尼版：把 Excel 模板内嵌，供页面的下载按钮使用（要先运行 scripts/build_xlsx.py）

用法（在仓库根目录运行）：
  python3 scripts/build_artifact.py
输出：
  dist/aeration-calculator.artifact.html
  dist/hemat-listrik-kincir.artifact.html
"""
import base64
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    (ROOT / "index.html", ROOT / "dist" / "aeration-calculator.artifact.html"),
    (ROOT / "indonesia.html", ROOT / "dist" / "hemat-listrik-kincir.artifact.html"),
]
XLSX = ROOT / "dist" / "perbandingan-hemat-listrik-kincir.xlsx"
XLSX_SLOT = "__XLSX_B64__"


def inline_assets(html: str) -> str:
    def repl(m):
        path = ROOT / m.group(1)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:{mime};base64,{data}"'
    return re.sub(r'src="(assets/[^"]+)"', repl, html)


def build(src: Path, out_path: Path):
    html = src.read_text(encoding="utf-8")
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    head = re.sub(r'\s*<meta charset="utf-8">', "", head)
    out = inline_assets(head.strip() + "\n\n" + body.strip() + "\n")
    if "assets/" in out:
        raise SystemExit(f"还有未内嵌的 assets/ 引用，请检查 {src.name}")
    if XLSX_SLOT in out:
        if not XLSX.exists():
            raise SystemExit("缺少 Excel 模板，请先运行 python3 scripts/build_xlsx.py")
        out = out.replace(XLSX_SLOT, base64.b64encode(XLSX.read_bytes()).decode())
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"OK -> {out_path.relative_to(ROOT)}  ({len(out):,} chars)")


def main():
    for src, out_path in TARGETS:
        build(src, out_path)


if __name__ == "__main__":
    main()
