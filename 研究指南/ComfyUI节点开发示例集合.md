# ComfyUI 节点开发示例集合

## 🎯 基础示例

### 1. 简单数学运算节点

```python
class SimpleMathNode:
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
    CATEGORY = "Math"
    
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

### 2. 文本处理节点

```python
class TextProcessNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello World"}),
                "operation": (["uppercase", "lowercase", "reverse", "length"], {"default": "uppercase"})
            }
        }
    
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("processed_text", "text_length")
    FUNCTION = "process_text"
    CATEGORY = "Text"
    
    def process_text(self, text, operation):
        if operation == "uppercase":
            result = text.upper()
        elif operation == "lowercase":
            result = text.lower()
        elif operation == "reverse":
            result = text[::-1]
        elif operation == "length":
            result = text
        
        return (result, len(text))
```

## 🖼️ 图像处理示例

### 3. 图像调整节点

```python
import torch
import numpy as np
from PIL import Image, ImageEnhance

class ImageAdjustNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "brightness": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "saturation": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1})
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("adjusted_image",)
    FUNCTION = "adjust_image"
    CATEGORY = "Image"
    
    def adjust_image(self, image, brightness, contrast, saturation):
        # 处理批次维度
        if len(image.shape) == 4:
            image = image[0]
        
        # 转换为PIL图像
        img_array = image.cpu().numpy()
        img_array = np.clip(img_array, 0, 1)
        img_pil = Image.fromarray((img_array * 255).astype(np.uint8))
        
        # 调整图像属性
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img_pil)
            img_pil = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = enhancer.enhance(contrast)
        
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img_pil)
            img_pil = enhancer.enhance(saturation)
        
        # 转换回tensor
        result_array = np.array(img_pil) / 255.0
        result_tensor = torch.from_numpy(result_array).float()
        
        if len(result_tensor.shape) == 3:
            result_tensor = result_tensor.unsqueeze(0)
        
        return (result_tensor,)
```

### 4. 图像滤镜节点

```python
class ImageFilterNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "filter_type": (["blur", "sharpen", "edge", "emboss"], {"default": "blur"}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1})
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("filtered_image",)
    FUNCTION = "apply_filter"
    CATEGORY = "Image"
    
    def apply_filter(self, image, filter_type, strength):
        if len(image.shape) == 4:
            image = image[0]
        
        img_array = image.cpu().numpy()
        img_array = np.clip(img_array, 0, 1)
        img_pil = Image.fromarray((img_array * 255).astype(np.uint8))
        
        if filter_type == "blur":
            from PIL import ImageFilter
            img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=strength))
        elif filter_type == "sharpen":
            from PIL import ImageFilter
            img_pil = img_pil.filter(ImageFilter.UnsharpMask(radius=strength))
        # 添加更多滤镜...
        
        result_array = np.array(img_pil) / 255.0
        result_tensor = torch.from_numpy(result_array).float()
        
        if len(result_tensor.shape) == 3:
            result_tensor = result_tensor.unsqueeze(0)
        
        return (result_tensor,)
```

## 🧠 逻辑控制示例

### 5. 条件判断节点

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
    CATEGORY = "Logic"
    
    def conditional(self, condition, true_value, false_value):
        return (true_value if condition else false_value,)
```

### 6. 开关节点

```python
class SwitchNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "switch": ("BOOLEAN", {"default": False}),
                "input_a": ("*",),
                "input_b": ("*",)
            }
        }
    
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "Logic"
    
    def switch(self, switch, input_a, input_b):
        return (input_a if switch else input_b,)
```

## 🔢 高级数学示例

### 7. 统计计算节点

```python
class StatisticsNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data": ("FLOAT", {"default": 0.0}),
                "operation": (["mean", "sum", "max", "min", "std"], {"default": "mean"})
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("result",)
    FUNCTION = "calculate_statistics"
    CATEGORY = "Math"
    
    def calculate_statistics(self, data, operation):
        if isinstance(data, (list, tuple)):
            data = torch.tensor(data)
        
        if operation == "mean":
            result = torch.mean(data)
        elif operation == "sum":
            result = torch.sum(data)
        elif operation == "max":
            result = torch.max(data)
        elif operation == "min":
            result = torch.min(data)
        elif operation == "std":
            result = torch.std(data)
        
        return (result.item(),)
```

### 8. 范围限制节点

```python
class ClampNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("FLOAT", {"default": 0.0}),
                "min_value": ("FLOAT", {"default": 0.0}),
                "max_value": ("FLOAT", {"default": 1.0})
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("clamped_value",)
    FUNCTION = "clamp"
    CATEGORY = "Math"
    
    def clamp(self, value, min_value, max_value):
        result = max(min_value, min(max_value, value))
        return (result,)
```

## 🎨 创意示例

### 9. 颜色混合节点

```python
class ColorBlendNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "color1": ("STRING", {"default": "#FF0000"}),
                "color2": ("STRING", {"default": "#0000FF"}),
                "blend_mode": (["normal", "multiply", "screen", "overlay"], {"default": "normal"}),
                "opacity": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0})
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("blended_color",)
    FUNCTION = "blend_colors"
    CATEGORY = "Color"
    
    def blend_colors(self, color1, color2, blend_mode, opacity):
        # 解析颜色
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        
        # 混合颜色
        if blend_mode == "normal":
            blended = tuple(int(rgb1[i] * (1 - opacity) + rgb2[i] * opacity) for i in range(3))
        elif blend_mode == "multiply":
            blended = tuple(int(rgb1[i] * rgb2[i] / 255) for i in range(3))
        # 添加更多混合模式...
        
        return (rgb_to_hex(blended),)
```

