window.slideDataMap.set(11, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950">
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
        <svg class="w-[700px] h-[700px]" viewBox="0 0 600 600">
            <circle cx="300" cy="300" r="250" fill="none" stroke="#00ffff" stroke-width="1" opacity="0.3"/>
            <circle cx="300" cy="300" r="200" fill="none" stroke="#00ffff" stroke-width="1" opacity="0.4"/>
            <circle cx="300" cy="300" r="150" fill="none" stroke="#00ffff" stroke-width="1" opacity="0.5"/>
            <circle cx="300" cy="300" r="100" fill="none" stroke="#00ffff" stroke-width="1" opacity="0.6"/>
            <circle cx="300" cy="300" r="50" fill="none" stroke="#00ffff" stroke-width="2" opacity="0.7"/>
            <line x1="50" y1="300" x2="550" y2="300" stroke="#00ffff" stroke-width="1" opacity="0.3"/>
            <line x1="300" y1="50" x2="300" y2="550" stroke="#00ffff" stroke-width="1" opacity="0.3"/>
            <line x1="121" y1="121" x2="479" y2="479" stroke="#00ffff" stroke-width="1" opacity="0.2"/>
            <line x1="479" y1="121" x2="121" y2="479" stroke="#00ffff" stroke-width="1" opacity="0.2"/>
            <g style="transform-origin: center; animation: rotate 4s linear infinite;">
                <path d="M 300 300 L 300 50 A 250 250 0 0 1 477 123 Z" fill="url(#scanGrad11)" opacity="0.4"/>
            </g>
            <defs>
                <linearGradient id="scanGrad11" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#00ffff;stop-opacity:0" />
                    <stop offset="100%" style="stop-color:#00ffff;stop-opacity:0.6" />
                </linearGradient>
            </defs>
        </svg>
    </div>
    <style>
        @keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    <div class="w-full h-full flex items-center justify-center relative">
        <div class="w-[1350px] h-[720px] mx-auto my-[20px] p-12 flex items-center justify-center relative">
            <h2 class="absolute top-12 left-1/2 transform -translate-x-1/2 text-[42px] font-bold text-cyan-400 z-10">
                系统性能监控
            </h2>
            <div class="relative w-full max-w-4xl h-96">
                <div class="absolute" style="top: 5%; left: 5%;">
                    <div class="relative">
                        <div class="w-4 h-4 bg-red-500 rounded-full animate-ping"></div>
                        <div class="w-4 h-4 bg-red-500 rounded-full absolute top-0"></div>
                        <div class="absolute top-6 left-6 bg-black/90 border border-red-500 p-3 rounded min-w-[130px]">
                            <p class="text-red-400 font-bold text-[16px] mb-1">并发处理</p>
                            <p class="text-gray-400 text-[14px]">Multi-thread</p>
                            <p class="text-red-500 text-[14px] mt-1">支持: 100+</p>
                        </div>
                    </div>
                </div>
                <div class="absolute" style="top: 0%; right: 5%;">
                    <div class="relative">
                        <div class="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>
                        <div class="absolute top-6 right-0 bg-black/90 border border-yellow-500 p-3 rounded min-w-[130px]">
                            <p class="text-yellow-400 font-bold text-[16px] mb-1">响应速度</p>
                            <p class="text-gray-400 text-[14px]">Response</p>
                            <p class="text-yellow-500 text-[14px] mt-1">&lt; 2s</p>
                        </div>
                    </div>
                </div>
                <div class="absolute" style="bottom: 5%; left: 5%;">
                    <div class="relative">
                        <div class="w-3 h-3 bg-green-500 rounded-full"></div>
                        <div class="absolute bottom-6 left-0 bg-black/90 border border-green-500 p-3 rounded min-w-[130px]">
                            <p class="text-green-400 font-bold text-[16px] mb-1">准确率</p>
                            <p class="text-gray-400 text-[14px]">Accuracy</p>
                            <p class="text-green-500 text-[14px] mt-1">95%+</p>
                        </div>
                    </div>
                </div>
                <div class="absolute" style="bottom: 5%; right: 5%;">
                    <div class="relative">
                        <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
                        <div class="absolute bottom-6 right-0 bg-black/90 border border-blue-500 p-3 rounded min-w-[130px]">
                            <p class="text-blue-400 font-bold text-[16px] mb-1">可用性</p>
                            <p class="text-gray-400 text-[14px]">Uptime</p>
                            <p class="text-blue-500 text-[14px] mt-1">99.9%</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="absolute bottom-10 left-1/2 transform -translate-x-1/2 w-full max-w-5xl">
                <div class="bg-slate-900/80 border border-cyan-500/30 rounded-lg p-6">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center gap-3">
                            <div class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                            <span class="text-green-400 font-mono text-[16px]">SYSTEM ONLINE</span>
                        </div>
                        <div class="flex gap-8">
                            <div class="text-center">
                                <p class="text-red-400 text-[22px] font-bold">FastAPI</p>
                                <p class="text-gray-400 text-[14px]">后端框架</p>
                            </div>
                            <div class="text-center">
                                <p class="text-yellow-400 text-[22px] font-bold">Qwen</p>
                                <p class="text-gray-400 text-[14px]">大模型</p>
                            </div>
                            <div class="text-center">
                                <p class="text-cyan-400 text-[22px] font-bold">Vector</p>
                                <p class="text-gray-400 text-[14px]">向量检索</p>
                            </div>
                            <div class="text-center">
                                <p class="text-green-400 text-[22px] font-bold">Async</p>
                                <p class="text-gray-400 text-[14px]">异步处理</p>
                            </div>
                        </div>
                        <div class="font-mono text-cyan-400 text-[16px]">RAG v1.0</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
`);
