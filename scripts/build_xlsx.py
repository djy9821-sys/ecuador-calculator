#!/usr/bin/env python3
"""
生成印尼版的 Excel 对比表（公式实时计算，黄色格可填）。默认值要和 indonesia.html 的 BASE 一致。

用 XlsxWriter 而不是 openpyxl：它能给公式写入缓存结果，
这样手机预览、WhatsApp 预览这些不重新计算的地方也能看到数字。

准备：pip install xlsxwriter
运行（在仓库根目录）：python3 scripts/build_xlsx.py
输出：dist/perbandingan-hemat-listrik-kincir.xlsx
"""
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "perbandingan-hemat-listrik-kincir.xlsx"

# 和 indonesia.html 的 BASE 保持一致。价格留空：代码里不写任何设备价格。
UNITS, TARIFF, DAYS, CYCLES, HOURS, FX = 5, 1444.7, 120, 2.5, 24, 2720
KW_OLD, KW_NEW = 1.5, 1.64
LOAD_OLD, LOAD_NEW = [1, 1, 1, 1], [0.4, 0.5, 0.7, 0.9]
SCALES = [
    ("Kolam bulat Ø 6–8 m", "圆形小塘 Ø 6–8 米", 1),
    ("Petak 800–1.000 m² (4–6 kincir, dihitung 5)", "方塘 800–1000 m²（4–6 台，按 5 台算）", 5),
    ("Tambak 30 petak (5 per petak)", "30 个塘（每塘 5 台）", 150),
    ("Tambak 50 petak (5 per petak)", "50 个塘（每塘 5 台）", 250),
    ("Tambak besar", "大型养殖场", 1000),
    ("Tambak besar", "大型养殖场", 2000),
]
NAVY, LINE, TINT, YELLOW, BLUE, MUTED = "#0A2A9C", "#C9D2E0", "#EEF3F9", "#FFF9C4", "#0000FF", "#6B7488"
# 公式结果为空时的缓存值。写空字符串的话，手机预览会显示 0。
BLANK = " "


