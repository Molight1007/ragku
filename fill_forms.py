#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
填写4C2026参赛表格
"""

import os
import shutil
import zipfile
from xml.etree import ElementTree as ET

# 命名空间
namespaces = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

# 注册命名空间
for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

def fill_doc1():
    """填写作品信息概要表"""
    src = r"D:\BaiduNetdiskDownload\4C2026参赛作品提交要求（含赛事咨询联系方式）\05人工智能应用作品提交要求V2（4月17日更新）\05-1 作品信息概要表（人工智能实践赛、挑战赛，2026版）模板(1).docx"
    dst = r"d:\ragku\已填写表格\05-1-作品信息概要表-已填写.docx"
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    # 复制并解压
    temp_dir = r"d:\ragku\temp_doc1"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    with zipfile.ZipFile(src, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # 读取document.xml
    doc_path = os.path.join(temp_dir, 'word', 'document.xml')
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 填写作品名称
    content = content.replace(
        '<w:t>作品名称</w:t>',
        '<w:t>作品名称</w:t></w:r></w:p></w:tc><w:tc><w:tcPr><w:tcW w:w="4051" w:type="dxa"/><w:gridSpan w:val="7"/></w:tcPr><w:p><w:pPr><w:rPr><w:rFonts w:ascii="仿宋" w:eastAsia="仿宋" w:hAnsi="仿宋" w:hint="eastAsia"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:ascii="仿宋" w:eastAsia="仿宋" w:hAnsi="仿宋" w:hint="eastAsia"/></w:rPr><w:t>智核私有舱——基于RAG的多模态智能知识库系统</w:t>'
    )
    
    # 填写作品大类（已在模板中）
    # 选择实践赛
    content = content.replace(
        '<w:t xml:space="preserve">□实践赛 </w:t>',
        '<w:t xml:space="preserve">■实践赛 </w:t>'
    )
    
    # 填写作品简介
    intro = "本作品是一个基于RAG（检索增强生成）技术的多模态智能知识库系统，支持文档上传、向量化存储和智能问答。系统采用FastAPI构建后端，Vue3构建前端，集成百炼OCR实现图片和视频分析功能。核心特色是可更换知识库设计，适用于企业文档管理、教育培训等多种场景。已应用于乒乓球教学领域，支持动作视频分析和文档知识问答。"
    
    # 保存修改
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 重新打包
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    shutil.rmtree(temp_dir)
    print(f"已生成: {dst}")

def fill_doc2():
    """填写AI工具使用说明"""
    src = r"D:\BaiduNetdiskDownload\4C2026参赛作品提交要求（含赛事咨询联系方式）\05人工智能应用作品提交要求V2（4月17日更新）\05-2-AI工具使用说明（选用模板）（2026年版）(1).docx"
    dst = r"d:\ragku\已填写表格\05-2-AI工具使用说明-已填写.docx"
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    temp_dir = r"d:\ragku\temp_doc2"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    with zipfile.ZipFile(src, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    doc_path = os.path.join(temp_dir, 'word', 'document.xml')
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 填写作品名称
    content = content.replace(
        '<w:t>作品名称：</w:t>',
        '<w:t>作品名称：智核私有舱——基于RAG的多模态智能知识库系统</w:t>'
    )
    
    # 保存
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    shutil.rmtree(temp_dir)
    print(f"已生成: {dst}")

def fill_doc3():
    """填写作品报告"""
    src = r"D:\BaiduNetdiskDownload\4C2026参赛作品提交要求（含赛事咨询联系方式）\05人工智能应用作品提交要求V2（4月17日更新）\05-3 作品报告（人工智能实践赛，2026版）模板(1).docx"
    dst = r"d:\ragku\已填写表格\05-3-作品报告-已填写.docx"
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    temp_dir = r"d:\ragku\temp_doc3"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    with zipfile.ZipFile(src, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    doc_path = os.path.join(temp_dir, 'word', 'document.xml')
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 填写作品名称
    content = content.replace(
        '<w:t>作品名称：</w:t>',
        '<w:t>作品名称：智核私有舱——基于RAG的多模态智能知识库系统</w:t>'
    )
    
    # 保存
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    shutil.rmtree(temp_dir)
    print(f"已生成: {dst}")

if __name__ == "__main__":
    fill_doc1()
    fill_doc2()
    fill_doc3()
    print("\n所有表格填写完成！")
