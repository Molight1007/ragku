# Chapters: 多模态RAG知识库问答系统 PPT

## Page 1: 封面
- **Page Type**: Cover
- **Page Title**: 多模态RAG知识问答系统
- **Page Subtitle**: 知识库随换随用 · 图片视频同样可答
- **Selected Template**: cover/tech/051.tpl
- **Content Structure**:
  - 主标题：多模态RAG知识问答系统
  - 副标题：知识库随换随用 · 图片视频同样可答
  - 标签：阿里云通义千问 · FastAPI · Qwen-VL
  - 场景说明：全国大学生计算机设计大赛 AI 方向参赛作品
- **Content Density**: Light
- **Narrative Role**: 建立整体印象，突出最大亮点
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 2: 目录
- **Page Type**: TOC
- **Page Title**: 内容概览
- **Selected Template**: toc/tech/3580.tpl
- **Content Structure**:
  - 章节1：项目背景与价值
  - 章节2：核心功能全览
  - 章节3：最大亮点 — 知识库可更换
  - 章节4：图片处理能力
  - 章节5：视频分析能力
  - 章节6：系统架构与技术栈
  - 章节7：总结与展望
- **Content Density**: Light
- **Narrative Role**: 导航，帮助评委了解演讲结构
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 3: 过渡页-背景
- **Page Type**: Transition
- **Page Title**: 项目背景与价值
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：为什么需要 RAG？
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 4: 问题与痛点
- **Page Type**: Content
- **Page Title**: 传统大模型的局限
- **Selected Template**: content/tech/1582.tpl
- **Content Structure**:
  问题/解决方案结构：
  - 痛点1：知识截止——训练数据有时效，无法掌握最新/私有领域知识
  - 痛点2：固定知识库——资料库一旦构建便难以切换，多场景适应性差
  - 痛点3：只懂文字——传统问答系统无法理解图片和视频中的内容信息
  - 解法：RAG + 多模态 + 可切换知识库，三重突破一次解决
- **Content Density**: Medium
- **Narrative Role**: 建立问题背景，为后续解决方案铺垫
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 5: 过渡页-功能
- **Page Type**: Transition
- **Page Title**: 核心功能全览
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：核心功能全览
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 6: 功能全景图
- **Page Type**: Content
- **Page Title**: 六大核心能力
- **Selected Template**: content/tech/1581.tpl
- **Content Structure**:
  数据结构：6个功能卡片
  - 📁 多知识库管理：创建、删除、独立索引，互不干扰
  - 🔄 资料库随时切换：kb_id 参数一键切换，零停机
  - 🖼️ 图片 OCR 识字：提取图片文字，纳入可检索知识库
  - 👁️ 看图问答：Qwen-VL 理解画面，结合知识库综合回答
  - 🎬 视频关键帧分析：自动抽帧 + 多模态理解 + RAG 融合
  - 📄 多格式文档支持：TXT/MD/PDF/DOCX + 图片 + 视频
- **Content Density**: Medium
- **Narrative Role**: 全景展示系统能力，建立整体认知
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 7: 过渡页-知识库切换
- **Page Type**: Transition
- **Page Title**: 最大亮点：知识库可更换
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：最大亮点：知识库可更换
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 8: 知识库切换原理
- **Page Type**: Content
- **Page Title**: 多知识库架构设计
- **Selected Template**: content/tech/1683.tpl
- **Content Structure**:
  对比结构：传统 vs 本系统
  - 传统系统：单一固定知识库 → 切换需重启 → 大量停机时间 → 多场景无法兼顾
  - 本系统：多知识库独立存储 → kb_id 动态路由 → 毫秒级切换 → 无限场景扩展
  - 技术实现：每个 KB 有独立目录 + 独立向量索引文件，服务层按 ID 动态加载
  - 实际效果：1个服务实例 → 支撑 N 个独立领域知识库并发使用
- **Content Density**: Medium
- **Narrative Role**: 深度讲解核心差异化优势
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 9: 知识库切换演示
- **Page Type**: Content
- **Page Title**: 场景演示：一键切换领域
- **Selected Template**: content/tech/1687.tpl
- **Content Structure**:
  场景展示（3个切换案例）：
  - 场景A：消防安全库（消防规范、应急处置指南）→ 问"如何处置电气火灾"
  - 场景B：企业规章库（公司制度、员工手册）→ 问"年假政策是什么"
  - 场景C：体育训练库（专项动作标准、训练计划）→ 结合视频分析"动作是否规范"
  - 仅需修改请求中的 kb_id 字段，其余代码零改动
  - 知识库按需新建：上传文档 → 自动向量化 → 立即可用
- **Content Density**: Medium
- **Narrative Role**: 用具体场景证明切换能力的实用价值
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 10: 过渡页-图片处理
- **Page Type**: Transition
- **Page Title**: 图片处理能力
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：图片处理能力
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 11: 图片多模态能力
- **Page Type**: Content
- **Page Title**: 看懂图片 · 不止识字
- **Selected Template**: content/tech/1673.tpl
- **Content Structure**:
  两条处理链路：
  - 链路1 — OCR 识字入库：
    上传图片 → Qwen-VL-OCR 提取全部文字 → 切分分片 → 向量化存入知识库 → 后续可被检索
    适用：扫描件、截图、含文字的产品图等
  - 链路2 — 看图直接问答：
    上传图片 + 输入问题 → Qwen-VL 分析画面内容 → 结合知识库 RAG → 给出综合回答
    适用："这个零件是什么型号？"、"图中动作有何问题？"等
  - 支持格式：JPG、PNG、BMP、WebP、GIF
