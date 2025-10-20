#!/usr/bin/env python3
"""
ComfyUI 源码分析工具
用于帮助开发者快速理解项目结构和关键模块
"""

import os
import sys
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse

class ComfyUIAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analysis_results = {}
        
    def analyze_project_structure(self) -> Dict:
        """分析项目整体结构"""
        structure = {
            "core_files": [],
            "modules": {},
            "dependencies": {},
            "entry_points": [],
            "api_endpoints": [],
            "custom_nodes": []
        }
        
        # 核心文件分析
        core_files = [
            "main.py", "server.py", "execution.py", "nodes.py",
            "folder_paths.py", "protocol.py"
        ]
        
        for file in core_files:
            file_path = self.project_root / file
            if file_path.exists():
                structure["core_files"].append({
                    "file": file,
                    "size": file_path.stat().st_size,
                    "lines": self._count_lines(file_path)
                })
        
        # 模块分析
        for py_file in self.project_root.rglob("*.py"):
            if py_file.is_file():
                rel_path = py_file.relative_to(self.project_root)
                module_info = self._analyze_python_file(py_file)
                if module_info:
                    structure["modules"][str(rel_path)] = module_info
        
        return structure
    
    def _count_lines(self, file_path: Path) -> int:
        """计算文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except:
            return 0
    
    def _analyze_python_file(self, file_path: Path) -> Dict:
        """分析Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            analysis = {
                "classes": [],
                "functions": [],
                "imports": [],
                "decorators": [],
                "complexity": 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append(f"{module}.{alias.name}")
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def find_key_modules(self) -> Dict[str, List[str]]:
        """找出关键模块和文件"""
        key_modules = {
            "启动相关": [
                "main.py",
                "comfy/cli_args.py",
                "app/logger.py",
                "folder_paths.py"
            ],
            "核心执行": [
                "execution.py",
                "comfy_execution/",
                "nodes.py"
            ],
            "Web服务": [
                "server.py",
                "api_server/",
                "protocol.py"
            ],
            "AI模型": [
                "comfy/model_management.py",
                "comfy/samplers.py",
                "comfy/sd.py",
                "comfy/lora.py",
                "comfy/controlnet.py"
            ],
            "节点系统": [
                "comfy_api/latest/io.py",
                "comfy/comfy_types/",
                "custom_nodes/"
            ],
            "工具函数": [
                "comfy/utils.py",
                "node_helpers.py",
                "comfy/model_base.py"
            ]
        }
        
        # 验证文件是否存在
        verified_modules = {}
        for category, files in key_modules.items():
            verified_files = []
            for file in files:
                if (self.project_root / file).exists():
                    verified_files.append(file)
            if verified_files:
                verified_modules[category] = verified_files
        
        return verified_modules
    
    def analyze_dependencies(self) -> Dict:
        """分析依赖关系"""
        dependencies = {
            "external": set(),
            "internal": set(),
            "comfy_modules": set()
        }
        
        for py_file in self.project_root.rglob("*.py"):
            if py_file.is_file():
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            module = node.module
                            if module:
                                if module.startswith('comfy'):
                                    dependencies["comfy_modules"].add(module)
                                elif module.startswith('.'):
                                    dependencies["internal"].add(module)
                                else:
                                    dependencies["external"].add(module)
                                    
                except Exception as e:
                    continue
        
        # 转换为列表并排序
        for key in dependencies:
            dependencies[key] = sorted(list(dependencies[key]))
        
        return dependencies
    
    def find_api_endpoints(self) -> List[Dict]:
        """查找API端点"""
        endpoints = []
        
        # 在server.py中查找路由
        server_file = self.project_root / "server.py"
        if server_file.exists():
            with open(server_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '@routes.' in line and ('get' in line or 'post' in line or 'put' in line or 'delete' in line):
                    method = line.split('@routes.')[1].split('(')[0]
                    if 'async def' in lines[i+1]:
                        func_name = lines[i+1].split('async def ')[1].split('(')[0]
                        endpoints.append({
                            "method": method.upper(),
                            "function": func_name,
                            "file": "server.py",
                            "line": i+1
                        })
        
        return endpoints
    
    def generate_learning_roadmap(self) -> Dict:
        """生成学习路线图"""
        roadmap = {
            "第一阶段_基础架构": {
                "目标": "理解ComfyUI的整体架构和启动流程",
                "重点文件": [
                    "main.py",
                    "server.py", 
                    "execution.py",
                    "nodes.py"
                ],
                "学习时间": "1-2周",
                "实践任务": [
                    "跟踪程序启动流程",
                    "理解核心组件关系",
                    "修改基本配置参数"
                ]
            },
            "第二阶段_节点系统": {
                "目标": "深入理解节点系统的工作原理",
                "重点文件": [
                    "comfy_api/latest/io.py",
                    "comfy/comfy_types/",
                    "custom_nodes/example_node.py.example"
                ],
                "学习时间": "1-2周",
                "实践任务": [
                    "创建简单自定义节点",
                    "理解节点执行流程",
                    "掌握节点接口设计"
                ]
            },
            "第三阶段_AI模型": {
                "目标": "掌握AI模型的集成和管理",
                "重点文件": [
                    "comfy/model_management.py",
                    "comfy/samplers.py",
                    "comfy/sd.py",
                    "comfy/lora.py"
                ],
                "学习时间": "1-2周",
                "实践任务": [
                    "理解模型加载流程",
                    "分析采样器实现",
                    "掌握内存管理策略"
                ]
            },
            "第四阶段_高级功能": {
                "目标": "学习高级功能和性能优化",
                "重点文件": [
                    "comfy/controlnet.py",
                    "comfy/gligen.py",
                    "api_server/",
                    "tests/"
                ],
                "学习时间": "1-2周",
                "实践任务": [
                    "实现复杂自定义节点",
                    "优化性能",
                    "编写测试用例"
                ]
            }
        }
        
        return roadmap
    
    def generate_report(self) -> str:
        """生成分析报告"""
        structure = self.analyze_project_structure()
        key_modules = self.find_key_modules()
        dependencies = self.analyze_dependencies()
        endpoints = self.find_api_endpoints()
        roadmap = self.generate_learning_roadmap()
        
        report = f"""
# ComfyUI 源码分析报告

## 项目概览
- 项目根目录: {self.project_root}
- 核心文件数量: {len(structure['core_files'])}
- Python模块数量: {len(structure['modules'])}
- API端点数量: {len(endpoints)}

## 核心文件分析
"""
        
        for file_info in structure['core_files']:
            report += f"- {file_info['file']}: {file_info['lines']} 行, {file_info['size']} 字节\n"
        
        report += "\n## 关键模块分类\n"
        for category, files in key_modules.items():
            report += f"\n### {category}\n"
            for file in files:
                report += f"- {file}\n"
        
        report += "\n## 依赖关系分析\n"
        report += f"\n### 外部依赖 ({len(dependencies['external'])} 个)\n"
        for dep in dependencies['external'][:10]:  # 只显示前10个
            report += f"- {dep}\n"
        
        report += f"\n### ComfyUI内部模块 ({len(dependencies['comfy_modules'])} 个)\n"
        for dep in dependencies['comfy_modules'][:10]:
            report += f"- {dep}\n"
        
        report += "\n## API端点\n"
        for endpoint in endpoints[:10]:  # 只显示前10个
            report += f"- {endpoint['method']} {endpoint['function']} (server.py:{endpoint['line']})\n"
        
        report += "\n## 学习路线图\n"
        for phase, info in roadmap.items():
            report += f"\n### {phase}\n"
            report += f"**目标**: {info['目标']}\n"
            report += f"**学习时间**: {info['学习时间']}\n"
            report += f"**重点文件**: {', '.join(info['重点文件'])}\n"
            report += f"**实践任务**: {', '.join(info['实践任务'])}\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='ComfyUI 源码分析工具')
    parser.add_argument('--project-root', default='..', help='项目根目录路径（相对于研究指南文件夹）')
    parser.add_argument('--output', help='输出报告文件路径')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式')
    
    args = parser.parse_args()
    
    # 获取当前脚本所在目录（研究指南文件夹）
    current_dir = Path(__file__).parent
    # 项目根目录是研究指南文件夹的上级目录
    project_root = current_dir / args.project_root
    
    analyzer = ComfyUIAnalyzer(str(project_root))
    report = analyzer.generate_report()
    
    if args.output:
        # 如果输出路径是相对路径，则相对于研究指南文件夹
        if not Path(args.output).is_absolute():
            output_path = current_dir / args.output
        else:
            output_path = Path(args.output)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"分析报告已保存到: {output_path}")
    else:
        print(report)

if __name__ == "__main__":
    main()
