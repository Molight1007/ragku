"""
截图工具 - 捕获 PPT 幻灯片
"""
import asyncio
import os
import sys
from pathlib import Path

# 检查 playwright
async def capture_slides():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("正在安装 playwright...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.async_api import async_playwright
    
    output_dir = Path("d:/ragku/frontend/public/assets/images/posters/pages")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 810})
        
        # 总共13页
        for i in range(1, 14):
            url = f"http://localhost:5173/?page={i}"
            print(f"正在截图第 {i} 页...")
            
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(1)  # 等待动画
            
            output_file = output_dir / f"page-{i:02d}.png"
            await page.screenshot(path=str(output_file), full_page=False)
            print(f"已保存: {output_file}")
        
        await browser.close()
        print("截图完成!")

if __name__ == "__main__":
    asyncio.run(capture_slides())
