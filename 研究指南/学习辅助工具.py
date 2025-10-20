#!/usr/bin/env python3
"""
ComfyUI 学习辅助工具
提供各种学习辅助功能，帮助快速理解源码
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

class ComfyUILearningHelper:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def find_function_usage(self, function_name: str) -> List[Dict]:
        """查找函数的使用情况"""
        usages = []
        
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines):
                    if function_name in line:
                        usages.append({
                            "file": str(py_file.relative_to(self.project_root)),
                            "line": i + 1,
                            "content": line.strip(),
                            "context": lines[max(0, i-2):i+3]
                        })
            except Exception as e:
                continue
                
        return usages
    
    def find_class_hierarchy(self, class_name: str) -> Dict:
        """查找类的继承层次"""
        hierarchy = {
            "class": class_name,
            "parent_classes": [],
            "child_classes": [],
            "methods": [],
            "file": None
        }
        
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找类定义
                class_pattern = rf"class\s+{class_name}\s*\([^)]*\):"
                if re.search(class_pattern, content):
                    hierarchy["file"] = str(py_file.relative_to(self.project_root))
                    
                    # 查找父类
                    match = re.search(rf"class\s+{class_name}\s*\(([^)]*)\):", content)
                    if match:
                        parent_classes = [p.strip() for p in match.group(1).split(',')]
                        hierarchy["parent_classes"] = parent_classes
                    
                    # 查找方法
                    lines = content.split('\n')
                    in_class = False
                    for i, line in enumerate(lines):
                        if f"class {class_name}" in line:
                            in_class = True
                            continue
                        elif in_class and line.startswith('class '):
                            break
                        elif in_class and line.strip().startswith('def '):
                            method_name = line.strip().split('def ')[1].split('(')[0]
                            hierarchy["methods"].append({
                                "name": method_name,
                                "line": i + 1
                            })
                    break
                    
            except Exception as e:
                continue
                
        return hierarchy
    
    def trace_execution_flow(self, start_function: str) -> List[Dict]:
        """跟踪执行流程"""
        flow = []
        visited = set()
        
        def trace_function(func_name: str, depth: int = 0):
            if func_name in visited or depth > 10:  # 防止无限递归
                return
                
            visited.add(func_name)
            
            # 查找函数定义
            for py_file in self.project_root.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for i, line in enumerate(lines):
                        if f"def {func_name}(" in line:
                            flow.append({
                                "function": func_name,
                                "file": str(py_file.relative_to(self.project_root)),
                                "line": i + 1,
                                "depth": depth
                            })
                            
                            # 查找函数调用
                            for j in range(i, min(i + 50, len(lines))):  # 只查找函数内部
                                call_line = lines[j]
                                if '(' in call_line and ')' in call_line:
                                    # 简单的函数调用匹配
                                    calls = re.findall(r'(\w+)\s*\(', call_line)
                                    for call in calls:
                                        if call != func_name and call not in visited:
                                            trace_function(call, depth + 1)
                            break
                            
                except Exception as e:
                    continue
                    
        trace_function(start_function)
        return flow
    
    def find_import_chain(self, module_name: str) -> List[Dict]:
        """查找模块的导入链"""
        import_chain = []
        
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for i, line in enumerate(lines):
                    if f"import {module_name}" in line or f"from {module_name}" in line:
                        import_chain.append({
                            "file": str(py_file.relative_to(self.project_root)),
                            "line": i + 1,
                            "import_statement": line.strip()
                        })
                        
            except Exception as e:
                continue
                
        return import_chain
    
    def generate_learning_notes(self, topic: str) -> str:
        """生成学习笔记模板"""
        templates = {
            "节点开发": """
# 节点开发学习笔记

## 基本概念
- 节点是ComfyUI的基本执行单元
- 每个节点都有输入、输出和执行逻辑
- 节点通过连接形成工作流

## 关键文件
- `comfy_api/latest/io.py` - 节点接口定义
- `comfy/comfy_types/` - 类型定义
- `custom_nodes/` - 自定义节点目录

## 开发步骤
1. 继承 `io.ComfyNode` 基类
2. 定义 `define_schema()` 方法
3. 实现 `execute()` 方法
4. 创建扩展类

## 示例代码
```python
class MyNode(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MyNode",
            display_name="我的节点",
            inputs=[io.String.Input("input")],
            outputs=[io.String.Output()]
        )
    
    @classmethod
    def execute(cls, input):
        return io.NodeOutput(f"处理: {input}")
```

## 常见问题
- Q: 节点不显示？
- A: 检查 `comfy_entrypoint()` 函数是否正确返回扩展实例

- Q: 输入类型错误？
- A: 确保输入类型与 `define_schema()` 中定义的一致
""",
            
            "模型管理": """
# 模型管理学习笔记

## 核心概念
- 模型加载和卸载
- 内存管理策略
- GPU/CPU切换
- 模型缓存

## 关键文件
- `comfy/model_management.py` - 模型管理核心
- `comfy/model_base.py` - 模型基类
- `comfy/model_patcher.py` - 模型补丁

## 主要功能
1. 模型加载: `load_model()`
2. 模型卸载: `unload_model()`
3. 内存管理: `cleanup_models_gc()`
4. 设备管理: `get_torch_device()`

## 内存优化策略
- `--highvram` - 高显存模式
- `--normalvram` - 标准模式
- `--lowvram` - 低显存模式
- `--cpu` - CPU模式

