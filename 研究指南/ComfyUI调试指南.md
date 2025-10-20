# ComfyUI 调试指南

## 🎯 调试目标
学习如何有效地调试ComfyUI项目，包括断点调试、日志调试、异步代码调试等。

## 🔧 调试方法

### 1. Python内置调试器 (pdb)

#### 1.1 基本断点设置
```python
# 在需要调试的代码行添加断点
import pdb; pdb.set_trace()

# 或者使用更简洁的方式
breakpoint()  # Python 3.7+
```

#### 1.2 常用pdb命令
```bash
# 在pdb调试器中使用的命令：
l (list)     # 显示当前代码
n (next)     # 执行下一行
s (step)     # 进入函数内部
c (continue) # 继续执行
p variable   # 打印变量值
pp variable  # 美化打印变量
h (help)     # 显示帮助
q (quit)     # 退出调试器
```

#### 1.3 条件断点
```python
# 只在特定条件下触发断点
if some_condition:
    import pdb; pdb.set_trace()
```

### 2. IDE调试器

#### 2.1 VS Code调试配置
创建 `.vscode/launch.json` 文件：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "ComfyUI Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "args": [
                "--listen", "127.0.0.1",
                "--port", "8188",
                "--verbose"
            ],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "justMyCode": false
        },
        {
            "name": "ComfyUI Debug (Custom Args)",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main.py",
            "args": [
                "--listen", "0.0.0.0",
                "--port", "8188",
                "--verbose",
                "--output-directory", "./output"
            ],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            },
            "justMyCode": false
        }
    ]
}
```

#### 2.2 PyCharm调试配置
1. 打开 "Run/Debug Configurations"
2. 创建新的 "Python" 配置
3. 设置：
   - Script path: `/path/to/ComfyUI/main.py`
   - Parameters: `--listen 127.0.0.1 --port 8188 --verbose`
   - Working directory: `/path/to/ComfyUI`

### 3. 异步代码调试

#### 3.1 异步断点设置
```python
import asyncio
import pdb

async def async_function():
    # 在异步函数中设置断点
    pdb.set_trace()
    await some_async_operation()
```

#### 3.2 调试异步事件循环
```python
# 在main.py中添加调试代码
if __name__ == "__main__":
    # 启用异步调试
    import asyncio
    asyncio.get_event_loop().set_debug(True)
    
    # 其他代码...
```

### 4. 日志调试

#### 4.1 添加详细日志
```python
import logging

# 设置详细日志级别
logging.basicConfig(level=logging.DEBUG)

# 在关键位置添加日志
logging.debug(f"变量值: {variable}")
logging.info(f"执行步骤: {step_name}")
logging.warning(f"警告信息: {warning_msg}")
logging.error(f"错误信息: {error_msg}")
```

#### 4.2 创建调试日志工具
```python
# 创建 debug_utils.py
import logging
import time
import functools

