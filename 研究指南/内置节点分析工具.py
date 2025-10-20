#!/usr/bin/env python3
"""
ComfyUI内置节点分析工具
用于学习和研究ComfyUI内置节点的实现
"""

import ast
import inspect
import os
import sys
import json
import time
from typing import Dict, List, Any, Optional

class NodeAnalyzer:
    """节点分析器"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.nodes_file = os.path.join(project_root, "nodes.py")
        self.comfy_dir = os.path.join(project_root, "comfy")
        self.analysis_results = {}
    
    def analyze_nodes_file(self) -> Dict[str, Any]:
        """分析nodes.py文件"""
        print("🔍 分析nodes.py文件...")
        
        if not os.path.exists(self.nodes_file):
            print(f"❌ 文件不存在: {self.nodes_file}")
            return {}
        
        with open(self.nodes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # 查找所有节点类
        node_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否是节点类（有INPUT_TYPES方法）
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "INPUT_TYPES":
                        node_classes.append(node.name)
                        break
        
        print(f"✅ 找到 {len(node_classes)} 个节点类")
        
        return {
            "file": self.nodes_file,
            "node_classes": node_classes,
            "total_nodes": len(node_classes)
        }
    
    def analyze_node_class(self, class_name: str) -> Dict[str, Any]:
        """分析特定节点类"""
        print(f"🔍 分析节点类: {class_name}")
        
        try:
            # 动态导入节点类
            sys.path.insert(0, self.project_root)
            import nodes
            
            # 获取节点类
            node_class = getattr(nodes, class_name, None)
            if not node_class:
                print(f"❌ 找不到节点类: {class_name}")
                return {}
            
            # 分析类结构
            class_info = {
                "name": class_name,
                "docstring": node_class.__doc__,
                "methods": [],
                "attributes": [],
                "input_types": None,
                "return_types": None,
                "return_names": None,
                "function": None,
                "category": None
            }
            
            # 分析方法
            for name, method in inspect.getmembers(node_class, inspect.isfunction):
                if not name.startswith('_'):
                    method_info = {
                        "name": name,
                        "docstring": method.__doc__,
                        "signature": str(inspect.signature(method))
                    }
                    class_info["methods"].append(method_info)
            
            # 分析属性
            for name, value in inspect.getmembers(node_class):
                if not name.startswith('_') and not inspect.isfunction(value):
                    attr_info = {
                        "name": name,
                        "value": str(value) if not callable(value) else "callable",
                        "type": type(value).__name__
                    }
                    class_info["attributes"].append(attr_info)
            
            # 获取节点特定属性
            if hasattr(node_class, 'INPUT_TYPES'):
                try:
                    class_info["input_types"] = node_class.INPUT_TYPES()
                except:
                    class_info["input_types"] = "无法获取"
            
            if hasattr(node_class, 'RETURN_TYPES'):
                class_info["return_types"] = node_class.RETURN_TYPES
            
            if hasattr(node_class, 'RETURN_NAMES'):
                class_info["return_names"] = node_class.RETURN_NAMES
            
            if hasattr(node_class, 'FUNCTION'):
                class_info["function"] = node_class.FUNCTION
            
            if hasattr(node_class, 'CATEGORY'):
                class_info["category"] = node_class.CATEGORY
            
            print(f"✅ 分析完成: {class_name}")
            return class_info
            
        except Exception as e:
            print(f"❌ 分析失败: {class_name} - {e}")
            return {}
    
    def analyze_comfy_modules(self) -> Dict[str, Any]:
        """分析comfy目录下的模块"""
        print("🔍 分析comfy模块...")
        
        modules_info = {}
        
        if not os.path.exists(self.comfy_dir):
            print(f"❌ 目录不存在: {self.comfy_dir}")
            return modules_info
        
        for root, dirs, files in os.walk(self.comfy_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        
                        # 查找类和函数
                        classes = []
                        functions = []
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                classes.append(node.name)
                            elif isinstance(node, ast.FunctionDef):
                                functions.append(node.name)
                        
                        modules_info[rel_path] = {
                            "classes": classes,
                            "functions": functions,
                            "total_classes": len(classes),
                            "total_functions": len(functions)
                        }
                        
                    except Exception as e:
                        print(f"❌ 分析文件失败: {file_path} - {e}")
        
        print(f"✅ 分析了 {len(modules_info)} 个模块")
        return modules_info
    
    def generate_learning_report(self) -> str:
        """生成学习报告"""
        print("📝 生成学习报告...")
        
        # 分析nodes.py
        nodes_analysis = self.analyze_nodes_file()
        
        # 分析comfy模块
        comfy_analysis = self.analyze_comfy_modules()
        
        # 分析关键节点类
        key_nodes = ["LoadImage", "CheckpointLoaderSimple", "CLIPTextEncode", "KSampler", "VAEDecode"]
        node_details = {}
        
        for node_name in key_nodes:
            if node_name in nodes_analysis.get("node_classes", []):
                node_details[node_name] = self.analyze_node_class(node_name)
        
        # 生成报告
        report = f"""
# ComfyUI 内置节点学习报告

