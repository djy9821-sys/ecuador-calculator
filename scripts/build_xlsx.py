#!/usr/bin/env python3
"""
生成印尼版的 Excel 对比表，两张表：
  Perbandingan：公式和客户的《池塘水车耗电对比》一样，A–U 列。多了两款水车的电流（节电率由电流算出来）和小四方型，
                池塘按面积排序。文字换成印尼语 + 中文，右上角有 Logo 和两款水车的照片。
  Tukar tambah：以旧换新政策和回本计算，数字都引用第一张表。
默认值要和 indonesia.html 的 BASE、PONDS 一致。

用 XlsxWriter 而不是 openpyxl：它能给公式写入缓存结果，
这样手机预览、WhatsApp 预览这些不重新计算的地方也能看到数字。

准备：pip install xlsxwriter
运行（在仓库根目录）：python3 scripts/build_xlsx.py
输出：dist/perbandingan-hemat-listrik-kincir.xlsx
"""
import math
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "perbandingan-hemat-listrik-kincir.xlsx"
ASSETS = ROOT / "assets"

# 和 indonesia.html 的 BASE 保持一致。新水车的价格留空，只在页面或 Excel 里填。
DAYS, HOURS, CYCLES, KW_OLD, I_OLD, I_NEW, TARIFF = 120, 24, 2.5, 0.75, 1.3, 1.0, 1444.7
# 以旧换新的最低售价 = 550 元人民币 × 汇率 2725（2026-11-03）× 1.35，取整到 1 印尼盾。
# 这个文件要发给客户，所以表里只写印尼盾售价，不写人民币和加价比例。
TRADE_RP = 2023313
# 产品品牌：产品上的拉丁字母写法，和客户表格里的中文名
BRAND, BRAND_ZH = "WANGJIA", "旺佳"
NEW_ID, NEW_ZH = f"Kincir magnet permanen {BRAND}", f"{BRAND_ZH} 永磁变频水车"
# 按面积从小到大。台数和摆法是客户后来定的。
PONDS = [
    ("Bundar · 圆型", "Ø 8 m · 直径 8 米", None, 2),
    ("Persegi kecil · 小四方型", "20 × 20 m · 20 × 20 米", 400, 6),
    ("Persegi sedang · 中四方型", "30 × 30 m · 30 × 30 米", 900, 10),
    ("Persegi panjang sedang · 中长方型", "30 × 50 m · 30 × 50 米", 1500, 16),
    ("Persegi besar · 大四方型", "50 × 50 m · 50 × 50 米", 2500, 16),
    ("Persegi panjang besar · 大长方型", "50 × 80 m · 50 × 80 米", 4000, 24),
]
ROUND_AREA = math.pi * (8 / 2) ** 2
NOW = "Langsung · 立即"
# 公式结果为空时的缓存值。写空字符串的话，手机预览会显示 0。
BLANK = " "
# 和客户表格一样的颜色，B 列换成 WANGJIA 的蓝色
CHAR, GREY, NAVY, GREEN, DEEP, ORANGE = "#404040", "#7F7F7F", "#1066DC", "#548235", "#375623", "#C55A11"
INPUT, HOT, BLUE, HEAD, HL, LINE, MUTED = "#FFF2CC", "#FFFF00", "#0000FF", "#F2F2F2", "#E2EFDA", "#BFBFBF", "#595959"
INT0, DEC2, DEC1 = "#,##0;\\(#,##0\\);\\-", "#,##0.00;\\(#,##0.00\\);\\-", "#,##0.0;\\(#,##0.0\\);\\-"
# 第一张表的单元格位置
R_DAYS, R_HOURS, R_CYCLES, R_KW, R_IOLD, R_INEW, R_RATE, R_KWNEW, R_TARIFF, R_POLD, R_PNEW = 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
R_BAND, R_HEAD, R_FIRST = 18, 19, 20
SHEET1 = "Perbandingan"


