#!/usr/bin/env python3
"""
ComfyUI 启动调试脚本
用于调试ComfyUI的启动过程和关键功能
"""

import sys
import os
import logging
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_startup.log')
    ]
)

def debug_imports():
    """调试模块导入过程"""
    print("=== 调试模块导入 ===")
    
    try:
        print("1. 导入comfy.options...")
        import comfy.options
        comfy.options.enable_args_parsing()
        print("   ✓ comfy.options 导入成功")
        
        print("2. 导入基础模块...")
        import os
        import importlib.util
        import folder_paths
        import time
        import itertools
        import logging
        import sys
        print("   ✓ 基础模块导入成功")
        
        print("3. 导入ComfyUI核心模块...")
        from comfy.cli_args import args
        from app.logger import setup_logger
        from utils.extra_config import load_extra_path_config
        print("   ✓ ComfyUI核心模块导入成功")
        
        print("4. 设置日志系统...")
        setup_logger(log_level=args.verbose, use_stdout=args.log_stdout)
        print("   ✓ 日志系统设置成功")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_paths():
    """调试路径配置"""
    print("\n=== 调试路径配置 ===")
    
    try:
        from main import apply_custom_paths
        print("1. 执行路径配置...")
        apply_custom_paths()
        print("   ✓ 路径配置成功")
        
        print("2. 检查路径设置...")
        import folder_paths
        output_dir = folder_paths.get_output_directory()
        input_dir = folder_paths.get_input_directory()
        print(f"   输出目录: {output_dir}")
        print(f"   输入目录: {input_dir}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 路径配置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_custom_nodes():
    """调试自定义节点加载"""
    print("\n=== 调试自定义节点加载 ===")
    
    try:
        from main import execute_prestartup_script
        print("1. 执行自定义节点预启动...")
        execute_prestartup_script()
        print("   ✓ 自定义节点预启动完成")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 自定义节点加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_server_startup():
    """调试服务器启动"""
    print("\n=== 调试服务器启动 ===")
    
    try:
        from main import start_comfyui
        
        print("1. 启动ComfyUI...")
        # 这里可以添加断点
        # import pdb; pdb.set_trace()
        
        event_loop, server, start_all = start_comfyui()
        print("   ✓ ComfyUI启动成功")
        
        print("2. 检查启动结果...")
        print(f"   事件循环: {event_loop}")
        print(f"   服务器: {server}")
        print(f"   启动函数: {start_all}")
        
        return event_loop, server, start_all
        
    except Exception as e:
        print(f"   ✗ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def debug_async_startup(event_loop, start_all):
    """调试异步启动"""
    print("\n=== 调试异步启动 ===")
    
    if not event_loop or not start_all:
        print("   ✗ 无法进行异步启动调试")
        return False
    
    try:
        print("1. 运行异步启动函数...")
        # 这里可以添加断点
        # import pdb; pdb.set_trace()
        
        x = start_all()
        print("   ✓ 异步启动函数创建成功")
        
        print("2. 运行事件循环...")
        print("   注意：这将启动Web服务器，按Ctrl+C停止")
        
        # 运行事件循环
        event_loop.run_until_complete(x)
        
        return True
        
    except KeyboardInterrupt:
        print("\n   ✓ 用户中断，停止服务器")
        return True
    except Exception as e:
        print(f"   ✗ 异步启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主调试函数"""
    print("ComfyUI 启动调试脚本")
    print("=" * 50)
    
    # 步骤1：调试模块导入
    if not debug_imports():
        print("\n❌ 模块导入失败，无法继续")
        return
    
    # 步骤2：调试路径配置
    if not debug_paths():
        print("\n❌ 路径配置失败，无法继续")
        return
    
    # 步骤3：调试自定义节点加载
    if not debug_custom_nodes():
        print("\n⚠️ 自定义节点加载失败，但可以继续")
    
    # 步骤4：调试服务器启动
    event_loop, server, start_all = debug_server_startup()
    if not event_loop:
        print("\n❌ 服务器启动失败，无法继续")
        return
    
    # 步骤5：调试异步启动
    print("\n是否要启动Web服务器进行完整调试？(y/n): ", end="")
    choice = input().lower().strip()
    
    if choice == 'y':
        debug_async_startup(event_loop, start_all)
    else:
        print("\n✓ 调试完成，服务器未启动")
    
    print("\n调试脚本执行完成")

if __name__ == "__main__":
    main()