- **Content Density**: Heavy
- **Narrative Role**: 展示图片处理的两大链路，强调比纯 OCR 更智能
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 12: 过渡页-视频分析
- **Page Type**: Transition
- **Page Title**: 视频分析能力
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：视频分析能力
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 13: 视频分析流程
- **Page Type**: Content
- **Page Title**: 视频 × RAG：关键帧智能分析
- **Selected Template**: content/tech/1584.tpl
- **Content Structure**:
  流程步骤（5步）：
  - Step 1 上传视频：支持 MP4/AVI/MOV，最大 100 MB，网页拖拽上传
  - Step 2 输入问题：自然语言提问（例：我的发球动作规范吗？）
  - Step 3 自动抽帧：OpenCV 均匀抽取 4~8 帧，覆盖全程关键时刻
  - Step 4 多模态分析：逐帧调用 Qwen-VL，识别动作姿态、场景内容、细节问题
  - Step 5 RAG 融合输出：帧分析结论 + 知识库检索 → 通义千问综合生成专业回答
  - 典型用例："发球动作规范性分析"、"生产流程安全检查"、"实验操作步骤评估"
- **Content Density**: Heavy
- **Narrative Role**: 系统性展示视频分析技术链路，体现深度技术能力
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 14: 过渡页-架构
- **Page Type**: Transition
- **Page Title**: 系统架构与技术栈
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：系统架构与技术栈
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 15: 技术架构
- **Page Type**: Content
- **Page Title**: 技术架构一览
- **Selected Template**: content/tech/1686.tpl
- **Content Structure**:
  分层架构展示：
  - 前端层：响应式 Web UI，支持图片/视频拖拽上传，实时进度显示，多知识库切换下拉
  - API 层：FastAPI REST API，CORS 支持，自动接口文档（/docs）
  - 业务层：RAG 检索引擎 / 多模态处理（图片+视频）/ 知识库管理 / 向量化队列
  - 模型层：通义千问 Qwen-Turbo（生成回答）/ Qwen-VL-OCR（图片识字）/ Qwen-VL（视觉理解）
  - 存储层：本地文件系统（知识库目录）/ NumPy 向量索引文件（.npy）
  - 部署：桌面 EXE 启动器 + 后台 FastAPI Server，一键启动
- **Content Density**: Heavy
- **Narrative Role**: 展示系统工程深度，建立技术可信度
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 16: 过渡页-总结
- **Page Type**: Transition
- **Page Title**: 总结与展望
- **Selected Template**: transition/tech/559.tpl
- **Content Structure**:
  - 标题：总结与展望
- **Content Density**: Light
- **Narrative Role**: 章节过渡
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 17: 核心价值总结
- **Page Type**: Content
- **Page Title**: 三大核心价值
- **Selected Template**: content/tech/1690.tpl
- **Content Structure**:
  三栏价值主张：
  - 🔄 灵活：知识库随换随用，一个系统服务多个领域，零停机切换
  - 👁️ 多模态：文字、图片、视频三类内容统一入库、统一检索、统一问答
  - ⚙️ 可靠：并发向量化、实时进度监控、断点续传，工程级稳定性
  - 底部点睛：不只是会"聊天"的 AI，而是真正能用起来的知识管理工具
- **Content Density**: Medium
- **Narrative Role**: 提炼核心价值，加深评委印象
- **Image Requirements**: 
- **Page Weight**: Core page

## Page 18: 展望
- **Page Type**: Content
- **Page Title**: 未来迭代方向
- **Selected Template**: content/tech/1689.tpl
- **Content Structure**:
  未来规划（4个方向）：
  - 向量数据库升级：接入 FAISS/Milvus，支持亿级文档高效检索
  - 检索质量提升：引入 re-ranking 重排序，进一步提高答案准确率
  - 音视频扩展：集成 ASR 语音识别，视频音轨内容同步入库
  - 平台化演进：多租户 SaaS 架构，支持团队协作知识管理
- **Content Density**: Medium
- **Narrative Role**: 展示项目可延伸性和发展潜力
- **Image Requirements**: 
- **Page Weight**: Secondary page

## Page 19: 结束页
- **Page Type**: Ending
- **Page Title**: 谢谢观看
- **Selected Template**: ending/tech/1106.tpl
- **Content Structure**:
  - 主标题：谢谢观看
  - 副标题：多模态RAG知识问答系统
  - 标语：知识库随换随用 · 图片视频同样可答
  - 致谢：感谢评委老师的宝贵时间
- **Content Density**: Light
- **Narrative Role**: 礼貌收尾，留下良好印象
- **Image Requirements**: 
- **Page Weight**: Secondary page
