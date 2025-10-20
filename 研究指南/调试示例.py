#!/usr/bin/env python3
"""
ComfyUI 调试示例
演示如何使用不同的调试方法
"""

import sys
import os
import logging
import time
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def example_1_pdb_debug():
    """示例1：使用pdb进行断点调试"""
    print("=== 示例1：pdb断点调试 ===")
    
    def test_function(x, y):
        result = x + y
        # 在这里设置断点
        import pdb; pdb.set_trace()
        return result * 2
    
    print("调用test_function(3, 4)")
    print("在pdb中可以使用以下命令：")
    print("  l (list) - 显示当前代码")
    print("  n (next) - 执行下一行")
    print("  p x - 打印变量x的值")
    print("  c (continue) - 继续执行")
    print("  q (quit) - 退出调试器")
    
    # 取消注释下面这行来启用断点调试
    # result = test_function(3, 4)
    # print(f"结果: {result}")

def example_2_logging_debug():
    """示例2：使用日志进行调试"""
    print("\n=== 示例2：日志调试 ===")
    
    # 设置详细日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def process_data(data):
        logging.debug(f"开始处理数据: {data}")
        
        # 模拟处理步骤
        step1 = data * 2
        logging.debug(f"步骤1完成: {step1}")
        
        step2 = step1 + 10
        logging.debug(f"步骤2完成: {step2}")
        
        result = step2 / 2
        logging.info(f"处理完成，结果: {result}")
        
        return result
    
    result = process_data(5)
    print(f"处理结果: {result}")

def example_3_performance_debug():
    """示例3：性能调试"""
    print("\n=== 示例3：性能调试 ===")
    
    import time
    import functools
    
    def timing_decorator(func):
        """计时装饰器"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            print(f"函数 {func.__name__} 执行时间: {end_time - start_time:.4f}秒")
            return result
        return wrapper
    
    @timing_decorator
    def slow_function():
        """模拟慢函数"""
        time.sleep(0.1)  # 模拟耗时操作
        return "完成"
    
    result = slow_function()
    print(f"结果: {result}")

def example_4_async_debug():
    """示例4：异步代码调试"""
    print("\n=== 示例4：异步代码调试 ===")
    
    async def async_function(name, delay):
        print(f"开始异步函数: {name}")
        await asyncio.sleep(delay)
        print(f"完成异步函数: {name}")
        return f"结果: {name}"
    
    async def debug_async():
        print("开始异步调试")
        
        # 创建多个异步任务
        tasks = [
            async_function("任务1", 0.1),
            async_function("任务2", 0.2),
            async_function("任务3", 0.15)
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks)
        print(f"所有任务完成: {results}")
    
    # 运行异步函数
    asyncio.run(debug_async())

def example_5_comfyui_debug():
    """示例5：ComfyUI特定调试"""
    print("\n=== 示例5：ComfyUI调试 ===")
    
    try:
        # 导入ComfyUI模块
        from main import apply_custom_paths, execute_prestartup_script
        from comfy.cli_args import args
        
        print("1. 调试路径配置...")
        apply_custom_paths()
        print("   ✓ 路径配置完成")
        
        print("2. 调试自定义节点...")
        execute_prestartup_script()
        print("   ✓ 自定义节点预启动完成")
        
        print("3. 检查参数配置...")
        print(f"   监听地址: {args.listen}")
        print(f"   端口: {args.port}")
        print(f"   详细模式: {args.verbose}")
        
    except Exception as e:
        print(f"   ✗ ComfyUI调试失败: {e}")
        import traceback
        traceback.print_exc()

def example_6_conditional_debug():
    """示例6：条件调试"""
    print("\n=== 示例6：条件调试 ===")
    
    def debug_function(data, debug=False):
        """带条件调试的函数"""
        if debug:
            print(f"调试信息: 输入数据 = {data}")
            print(f"调试信息: 数据类型 = {type(data)}")
        
        result = data * 2
        
        if debug:
            print(f"调试信息: 计算结果 = {result}")
        
        return result
    
    # 正常调用
    result1 = debug_function(5)
    print(f"正常调用结果: {result1}")
    
    # 调试调用
    result2 = debug_function(5, debug=True)
    print(f"调试调用结果: {result2}")

def example_7_error_debug():
    """示例7：错误调试"""
    print("\n=== 示例7：错误调试 ===")
    
    def risky_function(x, y):
        """可能出错的函数"""
        try:
            result = x / y
            return result
        except ZeroDivisionError as e:
            print(f"捕获到除零错误: {e}")
            return None
        except Exception as e:
            print(f"捕获到其他错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # 测试正常情况
    result1 = risky_function(10, 2)
    print(f"正常情况结果: {result1}")
    
    # 测试错误情况
    result2 = risky_function(10, 0)
    print(f"错误情况结果: {result2}")

def main():
    """主函数"""
    print("ComfyUI 调试示例")
    print("=" * 50)
    
    # 运行所有示例
    example_1_pdb_debug()
    example_2_logging_debug()
    example_3_performance_debug()
    example_4_async_debug()
    example_5_comfyui_debug()
    example_6_conditional_debug()
    example_7_error_debug()
    
    print("\n所有调试示例完成！")
    print("\n要启用pdb断点调试，请取消注释example_1_pdb_debug()中的相关代码")

if __name__ == "__main__":
    main()