## 📊 分析概览

### 节点文件分析
- 文件路径: {nodes_analysis.get('file', 'N/A')}
- 节点总数: {nodes_analysis.get('total_nodes', 0)}
- 节点列表: {', '.join(nodes_analysis.get('node_classes', []))}

### Comfy模块分析
- 模块总数: {len(comfy_analysis)}
- 主要模块:
"""
        
        for module_path, info in comfy_analysis.items():
            if info['total_classes'] > 0 or info['total_functions'] > 0:
                report += f"- {module_path}: {info['total_classes']} 类, {info['total_functions']} 函数\n"
        
        report += "\n## 🔍 关键节点分析\n\n"
        
        for node_name, details in node_details.items():
            if details:
                report += f"### {node_name}\n"
                report += f"- 分类: {details.get('category', 'N/A')}\n"
                report += f"- 函数: {details.get('function', 'N/A')}\n"
                report += f"- 返回类型: {details.get('return_types', 'N/A')}\n"
                report += f"- 返回名称: {details.get('return_names', 'N/A')}\n"
                report += f"- 方法数: {len(details.get('methods', []))}\n"
                report += f"- 属性数: {len(details.get('attributes', []))}\n"
                
                if details.get('docstring'):
                    report += f"- 文档: {details['docstring'][:100]}...\n"
                
                report += "\n"
        
        report += """
## 🎯 学习建议

### 1. 基础节点学习顺序
1. **LoadImage** - 学习图像加载和格式转换
2. **CheckpointLoaderSimple** - 学习模型加载和管理
3. **CLIPTextEncode** - 学习文本编码和处理
4. **KSampler** - 学习采样算法和推理
5. **VAEDecode** - 学习图像解码和输出

### 2. 学习重点
- 理解节点的输入输出类型定义
- 掌握图像和模型数据的处理流程
- 学习错误处理和内存管理
- 了解性能优化技巧

### 3. 实践建议
- 创建简单的测试节点
- 修改现有节点参数
- 实现自定义处理逻辑
- 进行性能测试和优化

## 📚 下一步学习
1. 深入研究关键节点的实现细节
2. 学习ComfyUI的核心架构
3. 掌握AI模型的集成方法
4. 开发自己的自定义节点
"""
        
        return report
    
    def save_analysis_results(self, output_file: str):
        """保存分析结果"""
        print(f"💾 保存分析结果到: {output_file}")
        
        # 生成学习报告
        report = self.generate_learning_report()
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 分析结果已保存")
    
    def run_interactive_analysis(self):
        """运行交互式分析"""
        print("🚀 启动ComfyUI内置节点分析工具")
        print("=" * 50)
        
        while True:
            print("\n请选择操作:")
            print("1. 分析nodes.py文件")
            print("2. 分析特定节点类")
            print("3. 分析comfy模块")
            print("4. 生成学习报告")
            print("5. 退出")
            
            choice = input("\n请输入选择 (1-5): ").strip()
            
            if choice == "1":
                result = self.analyze_nodes_file()
                print(f"\n分析结果:")
                print(f"节点总数: {result.get('total_nodes', 0)}")
                print(f"节点列表: {', '.join(result.get('node_classes', []))}")
            
            elif choice == "2":
                node_name = input("请输入节点类名: ").strip()
                if node_name:
                    result = self.analyze_node_class(node_name)
                    if result:
                        print(f"\n节点分析结果:")
                        print(f"名称: {result.get('name')}")
                        print(f"分类: {result.get('category')}")
                        print(f"函数: {result.get('function')}")
                        print(f"返回类型: {result.get('return_types')}")
                        print(f"方法数: {len(result.get('methods', []))}")
                    else:
                        print("❌ 分析失败")
            
            elif choice == "3":
                result = self.analyze_comfy_modules()
                print(f"\n模块分析结果:")
                for module, info in result.items():
                    print(f"{module}: {info['total_classes']} 类, {info['total_functions']} 函数")
            
            elif choice == "4":
                output_file = input("请输入输出文件名 (默认: 内置节点学习报告.md): ").strip()
                if not output_file:
                    output_file = "内置节点学习报告.md"
                
                self.save_analysis_results(output_file)
            
            elif choice == "5":
                print("👋 再见!")
                break
            
            else:
                print("❌ 无效选择，请重试")

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 创建分析器
    analyzer = NodeAnalyzer(project_root)
    
    # 检查参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            # 生成报告
            output_file = sys.argv[2] if len(sys.argv) > 2 else "内置节点学习报告.md"
            analyzer.save_analysis_results(output_file)
        elif sys.argv[1] == "--analyze":
            # 分析特定节点
            node_name = sys.argv[2] if len(sys.argv) > 2 else "LoadImage"
            result = analyzer.analyze_node_class(node_name)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("用法:")
            print("  python 内置节点分析工具.py --report [输出文件]")
            print("  python 内置节点分析工具.py --analyze [节点名]")
            print("  python 内置节点分析工具.py  # 交互模式")
    else:
        # 交互模式
        analyzer.run_interactive_analysis()

if __name__ == "__main__":
    main()
