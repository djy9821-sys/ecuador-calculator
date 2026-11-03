#!/usr/bin/env python3
"""
印尼版冒烟测试：用无头浏览器打开 indonesia.html，检查默认算例、三语切换、价格和以旧换新、
手机宽度、JS 报错，并核对 Excel 模板里的缓存结果和网页一致。
改了计算逻辑后先跑一遍；如果数字是“有意”改变的，把下面 EXPECTED 一起更新。

准备：pip install playwright openpyxl && playwright install chromium
运行（在仓库根目录）：python3 tests/smoke_test_indonesia.py
已装 Chrome、不想下载 Chromium 时：PW_CHANNEL=chrome python3 tests/smoke_test_indonesia.py
"""
import asyncio
import os
import sys
from pathlib import Path

from openpyxl import load_workbook
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "indonesia.html").as_uri()
XLSX = ROOT / "dist" / "perbandingan-hemat-listrik-kincir.xlsx"

# 默认算例：5 台、Rp 1,444.70/kWh、120 天、2.5 造、24 小时、老款 1.5 kW、新款 1.64 kW、负荷 40/50/70/90%
EXPECTED = {
    "hero": "Rp 24,7 juta",     # 5 台每年省 Rp 24.7 百万
    "pct": "32%",               # 省电 31.7%
    "saved_day": "11,4",        # 每台每天省 11.4 度
    "old_day": "36,0 kWh",      # 老款每天 36 度
    "new_day": "24,6 kWh",      # 新款每天 24.6 度
    "cycle": "Rp 1,98 juta",    # 每台每造省 Rp 1.98 百万
    "scale_2000": "Rp 9,88 miliar",  # 2000 台每年省 Rp 9.88 十亿
    "range": ["20%", "48%"],    # 溶氧校核给出的省电范围
}
# 不能出现在发给印尼客户的页面上
FORBIDDEN = ["CODEMET", "Segundo", "Ecuador", "camaronera", "piscina", "李总"]