def main():
    OUT.parent.mkdir(exist_ok=True)
    wb = xlsxwriter.Workbook(str(OUT))
    wb.set_properties({"title": "Perbandingan Hemat Listrik Kincir", "company": "WUXI SUNOLTA TECHNOLOGY CO.,LTD"})
    ws = wb.add_worksheet("Perbandingan")

    def f(**kw):
        base = {"font_name": "Arial", "font_size": 10, "valign": "vcenter"}
        base.update(kw)
        return wb.add_format(base)

    grid = {"border": 1, "border_color": LINE}
    title = f(bold=True, font_size=15, font_color=NAVY)
    sub = f(font_color=MUTED)
    section = f(bold=True, font_color="#FFFFFF", bg_color=NAVY)
    head = f(bold=True, bg_color=TINT, align="center", text_wrap=True, **grid)
    head_l = f(bold=True, bg_color=TINT, text_wrap=True, **grid)
    label = f(text_wrap=True, **grid)
    zh = f(text_wrap=True, font_color=MUTED, **grid)
    note = f(text_wrap=True, font_color=MUTED, font_size=9, **grid)
    plain_note = f(text_wrap=True, font_color=MUTED, font_size=9)
    unit = f(font_color=MUTED, **grid)
    legend = f(bg_color=YELLOW, font_color=BLUE, **grid)
    photo = f(align="center", font_color=MUTED, font_size=9, text_wrap=True, **grid)

    def inp(num_format):
        return f(bg_color=YELLOW, font_color=BLUE, num_format=num_format, **grid)

    def out(num_format, **kw):
        return f(num_format=num_format, **grid, **kw)

    i_int, i_rp, i_dec, i_pct = inp("#,##0"), inp("#,##0.00"), inp("0.00"), inp("0%")
    i_gen = inp("#,##0.##")
    o_rp, o_kwh, o_kwh1, o_kw = out('"Rp" #,##0'), out("#,##0"), out("#,##0.0"), out("0.00")
    o_pct_s, o_mo = out("+0%;-0%;0%"), out('0.0')
    o_rp_s = out('+"Rp" #,##0;-"Rp" #,##0;"Rp" 0')
    o_kw_s, o_kwh1_s, o_kwh_s = out("+0.00;-0.00;0.00"), out("+#,##0.0;-#,##0.0;0.0"), out("+#,##0;-#,##0;0")
    o_cur_s = out("+#,##0.##;-#,##0.##;0")
    tot_l = f(bold=True, bg_color=TINT, text_wrap=True, **grid)
    tot_pct = out("0.0%", bold=True, bg_color=TINT)
    tot_mo = out("0.0", bold=True, bg_color=TINT)
    tot_blank = f(bg_color=TINT, **grid)

    ws.hide_gridlines(2)
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
    ws.set_column("A:A", 38)
    ws.set_column("B:B", 26)
    ws.set_column("C:G", 17)

    # Python 里算一遍同样的结果，写成公式的缓存值
    avg_old, avg_new = sum(LOAD_OLD) / 4, sum(LOAD_NEW) / 4
    kw_o, kw_n = KW_OLD * avg_old, KW_NEW * avg_new
    day_o, day_n = kw_o * HOURS, kw_n * HOURS
    cyc_o, cyc_n = day_o * DAYS, day_n * DAYS
    cost_o, cost_n = cyc_o * TARIFF, cyc_n * TARIFF
    yr_o, yr_n = cost_o * CYCLES, cost_n * CYCLES
    save_day, save_cyc, save_cost, save_yr = day_o - day_n, cyc_o - cyc_n, cost_o - cost_n, yr_o - yr_n

    ws.merge_range("A1:G1", "Perbandingan Hemat Listrik Kincir · 水车省电对比表", title)
    ws.merge_range("A2:G2", "Kincir lama (gearbox) dibanding kincir magnet permanen + inverter. Perkiraan awal, bukan jaminan. · 老款（带减速机）对比永磁变频。初步估算，不作保证。", sub)
    ws.merge_range("A3:C3", "Sel kuning boleh diisi. Sel lain dihitung otomatis. · 黄色格可填写，其余自动计算。", legend)

    # 1. 输入
    ws.merge_range("A5:G5", "1. Data masukan · 输入数据", section)
    inputs = [
        (6, "Jumlah kincir", "水车台数", UNITS, i_int, "unit", "Ganti dengan jumlah kincir tambak. · 改成养殖场的实际台数。"),
        (7, "Tarif listrik", "电价", TARIFF, i_rp, "Rp/kWh", "PLN B-2 (Okt–Des 2026), belum termasuk pajak. B-3 / I-3: 1.114,74. Ganti dengan tarif di tagihan. · 不含税，请换成电费单上的电价。"),
        (8, "Hari per siklus", "每造天数", DAYS, i_int, "hari", "Dari persiapan air sampai panen, sekitar 120–125 hari. · 从做水到收成。"),
        (9, "Siklus per tahun", "每年造数", CYCLES, i_gen, "siklus", "Biasanya 2–3. · 一般 2–3 造。"),
        (10, "Jam nyala per hari", "每天运行小时", HOURS, i_int, "jam", "Kalau tidak nyala 24 jam, isi rata-ratanya. · 不是 24 小时的话填平均值。"),
        (11, "Kurs: 1 mata uang harga = Rp", "汇率：价格币种 1 元 = 印尼盾", FX, i_int, "Rp", "Harga dalam CNY: 2.720. Dalam USD: 18.150. Dalam rupiah: 1. Kurs pasar 3 Nov 2026. · 价格用人民币填 2720，美元填 18150，印尼盾填 1。"),
        (12, "Daya kincir lama", "老款功率", KW_OLD, i_dec, "kW", "Asumsi 2 HP, belum hasil ukur. Ganti dengan hasil ukur. · 假设 2 HP，请换成实测值。"),
        (13, "Daya penuh kincir baru", "新款满速功率", KW_NEW, i_dec, "kW", "SC15, hasil uji JS2024TJ03119J (SOTR 2,64 kg O₂/jam). · SC15 检测报告实测值。"),
    ]
    for row, id_, cn, val, fmt, u, nt in inputs:
        ws.write(f"A{row}", id_, label)
        ws.write(f"B{row}", cn, zh)
        ws.write_number(f"C{row}", val, fmt)
        ws.write(f"D{row}", u, unit)
        ws.merge_range(f"E{row}:G{row}", nt, note)
        ws.set_row(row - 1, 38 if len(nt) > 70 else 26)

    # 2. 负荷模式
    ws.merge_range("A15:G15", "2. Pola beban · 负荷模式", section)
    ws.write("A16", "Tahap", head_l)
    ws.write("B16", "阶段", head_l)
    ws.write("C16", "Kincir lama: menyala · 老款开机比例", head)
    ws.write("D16", "Kincir baru: daya · 新款功率比例", head)
    ws.merge_range("E16:G16", "Catatan · 说明", head)
    ws.set_row(15, 40)
    stages = [("Tahap 1: ¼ pertama siklus", "第 1 阶段：一造的前 ¼"), ("Tahap 2", "第 2 阶段"), ("Tahap 3", "第 3 阶段"), ("Tahap 4: menjelang panen", "第 4 阶段：临近收成")]
    for i, (a, b) in enumerate(stages):
        row = 17 + i
        ws.write(f"A{row}", a, label)
        ws.write(f"B{row}", b, zh)
        ws.write_number(f"C{row}", LOAD_OLD[i], i_pct)
        ws.write_number(f"D{row}", LOAD_NEW[i], i_pct)
    ws.merge_range("E17:G20", "Kincir baru tidak perlu jalan penuh saat udang masih kecil. Angka ini asumsi yang berhati-hati. Kalau kincir lama tidak selalu nyala semua, turunkan kolom kincir lama; hematnya jadi lebih kecil. · 虾小时新款不用全速。这些是偏保守的假设值。老款如果不是一直全开，要调低老款这一列，省电比例会变小。", note)
    ws.write("A21", "Rata-rata", tot_l)
    ws.write("B21", "平均", tot_l)
    ws.write_formula("C21", "=AVERAGE(C17:C20)", tot_pct, avg_old)
    ws.write_formula("D21", "=AVERAGE(D17:D20)", tot_pct, avg_new)

    # 3. 单台对比
    ws.merge_range("A23:G23", "3. Perbandingan per kincir · 单台对比", section)
    for col, txt in zip("ABCDEF", ["", "", "Kincir lama · 老款", "Kincir baru · 新款", "Selisih · 差额", "Selisih % · 差额 %"]):
        ws.write(f"{col}24", txt, head)
    ws.write("A25", "Foto", label)
    ws.write("B25", "照片", zh)
    ws.write("C25", "Tempel foto di sini · 在这里贴照片", photo)
    ws.write("D25", "Tempel foto di sini · 在这里贴照片", photo)
    ws.write_blank("E25", None, label)
    ws.write_blank("F25", None, label)
    ws.set_row(24, 92)

    def diff_row(row, id_, cn, form_o, val_o, form_n, val_n, fmt, dfmt):
        ws.write(f"A{row}", id_, label)
        ws.write(f"B{row}", cn, zh)
        ws.write_formula(f"C{row}", form_o, fmt, val_o)
        ws.write_formula(f"D{row}", form_n, fmt, val_n)
        ws.write_formula(f"E{row}", f"=D{row}-C{row}", dfmt, val_n - val_o)
        ws.write_formula(f"F{row}", f"=IF(C{row}>0,(D{row}-C{row})/C{row},\"\")", o_pct_s, (val_n - val_o) / val_o)

    ws.write("A26", "Harga per unit (mata uang harga)", label)
    ws.write("B26", "单价（价格币种）", zh)
    ws.write_blank("C26", None, i_gen)
    ws.write_blank("D26", None, i_gen)
    ws.write_formula("E26", '=IF(COUNT(C26:D26)=2,D26-C26,"")', o_cur_s, BLANK)
    ws.write_formula("F26", '=IF(AND(COUNT(C26:D26)=2,C26>0),(D26-C26)/C26,"")', o_pct_s, BLANK)
    ws.write("A27", "Harga per unit (Rp)", label)
    ws.write("B27", "单价（印尼盾）", zh)
    ws.write_formula("C27", '=IF(ISNUMBER(C26),C26*$C$11,"")', o_rp, BLANK)
    ws.write_formula("D27", '=IF(ISNUMBER(D26),D26*$C$11,"")', o_rp, BLANK)
    ws.write_formula("E27", '=IF(COUNT(C27:D27)=2,D27-C27,"")', o_rp_s, BLANK)
    ws.write_blank("F27", None, label)
    diff_row(28, "Daya rata-rata (kW)", "平均功率（kW）", "=C12*C21", kw_o, "=C13*D21", kw_n, o_kw, o_kw_s)
    diff_row(29, "① Listrik per hari (kWh)", "① 每天用电（度）", "=C28*$C$10", day_o, "=D28*$C$10", day_n, o_kwh1, o_kwh1_s)
    diff_row(30, "② Listrik per siklus (kWh)", "② 每造用电（度）", "=C29*$C$8", cyc_o, "=D29*$C$8", cyc_n, o_kwh, o_kwh_s)
    diff_row(31, "③ Biaya listrik per siklus", "③ 每造电费", "=C30*$C$7", cost_o, "=D30*$C$7", cost_n, o_rp, o_rp_s)
    diff_row(32, "④ Biaya listrik per tahun", "④ 每年电费", "=C31*$C$9", yr_o, "=D31*$C$9", yr_n, o_rp, o_rp_s)
    ws.write("A33", "Hemat listrik", tot_l)
    ws.write("B33", "省电比例", tot_l)
    ws.write_blank("C33", None, tot_blank)
    ws.write_formula("D33", '=IF(C29>0,(C29-D29)/C29,"")', tot_pct, save_day / day_o)
    ws.write_blank("E33", None, tot_blank)
    ws.write_blank("F33", None, tot_blank)
    ws.write("A34", "Balik modal dari selisih harga (bulan)", tot_l)
    ws.write("B34", "差价回本时间（月）", tot_l)
    ws.write_blank("C34", None, tot_blank)
    ws.write_formula("D34", '=IF(AND(ISNUMBER(E27),C32>D32),MAX(E27,0)/(C32-D32)*12,"")', tot_mo, BLANK)
    ws.write_blank("E34", None, tot_blank)
    ws.write_blank("F34", None, tot_blank)

    # 4. 按规模
    ws.merge_range("A36:G36", "4. Hemat menurut ukuran tambak · 按规模算省多少", section)
    heads = ["Ukuran", "规模", "Kincir · 台数", "Hemat listrik per tahun (kWh) · 每年省电", "Hemat per siklus · 每造省", "Hemat per tahun · 每年省", "Total selisih harga · 差价合计"]
    for col, txt in zip("ABCDEFG", heads):
        ws.write(f"{col}37", txt, head)
    ws.set_row(36, 40)

    def scale_row(row, id_, cn, n, formula=None):
        ws.write(f"A{row}", id_, label)
        ws.write(f"B{row}", cn, zh)
        if formula:
            ws.write_formula(f"C{row}", formula, o_kwh, n)
        else:
            ws.write_number(f"C{row}", n, o_kwh)
        ws.write_formula(f"D{row}", f"=C{row}*($C$30-$D$30)*$C$9", o_kwh, n * save_cyc * CYCLES)
        ws.write_formula(f"E{row}", f"=C{row}*($C$31-$D$31)", o_rp, n * save_cost)
        ws.write_formula(f"F{row}", f"=C{row}*($C$32-$D$32)", o_rp, n * save_yr)
        ws.write_formula(f"G{row}", f'=IF(ISNUMBER($E$27),C{row}*$E$27,"")', o_rp, BLANK)

    for i, (a, b, n) in enumerate(SCALES):
        scale_row(38 + i, a, b, n)
    scale_row(44, "Isi sendiri (dari Jumlah kincir di atas)", "自己填（用上面的水车台数）", UNITS, "=C6")

    # 5. 以旧换新
    ws.merge_range("A46:G46", "5. Tukar tambah: rangka lama tetap dipakai · 以旧换新：保留老支架", section)
    ws.write("A47", "Harga set: motor magnet permanen + inverter", label)
    ws.write("B47", "套件单价：永磁电机 + 变频器", zh)
    ws.write_blank("C47", None, i_gen)
    ws.write("D47", "mata uang harga", unit)
    ws.merge_range("E47:G48", "Lubang dudukan set baru harus dicek cocok dengan rangka lama, untuk setiap model. · 每个型号都要先确认新电机安装孔能对上老支架。", note)
    ws.write("A48", "Nilai tukar mesin lama per unit (kalau ada)", label)
    ws.write("B48", "旧机抵价（没有可不填）", zh)
    ws.write_blank("C48", None, i_gen)
    ws.write("D48", "mata uang harga", unit)
    for col, txt in zip("ABCDEF", ["Pilihan", "方案", "Modal per kincir · 每台投入", "Modal total · 总投入", "Hemat per tahun · 每年省", "Balik modal (bulan) · 回本（月）"]):
        ws.write(f"{col}49", txt, head)
    ws.set_row(48, 28)
    credit = "IF(ISNUMBER($C$48),$C$48,0)"
    options = [
        (50, "Beli kincir baru, bukan kincir lama", "买新款而不是老款（只算差价）", '=IF(ISNUMBER(E27),E27,"")'),
        (51, "Ganti seluruh kincir lama", "整台换掉老款", f'=IF(ISNUMBER(D26),(D26-{credit})*$C$11,"")'),
        (52, "Tukar tambah: ganti motor + gearbox saja", "以旧换新：只换电机 + 减速机", f'=IF(ISNUMBER(C47),(C47-{credit})*$C$11,"")'),
    ]
    for row, a, b, formula in options:
        ws.write(f"A{row}", a, label)
        ws.write(f"B{row}", b, zh)
        ws.write_formula(f"C{row}", formula, o_rp, BLANK)
        ws.write_formula(f"D{row}", f'=IF(ISNUMBER(C{row}),C{row}*$C$6,"")', o_rp, BLANK)
        ws.write_formula(f"E{row}", "=($C$32-$D$32)*$C$6", o_rp, save_yr * UNITS)
        ws.write_formula(f"F{row}", f'=IF(AND(ISNUMBER(D{row}),E{row}>0),MAX(D{row},0)/E{row}*12,"")', o_mo, BLANK)

    ws.merge_range("A54:G54", "Perkiraan awal. Hasil nyata tergantung kolam, cara pakai kincir, dan tarif. Ukur dengan kWh meter sebelum mengambil keputusan investasi. · 初步估算。实际结果取决于塘口、水车用法和电价，做投资决定前请用电表实测。", plain_note)
    ws.set_row(53, 28)
    ws.merge_range("A55:G55", "WUXI SUNOLTA TECHNOLOGY CO.,LTD", plain_note)
    ws.print_area("A1:G55")

    wb.close()
    print(f"OK -> {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
