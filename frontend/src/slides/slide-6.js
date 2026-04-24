window.slideDataMap.set(6, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
    <div class="absolute inset-0" style="background-image: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(59, 130, 246, 0.05) 2px, rgba(59, 130, 246, 0.05) 4px), repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(59, 130, 246, 0.05) 2px, rgba(59, 130, 246, 0.05) 4px);"></div>
    <div class="w-full h-full flex items-center justify-center relative">
        <div class="w-[1350px] h-[720px] mx-auto my-[20px] p-14 relative z-10">
            <div class="bg-slate-800/80 backdrop-blur p-8 rounded-lg shadow-lg shadow-blue-500/20 mb-6">
                <h2 class="text-[32px] font-bold text-blue-400 mb-4 flex items-center gap-3" style="font-family: 'Courier New', monospace;">
                    <div class="w-10 h-10 bg-blue-500 flex items-center justify-center text-white font-mono text-[18px]">&lt;/&gt;</div>
                    多格式文档智能解析
                </h2>
                <p class="text-gray-200 text-[18px] leading-relaxed mb-4" style="font-family: 'Courier New', monospace;">
                    支持 PDF、Word、TXT、Markdown 等主流文档格式的自动解析与向量化处理。系统采用先进的文本提取技术，保留文档结构和语义信息。
                </p>
                <p class="text-gray-200 text-[18px] leading-relaxed" style="font-family: 'Courier New', monospace;">
                    内置 OCR 能力，可识别扫描版 PDF 和图片中的文字内容，实现真正的全格式覆盖。
                </p>
            </div>
            <div class="grid grid-cols-3 gap-6">
                <div class="col-span-2 grid grid-cols-2 gap-4">
                    <div class="bg-gradient-to-br from-blue-600/30 to-cyan-600/30 backdrop-blur shadow-md p-7 rounded hover:border-blue-400 transition-colors">
                        <div class="flex items-center gap-2 mb-3"><div class="w-8 h-8 bg-blue-500 text-white flex items-center justify-center font-mono text-[14px]">01</div><h4 class="text-[20px] font-bold text-blue-300" style="font-family: 'Courier New', monospace;">PDF 文档</h4></div>
                        <p class="text-gray-300 text-[16px]" style="font-family: 'Courier New', monospace;">原生 + 扫描版全支持</p>
                    </div>
                    <div class="bg-gradient-to-br from-cyan-600/30 to-teal-600/30 backdrop-blur shadow-md p-7 rounded hover:border-cyan-400 transition-colors">
                        <div class="flex items-center gap-2 mb-3"><div class="w-8 h-8 bg-cyan-500 text-white flex items-center justify-center font-mono text-[14px]">02</div><h4 class="text-[20px] font-bold text-cyan-300" style="font-family: 'Courier New', monospace;">Word 文档</h4></div>
                        <p class="text-gray-300 text-[16px]" style="font-family: 'Courier New', monospace;">DOCX 格式完美解析</p>
                    </div>
                    <div class="bg-gradient-to-br from-teal-600/30 to-green-600/30 backdrop-blur shadow-md p-7 rounded hover:border-teal-400 transition-colors">
                        <div class="flex items-center gap-2 mb-3"><div class="w-8 h-8 bg-teal-500 text-white flex items-center justify-center font-mono text-[14px]">03</div><h4 class="text-[20px] font-bold text-teal-300" style="font-family: 'Courier New', monospace;">纯文本</h4></div>
                        <p class="text-gray-300 text-[16px]" style="font-family: 'Courier New', monospace;">TXT / Markdown 支持</p>
                    </div>
                    <div class="bg-gradient-to-br from-green-600/30 to-emerald-600/30 backdrop-blur shadow-md p-7 rounded hover:border-green-400 transition-colors">
                        <div class="flex items-center gap-2 mb-3"><div class="w-8 h-8 bg-green-500 text-white flex items-center justify-center font-mono text-[14px]">04</div><h4 class="text-[20px] font-bold text-green-300" style="font-family: 'Courier New', monospace;">OCR 识别</h4></div>
                        <p class="text-gray-300 text-[16px]" style="font-family: 'Courier New', monospace;">图片文字智能提取</p>
                    </div>
                </div>
                <div class="flex flex-col gap-6">
                    <div class="bg-black border-2 border-blue-500 p-6 rounded relative overflow-hidden">
                        <div class="absolute top-0 right-0 text-[42px] text-blue-500/10 font-mono">{}</div>
                        <div class="relative z-10">
                            <p class="text-blue-400 text-[18px] leading-relaxed mb-3 font-mono">"支持几乎所有常见文档格式，无需预处理即可直接上传"</p>
                        </div>
                    </div>
                    <div class="bg-blue-950/50 backdrop-blur p-5 rounded border border-blue-600/30">
                        <p class="text-blue-300 text-[14px] leading-relaxed mb-2 font-mono"><span class="font-bold text-blue-400">// 技术栈:</span> PyPDF2 / python-docx</p>
                        <p class="text-blue-400 text-[14px] font-mono">// OCR: 阿里云 Qwen-VL</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
`);
