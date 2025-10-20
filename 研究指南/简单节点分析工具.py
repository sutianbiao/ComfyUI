#!/usr/bin/env python3
"""
ComfyUI内置节点简单分析工具
"""

import ast
import os
import sys

def analyze_nodes_file(file_path):
    """分析nodes.py文件"""
    print(f"🔍 分析文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # 查找所有节点类
    node_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # 检查是否有INPUT_TYPES方法
            has_input_types = False
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "INPUT_TYPES":
                    has_input_types = True
                    break
            
            if has_input_types:
                node_classes.append(node.name)
    
    print(f"✅ 找到 {len(node_classes)} 个节点类")
    return node_classes

def analyze_node_structure(file_path, class_name):
    """分析特定节点类的结构"""
    print(f"🔍 分析节点类: {class_name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # 分析类结构
            methods = []
            attributes = []
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith('_'):
                        methods.append(item.name)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            attributes.append(target.id)
            
            return {
                "name": class_name,
                "methods": methods,
                "attributes": attributes,
                "docstring": ast.get_docstring(node)
            }
    
    return None

def generate_learning_report(nodes_file, output_file):
    """生成学习报告"""
    print("📝 生成学习报告...")
    
    # 分析nodes.py
    node_classes = analyze_nodes_file(nodes_file)
    
    # 分析关键节点
    key_nodes = ["LoadImage", "CheckpointLoaderSimple", "CLIPTextEncode", "KSampler", "VAEDecode"]
    
    report = f"""# ComfyUI 内置节点学习报告

## 📊 分析概览

### 节点文件分析
- 文件路径: {nodes_file}
- 节点总数: {len(node_classes)}
- 节点列表: {', '.join(node_classes[:20])}{'...' if len(node_classes) > 20 else ''}

## 🔍 关键节点分析

"""
    
    for node_name in key_nodes:
        if node_name in node_classes:
            structure = analyze_node_structure(nodes_file, node_name)
            if structure:
                report += f"### {node_name}\n"
                report += f"- 方法: {', '.join(structure['methods'])}\n"
                report += f"- 属性: {', '.join(structure['attributes'])}\n"
                if structure['docstring']:
                    report += f"- 文档: {structure['docstring'][:100]}...\n"
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
    
    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 学习报告已保存到: {output_file}")

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_file = os.path.join(project_root, "nodes.py")
    output_file = "内置节点学习报告.md"
    
    print("🚀 ComfyUI内置节点分析工具")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # 生成报告
        generate_learning_report(nodes_file, output_file)
    else:
        # 交互模式
        while True:
            print("\n请选择操作:")
            print("1. 分析nodes.py文件")
            print("2. 分析特定节点类")
            print("3. 生成学习报告")
            print("4. 退出")
            
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == "1":
                node_classes = analyze_nodes_file(nodes_file)
                print(f"\n找到的节点类:")
                for i, node in enumerate(node_classes, 1):
                    print(f"{i:2d}. {node}")
            
            elif choice == "2":
                node_name = input("请输入节点类名: ").strip()
                if node_name:
                    structure = analyze_node_structure(nodes_file, node_name)
                    if structure:
                        print(f"\n节点分析结果:")
                        print(f"名称: {structure['name']}")
                        print(f"方法: {', '.join(structure['methods'])}")
                        print(f"属性: {', '.join(structure['attributes'])}")
                        if structure['docstring']:
                            print(f"文档: {structure['docstring']}")
                    else:
                        print("❌ 找不到节点类")
            
            elif choice == "3":
                generate_learning_report(nodes_file, output_file)
            
            elif choice == "4":
                print("👋 再见!")
                break
            
            else:
                print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()
