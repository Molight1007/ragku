window.slideDataMap.set(2, `
<div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative">
        <!-- 赛博朋克故障效果背景 -->
        <div style="position: absolute; inset: 0; opacity: 0.1; background: repeating-linear-gradient(0deg, rgba(37, 99, 235, 0.3) 0px, transparent 2px, transparent 4px);"></div>
        
        <!-- 霓虹灯条 -->
        <div style="position: absolute; top: 10%; left: 0; width: 100%; height: 2px; background: linear-gradient(to right, transparent, #2563EB, #0EA5E9, transparent); opacity: 0.6;"></div>
        <div style="position: absolute; bottom: 15%; left: 0; width: 100%; height: 2px; background: linear-gradient(to right, transparent, #0EA5E9, #2563EB, transparent); opacity: 0.6;"></div>

        <div class="flex items-center h-full">
            <!-- 左侧标题区 -->
            <div style="width: 35%; padding-right: 40px;">
                <h1 class="text-5xl font-bold mb-6" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 0 30px rgba(37, 99, 235, 0.5); letter-spacing: 4px; font-family: 'Montserrat', sans-serif;">
                    CONTENTS<br/>目录
                </h1>
                <div class="space-y-1">
                    <div class="w-full h-1 bg-gradient-to-r from-blue-500 to-transparent"></div>
                    <div class="w-3/4 h-1 bg-gradient-to-r from-cyan-500 to-transparent"></div>
                    <div class="w-1/2 h-1 bg-gradient-to-r from-blue-500 to-transparent"></div>
                </div>
            </div>
            
            <!-- 右侧内容区 - 垂直列表 -->
            <div style="flex: 1;" class="space-y-3">
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">1</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">项目背景与价值</h3>
                                <p class="text-cyan-300 text-sm opacity-80">为什么需要 RAG？</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">2</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">核心功能全览</h3>
                                <p class="text-cyan-300 text-sm opacity-80">六大核心能力介绍</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">3</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">知识库可更换</h3>
                                <p class="text-cyan-300 text-sm opacity-80">最大亮点深度解析</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">4</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">图片与视频处理</h3>
                                <p class="text-cyan-300 text-sm opacity-80">多模态能力展示</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">5</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">系统架构与技术栈</h3>
                                <p class="text-cyan-300 text-sm opacity-80">技术实现深度解析</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
                <div class="group cursor-pointer">
                    <div style="position: relative; padding: 16px 22px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(14, 165, 233, 0.05) 100%); border: 2px solid; border-image: linear-gradient(135deg, #2563EB, #0EA5E9) 1; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px)); transition: all 0.3s;">
                        <div class="flex items-center gap-5">
                            <div style="width: 50px; height: 50px; background: linear-gradient(135deg, rgba(37, 99, 235, 0.3), rgba(14, 165, 233, 0.3)); border: 2px solid #2563EB; clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);">
                                <span class="text-xl font-bold text-blue-400">6</span>
                            </div>
                            <div style="flex: 1;">
                                <h3 class="text-lg font-bold mb-1" style="background: linear-gradient(90deg, #2563EB, #0EA5E9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">总结与展望</h3>
                                <p class="text-cyan-300 text-sm opacity-80">核心价值与未来规划</p>
                            </div>
                        </div>
                        <div style="position: absolute; top: 0; right: 0; width: 12px; height: 12px; background: #2563EB; clip-path: polygon(100% 0, 100% 100%, 0 100%);"></div>
                        <div style="position: absolute; bottom: 0; left: 0; width: 12px; height: 12px; background: #0EA5E9; clip-path: polygon(0 0, 100% 100%, 0 100%);"></div>
                    </div>
                </div>
                
            </div>
        </div>
    </div>
</div>
`);
