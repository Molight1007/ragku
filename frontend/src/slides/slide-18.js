window.slideDataMap.set(18, `
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="absolute inset-0 opacity-10" style="background-image:linear-gradient(rgba(99,102,241,0.3) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,0.3) 1px,transparent 1px);background-size:60px 60px;"></div>
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative z-10 flex flex-col justify-center">
      <div class="text-center mb-6">
        <div class="inline-flex items-center gap-2 bg-sky-500/20 px-5 py-2 rounded-full mb-3">
          <div class="w-2 h-2 bg-sky-400 rounded-full animate-pulse"></div>
          <span class="text-sky-400 font-mono text-sm tracking-wider">FUTURE ROADMAP</span>
        </div>
        <h2 class="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-cyan-400 to-purple-400">
          未来迭代方向
        </h2>
      </div>
      
      <div class="grid grid-cols-2 gap-5">
        <div class="bg-gradient-to-br from-blue-500/15 to-indigo-500/15 border border-blue-500/40 p-6 rounded-xl flex items-start gap-4">
          <div class="text-3xl shrink-0">🗄️</div>
          <div>
            <h3 class="text-blue-300 font-bold text-lg mb-2">向量数据库升级</h3>
            <p class="text-gray-300 text-sm leading-relaxed">接入 FAISS 或 Milvus 向量数据库，支持亿级文档高效检索，突破当前 NumPy 内存索引的容量瓶颈。</p>
          </div>
        </div>
        <div class="bg-gradient-to-br from-purple-500/15 to-violet-500/15 border border-purple-500/40 p-6 rounded-xl flex items-start gap-4">
          <div class="text-3xl shrink-0">🎯</div>
          <div>
            <h3 class="text-purple-300 font-bold text-lg mb-2">检索质量提升</h3>
            <p class="text-gray-300 text-sm leading-relaxed">引入 re-ranking 重排序模型，对候选文档精细化评分，进一步提高答案准确率与相关性。</p>
          </div>
        </div>
        <div class="bg-gradient-to-br from-emerald-500/15 to-cyan-500/15 border border-emerald-500/40 p-6 rounded-xl flex items-start gap-4">
          <div class="text-3xl shrink-0">🔊</div>
          <div>
            <h3 class="text-emerald-300 font-bold text-lg mb-2">音视频扩展</h3>
            <p class="text-gray-300 text-sm leading-relaxed">集成 ASR 语音识别引擎，将视频音轨内容同步转文字入库，进一步丰富多媒体知识覆盖。</p>
          </div>
        </div>
        <div class="bg-gradient-to-br from-amber-500/15 to-orange-500/15 border border-amber-500/40 p-6 rounded-xl flex items-start gap-4">
          <div class="text-3xl shrink-0">🌐</div>
          <div>
            <h3 class="text-amber-300 font-bold text-lg mb-2">平台化演进</h3>
            <p class="text-gray-300 text-sm leading-relaxed">构建多租户 SaaS 架构，支持团队协作知识管理，实现知识库增量更新、权限管理与共享。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
`);
