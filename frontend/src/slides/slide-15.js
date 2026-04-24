window.slideDataMap.set(15, `
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="absolute inset-0 opacity-10" style="background-image:linear-gradient(rgba(99,102,241,0.3) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,0.3) 1px,transparent 1px);background-size:60px 60px;"></div>
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative z-10 flex flex-col justify-center">
      <div class="text-center mb-4">
        <div class="inline-flex items-center gap-2 bg-sky-500/20 px-5 py-2 rounded-full mb-3">
          <div class="w-2 h-2 bg-sky-400 rounded-full animate-pulse"></div>
          <span class="text-sky-400 font-mono text-sm tracking-wider">SYSTEM ARCHITECTURE</span>
        </div>
        <h2 class="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-cyan-400 to-purple-400">
          技术架构一览
        </h2>
      </div>
      
      <div class="space-y-2">
        ${[
          {label:'前端层', tags:['响应式 Web UI', '图片/视频拖拽上传', '实时进度显示', '多知识库切换下拉'], color:'from-sky-500/20 to-blue-500/20', border:'border-sky-500/35', text:'text-sky-300'},
          {label:'API 层', tags:['FastAPI REST API', 'CORS 支持', '自动接口文档 /docs', '文件上传接口', '向量化进度 SSE'], color:'from-blue-500/20 to-indigo-500/20', border:'border-blue-500/35', text:'text-blue-300'},
          {label:'业务层', tags:['RAG 检索引擎', '多模态处理（图片+视频）', '多知识库管理', '并发向量化队列', '断点续传'], color:'from-indigo-500/20 to-purple-500/20', border:'border-indigo-500/35', text:'text-indigo-300'},
          {label:'模型层', tags:['Qwen-Turbo（生成回答）', 'Qwen-VL-OCR（图片识字）', 'Qwen-VL（视觉理解）', 'DashScope SDK'], color:'from-purple-500/20 to-violet-500/20', border:'border-purple-500/35', text:'text-purple-300'},
          {label:'存储层', tags:['本地文件系统（知识库目录）', 'NumPy 向量索引（.npy）', '上传文件缓存', '桌面 EXE 启动器'], color:'from-violet-500/20 to-cyan-500/20', border:'border-violet-500/35', text:'text-violet-300'},
        ].map(row => `
        <div class="bg-gradient-to-r ${row.color} border ${row.border} p-3 rounded-xl flex items-center gap-5">
          <div class="${row.text} font-bold text-sm w-16 shrink-0">${row.label}</div>
          <div class="w-px h-8 bg-slate-600/60 shrink-0"></div>
          <div class="flex gap-2 flex-wrap">
            ${row.tags.map(t => `<span class="bg-slate-800/60 text-gray-300 px-2 py-1 rounded text-xs">${t}</span>`).join('')}
          </div>
        </div>
        `).join('')}
      </div>
    </div>
  </div>
`);
