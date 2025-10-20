# ComfyUI 节点开发快速参考

## 🚀 快速开始模板

```python
class MyNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_param": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0})
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("output",)
    FUNCTION = "process"
    CATEGORY = "MyNodes"
    
    def process(self, input_param):
        result = input_param * 2
        return (result,)
```

## 📊 数据类型速查

| 类型 | 说明 | 示例值 |
|------|------|--------|
| `FLOAT` | 浮点数 | `3.14` |
| `INT` | 整数 | `42` |
| `STRING` | 字符串 | `"hello"` |
| `BOOLEAN` | 布尔值 | `True` |
| `IMAGE` | 图像 | `torch.Tensor [B,H,W,C]` |
| `MASK` | 遮罩 | `torch.Tensor [B,H,W,1]` |
| `*` | 任意类型 | 任何值 |

## 🎨 界面控件速查

```python
# 数字输入框
"number": ("FLOAT", {"default": 1.0, "display": "number"})

# 滑块
"slider": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "display": "slider"})

# 文本输入
"text": ("STRING", {"default": "hello", "display": "text"})

# 多行文本
"multiline": ("STRING", {"multiline": True, "default": "hello\nworld"})

# 下拉选择
"choice": (["option1", "option2"], {"default": "option1"})

# 复选框
"checkbox": ("BOOLEAN", {"default": True, "display": "checkbox"})
```

## 🏗️ 节点属性速查

```python
# 必需属性
RETURN_TYPES = ("FLOAT",)        # 输出类型
RETURN_NAMES = ("result",)       # 输出名称
FUNCTION = "process"             # 处理函数名
CATEGORY = "MyNodes"             # 节点分类

# 可选属性
OUTPUT_NODE = False              # 是否为输出节点
BATCH_SIZE = 1                   # 批处理大小
CACHE_ENABLED = True             # 启用缓存
```

## 🔧 常用代码片段

### 图像处理
```python
def process_image(self, image, strength):
    # 处理批次维度
    if len(image.shape) == 4:
        image = image[0]
    
    # 转换为PIL
    img_array = image.cpu().numpy()
    img_pil = Image.fromarray((img_array * 255).astype(np.uint8))
    
    # 处理图像
    processed = self.apply_effect(img_pil, strength)
    
    # 转换回tensor
    result_array = np.array(processed) / 255.0
    result_tensor = torch.from_numpy(result_array).float()
    
    # 添加批次维度
    if len(result_tensor.shape) == 3:
        result_tensor = result_tensor.unsqueeze(0)
    
    return (result_tensor,)
```

### 数学运算
```python
def calculate(self, a, b, operation):
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b if b != 0 else 0
    else:
        result = 0
    
    return (result,)
```

### 条件判断
```python
def conditional(self, condition, true_value, false_value):
    return (true_value if condition else false_value,)
```

### 错误处理
```python
def process(self, input_data):
    try:
        # 验证输入
        if input_data is None:
            raise ValueError("输入不能为空")
        
        # 执行处理
        result = self.compute(input_data)
        return (result,)
    except Exception as e:
        print(f"错误: {e}")
        return (input_data,)  # 返回原始输入
```

## 🗂️ 分类系统

```python
# 主分类
CATEGORY = "MyNodes"

# 子分类
CATEGORY = "MyNodes/Image"      # 图像处理
CATEGORY = "MyNodes/Text"       # 文本处理
CATEGORY = "MyNodes/Math"       # 数学运算
CATEGORY = "MyNodes/Logic"      # 逻辑控制
```

## 🐛 调试技巧

```python
def process(self, input_data):
    # 打印调试信息
    print(f"输入形状: {input_data.shape}")
    print(f"输入类型: {input_data.dtype}")
    
    # 使用断点
    import pdb; pdb.set_trace()
    
    # 记录日志
    import logging
    logging.info(f"处理数据: {input_data.shape}")
    
    result = self.compute(input_data)
    return (result,)
```

## 📝 注册节点

```python
# 节点映射
NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
    "AnotherNode": AnotherNode,
}

# 显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "MyNode": "我的节点",
    "AnotherNode": "另一个节点",
}
```

## ⚡ 性能优化

```python
class OptimizedNode:
    def __init__(self):
        # 预加载模型
        self.model = self.load_model()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def process(self, input_data):
        # 使用GPU
        input_tensor = input_data.to(self.device)
        
        with torch.no_grad():
            result = self.model(input_tensor)
        
        return (result.cpu(),)
```

## 🔍 常见问题

### Q: 节点不显示？
A: 检查 `NODE_CLASS_MAPPINGS` 和 `prestartup_script.py`

### Q: 类型错误？
A: 检查 `RETURN_TYPES` 和 `INPUT_TYPES` 是否匹配

### Q: 参数不显示？
A: 检查 `INPUT_TYPES` 中的参数定义

### Q: 处理函数不执行？
A: 检查 `FUNCTION` 名称是否与函数名一致

---

**提示**: 保存这个快速参考，开发时随时查阅！🚀