async def main():
    failures = []
    source = (ROOT / "indonesia.html").read_text(encoding="utf-8")
    for word in FORBIDDEN:
        if word.lower() in source.lower():
            failures.append(f"页面源码里出现了不该有的词: {word}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel=os.environ.get("PW_CHANNEL") or None)
        page = await browser.new_page(viewport={"width": 1320, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(INDEX)
        await page.wait_for_timeout(500)

        async def has(selector, text, why):
            content = await page.inner_text(selector)
            if text not in content:
                failures.append(f"{why}: 期望 {text!r}，实际 {content[:160]!r}")

        await has("#hero", EXPECTED["hero"], "默认年节省")
        await has("#kpis", EXPECTED["pct"], "省电比例")
        await has("#kpis", EXPECTED["saved_day"], "每台每天省电")
        await has("#cmpB", EXPECTED["old_day"], "老款每天用电")
        await has("#cmpB", EXPECTED["new_day"], "新款每天用电")
        await has("#cmpB", EXPECTED["cycle"], "每台每造节省")
        await has("#scB", EXPECTED["scale_2000"], "2000 台每年节省")
        for value in EXPECTED["range"]:
            await has("#notes", value, "省电范围")
        await has("#hero", "Perkiraan hemat", "默认语言应为印尼语")

        # 默认没有任何价格
        if await page.input_value("#pOld") or await page.input_value("#pNew") or await page.input_value("#pKit"):
            failures.append("价格默认应该是空的")

        # 规模按钮和最后一行联动
        await page.click('#scaleChips .chip[data-n="1000"]')
        await page.wait_for_timeout(100)
        await has("#hero", "Rp 4,94 miliar", "选 1000 台")
        if await page.input_value("#unitsRow") != "1000":
            failures.append("最后一行台数没有同步")
        await page.fill("#unitsRow", "20")
        await page.wait_for_timeout(100)
        await has("#hero", "Rp 98,8 juta", "最后一行填 20 台")

        # 价格：新款贵 200 元，差价 Rp 544,000，每台每年省 Rp 4.94 百万，回本约 1.3 个月
        await page.click('#scaleChips .chip[data-n="5"]')
        await page.evaluate('document.getElementById("dPrice").open=true')
        await page.select_option("#cur", "CNY")
        await page.fill("#pOld", "1000")
        await page.fill("#pNew", "1200")
        await page.fill("#pKit", "600")
        await page.fill("#pTrade", "100")
        await page.wait_for_timeout(100)
        await has("#kpis", "1,3 bulan", "差价回本")
        await has("#cmpB", "20%", "贵百分之几")
        await has("#tr", "Rp 1,36 juta", "以旧换新每台投入 (600-100)×2720")
        await has("#tr", "3,3 bulan", "以旧换新回本")

        # 三语切换
        await page.click(".lang button[data-l=en]")
        await page.wait_for_timeout(150)
        await has("#hero", "Rp 24.7 million", "切换英语")
        await page.click(".lang button[data-l=zh]")
        await page.wait_for_timeout(150)
        await has("#hero", "Rp 2,470万", "切换中文")
        await page.click(".lang button[data-l=id]")
        await page.wait_for_timeout(150)

        # 恢复初始数字，价格清空
        await page.click("#reset")
        await page.wait_for_timeout(100)
        if await page.input_value("#pOld"):
            failures.append("恢复初始数字后价格没有清空")

        # 实测值替换计算
        await page.evaluate('document.querySelectorAll("details.adv").forEach(function(d){d.open=true})')
        await page.fill("#measOld", "40")
        await page.fill("#measNew", "30")
        await page.wait_for_timeout(100)
        await has("#kpis", "25%", "实测值")
        await page.click("#reset")

        # 负荷太低要警告
        await page.fill("#ln3", "20")
        await page.wait_for_timeout(100)
        if "note w" not in await page.inner_html("#notes"):
            failures.append("负荷低于需氧量时没有警告")
        await page.click("#reset")

        # 默认币种是印尼盾，首屏不出现外币
        if "¥" in await page.inner_text("#hero"):
            failures.append("默认不应该显示外币")

        # 添加和删除照片
        await page.set_input_files('input[type=file][data-ph="old"]', str(ROOT / "assets" / "logo.png"))
        await page.wait_for_selector('.ph[data-ph="old"] img', timeout=3000)
        await page.click('[data-phdel="old"]')
        await page.wait_for_timeout(100)
        if await page.query_selector('.ph[data-ph="old"] img'):
            failures.append("删除照片后还显示照片")

        # 图表悬停提示
        svg = await page.query_selector("#ch1 svg")
        await svg.scroll_into_view_if_needed()
        box = await svg.bounding_box()
        await page.mouse.move(box["x"] + box["width"] * 0.25, box["y"] + box["height"] * 0.5)
        await page.wait_for_timeout(100)
        tip = await page.inner_text("#ch1 .tip")
        if "1,50 kW" not in tip or "0,66 kW" not in tip:
            failures.append(f"图表提示不对: {tip!r}")

        # 技术校核展开后能画图，四个阶段都够用
        await page.evaluate('document.getElementById("tech").open=true')
        await page.wait_for_timeout(200)
        if not await page.query_selector("#ch2 svg"):
            failures.append("技术校核图没有画出来")
        if "Kurang" in await page.inner_text("#stT"):
            failures.append("默认负荷模式应该四个阶段都够用")

        # 手机宽度不能横向滚动，三种语言都查
        mobile = await browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda e: errors.append(str(e)))
        await mobile.goto(INDEX)
        for lang in ("id", "en", "zh"):
            await mobile.click(f".lang button[data-l={lang}]")
            await mobile.wait_for_timeout(250)
            sw = await mobile.evaluate("document.documentElement.scrollWidth")
            if sw > 390:
                failures.append(f"手机宽度出现横向滚动 lang={lang} scrollWidth={sw}")
            # 三张结果表在手机上不能靠横向滑动才看全
            for table in ("#cmp", "#sc", "#tr"):
                over = await mobile.evaluate(f"(function(){{var t=document.querySelector('{table}');return t.scrollWidth-t.parentElement.clientWidth;}})()")
                if over > 1:
                    failures.append(f"手机上 {table} 超出 {over}px lang={lang}")

        if errors:
            failures.append(f"JS 报错: {errors}")
        await browser.close()

    # Excel 模板的缓存结果要和网页默认算例一致
    ws = load_workbook(XLSX, data_only=True)["Perbandingan"]
    checks = {"C29": 36.0, "D29": 24.6, "D33": 0.316667, "F39": 24_704_370, "F43": 9_881_748_000}
    for cell, want in checks.items():
        got = ws[cell].value
        if got is None or abs(got - want) > max(0.001, abs(want) * 1e-5):
            failures.append(f"Excel {cell}: 期望约 {want}，实际 {got}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("PASS: 默认算例、规模联动、价格回本、以旧换新、三语、实测值、负荷警告、溶氧校核、手机布局、Excel、无 JS 报错")


if __name__ == "__main__":
    asyncio.run(main())
