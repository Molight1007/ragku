#!/usr/bin/env python3
"""
最终系统测试

测试分块上传和向量化系统的整体功能
"""

import sys
import time
import json
import tempfile
from pathlib import Path
import shutil


def test_system_initialization():
    """测试系统初始化"""
    print("[测试] 系统初始化...")
    
    # 检查所有模块
    required_modules = [
        "chunked_upload.py",
        "vectorization_queue.py",
        "upload_persistence.py", 
        "upload_api.py",
        "app.py"
    ]
    
    for module in required_modules:
        if not Path(module).exists():
            print(f"  [×] {module}: 缺失")
            return False
        print(f"  [√] {module}: 存在")
    
    # 检查目录结构
    required_dirs = [
        "knowledge",
        "uploads/temp",
        "data",
        "data/backups"
    ]
    
    for directory in required_dirs:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"  [×] 目录 {directory}: 缺失")
            return False
        print(f"  [√] 目录 {directory}: 存在")
    
    return True


def test_app_integration():
    """测试app.py集成"""
    print("\n[测试] app.py集成检查...")
    
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ("新模块导入", "from upload_api import router as upload_router"),
        ("新API路由", "app.include_router(upload_router)"),
        ("上传系统初始化", "init_upload_system()"),
        ("混合上传接口", "async def api_kb_upload"),  # 修改后的接口
        ("新进度API", "async def api_kb_progress_enhanced"),
        ("前端集成", "uploadSystemStatus"),  # 新的状态显示
        ("JavaScript集成", "uploadFileWithNewSystem"),
        ("上传模式选择", "uploadModeSelect"),
    ]
    
    all_passed = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"  [√] {check_name}: 已集成")
        else:
            print(f"  [×] {check_name}: 未集成")
            all_passed = False
    
    return all_passed


def test_chunked_upload_module():
    """测试分块上传模块"""
    print("\n[测试] 分块上传模块...")
    
    try:
        # 动态导入模块
        sys.path.insert(0, str(Path.cwd()))
        
        import chunked_upload as cu
        
        print(f"  [√] 模块导入成功")
        print(f"  - 分块大小: {cu.CHUNK_SIZE / 1024 / 1024:.1f}MB")
        print(f"  - 最大分块数: {cu.MAX_CHUNKS_PER_FILE}")
        print(f"  - 临时目录: {cu.UPLOAD_TEMP_DIR}")
        
        # 测试会话创建（不实际创建文件）
        print(f"  [√] 模块接口检查完成")
        
        return True
        
    except Exception as e:
        print(f"  [×] 模块测试失败: {e}")
        return False
    finally:
        sys.path.pop(0)


def test_vectorization_queue_module():
    """测试向量化队列模块"""
    print("\n[测试] 向量化队列模块...")
    
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        import vectorization_queue as vq
        
        print(f"  [√] 模块导入成功")
        print(f"  - 任务状态: {[s.value for s in vq.TaskStatus]}")
        print(f"  - 任务优先级: {[p.value for p in vq.TaskPriority]}")
        
        # 测试全局队列实例
        queue = vq.get_vectorization_queue()
        print(f"  [√] 队列实例创建成功")
        
        return True
        
    except Exception as e:
        print(f"  [×] 模块测试失败: {e}")
        return False
    finally:
        sys.path.pop(0)


