#!/usr/bin/env python3
"""
冒烟测试：用无头浏览器打开 index.html，检查默认算例结果、双语切换、手机宽度和 JS 报错。
改了计算逻辑后先跑一遍；如果数字是“有意”改变的，把下面 EXPECTED 一起更新。

准备：pip install playwright && playwright install chromium
运行（在仓库根目录）：python3 tests/smoke_test.py
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

INDEX = (Path(__file__).resolve().parent.parent / "index.html").as_uri()

# 默认“养成池”算例：5 ha、1.5 m、20 尾/m²、80% 成活、1→25 g、100 天、28 °C、15 ppt、SC15
EXPECTED = {
    "units": "43",            # 需要 43 台 SC15
    "peak": "49.0",           # 峰值夜间需氧 49.0 kg O2/h（整塘）
    "biomass": "4,000",       # 收获生物量 4,000 kg/ha
    "coverage": "141%",       # 现有 30 HP/ha 相当于需求的 141%
    "saving_grid": "−65%",    # 变频（电网）比现有电动“全开”省 65%
    "saving_gen": "−45%",     # 变频（柴油发电机）比柴油水车省 45%
}


async def main():
    failures = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1320, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(INDEX)
        await page.wait_for_timeout(500)

        kpis = await page.inner_text("#kpis")
        cost = await page.inner_text("#cost")
        for key in ("units", "peak", "biomass", "coverage"):
            if EXPECTED[key] not in kpis:
                failures.append(f"KPI 缺少 {key}={EXPECTED[key]}")
        for key in ("saving_grid", "saving_gen"):
            if EXPECTED[key] not in cost:
                failures.append(f"成本表缺少 {key}={EXPECTED[key]}")

        # 默认语言应为西班牙语，切换后为英语
        if "Aireadores SUNOLTA necesarios" not in kpis:
            failures.append("默认语言不是西班牙语")
        await page.click(".lang button[data-l=en]")
        await page.wait_for_timeout(200)
        if "SUNOLTA aerators required" not in await page.inner_text("#kpis"):
            failures.append("切换英语失败")

        # 三个预设都能跑
        for preset in ("nursery", "offgrid", "grow"):
            await page.click(f"button[data-p={preset}]")
            await page.wait_for_timeout(150)
            if not (await page.inner_text("#kpis")).strip():
                failures.append(f"预设 {preset} 没有结果")

        # 手机宽度不能横向滚动
        mobile = await browser.new_page(viewport={"width": 390, "height": 844})
        await mobile.goto(INDEX)
        await mobile.wait_for_timeout(400)
        sw = await mobile.evaluate("document.documentElement.scrollWidth")
        if sw > 390:
            failures.append(f"手机宽度出现横向滚动 scrollWidth={sw}")

        if errors:
            failures.append(f"JS 报错: {errors}")
        await browser.close()

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("PASS: 默认算例、双语切换、预设、手机布局、无 JS 报错")


if __name__ == "__main__":
    asyncio.run(main())