### 10. 随机数生成节点

```python
import random

class RandomNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_value": ("FLOAT", {"default": 0.0}),
                "max_value": ("FLOAT", {"default": 1.0}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 999999})
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("random_value",)
    FUNCTION = "generate_random"
    CATEGORY = "Math"
    
    def generate_random(self, min_value, max_value, seed):
        if seed != 0:
            random.seed(seed)
        
        result = random.uniform(min_value, max_value)
        return (result,)
```

## 🔧 工具节点示例

### 11. 数据类型转换节点

```python
class TypeConvertNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_value": ("*",),
                "target_type": (["FLOAT", "INT", "STRING", "BOOLEAN"], {"default": "FLOAT"})
            }
        }
    
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("converted_value",)
    FUNCTION = "convert_type"
    CATEGORY = "Utility"
    
    def convert_type(self, input_value, target_type):
        try:
            if target_type == "FLOAT":
                result = float(input_value)
            elif target_type == "INT":
                result = int(input_value)
            elif target_type == "STRING":
                result = str(input_value)
            elif target_type == "BOOLEAN":
                result = bool(input_value)
            else:
                result = input_value
        except (ValueError, TypeError):
            result = input_value
        
        return (result,)
```

### 12. 调试信息节点

```python
class DebugNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_data": ("*",),
                "debug_level": (["info", "warning", "error"], {"default": "info"})
            }
        }
    
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output_data",)
    FUNCTION = "debug"
    CATEGORY = "Utility"
    
    def debug(self, input_data, debug_level):
        if debug_level == "info":
            print(f"DEBUG INFO: {input_data}")
        elif debug_level == "warning":
            print(f"DEBUG WARNING: {input_data}")
        elif debug_level == "error":
            print(f"DEBUG ERROR: {input_data}")
        
        return (input_data,)
```

## 🚀 高级示例

### 13. 批处理节点

```python
class BatchProcessNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "operation": (["resize", "crop", "flip"], {"default": "resize"}),
                "batch_size": ("INT", {"default": 4, "min": 1, "max": 32})
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_images",)
    FUNCTION = "process_batch"
    CATEGORY = "Image"
    
    def process_batch(self, images, operation, batch_size):
        results = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            processed_batch = self.process_single_batch(batch, operation)
            results.append(processed_batch)
        
        return (torch.cat(results, dim=0),)
    
    def process_single_batch(self, batch, operation):
        # 处理单个批次
        if operation == "resize":
            # 调整大小逻辑
            pass
        elif operation == "crop":
            # 裁剪逻辑
            pass
        elif operation == "flip":
            # 翻转逻辑
            pass
        
        return batch
```

### 14. 缓存节点

```python
class CachedNode:
    def __init__(self):
        self.cache = {}
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_data": ("*",),
                "cache_key": ("STRING", {"default": ""})
            }
        }
    
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output_data",)
    FUNCTION = "process_with_cache"
    CATEGORY = "Utility"
    
    def process_with_cache(self, input_data, cache_key):
        # 生成缓存键
        if not cache_key:
            cache_key = str(hash(str(input_data)))
        
        # 检查缓存
        if cache_key in self.cache:
            print(f"使用缓存: {cache_key}")
            return (self.cache[cache_key],)
        
        # 执行处理
        result = self.expensive_operation(input_data)
        
        # 缓存结果
        self.cache[cache_key] = result
        print(f"缓存结果: {cache_key}")
        
        return (result,)
    
    def expensive_operation(self, data):
        # 模拟耗时操作
        import time
        time.sleep(0.1)
        return data * 2
```

## 📝 节点注册

```python
# 注册所有节点
NODE_CLASS_MAPPINGS = {
    "SimpleMathNode": SimpleMathNode,
    "TextProcessNode": TextProcessNode,
    "ImageAdjustNode": ImageAdjustNode,
    "ImageFilterNode": ImageFilterNode,
    "ConditionalNode": ConditionalNode,
    "SwitchNode": SwitchNode,
    "StatisticsNode": StatisticsNode,
    "ClampNode": ClampNode,
    "ColorBlendNode": ColorBlendNode,
    "RandomNode": RandomNode,
    "TypeConvertNode": TypeConvertNode,
    "DebugNode": DebugNode,
    "BatchProcessNode": BatchProcessNode,
    "CachedNode": CachedNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SimpleMathNode": "简单数学",
    "TextProcessNode": "文本处理",
    "ImageAdjustNode": "图像调整",
    "ImageFilterNode": "图像滤镜",
    "ConditionalNode": "条件判断",
    "SwitchNode": "开关",
    "StatisticsNode": "统计计算",
    "ClampNode": "范围限制",
    "ColorBlendNode": "颜色混合",
    "RandomNode": "随机数",
    "TypeConvertNode": "类型转换",
    "DebugNode": "调试信息",
    "BatchProcessNode": "批处理",
    "CachedNode": "缓存节点",
}
```

---

这些示例涵盖了ComfyUI节点开发的各种场景，从基础到高级，从简单到复杂。你可以根据需要选择和学习相应的示例！🚀
