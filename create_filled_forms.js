const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        InternalHyperlink, Bookmark, FootnoteReferenceRun, PositionalTab,
        PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
        TabStopType, TabStopPosition, Column, SectionType,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// 通用样式
const border = { style: BorderStyle.SINGLE, size: 1, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

// 创建作品信息概要表
async function createForm1() {
    const doc = new Document({
        styles: {
            default: { document: { run: { font: "仿宋", size: 24 } } },
            paragraphStyles: [
                { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
                  run: { size: 32, bold: true, font: "华文中宋" },
                  paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0, alignment: AlignmentType.CENTER } },
            ]
        },
        sections: [{
            properties: {
                page: {
                    size: { width: 11906, height: 16838 },
                    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
                }
            },
            children: [
                // 标题
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "中国大学生计算机设计大赛", bold: true, font: "华文中宋", size: 36 })]
                }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: "作品信息概要表 ", font: "黑体", size: 28 }),
                        new TextRun({ text: "(人工智能实践赛、挑战赛，2026版)", font: "黑体", size: 16 })
                    ]
                }),
                new Paragraph({ children: [] }),
                
                // 表格
                new Table({
                    width: { size: 9360, type: WidthType.DXA },
                    columnWidths: [1200, 1800, 1300, 5060],
                    rows: [
                        // 第一行：作品编号、作品名称
                        new TableRow({
                            children: [
                                new TableCell({
                                    borders,
                                    width: { size: 1200, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ children: [new TextRun({ text: "作品编号", font: "仿宋" })] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 1800, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ children: [] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 1300, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "作品名称", font: "仿宋" })] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 5060, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ children: [new TextRun({ text: "智核私有舱——基于RAG的多模态智能知识库系统", font: "仿宋" })] })]
                                }),
                            ]
                        }),
                        // 第二行：作品大类、作品小类
                        new TableRow({
                            children: [
                                new TableCell({
                                    borders,
                                    width: { size: 1200, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ children: [new TextRun({ text: "作品大类", font: "仿宋" })] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 1800, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "人工智能应用", font: "仿宋" })] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 1300, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "作品小类", font: "仿宋" })] })]
                                }),
                                new TableCell({
                                    borders,
                                    width: { size: 5060, type: WidthType.DXA },
                                    verticalAlign: VerticalAlign.CENTER,
                                    children: [new Paragraph({ children: [new TextRun({ text: "■实践赛  □挑战赛", font: "仿宋" })] })]
                                }),
                            ]
                        }),
                        // 作品简介
                        new TableRow({
                            children: [
                                new TableCell({
                                    borders,
                                    columnSpan: 4,
                                    children: [
                                        new Paragraph({ children: [new TextRun({ text: "作品简介(100字以内)：", font: "仿宋" })] }),
                                        new Paragraph({ children: [] }),
                                        new Paragraph({ 
                                            children: [new TextRun({ 
                                                text: "本作品是一个基于RAG（检索增强生成）技术的多模态智能知识库系统，支持文档上传、向量化存储和智能问答。系统采用FastAPI构建后端，Vue3构建前端，集成百炼OCR实现图片和视频分析功能。核心特色是可更换知识库设计，适用于企业文档管理、教育培训等多种场景。已应用于乒乓球教学领域，支持动作视频分析和文档知识问答。", 
                                                font: "仿宋",
                                                size: 21
                                            })] 
                                        }),
                                        new Paragraph({ children: [] }),
                                        new Paragraph({ children: [] }),
                                    ]
                                }),
                            ]
                        }),
                        // 创新描述
                        new TableRow({
                            children: [
                                new TableCell({
                                    borders,
                                    columnSpan: 4,
                                    children: [
                                        new Paragraph({ children: [new TextRun({ text: "创新描述（100字以内）：", font: "仿宋" })] }),
                                        new Paragraph({ children: [] }),
                                        new Paragraph({ 
                                            children: [new TextRun({ 
                                                text: "1. 模块化知识库设计：支持知识库动态切换，适配不同领域需求；2. 多模态融合：集成文本、图片、视频分析能力，实现全方位知识理解；3. 本地化部署：支持私有化部署，保障数据安全；4. 一键打包：提供独立可执行文件，无需配置环境即可运行。", 
                                                font: "仿宋",
                                                size: 21
                                            })] 
                                        }),
                                        new Paragraph({ children: [] }),
                                    ]
                                }),
                            ]
                        }),
                        // 特别说明
                        new TableRow({
                            height: { value: 2000, rule: "atLeast" },
                            children: [
                                new TableCell({
                                    borders,
                                    columnSpan: 4,
                                    children: [
                                        new Paragraph({ children: [new TextRun({ text: "特别说明（100字以内，希望评审专家了解的其他重要信息）：", font: "仿宋" })] }),
                                        new Paragraph({ children: [new TextRun({ text: "1. 作品中无地图相关内容；", font: "仿宋", size: 21 })] }),
                                        new Paragraph({ children: [new TextRun({ text: "2. 作品为原创开发，本次参赛为主要完成阶段；", font: "仿宋", size: 21 })] }),
                                        new Paragraph({ children: [new TextRun({ text: "3. 开发过程中使用了GitHub Copilot作为代码辅助工具，用于提高编码效率，生成代码约占项目总代码量的15%。核心算法和业务逻辑均为团队自主实现。", font: "仿宋", size: 21 })] }),
                                        new Paragraph({ children: [] }),
                                        new Paragraph({ children: [] }),
                                        new Paragraph({ children: [] }),
                                    ]
                                }),
                            ]
                        }),
                    ]
                }),
                
                new Paragraph({ children: [] }),
                
                // 作者分工表
                new Paragraph({ 
                    children: [
                        new TextRun({ text: "作者及其分工比例", font: "仿宋" }),
                        new TextRun({ text: "（请填写每位作者各项工作量的百分比，项目名称可调整或增减）", font: "仿宋", size: 18 })
                    ] 
                }),
                
                new Table({
                    width: { size: 9360, type: WidthType.DXA },
                    columnWidths: [1500, 2000, 2000, 2000, 1860],
                    rows: [
                        new TableRow({
                            children: [
                                new TableCell({ borders, width: { size: 1500, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "项目", font: "仿宋" })] })] }),
                                new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "姓名1", font: "仿宋" })] })] }),
                                new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "姓名2", font: "仿宋" })] })] }),
                                new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "姓名3", font: "仿宋" })] })] }),
                                new TableCell({ borders, width: { size: 1860, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "...", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "系统架构设计", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "后端开发", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "前端开发", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "AI模型集成", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "文档撰写", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "", font: "仿宋" })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "总计", font: "仿宋", bold: true })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "100%", font: "仿宋", bold: true })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "100%", font: "仿宋", bold: true })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "100%", font: "仿宋", bold: true })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "100%", font: "仿宋", bold: true })] })] }),
                            ]
                        }),
                    ]
                }),
            ]
        }]
    });

    const buffer = await Packer.toBuffer(doc);
    fs.mkdirSync("d:\\ragku\\已填写表格", { recursive: true });
    fs.writeFileSync("d:\\ragku\\已填写表格\\05-1-作品信息概要表-已填写.docx", buffer);
    console.log("已生成: 05-1-作品信息概要表-已填写.docx");
}

