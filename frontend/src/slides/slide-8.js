window.slideDataMap.set(8, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950">
    <div class="absolute inset-0 overflow-hidden">
        <div class="absolute top-1/4 left-0 w-3 h-3 bg-cyan-400 rounded-full opacity-60 animate-ping"></div>
        <div class="absolute top-1/3 left-1/4 w-2 h-2 bg-blue-400 rounded-full opacity-70" style="animation: float 3s ease-in-out infinite;"></div>
        <div class="absolute top-1/2 left-1/3 w-2.5 h-2.5 bg-purple-400 rounded-full opacity-50" style="animation: float 4s ease-in-out infinite;"></div>
        <div class="absolute bottom-1/3 right-1/4 w-2 h-2 bg-cyan-500 rounded-full opacity-60" style="animation: float 3.5s ease-in-out infinite;"></div>
    </div>
    <style>
        @keyframes float {
            0%, 100% { transform: translateY(0px) translateX(0px); }
            50% { transform: translateY(-20px) translateX(20px); }
        }
    </style>
    <div class="w-full h-full flex items-center justify-center relative">
        <div class="w-[1350px] h-[720px] mx-auto my-[20px] p-12 flex items-center justify-center relative">
            <h2 class="absolute top-12 left-1/2 transform -translate-x-1/2 text-[42px] font-bold text-cyan-400 z-10">
                智能问答流程
            </h2>
            <div class="relative w-full max-w-6xl">
                <svg class="w-full h-96" viewBox="0 0 1000 400">
                    <defs>
                        <linearGradient id="lineGrad8" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:#00ffff;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#0080ff;stop-opacity:1" />
                        </linearGradient>
                        <marker id="arrowhead8" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                            <polygon points="0 0, 10 3, 0 6" fill="#00ffff" />
                        </marker>
                    </defs>
                    <path d="M 150 200 L 215 200" stroke="url(#lineGrad8)" stroke-width="3" marker-end="url(#arrowhead8)"/>
                    <path d="M 325 200 L 390 200" stroke="url(#lineGrad8)" stroke-width="3" marker-end="url(#arrowhead8)"/>
                    <path d="M 500 200 L 565 200" stroke="url(#lineGrad8)" stroke-width="3" marker-end="url(#arrowhead8)"/>
                    <path d="M 675 200 L 740 200" stroke="url(#lineGrad8)" stroke-width="3" marker-end="url(#arrowhead8)"/>
                    <circle r="4" fill="#00ffff">
                        <animateMotion dur="4s" repeatCount="indefinite" path="M 150 200 L 225 200 L 325 200 L 400 200 L 500 200 L 575 200 L 675 200 L 800 200"/>
                    </circle>
                    <g>
                        <rect x="50" y="150" width="100" height="100" rx="10" fill="#1e293b" stroke="#00ffff" stroke-width="2"/>
                        <text x="100" y="190" text-anchor="middle" fill="#00ffff" font-size="16" font-weight="bold">用户</text>
                        <text x="100" y="210" text-anchor="middle" fill="#00ffff" font-size="16" font-weight="bold">提问</text>
                        <text x="100" y="235" text-anchor="middle" fill="#64748b" font-size="12">Query</text>
                    </g>
                    <g>
                        <rect x="225" y="150" width="100" height="100" rx="10" fill="#1e293b" stroke="#0080ff" stroke-width="2"/>
                        <text x="275" y="190" text-anchor="middle" fill="#0080ff" font-size="16" font-weight="bold">语义</text>
                        <text x="275" y="210" text-anchor="middle" fill="#0080ff" font-size="16" font-weight="bold">检索</text>
                        <text x="275" y="235" text-anchor="middle" fill="#64748b" font-size="12">Retrieve</text>
                    </g>
                    <g>
                        <rect x="400" y="150" width="100" height="100" rx="10" fill="#1e293b" stroke="#8b5cf6" stroke-width="2"/>
                        <text x="450" y="190" text-anchor="middle" fill="#8b5cf6" font-size="16" font-weight="bold">上下文</text>
                        <text x="450" y="210" text-anchor="middle" fill="#8b5cf6" font-size="16" font-weight="bold">构建</text>
                        <text x="450" y="235" text-anchor="middle" fill="#64748b" font-size="12">Context</text>
                    </g>
                    <g>
                        <rect x="575" y="150" width="100" height="100" rx="10" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
                        <text x="625" y="190" text-anchor="middle" fill="#10b981" font-size="16" font-weight="bold">LLM</text>
                        <text x="625" y="210" text-anchor="middle" fill="#10b981" font-size="16" font-weight="bold">生成</text>
                        <text x="625" y="235" text-anchor="middle" fill="#64748b" font-size="12">Generate</text>
                    </g>
                    <g>
                        <rect x="750" y="150" width="100" height="100" rx="10" fill="#1e293b" stroke="#f59e0b" stroke-width="2"/>
                        <text x="800" y="190" text-anchor="middle" fill="#f59e0b" font-size="16" font-weight="bold">智能</text>
                        <text x="800" y="210" text-anchor="middle" fill="#f59e0b" font-size="16" font-weight="bold">回答</text>
                        <text x="800" y="235" text-anchor="middle" fill="#64748b" font-size="12">Answer</text>
                    </g>
                    <g>
                        <text x="100" y="120" text-anchor="middle" fill="#64748b" font-size="16">自然语言</text>
                        <text x="275" y="120" text-anchor="middle" fill="#64748b" font-size="16">向量匹配</text>
                        <text x="450" y="120" text-anchor="middle" fill="#64748b" font-size="16">知识注入</text>
                        <text x="625" y="120" text-anchor="middle" fill="#64748b" font-size="16">Qwen Turbo</text>
                        <text x="800" y="120" text-anchor="middle" fill="#64748b" font-size="16">精准回复</text>
                    </g>
                    <g>
                        <text x="100" y="290" text-anchor="middle" fill="#00ffff" font-size="24" font-weight="bold">Any</text>
                        <text x="275" y="290" text-anchor="middle" fill="#0080ff" font-size="24" font-weight="bold">Top-K</text>
                        <text x="450" y="290" text-anchor="middle" fill="#8b5cf6" font-size="24" font-weight="bold">RAG</text>
                        <text x="625" y="290" text-anchor="middle" fill="#10b981" font-size="24" font-weight="bold">AI</text>
                        <text x="800" y="290" text-anchor="middle" fill="#f59e0b" font-size="24" font-weight="bold">Stream</text>
                    </g>
                </svg>
            </div>
            <div class="absolute bottom-12 left-1/2 transform -translate-x-1/2 text-center">
                <p class="text-cyan-400 text-[20px] font-mono">RAG PIPELINE · KNOWLEDGE AUGMENTED · REAL-TIME</p>
            </div>
        </div>
    </div>
</div>
`);
