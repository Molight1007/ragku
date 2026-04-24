window.slideDataMap.set(19, `
  <div class="w-[1440px] h-[810px] shadow-2xl relative overflow-hidden slide-bg">
    <div class="w-[1350px] h-[720px] mx-auto my-[45px] relative">
      <!-- 能量波背景 -->
      <svg style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:900px;height:900px;opacity:0.25;">
        <circle cx="450" cy="450" r="100" fill="none" stroke="#6366f1" stroke-width="2" opacity="0.8">
          <animate attributeName="r" values="100;360;100" dur="4s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.8;0.2;0.8" dur="4s" repeatCount="indefinite"/>
        </circle>
        <circle cx="450" cy="450" r="150" fill="none" stroke="#22d3ee" stroke-width="2" opacity="0.7">
          <animate attributeName="r" values="150;410;150" dur="4.5s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.7;0.15;0.7" dur="4.5s" repeatCount="indefinite"/>
        </circle>
        <circle cx="450" cy="450" r="200" fill="none" stroke="#a78bfa" stroke-width="2" opacity="0.5">
          <animate attributeName="r" values="200;450;200" dur="5s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.5;0.1;0.5" dur="5s" repeatCount="indefinite"/>
        </circle>
      </svg>

      <!-- 粒子 -->
      <div style="position:absolute;top:20%;left:15%;width:8px;height:8px;background:#6366f1;border-radius:50%;box-shadow:0 0 20px #6366f1;"></div>
      <div style="position:absolute;bottom:18%;right:12%;width:6px;height:6px;background:#22d3ee;border-radius:50%;box-shadow:0 0 15px #22d3ee;"></div>
      <div style="position:absolute;top:30%;right:15%;width:7px;height:7px;background:#a78bfa;border-radius:50%;box-shadow:0 0 18px #a78bfa;"></div>

      <div class="absolute inset-0 flex flex-col items-center justify-center z-10">
        <div style="position:relative;padding:50px 90px;background:rgba(15,23,42,0.9);backdrop-filter:blur(15px);border:2px solid rgba(99,102,241,0.6);box-shadow:0 0 60px rgba(99,102,241,0.35),inset 0 0 40px rgba(99,102,241,0.08);">
          <!-- 能量节点 -->
          <div style="position:absolute;top:-8px;left:50%;transform:translateX(-50%);width:14px;height:14px;background:#6366f1;border-radius:50%;box-shadow:0 0 25px #6366f1;"></div>
          <div style="position:absolute;bottom:-8px;left:50%;transform:translateX(-50%);width:14px;height:14px;background:#6366f1;border-radius:50%;box-shadow:0 0 25px #6366f1;"></div>
          <div style="position:absolute;left:-8px;top:50%;transform:translateY(-50%);width:14px;height:14px;background:#22d3ee;border-radius:50%;box-shadow:0 0 25px #22d3ee;"></div>
          <div style="position:absolute;right:-8px;top:50%;transform:translateY(-50%);width:14px;height:14px;background:#22d3ee;border-radius:50%;box-shadow:0 0 25px #22d3ee;"></div>
          
          <div class="text-6xl font-bold mb-4 text-center" style="background:linear-gradient(135deg,#6366f1 0%,#22d3ee 50%,#a78bfa 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:6px;filter:drop-shadow(0 0 30px rgba(99,102,241,0.6));">
            谢谢观看
          </div>
          <div class="text-xl text-cyan-400 text-center mb-4" style="letter-spacing:3px;">
            多模态RAG知识问答系统
          </div>
          <div class="text-base text-purple-300 text-center" style="letter-spacing:2px;">
            知识库随换随用 · 图片视频同样可答
          </div>
          <div class="text-sm text-slate-500 text-center mt-4">感谢评委老师的宝贵时间</div>
        </div>
      </div>

      <!-- 底部指示器 -->
      <div style="position:absolute;bottom:25px;left:50%;transform:translateX(-50%);display:flex;gap:8px;align-items:center;">
        <div style="width:8px;height:8px;background:#6366f1;border-radius:50%;box-shadow:0 0 15px #6366f1;animation:indicator-blink 1s ease-in-out infinite;"></div>
        <div style="width:8px;height:8px;background:#22d3ee;border-radius:50%;box-shadow:0 0 15px #22d3ee;animation:indicator-blink 1s ease-in-out infinite 0.3s;"></div>
        <div style="width:8px;height:8px;background:#a78bfa;border-radius:50%;box-shadow:0 0 15px #a78bfa;animation:indicator-blink 1s ease-in-out infinite 0.6s;"></div>
      </div>
    </div>
    <style>
      @keyframes indicator-blink { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
    </style>
  </div>
`);
