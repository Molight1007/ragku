window.slideDataMap.set(9, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden bg-black">
    <div class="absolute inset-0 opacity-10" style="background-image: repeating-linear-gradient(0deg, transparent, transparent 40px, #00ffff 40px, #00ffff 41px), repeating-linear-gradient(90deg, transparent, transparent 40px, #00ffff 40px, #00ffff 41px);"></div>
    <div class="w-full h-full flex items-center justify-center relative">
        <div class="w-[1350px] h-[720px] mx-auto my-[20px] p-12 flex flex-col items-center justify-center relative perspective-1000">
            <h2 class="text-[42px] font-bold text-cyan-400 mb-16 relative z-10">
                多模态内容理解
            </h2>
            <div class="relative w-full max-w-5xl" style="transform-style: preserve-3d; perspective: 1200px;">
                <div class="flex justify-center items-center gap-14">
                    <div class="relative w-52 h-52" style="transform-style: preserve-3d; transform: rotateX(-15deg) rotateY(-25deg);">
                        <div class="absolute w-full h-full bg-gradient-to-br from-cyan-500/80 to-blue-600/80 border-2 border-cyan-400 flex items-center justify-center" style="transform: translateZ(104px);">
                            <div class="text-center">
                                <div class="text-[38px] mb-3">🖼️</div>
                                <p class="text-white font-bold text-[22px]">图片理解</p>
                                <p class="text-cyan-200 text-[16px] mt-2">Image</p>
                            </div>
                        </div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-cyan-600/60 to-blue-700/60 border-2 border-cyan-500" style="transform: rotateY(90deg) translateZ(104px);"></div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-cyan-400/40 to-blue-500/40 border-2 border-cyan-600" style="transform: rotateX(90deg) translateZ(104px);"></div>
                    </div>
                    <div class="relative w-52 h-52" style="transform-style: preserve-3d; transform: rotateX(-15deg) rotateY(-25deg);">
                        <div class="absolute w-full h-full bg-gradient-to-br from-purple-500/80 to-pink-600/80 border-2 border-purple-400 flex items-center justify-center" style="transform: translateZ(104px);">
                            <div class="text-center">
                                <div class="text-[38px] mb-3">🎬</div>
                                <p class="text-white font-bold text-[22px]">视频分析</p>
                                <p class="text-purple-200 text-[16px] mt-2">Video</p>
                            </div>
                        </div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-purple-600/60 to-pink-700/60 border-2 border-purple-500" style="transform: rotateY(90deg) translateZ(104px);"></div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-purple-400/40 to-pink-500/40 border-2 border-purple-600" style="transform: rotateX(90deg) translateZ(104px);"></div>
                    </div>
                    <div class="relative w-52 h-52" style="transform-style: preserve-3d; transform: rotateX(-15deg) rotateY(-25deg);">
                        <div class="absolute w-full h-full bg-gradient-to-br from-green-500/80 to-emerald-600/80 border-2 border-green-400 flex items-center justify-center" style="transform: translateZ(104px);">
                            <div class="text-center">
                                <div class="text-[38px] mb-3">💬</div>
                                <p class="text-white font-bold text-[22px]">智能问答</p>
                                <p class="text-green-200 text-[16px] mt-2">Q&A</p>
                            </div>
                        </div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-green-600/60 to-emerald-700/60 border-2 border-green-500" style="transform: rotateY(90deg) translateZ(104px);"></div>
                        <div class="absolute w-full h-full bg-gradient-to-br from-green-400/40 to-emerald-500/40 border-2 border-green-600" style="transform: rotateX(90deg) translateZ(104px);"></div>
                    </div>
                </div>
                <svg class="absolute inset-0 w-full h-full pointer-events-none" style="top: 50%; transform: translateY(-50%);">
                    <defs>
                        <marker id="arrow9" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                            <polygon points="0 0, 8 3, 0 6" fill="#00ffff" />
                        </marker>
                    </defs>
                    <line x1="250" y1="130" x2="390" y2="130" stroke="#00ffff" stroke-width="3" stroke-dasharray="10,5" marker-end="url(#arrow9)"/>
                    <line x1="640" y1="130" x2="780" y2="130" stroke="#00ffff" stroke-width="3" stroke-dasharray="10,5" marker-end="url(#arrow9)"/>
                </svg>
            </div>
            <div class="mt-16 flex justify-center gap-16 relative z-10">
                <div class="text-center">
                    <p class="text-[32px] font-bold text-cyan-400 mb-2">OCR</p>
                    <p class="text-gray-400 text-[16px]">图片文字识别</p>
                </div>
                <div class="text-center">
                    <p class="text-[32px] font-bold text-purple-400 mb-2">VL</p>
                    <p class="text-gray-400 text-[16px]">视觉语言模型</p>
                </div>
                <div class="text-center">
                    <p class="text-[32px] font-bold text-green-400 mb-2">RAG</p>
                    <p class="text-gray-400 text-[16px]">知识增强回答</p>
                </div>
            </div>
        </div>
    </div>
</div>
`);
