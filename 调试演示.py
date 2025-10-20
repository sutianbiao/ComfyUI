#!/usr/bin/env python3
"""
ComfyUI 编辑器调试演示脚本
演示如何在编辑器中设置断点和调试
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_function_1():
    """演示函数1：基础调试"""
    print("=== 演示函数1：基础调试 ===")
    
    # 设置一些变量供调试观察
    name = "ComfyUI"
    version = "1.0.0"
    port = 8188
    debug_mode = True
    
    # 🔍 在这里设置断点（在VS Code中点击行号左侧）
    # 或者取消下面注释使用pdb
    # import pdb; pdb.set_trace()
    
    print(f"应用名称: {name}")
    print(f"版本: {version}")
    print(f"端口: {port}")
    print(f"调试模式: {debug_mode}")
    
    return {"name": name, "version": version, "port": port, "debug": debug_mode}

def demo_function_2(data):
    """演示函数2：数据处理调试"""
    print("\n=== 演示函数2：数据处理调试 ===")
    
    # 🔍 在这里设置断点观察数据处理过程
    # import pdb; pdb.set_trace()
    
    result = {}
    
    # 处理数据
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = value.upper()
        elif isinstance(value, int):
            result[key] = value * 2
        else:
            result[key] = value
    
    print(f"原始数据: {data}")
    print(f"处理结果: {result}")
    
    return result

def demo_function_3():
    """演示函数3：异步调试"""
    print("\n=== 演示函数3：异步调试 ===")
    
    import asyncio
    
    async def async_task(name, delay):
        print(f"开始异步任务: {name}")
        await asyncio.sleep(delay)
        print(f"完成异步任务: {name}")
        return f"结果: {name}"
    
    async def main():
        # 🔍 在这里设置断点观察异步执行
        # import pdb; pdb.set_trace()
        
        tasks = [
            async_task("任务1", 0.1),
            async_task("任务2", 0.2),
            async_task("任务3", 0.15)
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"所有任务完成: {results}")
        return results
    
    # 运行异步函数
    return asyncio.run(main())

def demo_function_4():
    """演示函数4：错误调试"""
    print("\n=== 演示函数4：错误调试 ===")
    
    def risky_operation(x, y):
        # 🔍 在这里设置断点观察错误处理
        # import pdb; pdb.set_trace()
        
        try:
            result = x / y
            return result
        except ZeroDivisionError as e:
            print(f"捕获到除零错误: {e}")
            return None
        except Exception as e:
            print(f"捕获到其他错误: {e}")
            return None
    
    # 测试正常情况
    result1 = risky_operation(10, 2)
    print(f"正常情况结果: {result1}")
    
    # 测试错误情况
    result2 = risky_operation(10, 0)
    print(f"错误情况结果: {result2}")
    
    return result1, result2

def demo_comfyui_debug():
    """演示ComfyUI特定调试"""
    print("\n=== 演示ComfyUI特定调试 ===")
    
    try:
        # 导入ComfyUI模块
        from comfy.cli_args import args
        import folder_paths
        
        # 🔍 在这里设置断点观察ComfyUI配置
        # import pdb; pdb.set_trace()
        
        print("ComfyUI配置信息:")
        print(f"  监听地址: {args.listen}")
        print(f"  端口: {args.port}")
        print(f"  详细模式: {args.verbose}")
        print(f"  输出目录: {folder_paths.get_output_directory()}")
        print(f"  输入目录: {folder_paths.get_input_directory()}")
        
        return True
        
    except Exception as e:
        print(f"ComfyUI调试失败: {e}")
        return False

def main():
    """主函数：演示完整的调试流程"""
    print("ComfyUI 编辑器调试演示")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 演示1：基础调试
    data1 = demo_function_1()
    
    # 演示2：数据处理调试
    data2 = demo_function_2(data1)
    
    # 演示3：异步调试
    data3 = demo_function_3()
    
    # 演示4：错误调试
    data4 = demo_function_4()
    
    # 演示5：ComfyUI特定调试
    data5 = demo_comfyui_debug()
    
    print("\n=== 调试演示完成 ===")
    print("在VS Code中设置断点后重新运行此脚本进行调试")
    print("断点位置已标记为 🔍 符号")

if __name__ == "__main__":
    main()