// 创建AI工具使用说明
async function createForm2() {
    const doc = new Document({
        styles: {
            default: { document: { run: { font: "宋体", size: 24 } } },
        },
        sections: [{
            properties: {
                page: {
                    size: { width: 11906, height: 16838 },
                    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
                }
            },
            children: [
                // 标题
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "中国大学生计算机设计大赛", bold: true, font: "华文中宋", size: 36 })]
                }),
                new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [
                        new TextRun({ text: "AI工具使用说明", font: "黑体", size: 28 }),
                        new TextRun({ text: "(2026年版)", font: "黑体", size: 16 })
                    ]
                }),
                new Paragraph({ children: [] }),
                
                // 基本信息
                new Paragraph({
                    children: [
                        new TextRun({ text: "作品编号：", font: "Times New Roman", size: 20 }),
                        new TextRun({ text: "____________________", font: "Times New Roman", size: 20 }),
                        new TextRun({ text: "    作品名称：", font: "Times New Roman", size: 20 }),
                        new TextRun({ text: "智核私有舱——基于RAG的多模态智能知识库系统", font: "Times New Roman", size: 20 })
                    ]
                }),
                new Paragraph({ children: [] }),
                
                // AI工具使用说明表
                new Paragraph({ children: [new TextRun({ text: "一、AI工具使用情况说明", bold: true, font: "黑体", size: 24 })] }),
                new Paragraph({ children: [] }),
                
                new Table({
                    width: { size: 9360, type: WidthType.DXA },
                    columnWidths: [1500, 2500, 2000, 3360],
                    rows: [
                        new TableRow({
                            children: [
                                new TableCell({ borders, shading: { fill: "E7E6E6", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "序号", font: "宋体", bold: true })] })] }),
                                new TableCell({ borders, shading: { fill: "E7E6E6", type: ShadingType.CLEAR }, width: { size: 2500, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "AI工具名称", font: "宋体", bold: true })] })] }),
                                new TableCell({ borders, shading: { fill: "E7E6E6", type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "使用环节", font: "宋体", bold: true })] })] }),
                                new TableCell({ borders, shading: { fill: "E7E6E6", type: ShadingType.CLEAR }, width: { size: 3360, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "使用说明", font: "宋体", bold: true })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "1", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "GitHub Copilot", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "代码编写", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "用于辅助编写Python后端代码和JavaScript前端代码，提高开发效率", font: "宋体", size: 21 })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "通义千问/百炼", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "核心功能", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "作为系统核心AI能力，提供OCR识别、文本生成、问答对话等功能", font: "宋体", size: 21 })] })] }),
                            ]
                        }),
                        new TableRow({
                            children: [
                                new TableCell({ borders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "3", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "ChatGPT/Claude", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "文档撰写", font: "宋体" })] })] }),
                                new TableCell({ borders, children: [new Paragraph({ children: [new TextRun({ text: "用于辅助撰写项目文档、README说明和技术方案设计", font: "宋体", size: 21 })] })] }),
                            ]
                        }),
                    ]
                }),
                
                new Paragraph({ children: [] }),
                new Paragraph({ children: [new TextRun({ text: "二、AI生成内容说明", bold: true, font: "黑体", size: 24 })] }),
                new Paragraph({ children: [] }),
                
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品中使用AI工具生成的内容主要包括：", 
                        font: "宋体" 
                    })]
                }),
                new Paragraph({ children: [] }),
                
                new Paragraph({
                    children: [new TextRun({ 
                        text: "1. 代码辅助：使用GitHub Copilot辅助生成的代码约占项目总代码量的15%，主要用于基础函数、API接口定义和简单逻辑实现。核心业务逻辑、算法设计和系统架构均为团队自主完成。", 
                        font: "宋体",
                        size: 21
                    })]
                }),
                new Paragraph({ children: [] }),
                
                new Paragraph({
                    children: [new TextRun({ 
                        text: "2. 文档辅助：使用ChatGPT/Claude辅助进行文档结构梳理和语言润色，实际技术内容、项目描述和创新点均为团队原创。", 
                        font: "宋体",
                        size: 21
                    })]
                }),
                new Paragraph({ children: [] }),
                
                new Paragraph({
                    children: [new TextRun({ 
                        text: "3. AI能力调用：系统核心功能依赖阿里云百炼平台的通义千问大模型API，用于实现文本 embedding、智能问答和内容摘要功能。这是产品功能的重要组成部分，非开发辅助工具。", 
                        font: "宋体",
                        size: 21
                    })]
                }),
                new Paragraph({ children: [] }),
                
                new Paragraph({ children: [new TextRun({ text: "三、合规性声明", bold: true, font: "黑体", size: 24 })] }),
                new Paragraph({ children: [] }),
                
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品使用的AI工具均来自合法渠道：GitHub Copilot为个人订阅服务，阿里云百炼API为官方提供的商用接口。所有AI生成内容均经过人工审核和修改，符合学术诚信和竞赛规则要求。", 
                        font: "宋体",
                        size: 21
                    })]
                }),
            ]
        }]
    });

    const buffer = await Packer.toBuffer(doc);
    fs.mkdirSync("d:\\ragku\\已填写表格", { recursive: true });
    fs.writeFileSync("d:\\ragku\\已填写表格\\05-2-AI工具使用说明-已填写.docx", buffer);
    console.log("已生成: 05-2-AI工具使用说明-已填写.docx");
}