def debug_log(func):
    """函数调试装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logging.debug(f"调用函数: {func.__name__}")
        logging.debug(f"参数: args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            logging.debug(f"函数 {func.__name__} 执行完成，耗时: {end_time - start_time:.4f}秒")
            return result
        except Exception as e:
            logging.error(f"函数 {func.__name__} 执行出错: {e}")
            raise
    return wrapper
```

### 5. 网络调试

#### 5.1 WebSocket调试
```python
# 在server.py中添加WebSocket调试
@routes.get('/ws')
async def websocket_handler(request):
    logging.debug(f"WebSocket连接: {request.remote}")
    # 添加断点
    import pdb; pdb.set_trace()
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    # ... 其他代码
```

#### 5.2 HTTP请求调试
```python
# 添加请求中间件进行调试
@web.middleware
async def debug_middleware(request, handler):
    logging.debug(f"请求: {request.method} {request.path}")
    logging.debug(f"请求头: {dict(request.headers)}")
    
    response = await handler(request)
    
    logging.debug(f"响应状态: {response.status}")
    return response
```

## 🛠️ 调试实践

### 实践1：启动流程调试

#### 1.1 在关键函数添加断点
```python
# 在main.py的关键位置添加断点
def apply_custom_paths():
    import pdb; pdb.set_trace()  # 断点1：路径配置
    # ... 代码

def execute_prestartup_script():
    import pdb; pdb.set_trace()  # 断点2：自定义节点预启动
    # ... 代码

def start_comfyui(asyncio_loop=None):
    import pdb; pdb.set_trace()  # 断点3：主启动函数
    # ... 代码
```

#### 1.2 观察变量变化
```python
# 在断点处观察重要变量
def start_comfyui(asyncio_loop=None):
    import pdb; pdb.set_trace()
    
    # 在pdb中执行以下命令观察变量：
    # p args.temp_directory
    # p args.listen
    # p args.port
    # p asyncio_loop
```

### 实践2：工作流执行调试

#### 2.1 在prompt_worker中添加断点
```python
def prompt_worker(q, server_instance):
    import pdb; pdb.set_trace()  # 断点：工作线程开始
    
    while True:
        queue_item = q.get(timeout=timeout)
        if queue_item is not None:
            import pdb; pdb.set_trace()  # 断点：处理工作项
            # ... 处理逻辑
```

#### 2.2 调试执行器
```python
# 在execution.py中添加断点
class PromptExecutor:
    def execute(self, prompt, prompt_id, extra_data, execute_outputs):
        import pdb; pdb.set_trace()  # 断点：执行工作流
        # ... 执行逻辑
```

### 实践3：异步代码调试

#### 3.1 调试异步函数
```python
async def run(server_instance, address="", port=8188, verbose=True, call_on_start=None):
    import pdb; pdb.set_trace()  # 断点：异步运行函数
    
    addresses = []
    for addr in address.split(","):
        addresses.append((addr, port))
    
    # 在pdb中可以使用：
    # p addresses
    # p server_instance
```

#### 3.2 调试事件循环
```python
# 在main.py中添加事件循环调试
if __name__ == "__main__":
    # 启用事件循环调试
    import asyncio
    asyncio.get_event_loop().set_debug(True)
    
    event_loop, _, start_all_func = start_comfyui()
    
    try:
        x = start_all_func()
        import pdb; pdb.set_trace()  # 断点：事件循环开始
        event_loop.run_until_complete(x)
    except KeyboardInterrupt:
        logging.info("\n服务器已停止")
```

## 📊 调试工具

### 1. 性能分析工具

#### 1.1 使用cProfile
```python
import cProfile
import pstats

def profile_function(func):
    """性能分析装饰器"""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        # 生成报告
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # 显示前10个函数
        
        return result
    return wrapper

# 使用示例
@profile_function
def start_comfyui(asyncio_loop=None):
    # ... 函数代码
```

#### 1.2 内存分析
```python
import tracemalloc
import psutil

def memory_debug():
    """内存调试工具"""
    # 开始内存跟踪
    tracemalloc.start()
    
    # 获取当前进程
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    # 获取内存快照
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("内存使用最多的10行代码:")
    for stat in top_stats[:10]:
        print(stat)
```

### 2. 网络调试工具

#### 2.1 使用tcpdump
```bash
# 监听ComfyUI的网络流量
sudo tcpdump -i lo -A -s 0 port 8188
```

#### 2.2 使用curl测试API
```bash
# 测试ComfyUI API
curl -X GET http://127.0.0.1:8188/system_stats
curl -X GET http://127.0.0.1:8188/history
```

### 3. 自定义调试工具

#### 3.1 创建调试脚本
```python
# debug_comfyui.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import start_comfyui
import asyncio
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)

def debug_startup():
    """调试启动过程"""
    print("=== 开始调试ComfyUI启动过程 ===")
    
    # 添加断点
    import pdb; pdb.set_trace()
    
    # 启动ComfyUI
    event_loop, server, start_all = start_comfyui()
    
    print("=== ComfyUI启动完成 ===")
    print(f"事件循环: {event_loop}")
    print(f"服务器: {server}")
    
    return event_loop, server, start_all

if __name__ == "__main__":
    debug_startup()
```

## 🎯 调试技巧

### 1. 分层调试
- **系统层**: 调试启动流程、配置加载
- **网络层**: 调试HTTP请求、WebSocket连接
- **业务层**: 调试工作流执行、节点处理
- **数据层**: 调试模型加载、缓存管理

### 2. 渐进式调试
1. **先调试简单功能**: 从基础功能开始
2. **逐步增加复杂度**: 逐步调试复杂功能
3. **隔离问题**: 将问题隔离到最小范围
4. **验证修复**: 确保修复不会引入新问题

### 3. 调试最佳实践
- **使用版本控制**: 在调试前提交代码
- **记录调试过程**: 记录发现的问题和解决方案
- **测试边界条件**: 测试各种边界情况
- **性能监控**: 监控调试对性能的影响

## 🚀 快速开始调试

### 1. 立即开始调试
```bash
# 进入ComfyUI目录
cd /mnt/fde045dc-60c2-4db6-b37d-928569fbe4c0/work/workspace/github_2025/ComfyUI

# 使用pdb运行
python3 -m pdb main.py --listen 127.0.0.1 --port 8188

# 或者直接运行（如果已经添加了断点）
python3 main.py --listen 127.0.0.1 --port 8188
```

### 2. 使用VS Code调试
1. 打开VS Code
2. 打开ComfyUI项目文件夹
3. 按F5或点击"运行和调试"
4. 选择"ComfyUI Debug"配置
5. 在代码中设置断点
6. 开始调试

### 3. 调试特定功能
```python
# 调试特定功能时，可以创建专门的调试脚本
# debug_specific_feature.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入需要调试的模块
from execution import PromptExecutor
from server import PromptServer

def debug_execution():
    """调试执行引擎"""
    import pdb; pdb.set_trace()
    
    # 创建执行器实例
    executor = PromptExecutor(None)
    # ... 调试代码

if __name__ == "__main__":
    debug_execution()
```

通过这套完整的调试指南，你可以有效地调试ComfyUI项目的各个方面，从启动流程到工作流执行，从同步代码到异步代码！
