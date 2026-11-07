#!/usr/bin/env python3
"""
印尼版冒烟测试：用无头浏览器打开 indonesia.html，核对 6 种池塘的数字和客户 Excel《池塘水车耗电对比》的公式一致，
再查选塘、口塘数、价格和回本、以旧换新、三语切换、恢复初始数字、照片和 Logo、各种手机屏幕、JS 报错，
最后核对 Excel 模板里的缓存结果。
池塘和台数按客户后来的要求改过，公式没变。
改了计算逻辑后先跑一遍；如果数字是“有意”改变的，把下面 EXPECTED 一起更新。

准备：pip install playwright openpyxl && playwright install chromium
运行（在仓库根目录）：python3 tests/smoke_test_indonesia.py
已装 Chrome、不想下载 Chromium 时：PW_CHANNEL=chrome python3 tests/smoke_test_indonesia.py
"""
import asyncio
import os
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import load_workbook
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "indonesia.html").as_uri()
XLSX = ROOT / "dist" / "perbandingan-hemat-listrik-kincir.xlsx"

# 公式和客户 Excel 一样（120 天、24 小时、2.5 造、0.75 kW、Rp 1,444.70/kWh），只是节电率由电流算出来：1 − 1.0 A ÷ 1.3 A。
# 台数和池塘是客户后来定的：多了小四方型，按面积排序，圆型 2、中四方型 10、大长方型 24（原表是 1、8、22）。
# 键是页面上的池塘代号，值是 Excel 的列。row 是我们 Excel 里的行号。
KW, HOURS, DAYS, CYCLES, TARIFF = 0.75, 24, 120, 2.5, 1444.7
RATE = 1 - 1.0 / 1.3
TRADE_RP = 2023313      # 以旧换新最低售价：550 元 × 汇率 2725 × 1.35


def pond(row, units, area):
    F, I = units * KW, units * KW * (1 - RATE)
    G, J = F * HOURS * DAYS, I * HOURS * DAYS
    L = F - I
    M = L * HOURS
    N = M * DAYS
    O = N * TARIFF
    return {"row": row, "D": units, "E": area / units, "F": F, "G": G, "H": G * TARIFF, "I": I, "J": J, "K": J * TARIFF, "L": L, "M": M, "N": N, "O": O, "P": N * CYCLES, "Q": O * CYCLES}


EXPECTED = {
    "round": pond(20, 2, 3.14159265358979 * 16),
    "sqS": pond(21, 6, 400),
    "sqM": pond(22, 10, 900),
    "rcM": pond(23, 16, 1500),
    "sqL": pond(24, 16, 2500),
    "rcL": pond(25, 24, 4000),
}
ORDER = ["round", "sqS", "sqM", "rcM", "sqL", "rcL"]
# 每口塘的圈层：画面上的水车数量和说明都要对上
RINGS = {"round": (2, "diagonal"), "sqS": (6, "lingkar luar 4, lingkar dalam 2"), "sqM": (10, "lingkar luar 6, lingkar dalam 4"), "rcM": (16, "lingkar luar 10, lingkar dalam 6"), "sqL": (16, "lingkar luar 10, lingkar dalam 6"), "rcL": (24, "lingkar 1: 12, lingkar 2: 8, lingkar 3: 4")}
DECIMALS = {"E": 0, "F": 2, "G": 0, "H": 0, "I": 2, "J": 0, "K": 0, "L": 2, "M": 1, "N": 0, "O": 0, "P": 0, "Q": 0}
# 不能出现在发给印尼客户的页面上。新水车的价格只能在页面上填，SC15 的功率和这张表不是一回事；以旧换新只显示印尼盾售价，人民币价和加价比例不能让客户看到。
FORBIDDEN = ["CODEMET", "Segundo", "Ecuador", "camaronera", "piscina", "李总", "SC15", "CNY", "人民币", "¥", "yuan"]
SCREENS = [(320, 568), (360, 640), (360, 780), (393, 851), (412, 915), (480, 800), (673, 841), (740, 360), (851, 393), (915, 412), (800, 1280)]
STYLES = [(1, None), (1.3, None), (1, "Verdana")]
SET_STYLE = """(a)=>{var s=document.documentElement.style;s.fontSize=(16*a[0])+'px';
  if(a[1]){s.setProperty('--f-body',a[1]);s.setProperty('--f-num',a[1]);}else{s.removeProperty('--f-body');s.removeProperty('--f-num');}}"""