## 调试技巧
```python
import comfy.model_management as mm

# 查看当前设备
print(f"设备: {mm.get_torch_device()}")

# 查看可用内存
print(f"可用内存: {mm.get_free_memory()}")

# 查看已加载模型
print(f"已加载模型: {list(mm.loaded_models.keys())}")
```
""",
            
            "执行引擎": """
# 执行引擎学习笔记

## 核心组件
- `PromptExecutor` - 执行器
- `PromptQueue` - 任务队列
- `ExecutionList` - 执行列表
- `DynamicPrompt` - 动态提示

## 执行流程
1. 接收工作流定义
2. 解析节点依赖关系
3. 按拓扑顺序执行节点
4. 处理缓存和错误
5. 返回执行结果

## 关键文件
- `execution.py` - 执行引擎主文件
- `comfy_execution/` - 执行相关模块

## 缓存机制
- `BasicCache` - 基础缓存
- `LRUCache` - LRU缓存
- `NullCache` - 无缓存

## 调试技巧
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 跟踪执行过程
def debug_execution():
    print("=== 执行调试 ===")
    print(f"当前队列长度: {len(prompt_queue.queue)}")
    print(f"缓存状态: {cache.get_stats()}")
```
"""
        }
        
        return templates.get(topic, f"# {topic} 学习笔记\n\n请添加你的学习内容...")
    
    def create_study_checklist(self) -> str:
        """创建学习检查清单"""
        checklist = """
# ComfyUI 源码学习检查清单

## 第一阶段：基础架构理解
- [ ] 理解 main.py 的启动流程
- [ ] 掌握 server.py 的Web服务架构
- [ ] 熟悉 execution.py 的执行机制
- [ ] 了解 nodes.py 的节点管理
- [ ] 能够修改基本配置参数
- [ ] 理解日志系统的工作原理

## 第二阶段：节点系统深入
- [ ] 掌握 io.ComfyNode 基类
- [ ] 理解节点注册机制
- [ ] 熟悉节点执行流程
- [ ] 能够创建简单自定义节点
- [ ] 掌握节点接口设计
- [ ] 理解类型系统

## 第三阶段：AI模型集成
- [ ] 理解模型加载流程
- [ ] 掌握内存管理策略
- [ ] 熟悉采样器实现
- [ ] 了解SD模型集成
- [ ] 掌握LoRA和ControlNet
- [ ] 能够调试模型问题

## 第四阶段：高级功能
- [ ] 理解API系统设计
- [ ] 掌握WebSocket通信
- [ ] 熟悉前端集成
- [ ] 能够性能优化
- [ ] 掌握调试技巧
- [ ] 能够编写测试用例

## 实践项目
- [ ] 创建图像处理节点
- [ ] 实现自定义采样器
- [ ] 开发模型管理工具
- [ ] 构建性能监控系统
- [ ] 贡献开源代码

## 学习资源
- [ ] 阅读官方文档
- [ ] 研究示例代码
- [ ] 参与社区讨论
- [ ] 编写学习笔记
- [ ] 实践项目开发
"""
        return checklist

def main():
    parser = argparse.ArgumentParser(description='ComfyUI 学习辅助工具')
    parser.add_argument('--project-root', default='..', help='项目根目录路径（相对于研究指南文件夹）')
    parser.add_argument('--find-usage', help='查找函数使用情况')
    parser.add_argument('--find-class', help='查找类继承层次')
    parser.add_argument('--trace-flow', help='跟踪执行流程')
    parser.add_argument('--find-imports', help='查找模块导入链')
    parser.add_argument('--generate-notes', help='生成学习笔记模板')
    parser.add_argument('--checklist', action='store_true', help='生成学习检查清单')
    
    args = parser.parse_args()
    
    # 获取当前脚本所在目录（研究指南文件夹）
    current_dir = Path(__file__).parent
    # 项目根目录是研究指南文件夹的上级目录
    project_root = current_dir / args.project_root
    
    helper = ComfyUILearningHelper(str(project_root))
    
    if args.find_usage:
        usages = helper.find_function_usage(args.find_usage)
        print(f"函数 '{args.find_usage}' 的使用情况:")
        for usage in usages[:10]:  # 只显示前10个
            print(f"  {usage['file']}:{usage['line']} - {usage['content']}")
    
    elif args.find_class:
        hierarchy = helper.find_class_hierarchy(args.find_class)
        print(f"类 '{args.find_class}' 的继承层次:")
        print(f"  文件: {hierarchy['file']}")
        print(f"  父类: {hierarchy['parent_classes']}")
        print(f"  方法: {[m['name'] for m in hierarchy['methods']]}")
    
    elif args.trace_flow:
        flow = helper.trace_execution_flow(args.trace_flow)
        print(f"函数 '{args.trace_flow}' 的执行流程:")
        for step in flow[:20]:  # 只显示前20步
            print(f"  {step['depth']*'  '}{step['function']} ({step['file']}:{step['line']})")
    
    elif args.find_imports:
        imports = helper.find_import_chain(args.find_imports)
        print(f"模块 '{args.find_imports}' 的导入链:")
        for imp in imports[:10]:
            print(f"  {imp['file']}:{imp['line']} - {imp['import_statement']}")
    
    elif args.generate_notes:
        notes = helper.generate_learning_notes(args.generate_notes)
        print(notes)
    
    elif args.checklist:
        checklist = helper.create_study_checklist()
        print(checklist)
    
    else:
        print("请指定一个操作选项，使用 --help 查看帮助信息")

if __name__ == "__main__":
    main()