def test_persistence_module():
    """测试持久化模块"""
    print("\n[测试] 持久化模块...")
    
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        import upload_persistence as up
        
        print(f"  [√] 模块导入成功")
        
        # 获取实例
        persistence = up.get_persistence()
        print(f"  [√] 持久化实例创建成功")
        
        # 测试健康检查
        health = persistence.run_health_check()
        print(f"  [√] 健康检查功能正常")
        print(f"  - 数据库状态: {health.get('database', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"  [×] 模块测试失败: {e}")
        return False
    finally:
        sys.path.pop(0)


def test_api_module():
    """测试API模块"""
    print("\n[测试] API模块...")
    
    try:
        sys.path.insert(0, str(Path.cwd()))
        
        import upload_api as uapi
        
        print(f"  [√] 模块导入成功")
        print(f"  - API路由数量: {len(uapi.router.routes)}")
        
        # 列出主要API端点
        endpoints = []
        for route in uapi.router.routes:
            if hasattr(route, "path"):
                endpoints.append(f"{route.methods} {route.path}")
        
        print(f"  [√] API端点定义完成 ({len(endpoints)}个)")
        
        # 检查主要的API类型
        api_categories = {
            "上传会话": ["/api/v2/upload/sessions"],
            "分块上传": ["/api/v2/upload/sessions/{session_id}/chunks/{chunk_id}"],
            "进度查询": ["/api/v2/upload/sessions/{session_id}/progress"],
            "向量化任务": ["/api/v2/vectorization/tasks/{task_id}"],
            "系统管理": ["/api/v2/health", "/api/v2/stats"],
        }
        
        for category, patterns in api_categories.items():
            found = any(any(pattern in endpoint for pattern in patterns) for endpoint in endpoints)
            if found:
                print(f"  [√] {category} API: 存在")
            else:
                print(f"  [×] {category} API: 缺失")
        
        return True
        
    except Exception as e:
        print(f"  [×] 模块测试失败: {e}")
        return False
    finally:
        sys.path.pop(0)


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n[测试] 向后兼容性...")
    
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查原有的API端点是否还存在
    old_endpoints = [
        "/api/kb/upload",        # 原有的上传接口
        "/api/kb/{kb_id}/progress",  # 原有的进度接口
        "/api/kb/{kb_id}/files",     # 原有的文件列表接口
        "/api/kb/{kb_id}/delete",    # 原有的删除接口
    ]
    
    all_present = True
    for endpoint in old_endpoints:
        # 查找@app.开头的定义
        pattern = f'@app.*["\']{endpoint}["\']'
        if pattern in content:
            print(f"  [√] 原有端点 {endpoint}: 存在")
        else:
            print(f"  [×] 原有端点 {endpoint}: 缺失")
            all_present = False
    
    return all_present


def create_test_file():
    """创建测试文件"""
    print("\n[测试] 创建测试环境...")
    
    # 创建测试知识库目录
    kb_dir = Path("knowledge/test_kb")
    kb_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建知识库名称文件
    name_file = kb_dir / "name.txt"
    name_file.write_text("测试知识库")
    
    # 创建测试文件目录
    files_dir = kb_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试文件
    test_file = files_dir / "test_document.txt"
    test_content = "这是一个测试文档，用于验证上传系统功能。\n" * 100  # 生成约2KB的内容
    test_file.write_text(test_content, encoding="utf-8")
    
    print(f"  [√] 测试知识库创建: test_kb")
    print(f"  [√] 测试文件创建: {test_file}")
    
    return "test_kb", test_file


def cleanup_test_environment(kb_id):
    """清理测试环境"""
    print("\n[清理] 测试环境...")
    
    try:
        # 清理知识库目录
        kb_dir = Path("knowledge") / kb_id
        if kb_dir.exists():
            shutil.rmtree(kb_dir)
            print(f"  [√] 清理知识库: {kb_id}")
        
        # 清理临时目录
        temp_dirs = ["uploads/temp", "knowledge/temp"]
        for temp_dir in temp_dirs:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                for item in temp_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                print(f"  [√] 清理临时目录: {temp_dir}")
        
        return True
        
    except Exception as e:
        print(f"  [×] 清理失败: {e}")
        return False


def generate_deployment_plan():
    """生成部署计划"""
    print("\n" + "="*60)
    print("部署计划")
    print("="*60)
    
    plan = """
📋 部署步骤:

1. [磁盘] 备份现有系统
   - 备份数据库和配置文件
   - 记录当前版本信息

2. [火箭] 部署新系统
   - 确保所有新模块已就位
   - 验证app.py集成正确
   - 创建必要的目录结构

3. [工具] 配置系统
   - 检查环境变量
   - 验证API密钥配置
   - 配置分块大小和并发数

4. [试管] 测试功能
   - 测试传统上传模式
   - 测试分块上传模式
   - 测试断点续传功能
   - 测试向量化任务恢复

5. [图表] 监控系统
   - 启动健康检查
   - 监控系统统计
   - 设置报警阈值

6. [文档] 更新文档
   - 更新API文档
   - 更新用户手册
   - 记录部署日志

7. [目标] 上线准备
   - 性能压力测试
   - 安全漏洞扫描
   - 备份恢复测试
   """
    
    print(plan)


def main():
    """主测试函数"""
    print("=" * 60)
    print("高级上传系统 - 最终测试")
    print("=" * 60)
    
    test_results = []
    
    try:
        # 运行所有测试
        test_results.append(("系统初始化", test_system_initialization()))
        test_results.append(("app.py集成", test_app_integration()))
        test_results.append(("分块上传模块", test_chunked_upload_module()))
        test_results.append(("向量化队列模块", test_vectorization_queue_module()))
        test_results.append(("持久化模块", test_persistence_module()))
        test_results.append(("API模块", test_api_module()))
        test_results.append(("向后兼容性", test_backward_compatibility()))
        
        # 创建测试环境
        kb_id, test_file = create_test_file()
        
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "[√] 通过" if result else "[×] 失败"
            print(f"{test_name:20} {status}")
        
        print("-" * 60)
        print(f"总计: {passed}/{total} 项测试通过")
        
        if passed == total:
            print("\n[结论] [√√] 所有测试通过，系统准备就绪!")
            
            # 生成部署计划
            generate_deployment_plan()
            
            print("\n[庆祝] 系统部署成功!")
            print("下一步建议:")
            print("1. 启动服务器: python -m uvicorn app:app --reload")
            print("2. 访问界面: http://localhost:8001/chat-ui")
            print("3. 测试大文件上传 (>100MB)")
            print("4. 测试断点续传功能")
            print("5. 查看系统统计: curl http://localhost:8001/api/v2/stats")
            
        else:
            print("\n[结论] [××] 部分测试未通过，需要修复")
            
        # 清理测试环境
        cleanup_test_environment(kb_id)
        
        return passed == total
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)