# 超出屏幕、被裁掉的内容，以及太小点不到的按钮
FIT_PROBE = """(function(){
  var bad=[], w=document.documentElement.clientWidth;
  if(document.documentElement.scrollWidth>w) bad.push('整页横向滚动');
  document.querySelectorAll('body *').forEach(function(el){
    if(el.closest('svg')||el.closest('.tw')||el.classList.contains('vh')||el.id==='mbar'||el.closest('#mbar')) return;
    var cs=getComputedStyle(el); if(cs.display==='none'||cs.visibility==='hidden') return;
    var r=el.getBoundingClientRect(); if(!r.width) return;
    var name=el.id||el.className||el.tagName;
    if(r.right>w+1) bad.push('超出屏幕:'+name);
    if((cs.overflowX==='hidden'||cs.overflowX==='clip')&&el.scrollWidth>el.clientWidth+1) bad.push('被裁掉:'+name);
    if((el.tagName==='BUTTON'||el.classList.contains('phb'))&&r.height<30) bad.push('太小:'+name+':'+Math.round(r.height));
  });
  var bar=document.getElementById('mbar'); if(bar.scrollWidth>bar.clientWidth+1) bad.push('结果条超宽');
  return bad.slice(0,5);
})()"""


def id_number(value, decimals):
    """印尼语的数字写法：1.444,70。和 Excel 的显示一样四舍五入。"""
    number = Decimal(str(round(value, 9))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return f"{number:,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")


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
        await page.wait_for_timeout(400)

        async def has(selector, text, why):
            content = await page.inner_text(selector)
            if text not in content:
                failures.append(f"{why}: 期望 {text!r}，实际 {content[:200]!r}")

        # 默认：中四方型 10 台，每年省 Rp 18.0 百万
        await has("#hero", "Rp 18,0 juta", "默认每年节省")
        await has("#hero", "1,3 A → 1,0 A", "节电率要写明来自电流")
        await has("#hero", "23,1%", "节电率 = 1 − 1.0 ÷ 1.3")
        await has("#hero", "Hemat biaya listrik", "默认语言应为印尼语")
        await has("#compare", "Kincir magnet permanen WANGJIA", "B 列要写 WANGJIA")
        await has("#ladD", "Rp 18.003.185", "D 列每年省电费")
        await has("#ladC", "7.201.274", "C 列每造省电费")
        await has("#ladC", "4.985", "C 列每造节电")
        await has("#cmpRows", "21.600", "A 列耗电量")
        await has("#cmpRows", "16.615", "B 列耗电量")
        await has("#cmpRows", "1,3", "传统水车电流")
        await has("#cmpRows", "0,577", "永磁变频平均功率")
        await has("#cmpRows", "Rp 31.205.520", "A 列电费")
        await has("#cmpRows", "Rp 24.004.246", "B 列电费")

        # 默认没有任何价格
        for field in ("#pOld", "#pNew"):
            if await page.input_value(field):
                failures.append(f"价格默认应该是空的: {field}")

        # 完整表：5 种池塘的每一列都要和客户 Excel 一样
        if not await page.query_selector("table.full"):
            await page.click("#tFull")
        for key, row in EXPECTED.items():
            if await page.input_value(f"#u_{key}") != str(row["D"]):
                failures.append(f"{key} 水车数量不对")
            for col, decimals in DECIMALS.items():
                got = await page.inner_text(f'tr[data-k="{key}"] td[data-c="{col}"]')
                want = id_number(row[col], decimals)
                if got != want:
                    failures.append(f"{key} {col} 列: 期望 {want}，实际 {got}")

        # 每种池塘的画面：水车数量和圈层说明都要对上，台数变了画面也跟着变
        for key, (count, legend) in RINGS.items():
            await page.click(f'.pond[data-k="{key}"]')
            await page.wait_for_timeout(30)
            drawn = await page.evaluate("document.querySelectorAll('#scO use').length")
            if drawn != count:
                failures.append(f"{key} 画面上有 {drawn} 台，应该是 {count} 台")
            shown = await page.evaluate("Array.from(document.querySelectorAll('.sc-r')).filter(function(i){return !i.hidden}).map(function(i){return i.dataset.k+':'+i.naturalWidth})")
            if len(shown) != 1 or not shown[0].startswith(key + ":") or shown[0].endswith(":0"):
                failures.append(f"{key} 应该显示它的 3D 效果图: {shown}")
            await has("#scRings", legend, f"{key} 圈层说明")
        await page.click('[data-st="units"][data-d="1"]')
        await page.wait_for_timeout(30)
        if await page.evaluate("document.querySelectorAll('#scO use').length") != 25:
            failures.append("加一台后画面没有多一台")
        # 台数和效果图不一样时，要换成现场画的图，不能让图和数字对不上
        if await page.is_hidden("#scD") or await page.evaluate("document.querySelectorAll('.sc-r:not([hidden])').length"):
            failures.append("台数改了以后应该显示现场画的图")
        await page.click('[data-st="units"][data-d="-1"]')
        if await page.is_visible("#scD"):
            failures.append("台数改回去以后应该回到 3D 效果图")
        await page.evaluate("document.getElementById('scene').click()")
        if await page.is_hidden("#zoom"):
            failures.append("点大图应该能放大")
        await page.evaluate("window.hematBack()")
        # 从小到大排列：选择卡片和表格都一样
        order = await page.evaluate("Array.from(document.querySelectorAll('.pond')).map(function(b){return b.dataset.k})")
        if order != ORDER:
            failures.append(f"池塘没有从小到大排列: {order}")
        rows = await page.evaluate("Array.from(document.querySelectorAll('#tbl tr[data-k]')).map(function(r){return r.dataset.k})")
        if rows != ORDER:
            failures.append(f"表格没有从小到大排列: {rows}")
        if "Ukuran lain" in await page.inner_text("#pick"):
            failures.append("“其他尺寸”应该已经换成小四方型")
        clip = await page.evaluate("document.getElementById('scW').style.clipPath")
        if "inset" not in clip:
            failures.append(f"方塘的水面形状不对: {clip}")
        await page.click('.pond[data-k="round"]')
        await page.wait_for_timeout(30)
        if "ellipse" not in await page.evaluate("document.getElementById('scW').style.clipPath"):
            failures.append("圆塘的水面应该是圆的")
        # 两台对角：一上一下、一左一右，推水方向相反
        angles = await page.evaluate("""Array.from(document.querySelectorAll('#scO use')).map(function(u){var m=/translate\\(([\\d.]+) ([\\d.]+)\\) rotate\\(([\\d.]+)\\)/.exec(u.getAttribute('transform'));return [+m[1],+m[2],+m[3]];})""")
        (x1, y1, a1), (x2, y2, a2) = angles
        if not ((x1 - 180) * (x2 - 180) < 0 and (y1 - 112.5) * (y2 - 112.5) < 0 and abs(abs(a1 - a2) - 180) < 1):
            failures.append(f"圆塘的两台没有对角对打: {angles}")
        await page.click('.pond[data-k="sqM"]')

        # 点池塘卡片换结果；口塘数只乘总数，不改每口塘的数字
        await page.click('.pond[data-k="rcL"]')
        await page.wait_for_timeout(50)
        await has("#hero", "Rp 43,2 juta", "选大长方型")
        await has("#ladD", "Rp 43.207.643", "大长方型每年")
        await page.fill("#nPonds", "30")
        await page.wait_for_timeout(50)
        await has("#hero", "Rp 1,30 miliar", "30 口塘的年节省")
        await has("#ladD", "Rp 43.207.643", "每口塘的数字不能变")
        await has("#ladD", "Rp 1.296.229.292", "30 口塘的合计")
        await has("#totLine", "720 kincir", "总台数")
        await page.fill("#nPonds", "1")

        # 加减水车数量，完整表跟着变
        await page.click('.pond[data-k="sqM"]')
        await page.click('[data-st="units"][data-d="1"]')
        await page.wait_for_timeout(50)
        if await page.input_value("#u_sqM") != "11":
            failures.append("加一台后完整表没有同步")
        await has("#ladD", "Rp 19.803.503", "11 台每年")
        await page.click('[data-st="units"][data-d="-1"]')

        # 在表格里改数量，光标不能丢
        await page.fill("#u_sqL", "")
        await page.keyboard.type("20")
        await page.wait_for_timeout(50)
        if await page.input_value("#u_sqL") != "20":
            failures.append(f"表格里改数量失败: {await page.input_value('#u_sqL')!r}")
        got = await page.inner_text('tr[data-k="sqL"] td[data-c="Q"]')
        if got != "36.006.369":
            failures.append(f"表格里改成 20 台后年节省不对: {got}")
        await page.click("#reset")
        await page.wait_for_timeout(50)

        # 节电率、电价、天数都走公式
        await page.evaluate('document.getElementById("params").open=true')
        await page.fill("#iOld", "1.25")
        await page.wait_for_timeout(50)
        await has("#hero", "Hemat 20%", "电流改成 1.25 A 后节电率 = 20%")
        await has("#hero", "1,25 A", "电流要跟着变")
        await has("#ladD", "Rp 15.602.760", "节电率 20%")
        await page.click("#reset")
        await page.click('#tariffChips .chip[data-v="1114.74"]')
        await page.wait_for_timeout(50)
        await has("#ladD", "Rp 13.891.375", "B-3 / I-3 电价")
        await page.click("#reset")

        # 价格：回本时间按年，和 Excel 的 U 列一样；新款不贵时显示“立即”
        await page.fill("#pOld", "1000000")
        await page.fill("#pNew", "1500000")
        await page.wait_for_timeout(50)
        if await page.input_value("#pOld") != "1.000.000":
            failures.append(f"价格没有加千分位: {await page.input_value('#pOld')!r}")
        await has("#ladI", "Rp 10.000.000", "传统投资 10 台")
        await has("#ladI", "Rp 15.000.000", "永磁投资 10 台")
        await has("#ladI", "Rp 5.000.000", "多投入")
        await has("#ladI", "+50%", "贵百分之几")
        await has("#ladI", "0,3 tahun", "回本 5,000,000 / 18,003,185 = 0.28 年")
        await has("#ladI", "sekitar 3 bulan", "回本的月数")
        got = await page.inner_text('tr[data-k="rcL"] td[data-c="U"]')
        if got != "0,3":
            failures.append(f"完整表的回本时间不对: {got}")
        await page.fill("#pNew", "1000000")
        await page.wait_for_timeout(50)
        await has("#ladI", "Langsung", "多投入不大于 0 时显示立即")
        await page.fill("#pNew", "")
        await page.wait_for_timeout(50)
        if await page.inner_text('tr[data-k="rcL"] td[data-c="U"]'):
            failures.append("只填一个价格时回本时间应该是空的")
        await page.click("#reset")

        # 以旧换新：最低售价 Rp 2,023,313（550 元 × 2725 × 1.35）；每台每年省 Rp 1,800,318；约 13 个月回本
        await has("#trade", "Program tukar tambah", "以旧换新政策要有标题")
        await has("#trade", "Cukup ganti motor dan gearbox (unit utamanya).", "客户定的这句话")
        await has("#trPol", "motor dan gearbox lama, diganti dengan motor magnet permanen dan kontroler inverter", "政策要写换什么")
        await has("#trPol", "tetap dipakai", "政策要写其他配件不换")
        await has("#trPol", "mulai dari Rp 2.023.313", "政策要写最低售价")
        if await page.input_value("#pTrade") != "2.023.313":
            failures.append(f"售价框不对: {await page.input_value('#pTrade')!r}")
        await has("#ladT", "Rp 2.023.313", "每台售价")
        await has("#ladT", "0,173", "每台省功率")
        await has("#ladT", "Rp 6.001", "每天省电费")
        await has("#ladT", "Rp 720.127", "每造省电费")
        await has("#ladT", "Rp 1.800.318", "每年省电费")
        await has("#ladT", "± 13 bulan", "回本月数")
        await has("#ladT", "337 hari", "回本运转天数")
        await has("#ladT", "2,8 siklus", "回本造数")
        await has("#ladTP", "Rp 20.233.130", "10 台总售价")
        await has("#ladTP", "Rp 18.003.185", "10 台每年省")
        visible = await page.inner_text("#trade")
        for word in ("CNY", "¥", "550", "1,35", "35%"):
            if word in visible:
                failures.append(f"客户不能看到成本或加价: {word}")
        await page.fill("#pTrade", "1500000")
        await page.wait_for_timeout(50)
        await has("#ladT", "± 10 bulan", "改售价后回本")
        await page.fill("#pTrade", "")
        await page.wait_for_timeout(50)
        if "—" not in await page.inner_text("#ladT"):
            failures.append("售价清空后应该显示 —")
        await page.evaluate('document.getElementById("params").open=true')
        await page.click("#reset")
        await page.wait_for_timeout(50)
        if await page.input_value("#pTrade") != "2.023.313":
            failures.append(f"恢复后售价不对: {await page.input_value('#pTrade')!r}")

        # 三语切换
        await page.click(".lang button[data-l=en]")
        await page.wait_for_timeout(100)
        await has("#hero", "Rp 18.0 million", "切换英语")
        await page.click(".lang button[data-l=zh]")
        await page.wait_for_timeout(100)
        await has("#hero", "Rp 1,800万", "切换中文")
        await has("#trade", "以旧换新政策", "中文要写以旧换新政策")
        await has("#trade", "旧电机和减速机，换成永磁电机和变频控制器", "中文政策")
        await has("#trade", "每台最低 Rp 2,023,313", "中文政策要写最低售价")
        await has("#ladT", "约 13 个月", "中文回本时间")
        await has("#compare", "旺佳 永磁变频水车", "中文要和 Excel 的品牌一样")
        await page.click(".lang button[data-l=id]")
        await page.wait_for_timeout(100)

        # 填过的价格要跟着语言换写法，而且数字不变
        await page.fill("#pOld", "1000000")
        await page.click(".lang button[data-l=en]")
        await page.wait_for_timeout(50)
        if await page.input_value("#pOld") != "1,000,000":
            failures.append(f"换语言后价格写法不对: {await page.input_value('#pOld')!r}")
        await page.click(".lang button[data-l=id]")
        await page.click("#reset")

        # 刷新后还记得选择
        await page.click('.pond[data-k="sqL"]')
        await page.wait_for_timeout(50)
        await page.reload()
        await page.wait_for_timeout(200)
        await has("#hero", "Persegi besar", "刷新后还是上次选的池塘")
        await page.click("#reset")

        # 两款的照片和 Logo 要真的显示出来，点照片能放大，再点关闭；安卓返回键也能关
        loaded = await page.evaluate("Array.from(document.querySelectorAll('[data-zoom] img,.logo,.scene img,.pond img,#keyImg')).map(function(i){return i.naturalWidth})")
        if len(loaded) != 18 or min(loaded) == 0:
            failures.append(f"照片或 Logo 没有显示出来: {loaded}")
        await page.click('[data-zoom="nB"]')
        await page.wait_for_timeout(50)
        if await page.is_hidden("#zoom") or "WANGJIA" not in await page.inner_text("#zoomCap"):
            failures.append("点照片没有放大")
        if not await page.evaluate("window.hematBack()") or not await page.is_hidden("#zoom"):
            failures.append("安卓返回键关不掉放大的照片")
        if await page.evaluate("window.hematBack()"):
            failures.append("照片已经关了，返回键应该交给系统")
        await page.click('[data-zoom="nA"]')
        await page.wait_for_timeout(50)
        await page.click("#zoomX")
        if not await page.is_hidden("#zoom"):
            failures.append("点关闭没有关掉放大的照片")

        # 手机宽度不能横向滚动，三种语言都查（第一屏要看到结果，在下面的各种屏幕里查）
        mobile = await browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda e: errors.append(str(e)))
        await mobile.goto(INDEX)
        await mobile.wait_for_timeout(200)
        for lang in ("id", "en", "zh"):
            await mobile.click(f".lang button[data-l={lang}]")
            await mobile.wait_for_timeout(150)
            for mode in ("#tShort", "#tFull"):
                await mobile.click(mode)
                await mobile.wait_for_timeout(50)
                width = await mobile.evaluate("document.documentElement.scrollWidth")
                if width > 390:
                    failures.append(f"手机宽度出现横向滚动 lang={lang} {mode} scrollWidth={width}")
            await mobile.click("#tShort")
            over = await mobile.evaluate("(function(){var t=document.getElementById('tbl');return t.scrollWidth-t.parentElement.clientWidth;})()")
            if over > 1:
                failures.append(f"手机上简表超出 {over}px lang={lang}")

        # 各种屏幕：竖屏小屏到大屏、折叠屏、横屏，每种再试系统大字体和偏宽的字体（不同品牌手机字体宽度差很多）
        fit = await browser.new_page()
        fit.on("pageerror", lambda e: errors.append(str(e)))
        await fit.goto(INDEX)
        # 折叠区域也要查，而且收起的内容不会重新排版，量出来的尺寸不准，所以全部展开
        await fit.evaluate("document.querySelectorAll('details').forEach(function(d){d.open=true})")
        for width, height in SCREENS:
            await fit.set_viewport_size({"width": width, "height": height})
            for scale, font in (STYLES if width < 720 else STYLES[:1]):
                await fit.evaluate(SET_STYLE, [scale, font])
                for lang in ("id", "en", "zh"):
                    await fit.click(f".lang button[data-l={lang}]")
                    await fit.wait_for_timeout(60)
                    where = f"{width}x{height} 字体 {scale} {font or '默认'} {lang}"
                    problems = await fit.evaluate(FIT_PROBE)
                    if problems:
                        failures.append(f"{where}: {problems}")
                    # 打开这一屏时要看得到结果：大数字在屏幕内，或者底部结果条已经出现
                    seen = await fit.evaluate("(function(){var r=document.querySelector('.hv').getBoundingClientRect();return r.bottom<=innerHeight||!document.getElementById('mbar').classList.contains('off');})()")
                    if not seen:
                        failures.append(f"{where}: 第一屏看不到结果")
        await fit.evaluate(SET_STYLE, [1, None])
        await fit.click(".lang button[data-l=id]")

        # 横屏：结果和选塘要同时在第一屏
        await fit.set_viewport_size({"width": 800, "height": 360})
        await fit.wait_for_timeout(100)
        if not await fit.evaluate("document.querySelector('.hv').getBoundingClientRect().bottom<=innerHeight"):
            failures.append("横屏时年节省不在第一屏")

        # 底部结果条：滚走大数字后出现，内容跟着变，点一下回到结果
        await fit.set_viewport_size({"width": 390, "height": 844})
        await fit.evaluate("document.getElementById('hero').scrollIntoView({block:'center'})")
        await fit.wait_for_timeout(200)
        if not await fit.evaluate("document.getElementById('mbar').classList.contains('off')"):
            failures.append("大数字在屏幕内时不应该显示底部结果条")
        await fit.evaluate("window.scrollTo(0,1500)")
        await fit.wait_for_timeout(250)
        if "Rp 18,0 juta" not in await fit.inner_text("#mbar"):
            failures.append(f"底部结果条不对: {await fit.inner_text('#mbar')!r}")
        await fit.click("#mbar")
        await fit.wait_for_timeout(700)
        if not await fit.evaluate("document.getElementById('mbar').classList.contains('off')"):
            failures.append("点结果条后应该回到结果")

        # 完整表在手机上要提示可以滑动
        await fit.click("#tFull")
        await fit.wait_for_timeout(50)
        if await fit.is_hidden("#swipe"):
            failures.append("手机上的完整表应该提示左右滑动")
        await fit.click("#tShort")

        if errors:
            failures.append(f"JS 报错: {errors}")
        await browser.close()

    # Excel 模板：缓存结果要和上面的公式一样，以旧换新那张表也要对
    book = load_workbook(XLSX, data_only=True)
    ws = book["Perbandingan"]
    for row in EXPECTED.values():
        r = row["row"]
        if ws[f"D{r}"].value != row["D"]:
            failures.append(f"Excel D{r}: {ws[f'D{r}'].value}")
        for col in "FGHIJKLMNOPQ":
            got = ws[f"{col}{r}"].value
            if got is None or abs(got - row[col]) > 1e-6:
                failures.append(f"Excel {col}{r}: 期望 {row[col]}，实际 {got}")
    if abs(ws["B12"].value - RATE) > 1e-9 or abs(ws["B13"].value - KW * (1 - RATE)) > 1e-9:
        failures.append(f"Excel 节电率或平均功率不对: {ws['B12'].value} {ws['B13'].value}")
    if ws["B15"].value is not None or ws["B16"].value is not None:
        failures.append("Excel 里不能有新水车的价格")
    tt = book["Tukar tambah"]
    one = pond(0, 1, 1)
    for cell, want in {"B9": TRADE_RP, "B12": one["L"], "B14": one["M"] * TARIFF, "B15": one["O"], "B16": one["Q"], "B17": TRADE_RP / (one["M"] * TARIFF), "B19": TRADE_RP / one["Q"] * 12}.items():
        got = tt[cell].value
        if got is None or abs(got - want) > 1e-3:
            failures.append(f"Excel 以旧换新 {cell}: 期望 {want}，实际 {got}")

    # 这个 Excel 要发给客户：两张表都不能出现人民币价和加价比例
    for sheet in book.worksheets:
        for cells in sheet.iter_rows():
            for cell in cells:
                if isinstance(cell.value, str) and any(w in cell.value for w in ("CNY", "人民币", "1.35", "1,35")):
                    failures.append(f"Excel {sheet.title} {cell.coordinate} 出现了成本信息: {cell.value[:40]}")
                if cell.value in (550, 2725, 1.35):
                    failures.append(f"Excel {sheet.title} {cell.coordinate} 出现了成本数字: {cell.value}")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("PASS: 6 种池塘每列数字、从小到大排列、3D 效果图、选塘、口塘数、节电率、电价、价格回本、以旧换新政策和回本、三语、记住选择、照片和 Logo、手机布局、11 种屏幕和大字体、底部结果条、Excel、无 JS 报错")


if __name__ == "__main__":
    asyncio.run(main())
