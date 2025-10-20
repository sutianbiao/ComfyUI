# ComfyUI 自定义节点开发 API 文档

## 📚 目录

1. [基础概念](#基础概念)
2. [节点类结构](#节点类结构)
3. [输入类型定义](#输入类型定义)
4. [输出类型定义](#输出类型定义)
5. [节点属性](#节点属性)
6. [数据类型详解](#数据类型详解)
7. [界面控件类型](#界面控件类型)
8. [节点分类系统](#节点分类系统)
9. [高级功能](#高级功能)
10. [最佳实践](#最佳实践)
11. [常见问题](#常见问题)

## 🎯 基础概念

### 什么是ComfyUI节点？

ComfyUI节点是一个Python类，它定义了：
- **输入参数**：节点接收的数据
- **处理逻辑**：对输入数据的操作
- **输出结果**：节点产生的数据
- **界面控件**：用户在ComfyUI中看到的输入界面

### 节点生命周期

```
1. 定义节点类 → 2. 注册节点 → 3. 用户拖拽 → 4. 设置参数 → 5. 执行处理 → 6. 返回结果
```

## 🏗️ 节点类结构

### 基本结构

```python
class MyCustomNode:
    """
    节点文档字符串
    描述节点的功能和用途
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义输入参数类型和界面"""
        return {
            "required": {
                # 必需参数
            },
            "optional": {
                # 可选参数
            }
        }
    
    # 节点属性
    RETURN_TYPES = ("TYPE1", "TYPE2")      # 输出类型
    RETURN_NAMES = ("name1", "name2")      # 输出名称
    FUNCTION = "process"                   # 处理函数名
    CATEGORY = "MyNodes"                   # 节点分类
    OUTPUT_NODE = False                    # 是否为输出节点
    
    def process(self, **kwargs):
        """主要处理函数"""
        # 处理逻辑
        return (result1, result2)
```

## 📥 输入类型定义

### INPUT_TYPES 方法

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            # 必需参数 - 用户必须提供
        },
        "optional": {
            # 可选参数 - 用户可以选择性提供
        },
        "hidden": {
            # 隐藏参数 - 不显示在界面上，用于内部状态
        }
    }
```

### 参数定义格式

```python
"parameter_name": (TYPE, {
    "default": default_value,    # 默认值
    "min": min_value,           # 最小值（数值类型）
    "max": max_value,           # 最大值（数值类型）
    "step": step_value,         # 步长（数值类型）
    "display": "control_type",  # 界面控件类型
    "multiline": True,          # 多行文本（字符串类型）
    "forceInput": True,         # 强制输入连接
    "tooltip": "提示信息"       # 工具提示
})
```

## 📤 输出类型定义

### RETURN_TYPES

定义节点返回的数据类型：

```python
# 单个输出
RETURN_TYPES = ("FLOAT",)

# 多个输出
RETURN_TYPES = ("IMAGE", "MASK", "FLOAT")

# 任意类型
RETURN_TYPES = ("*",)
```

### RETURN_NAMES

定义输出在界面中显示的名称：

```python
# 单个输出
RETURN_NAMES = ("result",)

# 多个输出
RETURN_NAMES = ("image", "mask", "confidence")

# 与RETURN_TYPES一一对应
RETURN_TYPES = ("IMAGE", "MASK", "FLOAT")
RETURN_NAMES = ("image", "mask", "confidence")
```

## ⚙️ 节点属性

### 必需属性

```python
# 输出类型（必需）
RETURN_TYPES = ("FLOAT",)

# 输出名称（必需）
RETURN_NAMES = ("result",)

# 处理函数名（必需）
FUNCTION = "process"

# 节点分类（必需）
CATEGORY = "MyNodes"
```

### 可选属性

```python
# 是否为输出节点
OUTPUT_NODE = False

# 节点是否支持批处理
BATCH_SIZE = 1

# 节点是否支持动态批处理
DYNAMIC_BATCH_SIZE = True

# 节点是否支持缓存
CACHE_ENABLED = True

# 节点是否支持GPU加速
GPU_ENABLED = True
```

## 📊 数据类型详解

### 基础数据类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `FLOAT` | 浮点数 | `3.14` |
| `INT` | 整数 | `42` |
| `STRING` | 字符串 | `"hello"` |
| `BOOLEAN` | 布尔值 | `True/False` |

### 复合数据类型

| 类型 | 说明 | 格式 |
|------|------|------|
| `IMAGE` | 图像 | `torch.Tensor [B, H, W, C]` |
| `MASK` | 遮罩 | `torch.Tensor [B, H, W, 1]` |
| `LATENT` | 潜在空间 | `torch.Tensor [B, C, H, W]` |
| `CONDITIONING` | 条件 | `List[Tuple[torch.Tensor, Dict]]` |
| `MODEL` | 模型 | `torch.nn.Module` |
| `VAE` | VAE模型 | `torch.nn.Module` |
| `CLIP` | CLIP模型 | `torch.nn.Module` |

### 特殊类型

| 类型 | 说明 | 用途 |
|------|------|------|
| `*` | 任意类型 | 通用输入/输出 |
| `**` | 任意类型列表 | 可变参数 |
| `ENUM` | 枚举类型 | 选择列表 |

## 🎨 界面控件类型

### 数值控件

```python
# 数字输入框
"number": ("FLOAT", {
    "default": 1.0,
    "min": 0.0,
    "max": 100.0,
    "step": 0.1,
    "display": "number"
})

# 滑块控件
"slider": ("FLOAT", {
    "default": 0.5,
    "min": 0.0,
    "max": 1.0,
    "step": 0.01,
    "display": "slider"
})

# 整数滑块
"int_slider": ("INT", {
    "default": 10,
    "min": 1,
    "max": 100,
    "step": 1,
    "display": "slider"
})
```

### 文本控件

```python
# 单行文本
"text": ("STRING", {
    "default": "Hello",
    "display": "text"
})

# 多行文本
"multiline_text": ("STRING", {
    "default": "Hello\nWorld",
    "multiline": True,
    "display": "text"
})
```

### 选择控件

```python
# 下拉选择
"choice": (["option1", "option2", "option3"], {
    "default": "option1"
})

# 单选按钮
"radio": (["A", "B", "C"], {
    "default": "A",
    "display": "radio"
})
```

### 布尔控件

```python
# 复选框
"checkbox": ("BOOLEAN", {
    "default": True,
    "display": "checkbox"
})

# 开关
"toggle": ("BOOLEAN", {
    "default": False,
    "display": "toggle"
})
```

### 特殊控件

```python
# 颜色选择器
"color": ("STRING", {
    "default": "#FF0000",
    "display": "color"
})

# 文件路径
"file_path": ("STRING", {
    "default": "",
    "display": "file"
})

# 目录路径
"dir_path": ("STRING", {
    "default": "",
    "display": "directory"
})
```

## 🗂️ 节点分类系统

### 分类层次结构

```python
# 主分类
CATEGORY = "MyNodes"

# 子分类
CATEGORY = "MyNodes/Image"
CATEGORY = "MyNodes/Text"
CATEGORY = "MyNodes/Math"
CATEGORY = "MyNodes/Logic"
```

### 内置分类

```python
# ComfyUI内置分类
"loaders"           # 加载器
"conditioning"      # 条件
"latent"           # 潜在空间
"image"            # 图像
"mask"             # 遮罩
"controlnet"       # ControlNet
"sampling"         # 采样
"post_processing"  # 后处理
"utility"          # 工具
"advanced"         # 高级
```

## 🚀 高级功能

### 动态输入类型

```python
@classmethod
def INPUT_TYPES(cls):
    # 根据条件动态生成输入类型
    base_types = {
        "required": {
            "input_type": (["image", "text"], {"default": "image"})
        }
    }
    
    # 根据input_type动态添加参数
    if hasattr(cls, '_current_input_type'):
        if cls._current_input_type == "image":
            base_types["required"]["image"] = ("IMAGE",)
        else:
            base_types["required"]["text"] = ("STRING", {"multiline": True})
    
    return base_types
```

### 条件输入

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "enable_advanced": ("BOOLEAN", {"default": False}),
            "basic_param": ("FLOAT", {"default": 1.0}),
        },
        "optional": {
            "advanced_param": ("FLOAT", {"default": 0.0}),
        }
    }

def process(self, enable_advanced, basic_param, advanced_param=None):
    if enable_advanced and advanced_param is not None:
        # 使用高级参数
        result = basic_param + advanced_param
    else:
        # 使用基础参数
        result = basic_param
    return (result,)
```

### 批处理支持

```python
class BatchProcessNode:
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_images",)
    FUNCTION = "process_batch"
    CATEGORY = "MyNodes"
    
    def process_batch(self, images, operation):
        """处理图像批次"""
        results = []
        for image in images:
            # 处理单个图像
            processed = self.process_single(image, operation)
            results.append(processed)
        
        # 合并结果
        return (torch.cat(results, dim=0),)
```

### 缓存支持

```python
class CachedNode:
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("result",)
    FUNCTION = "compute"
    CATEGORY = "MyNodes"
    
    def compute(self, input_data):
        """支持缓存的计算"""
        # 生成缓存键
        cache_key = f"compute_{hash(str(input_data))}"
        
        # 检查缓存
        if hasattr(self, '_cache') and cache_key in self._cache:
            return (self._cache[cache_key],)
        
        # 执行计算
        result = self.expensive_computation(input_data)
        
        # 缓存结果
        if not hasattr(self, '_cache'):
            self._cache = {}
        self._cache[cache_key] = result
        
        return (result,)
```

## 🎯 最佳实践

### 1. 错误处理

```python
def process(self, input_data):
    try:
        # 验证输入
        if input_data is None:
            raise ValueError("输入数据不能为空")
        
        # 执行处理
        result = self.compute(input_data)
        
        return (result,)
    except Exception as e:
        print(f"节点处理错误: {e}")
        # 返回默认值或重新抛出异常
        return (0.0,)
```

### 2. 输入验证

```python
def process(self, image, strength):
    # 验证图像格式
    if len(image.shape) != 4:
        raise ValueError(f"图像必须是4维张量，当前是{len(image.shape)}维")
    
    # 验证强度范围
    if not 0.0 <= strength <= 1.0:
        strength = max(0.0, min(1.0, strength))
        print(f"强度值已限制到有效范围: {strength}")
    
    # 处理逻辑
    result = self.adjust_image(image, strength)
    return (result,)
```

### 3. 性能优化

```python
class OptimizedNode:
    def __init__(self):
        # 预加载模型
        self.model = self.load_model()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
    
    def process(self, input_data):
        # 使用GPU加速
        input_tensor = input_data.to(self.device)
        
        with torch.no_grad():
            result = self.model(input_tensor)
        
        return (result.cpu(),)
```

### 4. 内存管理

```python
def process(self, large_data):
    # 处理大数据时使用生成器
    results = []
    for chunk in self.chunk_data(large_data, chunk_size=1000):
        processed_chunk = self.process_chunk(chunk)
        results.append(processed_chunk)
        
        # 清理内存
        del chunk
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    return (torch.cat(results, dim=0),)
```

## ❓ 常见问题

### Q1: 如何创建图像处理节点？

```python
class ImageProcessNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0})
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_image",)
    FUNCTION = "process_image"
    CATEGORY = "MyNodes/Image"
    
    def process_image(self, image, strength):
        # 处理图像
        processed = self.apply_effect(image, strength)
        return (processed,)
```

### Q2: 如何创建条件节点？

```python
class ConditionalNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "condition": ("BOOLEAN", {"default": True}),
                "true_value": ("*",),
                "false_value": ("*",)
            }
        }
    
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "conditional"
    CATEGORY = "MyNodes/Logic"
    
    def conditional(self, condition, true_value, false_value):
        return (true_value if condition else false_value,)
```

### Q3: 如何创建数学运算节点？

```python
class MathNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("FLOAT", {"default": 0.0}),
                "b": ("FLOAT", {"default": 0.0}),
                "operation": (["add", "subtract", "multiply", "divide"], {"default": "add"})
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("result",)
    FUNCTION = "calculate"
    CATEGORY = "MyNodes/Math"
    
    def calculate(self, a, b, operation):
        if operation == "add":
            return (a + b,)
        elif operation == "subtract":
            return (a - b,)
        elif operation == "multiply":
            return (a * b,)
        elif operation == "divide":
            return (a / b if b != 0 else 0,)
```

### Q4: 如何调试节点？

```python
def process(self, input_data):
    # 使用print输出调试信息
    print(f"输入数据形状: {input_data.shape}")
    print(f"输入数据类型: {input_data.dtype}")
    
    # 使用日志记录
    import logging
    logging.info(f"开始处理数据: {input_data.shape}")
    
    # 使用断点调试
    import pdb; pdb.set_trace()
    
    result = self.compute(input_data)
    return (result,)
```

### Q5: 如何处理错误？

```python
def process(self, input_data):
    try:
        # 验证输入
        self.validate_input(input_data)
        
        # 执行处理
        result = self.compute(input_data)
        
        return (result,)
    except ValueError as e:
        print(f"输入错误: {e}")
        return (input_data,)  # 返回原始输入
    except Exception as e:
        print(f"处理错误: {e}")
        raise  # 重新抛出异常
```

## 📚 参考资源

### 官方文档
- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI Wiki](https://github.com/comfyanonymous/ComfyUI/wiki)

### 示例项目
- [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager)
- [ComfyUI Examples](https://github.com/comfyanonymous/ComfyUI/tree/master/custom_nodes)

### 开发工具
- [ComfyUI API](https://github.com/comfyanonymous/ComfyUI/wiki/ComfyUI-API)
- [ComfyUI Types](https://github.com/comfyanonymous/ComfyUI/tree/master/comfy/comfy_types)

---

这份API文档涵盖了ComfyUI自定义节点开发的所有核心概念和实用技巧。通过学习和实践这些内容，你将能够创建功能强大、用户友好的自定义节点！🚀
