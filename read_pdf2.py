# -*- coding: utf-8 -*-
import pdfplumber
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取第二个PDF
print('='*60)
print('PDF 2: 中国大学生计算机设计大赛2.pdf')
print('='*60)
with pdfplumber.open('C:/Users/35174/Desktop/中国大学生计算机设计大赛2.pdf') as pdf:
    for i, page in enumerate(pdf.pages):
        print(f'\n--- 第{i+1}页 ---')
        text = page.extract_text()
        if text:
            print(text)
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f'\n表格{j+1}:')
            for row in table:
                print(row)
