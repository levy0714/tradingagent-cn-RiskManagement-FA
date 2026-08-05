# -*- coding: utf-8 -*-
"""基本面图表 PDF:三图(节点标注版)+ Q2 预估(有则加)。"""
import os
from fpdf import FPDF

ROOT = os.path.dirname(os.path.abspath(__file__))  # 项目根(自动定位,不写死路径)
IMG = os.path.join(ROOT, 'results', '600010')

pdf = FPDF(orientation='L', unit='mm', format='A4')  # 横向,图片更宽
pdf.set_auto_page_break(auto=False)
pdf.add_font('CJK', '', r'C:/Windows/Fonts/msyh.ttc', collection_font_number=0)
pdf.add_font('CJK', 'B', r'C:/Windows/Fonts/msyhbd.ttc', collection_font_number=0)

def add_title(t):
    pdf.add_page()
    pdf.set_font('CJK', 'B', 15)
    pdf.cell(0, 10, t, new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(3)

def add_img(name, caption):
    p = os.path.join(IMG, name)
    if not os.path.exists(p):
        return
    pdf.set_font('CJK', '', 10)
    pdf.cell(0, 8, caption, new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.image(p, x=8, y=pdf.get_y(), w=281)
    pdf.ln(2)

# 封面
pdf.add_page()
pdf.set_font('CJK', 'B', 22)
pdf.ln(40)
pdf.cell(0, 15, '包钢股份(600010) 基本面图表', new_x='LMARGIN', new_y='NEXT', align='C')
pdf.set_font('CJK', '', 12)
pdf.cell(0, 10, '季度利润 / 资产负债 / 现金流  2016~2026(节点标注版)', new_x='LMARGIN', new_y='NEXT', align='C')
pdf.ln(10)
pdf.set_font('CJK', '', 10)
pdf.cell(0, 8, '数据源: 东方财富(巨潮披露口径), 单位: 亿元', new_x='LMARGIN', new_y='NEXT', align='C')
pdf.cell(0, 8, '2026Q2 归母净利为业绩预增公告(临2026-045)推算: 6.93~7.63 亿(中值 7.28)', new_x='LMARGIN', new_y='NEXT', align='C')
pdf.cell(0, 8, '资产负债/现金流 2026Q2 未披露', new_x='LMARGIN', new_y='NEXT', align='C')

# 图1 利润(有 Q2 预估 -> 含预估版)
add_title('图1: 季度利润走势(含 2026Q2 预估)')
add_img('600010_利润_季度折线_含Q2预估.png', '归母净利(蓝)/净利润(红), 每个节点标注数值+同比; ★=2026Q2 预估(公告推算)')

# 图2 资产负债(无预估 -> 标注版)
add_title('图2: 资产负债走势(2026Q2 未披露)')
add_img('600010_资产负债_含Q2标注.png', '总资产/总负债/资产负债率(右轴), 节点标注数值; 2026Q2 未披露')

# 图3 现金流(无预估 -> 标注版)
add_title('图3: 现金流走势(2026Q2 未披露)')
add_img('600010_现金流_含Q2标注.png', '经营/投资/筹资净现金流, 节点标注数值; 2026Q2 未披露')

out = os.path.join(ROOT, 'results', '600010', '600010_基本面图表.pdf')
pdf.output(out)
print('PDF:', out)
