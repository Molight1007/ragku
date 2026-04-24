# PPT Outline

## Overview
本 PPT 展示「多模态RAG知识库问答系统」（ragku）项目，重点突出两大差异化亮点：①知识库随时可切换，②支持图片 OCR / 看图问答 / 视频关键帧分析。面向全国大学生计算机设计大赛 AI 方向评委，技术风格，共 19 页。

## Outline Content

### Page 1: 封面
- **Page Type**: Cover
- **Page Title**: 多模态RAG知识问答系统
- **Page Subtitle**: 知识库随换随用 · 图片视频同样可答
- **Content Structure**:
  - 主标题：多模态RAG知识问答系统
  - 副标题：知识库随换随用 · 图片视频同样可答
  - 标签：阿里云通义千问 · FastAPI · Qwen-VL
  - 场景说明：全国大学生计算机设计大赛 AI 方向参赛作品

### Page 2: 目录
- **Page Type**: TOC
- **Page Title**: 内容概览
- **Content Structure**:
  - 章节1：项目背景与价值
  - 章节2：核心功能全览
  - 章节3：最大亮点 — 知识库可更换
  - 章节4：图片处理能力
  - 章节5：视频分析能力
  - 章节6：系统架构与技术栈
  - 章节7：总结与展望

### Page 3: 过渡页-背景
- **Page Type**: Transition
- **Page Title**: 项目背景与价值

### Page 4: 传统大模型的局限
- **Page Type**: Content
- **Page Title**: 传统大模型的局限
- **Content Structure**:
  - 痛点1：知识截止——训练数据有时效，无法掌握最新/私有领域知识
  - 痛点2：固定知识库——资料库一旦构建便难以切换，多场景适应性差
  - 痛点3：只懂文字——传统问答系统无法理解图片和视频中的内容信息
  - 解法：RAG + 多模态 + 可切换知识库，三重突破一次解决

### Page 5: 过渡页-功能
- **Page Type**: Transition
- **Page Title**: 核心功能全览

### Page 6: 六大核心能力
- **Page Type**: Content
- **Page Title**: 六大核心能力
- **Content Structure**:
  - 📁 多知识库管理：创建、删除、独立索引，互不干扰
  - 🔄 资料库随时切换：kb_id 参数一键切换，零停机
  - 🖼️ 图片 OCR 识字：提取图片文字，纳入可检索知识库
  - 👁️ 看图问答：Qwen-VL 理解画面，结合知识库综合回答
  - 🎬 视频关键帧分析：自动抽帧 + 多模态理解 + RAG 融合
  - 📄 多格式文档支持：TXT/MD/PDF/DOCX + 图片 + 视频

### Page 7: 过渡页-知识库切换
- **Page Type**: Transition
- **Page Title**: 最大亮点：知识库可更换

### Page 8: 多知识库架构设计
- **Page Type**: Content
- **Page Title**: 多知识库架构设计
- **Content Structure**:
  - 传统系统：单一固定知识库 → 切换需重启 → 多场景无法兼顾
  - 本系统：多知识库独立存储 → kb_id 动态路由 → 毫秒级切换 → 无限场景扩展
  - 技术实现：每个 KB 有独立目录 + 独立向量索引文件，服务层按 ID 动态加载
  - 实际效果：1个服务实例 → 支撑 N 个独立领域知识库并发使用

### Page 9: 一键切换场景演示
- **Page Type**: Content
- **Page Title**: 场景演示：一键切换领域
- **Content Structure**:
  - 场景A：消防安全库 → 问"如何处置电气火灾"
  - 场景B：企业规章库 → 问"年假政策是什么"
  - 场景C：体育训练库 → 结合视频分析"动作是否规范"
  - 仅需修改请求中的 kb_id 字段，其余代码零改动
  - 知识库按需新建：上传文档 → 自动向量化 → 立即可用

### Page 10: 过渡页-图片处理
- **Page Type**: Transition
- **Page Title**: 图片处理能力

### Page 11: 看懂图片·不止识字
- **Page Type**: Content
- **Page Title**: 看懂图片 · 不止识字
- **Content Structure**:
  - 链路1 — OCR 识字入库：上传图片 → Qwen-VL-OCR → 切分向量化 → 可检索
  - 链路2 — 看图直接问答：上传图片 + 提问 → Qwen-VL 画面理解 → RAG 融合 → 综合回答
  - 支持格式：JPG、PNG、BMP、WebP、GIF

### Page 12: 过渡页-视频分析
- **Page Type**: Transition
- **Page Title**: 视频分析能力

### Page 13: 视频×RAG关键帧分析
- **Page Type**: Content
- **Page Title**: 视频 × RAG：关键帧智能分析
- **Content Structure**:
  - Step 1 上传视频：支持 MP4/AVI/MOV，最大 100 MB
  - Step 2 输入问题：自然语言提问（例：我的发球动作规范吗？）
  - Step 3 自动抽帧：OpenCV 均匀抽取 4~8 帧，覆盖全程
  - Step 4 多模态分析：逐帧 Qwen-VL 识别动作姿态与细节
  - Step 5 RAG 融合输出：帧分析 + 知识库检索 → 综合专业回答

### Page 14: 过渡页-架构
- **Page Type**: Transition
- **Page Title**: 系统架构与技术栈

### Page 15: 技术架构一览
- **Page Type**: Content
- **Page Title**: 技术架构一览
- **Content Structure**:
  - 前端层：响应式 Web UI，拖拽上传，实时进度，多知识库切换
  - API 层：FastAPI REST API，CORS，自动接口文档
  - 业务层：RAG 引擎 / 多模态处理 / 知识库管理 / 向量化队列
  - 模型层：Qwen-Turbo（回答生成）/ Qwen-VL-OCR（图片识字）/ Qwen-VL（视觉理解）
  - 存储层：本地文件系统 + NumPy 向量索引

### Page 16: 过渡页-总结
- **Page Type**: Transition
- **Page Title**: 总结与展望

### Page 17: 三大核心价值
- **Page Type**: Content
- **Page Title**: 三大核心价值
- **Content Structure**:
  - 🔄 灵活：知识库随换随用，一个系统服务多个领域，零停机切换
  - 👁️ 多模态：文字、图片、视频三类内容统一入库、检索、问答
  - ⚙️ 可靠：并发向量化、实时进度监控、断点续传，工程级稳定性

### Page 18: 未来迭代方向
- **Page Type**: Content
- **Page Title**: 未来迭代方向
- **Content Structure**:
  - 向量数据库升级：接入 FAISS/Milvus，支持亿级文档高效检索
  - 检索质量提升：引入 re-ranking 重排序，进一步提高答案准确率
  - 音视频扩展：集成 ASR 语音识别，视频音轨内容同步入库
  - 平台化演进：多租户 SaaS 架构，支持团队协作知识管理

### Page 19: 结束页
- **Page Type**: Ending
- **Page Title**: 谢谢观看
- **Content Structure**:
  - 主标题：谢谢观看
  - 副标题：多模态RAG知识问答系统
  - 标语：知识库随换随用 · 图片视频同样可答

## Design Style
Tech（科技风）— 深色/渐变背景，蓝紫主色系，Montserrat + Noto Sans SC 字体组合，卡片式布局，强调技术感与工程质感。
