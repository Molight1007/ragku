window.slideDataMap.set(4, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="absolute inset-0 opacity-20">
        <div class="absolute top-1/4 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-blue-500 to-transparent"></div>
        <div class="absolute top-1/4 left-2/4 w-px h-full bg-gradient-to-b from-transparent via-cyan-500 to-transparent"></div>
        <div class="absolute top-1/4 left-3/4 w-px h-full bg-gradient-to-b from-transparent via-emerald-500 to-transparent"></div>
    </div>
    <div class="w-full h-full flex items-center justify-center relative">
        <div class="w-[1350px] h-[720px] mx-auto my-[20px] p-10 relative z-10 flex flex-col justify-center gap-6">
            <div class="text-center">
                <div class="inline-flex items-center gap-2 bg-red-500/20 shadow-md hover:shadow-lg px-5 py-2 rounded-full mb-3">
                    <div class="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
                    <span class="text-red-400 font-mono text-[14px] tracking-wider">PROBLEM ANALYSIS</span>
                </div>
                <h2 class="text-[38px] font-bold text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-orange-400 to-yellow-400 mb-2" style="font-family: 'Courier New', monospace;">
                    传统大模型的局限
                </h2>
                <p class="text-gray-400 text-[14px] font-mono">TRADITIONAL LLM LIMITATIONS</p>
            </div>
            
            <div class="max-w-5xl mx-auto">
                <div class="bg-slate-900/80 backdrop-blur border border-red-500/30 p-6 rounded-lg">
                    <p class="text-gray-200 text-[18px] leading-relaxed mb-3 font-mono">
                        传统大模型虽然具备强大的语言理解和生成能力，但存在三个核心痛点：知识截止导致无法回答最新信息、固定知识库无法适应多场景需求、仅支持文本无法理解图片视频内容。
                    </p>
                    <p class="text-gray-300 text-[16px] leading-relaxed font-mono">
                        本系统通过 RAG + 多模态 + 可切换知识库三重突破，彻底解决上述问题，实现真正的智能知识管理。
                    </p>
                </div>
            </div>
            
            <div class="grid grid-cols-3 gap-5">
                <div class="bg-gradient-to-br from-red-500/20 to-orange-500/20 backdrop-blur shadow-md hover:shadow-lg p-5 text-center hover:scale-105 transition-transform">
                    <div class="text-red-400 text-[30px] mb-2">⏰</div>
                    <p class="text-red-300 font-bold text-[18px] font-mono mb-1">知识截止</p>
                    <p class="text-gray-400 text-[12px] font-mono">训练数据有时效<br/>无法掌握最新知识</p>
                </div>
                <div class="bg-gradient-to-br from-orange-500/20 to-yellow-500/20 backdrop-blur shadow-md hover:shadow-lg p-5 text-center hover:scale-105 transition-transform">
                    <div class="text-orange-400 text-[30px] mb-2">🔒</div>
                    <p class="text-orange-300 font-bold text-[18px] font-mono mb-1">固定知识库</p>
                    <p class="text-gray-400 text-[12px] font-mono">资料库难以切换<br/>多场景适应性差</p>
                </div>
                <div class="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 backdrop-blur shadow-md hover:shadow-lg p-5 text-center hover:scale-105 transition-transform">
                    <div class="text-yellow-400 text-[30px] mb-2">📝</div>
                    <p class="text-yellow-300 font-bold text-[18px] font-mono mb-1">只懂文字</p>
                    <p class="text-gray-400 text-[12px] font-mono">无法理解图片<br/>和视频内容</p>
                </div>
            </div>
            
            <div class="grid grid-cols-2 gap-5">
                <div class="bg-black border-2 border-emerald-500 p-5 rounded-lg">
                    <div class="flex items-start gap-2">
                        <div class="text-emerald-400 text-[22px]">»</div>
                        <div>
                            <p class="text-emerald-300 text-[18px] leading-relaxed mb-1 font-mono italic">
                                "RAG 让大模型拥有了'记忆力'，可以实时注入私有知识。"
                            </p>
                            <p class="text-gray-500 text-[14px] font-mono">— 系统设计理念</p>
                        </div>
                    </div>
                </div>
                <div class="bg-emerald-950/50 backdrop-blur border border-emerald-600/30 p-5 rounded-lg">
                    <p class="text-emerald-300 text-[12px] leading-relaxed mb-1 font-mono">
                        <span class="text-emerald-400 font-bold">/* SOLUTION */</span>
                    </p>
                    <p class="text-gray-400 text-[12px] font-mono mb-1">RAG + 多模态 + 可切换知识库</p>
                    <p class="text-gray-400 text-[12px] font-mono">三重突破一次解决所有痛点</p>
                </div>
            </div>
        </div>
    </div>
</div>
`);