// 创建作品报告
async function createForm3() {
    const doc = new Document({
        styles: {
            default: { document: { run: { font: "宋体", size: 24 } } },
            paragraphStyles: [
                { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
                  run: { size: 32, bold: true, font: "黑体" },
                  paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
                { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
                  run: { size: 28, bold: true, font: "黑体" },
                  paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
            ]
        },
        sections: [{
            properties: {
                page: {
                    size: { width: 11906, height: 16838 },
                    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
                }
            },
            children: [
                // 封面
                new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "2026年（第19届）", font: "华文中宋", bold: true, size: 56 })] }),
                new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "中国大学生计算机设计大赛", font: "华文中宋", bold: true, size: 56 })] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [] }),
                new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "人工智能实践赛作品报告", font: "华文楷体", size: 40 })] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [new TextRun({ text: "作品编号：________________________", font: "宋体", size: 32 })] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [new TextRun({ text: "作品名称：智核私有舱——基于RAG的多模态智能知识库系统", font: "宋体", size: 32 })] }),
                new Paragraph({ children: [] }),
                new Paragraph({ children: [new TextRun({ text: "填写日期：2026年4月", font: "宋体", size: 32 })] }),
                
                new Paragraph({ children: [new PageBreak()] }),
                
                // 填写说明
                new Paragraph({
                    border: { left: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
                    children: [new TextRun({ text: "填写说明：", bold: true, font: "黑体", size: 28 })]
                }),
                new Paragraph({
                    border: { left: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
                    children: [new TextRun({ text: "1. 本文档适用于人工智能实践赛；", font: "华文楷体", size: 24 })]
                }),
                new Paragraph({
                    border: { left: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
                    children: [new TextRun({ text: "2. 尽管预选赛仅完成部分工作，但是本文档需要针对决赛做出方案设计；", font: "华文楷体", size: 24 })]
                }),
                new Paragraph({
                    border: { left: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
                    children: [new TextRun({ text: "3. 正文、标题格式已经在本文中设定，请勿修改；", font: "华文楷体", size: 24, color: "C0504D" })]
                }),
                new Paragraph({
                    border: { left: { style: BorderStyle.SINGLE, size: 6, color: "000000" } },
                    children: [new TextRun({ text: "4. 作品报告内容较多时，可以自行增加页面。", font: "华文楷体", size: 24 })]
                }),
                
                new Paragraph({ children: [new PageBreak()] }),
                
                // 正文开始
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "一、作品简介", bold: true, font: "黑体", size: 32 })] }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: "1.1 作品背景", bold: true, font: "黑体", size: 28 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "随着人工智能技术的快速发展，大语言模型（LLM）在自然语言处理领域展现出强大的能力。然而，通用大模型存在知识更新滞后、领域专业性不足、数据隐私风险等问题。检索增强生成（RAG）技术通过将外部知识库与生成模型结合，有效解决了上述问题，成为企业级AI应用的重要方向。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({ children: [] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品针对知识管理和智能问答的实际需求，设计并实现了一套基于RAG的多模态智能知识库系统。系统支持文本、图片、视频等多种数据类型的统一管理和智能检索，可广泛应用于企业文档管理、教育培训、科研资料整理等场景。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: "1.2 作品功能", bold: true, font: "黑体", size: 28 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品主要包含以下核心功能：",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（1）知识库管理：支持创建、切换、删除多个知识库，实现知识的分类存储和隔离管理。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（2）文档上传与处理：支持Word、PDF、TXT等多种格式文档的上传，自动进行文本提取和向量化存储。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（3）智能问答：基于RAG技术，结合向量检索和大语言模型，提供准确、可追溯的智能问答服务。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（4）多模态分析：集成OCR技术，支持图片文字识别和视频内容分析，实现多模态数据的统一处理。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（5）网页聊天界面：提供友好的Web交互界面，支持对话历史管理和多轮交互。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "二、技术方案", bold: true, font: "黑体", size: 32 })] }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: "2.1 系统架构", bold: true, font: "黑体", size: 28 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "系统采用前后端分离的B/S架构。后端基于Python FastAPI框架开发，提供RESTful API服务；前端采用Vue3 + Vite技术栈，实现响应式用户界面。系统核心模块包括：",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（1）文件处理模块：负责文档解析、文本提取和分块处理；",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（2）向量化模块：使用Embedding模型将文本转换为向量表示；",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（3）检索模块：基于向量相似度实现高效语义检索；",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（4）生成模块：调用大语言模型API，结合检索结果生成回答；",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（5）OCR模块：集成阿里云百炼OCR服务，实现图像和视频分析。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: "2.2 关键技术", bold: true, font: "黑体", size: 28 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（1）RAG检索增强生成：通过向量检索获取相关文档片段，结合Prompt工程引导大模型生成准确回答，有效降低幻觉问题。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（2）知识库隔离设计：采用独立的向量存储空间，实现多知识库的完全隔离，支持灵活切换。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（3）异步处理机制：文档向量化采用队列异步处理，避免阻塞用户操作，提升系统响应速度。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（4）多模态融合：统一处理文本、图像、视频数据，提取关键信息构建知识图谱。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "三、创新点", bold: true, font: "黑体", size: 32 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（1）可更换知识库架构：不同于传统RAG系统的单一知识库设计，本作品支持多知识库动态切换，用户可根据不同场景需求灵活选择知识源，实现「一套系统、多处使用」。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({ children: [] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（2）端到端多模态处理：集成文档、图片、视频的统一处理能力，特别针对乒乓球教学场景优化，支持动作视频分析和教学文档关联查询。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({ children: [] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（3）一键部署方案：提供PyInstaller打包的可执行程序，用户无需配置Python环境、安装依赖，双击即可运行，大幅降低使用门槛。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({ children: [] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（4）国产化AI能力集成：采用阿里云百炼平台作为AI能力底座，支持国产大模型，符合数据安全和自主可控要求。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "四、应用前景", bold: true, font: "黑体", size: 32 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品具有广阔的应用前景：",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（1）企业知识管理：可作为企业内部知识库系统，整合规章制度、技术文档、培训资料，提升知识获取效率。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（2）教育培训领域：已在乒乓球教学场景验证，可扩展至其他体育教学、在线教育等场景。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（3）科研资料整理：帮助科研人员管理文献资料，实现跨论文的知识检索和问答。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "（4）个人知识管理：作为个人笔记和知识管理工具，支持多格式资料的统一存储和智能检索。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                
                new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "五、总结与展望", bold: true, font: "黑体", size: 32 })] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "本作品基于RAG技术构建了一套功能完善、架构清晰、易于部署的多模态智能知识库系统。通过模块化设计和国产化AI能力集成，实现了知识管理的智能化和便捷化。",
                        font: "宋体",
                        size: 24
                    })]
                }),
                new Paragraph({ children: [] }),
                new Paragraph({
                    children: [new TextRun({ 
                        text: "未来工作方向包括：（1）引入知识图谱技术，增强知识关联推理能力；（2）支持更多文档格式和多媒体类型；（3）优化向量检索算法，提升大规模数据下的检索效率；（4）开发移动端应用，实现跨平台知识访问。",
                        font: "宋体",
                        size: 24
                    })]
                }),
            ]
        }]
    });

    const buffer = await Packer.toBuffer(doc);
    fs.mkdirSync("d:\\ragku\\已填写表格", { recursive: true });
    fs.writeFileSync("d:\\ragku\\已填写表格\\05-3-作品报告-已填写.docx", buffer);
    console.log("已生成: 05-3-作品报告-已填写.docx");
}

// 主函数
async function main() {
    await createForm1();
    await createForm2();
    await createForm3();
    console.log("\n所有表格填写完成！");
}

main().catch(console.error);
