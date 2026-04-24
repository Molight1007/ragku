window.slideDataMap.set(1, `
<div class="cover-wrapper relative w-[1440px] h-[810px]">
    <div class="absolute top-0 left-0 slide-bg flex items-center justify-center w-[1440px] h-[810px] relative overflow-hidden">
        <!-- 粒子流装饰 -->
        <div class="absolute top-1/4 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-blue-500/30 to-transparent"></div>
        <div class="absolute top-1/2 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent"></div>
        <div class="absolute top-3/4 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent"></div>
        
        <div class="relative z-10 text-center px-24 max-w-[1100px]">
            <div class="flex items-center justify-center gap-5 mb-8">
                <div class="w-20 h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent"></div>
                <div class="flex gap-2">
                    <div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                    <div class="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" style="animation-delay: 0.3s;"></div>
                    <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" style="animation-delay: 0.6s;"></div>
                </div>
                <div class="w-20 h-[2px] bg-gradient-to-l from-transparent via-blue-500 to-transparent"></div>
            </div>
            
            <h1 class="text-[4.5rem] font-bold text-white mb-6 tracking-wide leading-tight" style="text-shadow: 0 0 40px rgba(37, 99, 235, 0.6);">
                多模态RAG知识问答系统
            </h1>
            
            <p class="text-2xl text-blue-300 mb-10 max-w-[950px] mx-auto font-light">
                知识库随换随用 · 图片视频同样可答
            </p>
            
            <div class="inline-flex items-center gap-8 px-10 py-4 bg-blue-500/10 backdrop-blur-sm border-[2px] border-blue-500/30 rounded-2xl mb-8">
                <div class="text-left">
                    <div class="text-blue-400 text-xs uppercase tracking-wider mb-1">技术栈</div>
                    <div class="text-white font-medium text-base">阿里云通义千问 · FastAPI · Qwen-VL</div>
                </div>
            </div>
            
            <div class="text-cyan-400 text-sm tracking-wider">
                全国大学生计算机设计大赛 AI 方向参赛作品
            </div>
        </div>
        
        <!-- 光晕效果 -->
        <div class="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-blue-600/20 rounded-full blur-3xl"></div>
        <div class="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-cyan-600/20 rounded-full blur-3xl"></div>
    </div>
</div>
`);