def main():
    OUT.parent.mkdir(exist_ok=True)
    wb = xlsxwriter.Workbook(str(OUT))
    wb.set_properties({"title": f"{BRAND} · Perbandingan Listrik Kincir · 池塘水车耗电对比"})
    ws = wb.add_worksheet(SHEET1)

    def f(**kw):
        base = {"font_name": "Arial", "font_size": 10, "valign": "vcenter"}
        base.update(kw)
        return wb.add_format(base)

    grid = {"border": 1, "border_color": LINE}
    title = f(bold=True, font_size=14)
    sub = f(font_color=MUTED)
    h2 = f(bold=True, font_size=11)
    head_dark = f(bold=True, font_color="#FFFFFF", bg_color=CHAR, align="center", **grid)
    label = f(text_wrap=True, **grid)
    unit = f(align="center", text_wrap=True, **grid)
    note = f(text_wrap=True, **grid)
    head = f(bold=True, bg_color=HEAD, align="center", text_wrap=True, font_size=9, **grid)
    name = f(bold=True, align="center", text_wrap=True, **grid)
    spec = f(align="center", text_wrap=True, **grid)
    plain = f(font_color=MUTED, text_wrap=True)
    photo = f(align="center", font_color=MUTED, text_wrap=True, **grid)

    def band(color):
        return f(bold=True, font_color="#FFFFFF", bg_color=color, align="center", font_size=11, text_wrap=True, **grid)

    def inp(num_format, hot=False):
        return f(bg_color=HOT if hot else INPUT, font_color=BLUE, bold=hot, num_format=num_format, **grid)

    def out(num_format, **kw):
        return f(num_format=num_format, **grid, **kw)

    def hl(num_format):
        return f(num_format=num_format, bold=True, bg_color=HL, font_color=DEEP, **grid)

    ws.hide_gridlines(2)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
    widths = {"A": 40, "B": 18, "C": 16, "D": 11, "E": 12, "F": 9, "G": 11, "H": 14, "I": 9, "J": 11, "K": 14,
              "L": 12, "M": 11, "N": 11, "O": 14, "P": 11, "Q": 18, "R": 15, "S": 15, "T": 14, "U": 16}
    for col, width in widths.items():
        ws.set_column(f"{col}:{col}", width)
    ws.freeze_panes(0, 1)

    ws.write("A1", f"{BRAND} · Perbandingan Listrik Kincir · 池塘水车耗电对比：传统水车 vs {NEW_ZH}", title)
    ws.insert_image("M1", str(ASSETS / "wangjia-logo-blue.png"), {"x_scale": 0.34, "y_scale": 0.34, "y_offset": 4, "object_position": 3, "description": BRAND})
    ws.write("A2", "Sel kuning boleh diubah, sel lain dihitung otomatis. · 黄色底的格子可以改，其余格子自动计算。", sub)
    ws.set_row(0, 21)

    # 计算参数
    ws.write("A4", "Angka dasar · 计算参数", h2)
    ws.write("A5", "Parameter · 参数", head_dark)
    ws.write("B5", "Nilai · 数值", head_dark)
    ws.write("C5", "Satuan · 单位", head_dark)
    ws.merge_range("D5:J5", "Keterangan · 说明", head_dark)
    i_int, i_dec1, i_dec2, i_rp = inp(INT0), inp("0.0"), inp(DEC2), inp("#,##0.00")
    rows = [
        (R_DAYS, "Hari per siklus · 每造养殖天数", DAYS, i_int, "hari · 天", "Dari persiapan air sampai panen · 从做水到收成"),
        (R_HOURS, "Jam nyala per hari · 每天运转小时", HOURS, i_int, "jam · 小时", "Nyala terus 24 jam · 24 小时连续开机"),
        (R_CYCLES, "Siklus per tahun · 每年养殖造数", CYCLES, i_dec1, "siklus/tahun · 造/年", "Sekitar 2,5 siklus setahun · 一年约 2.5 造"),
        (R_KW, "Daya kincir biasa · 传统水车单台功率", KW_OLD, i_dec2, "kW/unit · kW/台", "1 HP = 0,75 kW, listrik 3 fase. Motor kincir magnet permanen juga 0,75 kW. · 按 1HP = 0.75 kW 计，三相电。永磁变频水车的电机也是 0.75 kW。"),
        (R_IOLD, "Arus kincir biasa · 传统水车电流", I_OLD, i_dec2, "A", "Listrik 3 fase · 三相电"),
        (R_INEW, f"Arus kincir magnet permanen · {BRAND_ZH} 永磁变频水车电流", I_NEW, i_dec2, "A", "Listrik 3 fase · 三相电"),
    ]
    for row, a, val, fmt, u, nt in rows:
        ws.write(f"A{row}", a, label)
        ws.write_number(f"B{row}", val, fmt)
        ws.write(f"C{row}", u, unit)
        ws.merge_range(f"D{row}:J{row}", nt, note)
    rate = max(0, 1 - I_NEW / I_OLD)
    kw_new = KW_OLD * (1 - rate)
    ws.write(f"A{R_RATE}", "Penghematan listrik · 节电率", label)
    ws.write_formula(f"B{R_RATE}", f"=IF(B{R_IOLD}>0,MAX(0,1-B{R_INEW}/B{R_IOLD}),0)", out("0.0%", bold=True), rate)
    ws.write(f"C{R_RATE}", "%", unit)
    ws.merge_range(f"D{R_RATE}:J{R_RATE}", "Otomatis = 1 − arus magnet permanen ÷ arus kincir biasa. P = √3 × V × I × cos φ, jadi kalau tegangan dan faktor daya sama, daya sebanding dengan arus. · 自动计算 = 1 − 永磁变频电流 ÷ 传统水车电流。电压和功率因数相同时，功率和电流成正比。", note)
    ws.write(f"A{R_KWNEW}", "Daya rata-rata magnet permanen · 永磁变频单台平均功率", label)
    ws.write_formula(f"B{R_KWNEW}", f"=B{R_KW}*(1-B{R_RATE})", out("0.000"), kw_new)
    ws.write(f"C{R_KWNEW}", "kW/unit · kW/台", unit)
    ws.merge_range(f"D{R_KWNEW}:J{R_KWNEW}", "Otomatis = daya kincir biasa × (1 − penghematan) · 自动计算 = 传统功率 × (1 − 节电率)", note)
    ws.write(f"A{R_TARIFF}", "Tarif listrik · 印尼电价", label)
    ws.write_number(f"B{R_TARIFF}", TARIFF, i_rp)
    ws.write(f"C{R_TARIFF}", "Rp/kWh", unit)
    ws.merge_range(f"D{R_TARIFF}:J{R_TARIFF}", "PLN B-2 (6.600 VA–200 kVA), Okt–Des 2026, belum termasuk pajak. Di atas 200 kVA (B-3 / I-3): 1.114,74. · PLN B-2 商业用电，2026 年第四季度，不含税费；200 kVA 以上的 B-3 / I-3 用户改为 1,114.74。", note)
    ws.write(f"A{R_POLD}", "Harga kincir biasa · 传统水车单价", label)
    ws.write_blank(f"B{R_POLD}", None, inp(INT0, hot=True))
    ws.write(f"C{R_POLD}", "Rp/unit · Rp/台", unit)
    ws.merge_range(f"D{R_POLD}:J{R_POLD}", "Untuk beli baru. Isi harga, investasi dan balik modal dihitung otomatis. Tukar tambah: lihat lembar berikutnya. · 买新水车用。填入后自动算投资与回本。以旧换新见下一张表。", note)
    ws.write(f"A{R_PNEW}", f"Harga kincir magnet permanen {BRAND} · {NEW_ZH}单价", label)
    ws.write_blank(f"B{R_PNEW}", None, inp(INT0, hot=True))
    ws.write(f"C{R_PNEW}", "Rp/unit · Rp/台", unit)
    ws.merge_range(f"D{R_PNEW}:J{R_PNEW}", "Untuk beli baru. Isi harga, investasi dan balik modal dihitung otomatis. · 买新水车用。填入后自动算投资与回本。", note)
    for row in range(R_DAYS, R_PNEW + 1):
        ws.set_row(row - 1, 28)
    ws.set_row(R_KW - 1, 30)
    ws.set_row(R_RATE - 1, 42)
    ws.set_row(R_TARIFF - 1, 42)

    # 两款的照片（放在参数表右边的空位，不影响任何公式）。
    # 从 M 列开始，空出 K、L 两列：有些预览（如手机上的快速查看）算出的图片位置偏左，不能盖住说明文字。
    ws.merge_range("M4:P4", "A · Foto kincir biasa · 传统水车照片", band(GREY))
    ws.merge_range("Q4:U4", f"B · {NEW_ID} · {NEW_ZH}照片", band(NAVY))
    ws.merge_range(f"M5:P{R_PNEW}", "", photo)
    ws.merge_range(f"Q5:U{R_PNEW}", "", photo)
    ws.insert_image("M5", str(ASSETS / "wangjia-biasa.jpg"), {"x_scale": 0.322, "y_scale": 0.322, "x_offset": 3, "y_offset": 70, "object_position": 1, "description": "Kincir biasa · 传统水车"})
    ws.insert_image("Q5", str(ASSETS / "wangjia-magnet.jpg"), {"x_scale": 0.458, "y_scale": 0.458, "x_offset": 10, "y_offset": 55, "object_position": 1, "description": f"{NEW_ID} · {NEW_ZH}"})

    # 池塘表
    ws.merge_range(f"A{R_BAND}:E{R_BAND}", "Kolam · 池塘", band(CHAR))
    ws.merge_range(f"F{R_BAND}:H{R_BAND}", "A  Kincir biasa · 传统水车", band(GREY))
    ws.merge_range(f"I{R_BAND}:K{R_BAND}", f"B  {NEW_ID} · {NEW_ZH}", band(NAVY))
    ws.merge_range(f"L{R_BAND}:O{R_BAND}", "C  Hemat listrik (per kolam) · 节电（每口塘）", band(GREEN))
    ws.merge_range(f"P{R_BAND}:Q{R_BAND}", "D  Hemat per tahun (per kolam) · 每年节省（每口塘）", band(DEEP))
    ws.merge_range(f"R{R_BAND}:U{R_BAND}", "Investasi kincir baru (isi harga) · 新水车投资对比（填单价后自动算）", band(ORANGE))
    ws.set_row(R_BAND - 1, 32)
    heads = [
        "Jenis kolam\n池塘类型", "Ukuran\n规格", "Luas\n面积\n(m²)", "Kincir\n水车数量\n(unit·台, 1HP)", "Luas per kincir\n每台负责面积\n(m²/unit·台)",
        "Total daya\n总功率\n(kW)", "Listrik\n耗电量\n(kWh/siklus·造)", "Biaya\n电费\n(Rp/siklus·造)",
        "Total daya\n总功率\n(kW)", "Listrik\n耗电量\n(kWh/siklus·造)", "Biaya\n电费\n(Rp/siklus·造)",
        "Hemat per jam\n每小时节电\n(kWh/jam·小时)", "Hemat per hari\n每天节电\n(kWh/hari·天)", "Hemat per siklus\n每造节电\n(kWh/siklus·造)", "Hemat biaya per siklus\n每造省电费\n(Rp/siklus·造)",
        "Hemat per tahun\n每年节电\n(kWh/tahun·年)", "Hemat biaya, 2,5 siklus\n每年（2.5造）省电费\n(Rp/tahun·年)",
        "Investasi kincir biasa\n传统水车投资\n(Rp)", "Investasi magnet permanen\n永磁变频投资\n(Rp)", "Tambahan modal\n多投入\n(Rp)", "Balik modal\n回本时间\n(tahun·年)",
    ]
    for col, txt in enumerate(heads):
        ws.write(R_HEAD - 1, col, txt, head)
    ws.set_row(R_HEAD - 1, 66)

    i_cell = inp(INT0)
    o_int, o_dec2, o_dec1 = out(INT0), out(DEC2), out(DEC1)
    h_int = hl(INT0)
    o_yr = out("0.0;\\(0.0\\);\\-", align="right")
    pond_rows = []
    for i, (a, b, area, units) in enumerate(PONDS):
        r = R_FIRST + i
        ws.set_row(r - 1, 28)
        ws.write(f"A{r}", a, name)
        ws.write(f"B{r}", b, spec)
        if area is None:
            ws.write_formula(f"C{r}", "=PI()*(8/2)^2", i_cell, ROUND_AREA)
            area = ROUND_AREA
        else:
            ws.write_number(f"C{r}", area, i_cell)
        ws.write_number(f"D{r}", units, i_cell)
        # Python 里算一遍同样的结果，写成公式的缓存值
        F = units * KW_OLD
        G = F * HOURS * DAYS
        H = G * TARIFF
        I = units * kw_new
        J = I * HOURS * DAYS
        K = J * TARIFF
        L = F - I
        M = L * HOURS
        N = M * DAYS
        O = N * TARIFF
        P = N * CYCLES
        Q = O * CYCLES
        F, G, H, I, J, K, L, M, N, O, P, Q = (round(v, 9) for v in (F, G, H, I, J, K, L, M, N, O, P, Q))
        ws.write_formula(f"E{r}", f'=IF(D{r}=0,"",C{r}/D{r})', o_int, area / units)
        ws.write_formula(f"F{r}", f"=D{r}*$B${R_KW}", o_dec2, F)
        ws.write_formula(f"G{r}", f"=F{r}*$B${R_HOURS}*$B${R_DAYS}", o_int, G)
        ws.write_formula(f"H{r}", f"=G{r}*$B${R_TARIFF}", o_int, H)
        ws.write_formula(f"I{r}", f"=D{r}*$B${R_KWNEW}", o_dec2, I)
        ws.write_formula(f"J{r}", f"=I{r}*$B${R_HOURS}*$B${R_DAYS}", o_int, J)
        ws.write_formula(f"K{r}", f"=J{r}*$B${R_TARIFF}", o_int, K)
        ws.write_formula(f"L{r}", f"=F{r}-I{r}", o_dec2, L)
        ws.write_formula(f"M{r}", f"=L{r}*$B${R_HOURS}", o_dec1, M)
        ws.write_formula(f"N{r}", f"=M{r}*$B${R_DAYS}", h_int, N)
        ws.write_formula(f"O{r}", f"=N{r}*$B${R_TARIFF}", o_int, O)
        ws.write_formula(f"P{r}", f"=N{r}*$B${R_CYCLES}", o_int, P)
        ws.write_formula(f"Q{r}", f"=O{r}*$B${R_CYCLES}", h_int, Q)
        ws.write_formula(f"R{r}", f'=IF($B${R_POLD}="","",D{r}*$B${R_POLD})', o_int, BLANK)
        ws.write_formula(f"S{r}", f'=IF($B${R_PNEW}="","",D{r}*$B${R_PNEW})', o_int, BLANK)
        ws.write_formula(f"T{r}", f'=IF(OR(R{r}="",S{r}=""),"",S{r}-R{r})', o_int, BLANK)
        ws.write_formula(f"U{r}", f'=IF(OR(T{r}="",Q{r}=0),"",IF(T{r}<=0,"{NOW}",T{r}/Q{r}))', o_yr, BLANK)
        pond_rows.append((r, a, units, Q))

    # 说明
    r_notes = R_FIRST + len(PONDS) + 1
    ws.write(f"A{r_notes}", "Keterangan · 说明", h2)
    notes = [
        "Susunan kincir: bundar 2 (diagonal, arah dorong berlawanan); 20×20: luar 4, dalam 2; 30×30: luar 6, dalam 4; 30×50 dan 50×50: luar 10, dalam 6; 50×80: lingkar 1 12, lingkar 2 8, lingkar 3 4. · 水车布置：圆型 2 台对角对打；20×20 外圈 4、内圈 2；30×30 外圈 6、内圈 4；30×50 和 50×50 外圈 10、内圈 6；50×80 第一圈 12、第二圈 8、第三圈 4。",
        "Sel kuning boleh diubah. Kuning terang berarti masih perlu diisi: harga kincir baru. · 黄色底可以改；亮黄色表示还要补填（新水车的单价）。",
        "A dan B: listrik dan biaya untuk 120 hari × 24 jam, jumlah kincir sama. · A、B 列组：按 120 天 × 24 小时、相同台数计算。",
        "C: selisih daya × jam per hari × hari per siklus × tarif listrik. · C 列组：先算每小时，再乘每天小时数，再乘每造天数，最后乘电价换成 Rp。",
        "D: hemat per siklus × 2,5 siklus per tahun. · D 列组：每造节省 × 每年 2.5 造。",
        f"Investasi kincir baru: isi B{R_POLD} dan B{R_PNEW}. Balik modal = tambahan modal ÷ hemat biaya per tahun. · 新水车投资：在 B{R_POLD}、B{R_PNEW} 填单价。回本时间 = 多投入 ÷ 每年省电费。",
        "Penghematan dihitung dari arus, dengan tegangan dan faktor daya yang sama. Hasil nyata tergantung kolam dan cara pakai. Ukur dengan kWh meter sebelum mengambil keputusan. · 节电率按电流计算，前提是电压和功率因数相同。实际结果取决于池塘和使用方式，做决定前请用电表实测。",
        "Tarif: MetroTV News mengutip ESDM, tarif PLN kuartal IV 2026 tidak berubah (B-2 Rp 1.444,70/kWh; B-3 / I-3 Rp 1.114,74/kWh), belum termasuk pajak dan biaya lain. · 电价来源：MetroTV News 引用 ESDM，PLN 2026 年第四季度电价不变，不含税费等其他费用。",
    ]
    for i, txt in enumerate(notes):
        ws.merge_range(r_notes + i, 0, r_notes + i, 10, "• " + txt, plain)
        ws.set_row(r_notes + i, 28)
    r_url = r_notes + len(notes) + 1
    ws.write_url(f"A{r_url}", "https://www.metrotvnews.com/read/NA0CzpEz-daftar-lengkap-tarif-listrik-pln-akhir-oktober-2026-per-kwh", string="metrotvnews.com · Daftar Lengkap Tarif Listrik PLN Akhir Oktober 2026")
    ws.print_area(f"A1:U{r_url}")

    # ---- 第二张表：以旧换新 ----
    t = wb.add_worksheet("Tukar tambah")
    t.hide_gridlines(2)
    t.set_landscape()
    t.set_paper(9)
    t.fit_to_pages(1, 0)
    t.set_column("A:A", 50)
    t.set_column("B:B", 18)
    t.set_column("C:C", 18)
    t.set_column("D:E", 22)
    t.write("A1", f"{BRAND} · Program tukar tambah · 以旧换新政策", title)
    t.insert_image("D1", str(ASSETS / "wangjia-logo-blue.png"), {"x_scale": 0.34, "y_scale": 0.34, "y_offset": 2, "object_position": 3, "description": BRAND})
    t.set_row(0, 24)
    policy = [
        "Untuk: tambak yang sudah memakai kincir biasa. · 适用：养殖场里已经在用传统水车的客户。",
        "Yang diganti: motor dan gearbox lama, diganti dengan motor magnet permanen dan kontroler inverter. · 更换：旧电机和减速机，换成永磁电机和变频控制器。",
        "Yang tidak diganti: semua komponen lain (rangka, pelampung, kipas, as) tetap dipakai. · 不换：其他配件都不换，支架、浮筒、叶轮、轴继续用。",
        "Cek dulu: lubang dudukan unit baru harus cocok dengan rangka lama. · 先确认：新主机的安装孔要能对上老支架。",
    ]
    for i, txt in enumerate(policy):
        t.merge_range(2 + i, 0, 2 + i, 4, "• " + txt, f(text_wrap=True))
        t.set_row(2 + i, 18)
    t.merge_range("A8:C8", "Harga · 售价", band(ORANGE))
    t.write("A9", "Harga terendah per kincir · 每台最低售价", f(bold=True, text_wrap=True, **grid))
    t.write_number("B9", TRADE_RP, inp(INT0))
    t.write("C9", "Rp", unit)
    unit_cost = TRADE_RP
    t.merge_range("A11:C11", "Hitungan per kincir · 每台怎么算", band(GREEN))
    p1 = f"{SHEET1}!$B$"
    d_kw = round(KW_OLD - kw_new, 9)
    day_kwh, day_rp = d_kw * HOURS, d_kw * HOURS * TARIFF
    cyc_rp, yr_rp = day_rp * DAYS, day_rp * DAYS * CYCLES
    steps = [
        (12, f"Hemat daya: arus {I_OLD} A → {I_NEW} A · 省功率：电流 {I_OLD} A → {I_NEW} A", f"={p1}{R_KW}-{p1}{R_KWNEW}", d_kw, "0.000", "kW"),
        (13, "Hemat listrik per hari · 每天省电", f"=B12*{p1}{R_HOURS}", day_kwh, "#,##0.00", "kWh"),
        (14, "Hemat biaya per hari · 每天省电费", f"=B13*{p1}{R_TARIFF}", day_rp, "#,##0", "Rp"),
        (15, "Hemat biaya per siklus · 每造省电费", f"=B14*{p1}{R_DAYS}", cyc_rp, "#,##0", "Rp"),
        (16, "Hemat biaya per tahun · 每年省电费", f"=B15*{p1}{R_CYCLES}", yr_rp, "#,##0", "Rp"),
        (17, "Modal kembali: hari nyala · 回本：运转天数", '=IF(B14>0,B9/B14,"")', unit_cost / day_rp, "#,##0", "hari · 天"),
        (18, "Modal kembali: siklus · 回本：造数", '=IF(B15>0,B9/B15,"")', unit_cost / cyc_rp, "0.0", "siklus · 造"),
    ]
    for row, a, form, val, nf, u in steps:
        t.write(f"A{row}", a, label)
        t.write_formula(f"B{row}", form, out(nf), val)
        t.write(f"C{row}", u, unit)
    t.write("A19", "Modal kembali: bulan · 回本：月数", f(bold=True, bg_color=HL, font_color=DEEP, text_wrap=True, **grid))
    t.write_formula("B19", '=IF(B16>0,B9/B16*12,"")', hl("0.0"), unit_cost / yr_rp * 12)
    t.write("C19", "bulan · 个月", f(bold=True, bg_color=HL, font_color=DEEP, align="center", **grid))
    t.merge_range("A21:E21", "Per jenis kolam · 按池塘类型", band(CHAR))
    for col, txt in enumerate(["Jenis kolam · 池塘类型", "Kincir · 台数", "Harga total (Rp) · 总售价", "Hemat per tahun (Rp) · 每年省", "Modal kembali (bulan) · 回本（月）"]):
        t.write(21, col, txt, head)
    t.set_row(21, 30)
    for i, (r1, a, units, Q) in enumerate(pond_rows):
        r = 23 + i
        t.write(f"A{r}", a, name)
        t.write_formula(f"B{r}", f"={SHEET1}!D{r1}", out(INT0), units)
        t.write_formula(f"C{r}", f"=$B$9*B{r}", out("#,##0"), unit_cost * units)
        t.write_formula(f"D{r}", f"={SHEET1}!Q{r1}", out("#,##0"), Q)
        t.write_formula(f"E{r}", f'=IF(D{r}>0,C{r}/D{r}*12,"")', hl("0.0"), unit_cost * units / Q * 12)
    t.merge_range(29, 0, 29, 4, "Harga di atas adalah harga terendah. Perkiraan awal, bukan jaminan. Penghematan dihitung dari arus, dengan tegangan dan faktor daya yang sama. Ukur dengan kWh meter sebelum mengambil keputusan. · 上面是最低售价。初步估算，不作保证。节电率按电流计算，前提是电压和功率因数相同。做决定前请用电表实测。", plain)
    t.set_row(29, 30)
    t.print_area("A1:E30")

    wb.close()
    print(f"OK -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
