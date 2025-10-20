"""
ComfyUI 节点辅助工具模块
提供节点开发中常用的工具函数和辅助功能

主要功能：
1. 条件向量操作和修改
2. 图像处理辅助函数
3. 哈希计算工具
4. 数据类型转换
5. 图像通道处理
"""

import hashlib  # 哈希算法库
import torch    # PyTorch深度学习框架

from comfy.cli_args import args  # 命令行参数

from PIL import ImageFile, UnidentifiedImageError  # PIL图像处理库

def conditioning_set_values(conditioning, values={}, append=False):
    """
    设置条件向量的值
    
    功能：
        为条件向量列表中的每个条件添加或修改指定的键值对
        支持追加模式和覆盖模式
    
    参数:
        conditioning: 条件向量列表，格式为 [[tensor, dict], ...]
        values: 要设置的值字典，键值对形式
        append: 是否使用追加模式，True时追加到现有值，False时覆盖
    
    返回:
        list: 修改后的条件向量列表
    
    示例:
        # 添加遮罩信息
        conditioning = [[tensor, {}]]
        values = {"mask": mask_tensor, "strength": 1.0}
        result = conditioning_set_values(conditioning, values)
    """
    c = []  # 存储修改后的条件向量
    for t in conditioning:  # 遍历每个条件向量
        n = [t[0], t[1].copy()]  # 复制条件向量，避免修改原始数据
        for k in values:  # 遍历要设置的值
            val = values[k]
            if append:  # 追加模式
                old_val = n[1].get(k, None)  # 获取现有值
                if old_val is not None:
                    val = old_val + val  # 追加到现有值

            n[1][k] = val  # 设置新值
        c.append(n)  # 添加到结果列表

    return c

def pillow(fn, arg):
    """
    PIL图像处理的安全包装函数
    
    功能：
        安全地执行PIL图像处理函数，自动处理截断图像和错误
        解决PIL库的已知问题（#4472和#2445）以及ComfyUI问题（#3416）
    
    参数:
        fn: PIL函数（如Image.open）
        arg: 传递给函数的参数
    
    返回:
        函数执行结果
    
    错误处理:
        - OSError: 文件系统错误
        - UnidentifiedImageError: 无法识别的图像格式
        - ValueError: 值错误
    """
    prev_value = None  # 存储原始设置
    try:
        x = fn(arg)  # 尝试执行PIL函数
    except (OSError, UnidentifiedImageError, ValueError): #PIL issues #4472 and #2445, also fixes ComfyUI issue #3416
        prev_value = ImageFile.LOAD_TRUNCATED_IMAGES  # 保存原始设置
        ImageFile.LOAD_TRUNCATED_IMAGES = True  # 启用截断图像加载
        x = fn(arg)  # 重新尝试执行函数
    finally:
        if prev_value is not None:
            ImageFile.LOAD_TRUNCATED_IMAGES = prev_value  # 恢复原始设置
    return x

def hasher():
    """
    获取哈希函数
    
    功能：
        根据命令行参数返回指定的哈希函数
        支持多种哈希算法
    
    返回:
        function: 哈希函数对象
    
    支持的算法:
        - md5: MD5哈希算法
        - sha1: SHA-1哈希算法
        - sha256: SHA-256哈希算法
        - sha512: SHA-512哈希算法
    """
    hashfuncs = {
        "md5": hashlib.md5,      # MD5哈希算法
        "sha1": hashlib.sha1,    # SHA-1哈希算法
        "sha256": hashlib.sha256, # SHA-256哈希算法
        "sha512": hashlib.sha512  # SHA-512哈希算法
    }
    return hashfuncs[args.default_hashing_function]  # 返回指定的哈希函数

def string_to_torch_dtype(string):
    """
    字符串转PyTorch数据类型
    
    功能：
        将字符串表示的数据类型转换为PyTorch张量数据类型
        用于配置和参数解析
    
    参数:
        string: 数据类型字符串
    
    返回:
        torch.dtype: PyTorch数据类型
    
    支持的类型:
        - "fp32": 32位浮点数
        - "fp16": 16位浮点数
        - "bf16": 16位脑浮点数
    """
    if string == "fp32":
        return torch.float32    # 32位浮点数
    if string == "fp16":
        return torch.float16    # 16位浮点数
    if string == "bf16":
        return torch.bfloat16   # 16位脑浮点数

def image_alpha_fix(destination, source):
    """
    图像Alpha通道修复函数
    
    功能：
        修复两个图像张量之间的Alpha通道不匹配问题
        确保源图像和目标图像的通道数一致
    
    参数:
        destination: 目标图像张量
        source: 源图像张量
    
    返回:
        tuple: (修复后的目标图像, 修复后的源图像)
    
    处理逻辑:
        - 如果目标图像通道数少于源图像：截取源图像的前N个通道
        - 如果目标图像通道数多于源图像：为目标图像添加Alpha通道并设为1.0
    """
    if destination.shape[-1] < source.shape[-1]:  # 目标通道数少于源图像
        source = source[...,:destination.shape[-1]]  # 截取源图像的前N个通道
    elif destination.shape[-1] > source.shape[-1]:  # 目标通道数多于源图像
        destination = torch.nn.functional.pad(destination, (0, 1))  # 在末尾添加一个通道
        destination[..., -1] = 1.0  # 将新添加的通道设为1.0（完全不透明）
    return destination, source
