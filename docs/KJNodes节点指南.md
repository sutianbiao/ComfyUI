# ComfyUI-KJNodes 常用节点详解与使用手册

> 版本基准：**kijai/ComfyUI-KJNodes v1.5.2**（2026-09-13），共 257 个节点类。
> 本文所有参数（默认值 / 最小值 / 最大值 / 步长 / 下拉选项 / tooltip）均从源码 AST 逐项提取核对，**不是凭记忆写的**。
> 表格列含义见 [1.0 表格列说明](#10-表格列说明)。

---

## 0. 安装状态与安装方式

### 0.1 当前项目是否安装？

**未安装。** 本仓库 `custom_nodes/` 下只有官方自带的两个示例文件，没有任何 `ComfyUI-KJNodes` 目录。

唯一「沾边」的是：**`ImageStitch` 这一个节点已被上游合并进 ComfyUI 核心**（`comfy_extras/nodes_images.py:419`，注释写着 `Upstreamed from https://github.com/kijai/ComfyUI-KJNodes`），所以你不装 KJNodes 也能用它。

### 0.2 手动下载放到哪里？（你要的答案）

**放这个目录：**

```
<ComfyUI 根目录>/custom_nodes/ComfyUI-KJNodes/
```

对应本仓库的绝对路径：

```
/mnt/fde045dc-60c2-4db6-b37d-928569fbe4c0/work/workspace/github_2026/ComfyUI/custom_nodes/ComfyUI-KJNodes/
```

**要求（重要）**：

1. **目录名必须是 `ComfyUI-KJNodes`**（或任意名字，但内部必须保持仓库原结构）。
2. **必须保留 `nodes/` 子目录和 `__init__.py`**。正确结构：
   ```
   custom_nodes/ComfyUI-KJNodes/
   ├── __init__.py          ← 必须有，ComfyUI 靠它识别这是一个节点包
   ├── nodes/               ← 257 个节点实现都在这里
   │   ├── image_nodes.py
   │   ├── mask_nodes.py
   │   ├── model_optimization_nodes.py
   │   └── ...
   ├── web/                 ← 前端 JS 扩展（SplineEditor / PointsEditor 等依赖它）
   ├── requirements.txt
   └── pyproject.toml
   ```
3. **源码 zip 解压陷阱**：从 GitHub 点「Code → Download ZIP」下载后解压，会得到一个 `ComfyUI-KJNodes-main/` 文件夹。**要把里面那一层的内容**放进 `custom_nodes/ComfyUI-KJNodes/`，不要多套一层目录（否则 `__init__.py` 不在包的根上，节点加载不到）。

**三种下载方式任选：**

| 方式 | 命令 / 操作 | 说明 |
|---|---|---|
| **A. git clone（推荐）** | `cd ComfyUI/custom_nodes && git clone https://github.com/kijai/ComfyUI-KJNodes.git` | 目录名自动正确，后续可 `git pull` 更新 |
| **B. 下载 ZIP** | https://github.com/kijai/ComfyUI-KJNodes/archive/refs/heads/main.zip | 解压后把内层文件夹改名并移到 `custom_nodes/` |
| **C. ComfyUI 管理器** | 界面搜 `ComfyUI-KJNodes` 一键安装 | 会自动处理依赖，最省事 |

**装完后：**

```bash
cd ComfyUI/custom_nodes/ComfyUI-KJNodes
pip install -r requirements.txt     # 务必执行，缺依赖会加载失败
```

然后**重启 ComfyUI**（不是刷新页面）。启动日志里看到类似 `Loaded 257 nodes from KJNodes` 即成功。

### 0.3 依赖提醒

KJNodes 是「依赖极少」的包，但以下几类节点**需要额外库**，缺了会加载失败或运行时报错：

| 功能 | 需要的库 | 安装 |
|---|---|---|
| `PathchSageAttentionKJ` | `sageattention` | `pip install sageattention`（需按 CUDA 版本选 wheel） |
| `ColorMatchV2` 部分方法 | `scikit-image` | `pip install scikit-image` |
| 蒙版 / 图像处理 | `opencv-python` | `pip install opencv-python` |
| `CreateFluidMask` | `scipy` | `pip install scipy` |
| `PreviewAnimation`（H.264） | `imageio-ffmpeg` | `pip install imageio-ffmpeg` |

---

## 1. 总览表（常用节点速查）

### 1.0 表格列说明

本文所有参数表使用统一的 6 列格式，含义如下：

| 列名 | 含义 |
|---|---|
| **参数** | API JSON 里 `inputs` 的 key 名，必须一字不差 |
| **类型** | 插槽/控件类型。`IMAGE`/`MASK`/`MODEL`/`LATENT` 等大写为**连线插槽**（填 `["节点ID", 槽位]`）；`INT`/`FLOAT`/`STRING`/`BOOLEAN`/`COMBO` 为**控件**（填字面量） |
| **默认值** | 源码里 `default=` 的值。控件不填时就是这个值 |
| **范围 / 可选值** | `min`~`max`（`step` 步长）；下拉则列出**全部可选枚举**（源码里的 list） |
| **说明** | 作用、语义、踩坑提示（多来自源码 tooltip） |
| **Demo 取值** | 本文配套 demo 里实际填的值，可直接抄。**`←` 表示连线** |

### 1.1 常量 / 文本 / 杂项

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `INTConstant` | KJNodes/constants | `value` → `INT` | 整数常量 | `value: 1024` |
| `BOOLConstant` | KJNodes/constants | `value` → `BOOLEAN` | 布尔常量 | `value: true` |
| `StringConstant` | KJNodes/constants | `string` → `STRING` | 字符串常量 | `string: "masterpiece"` |
| `ConditioningMultiCombine` | KJNodes/masking/conditioning | N×`CONDITIONING` → `CONDITIONING, INT` | 任意多条条件合并/拼接 | `inputcount: 2, operation: "combine"` |
| `WidgetToString` | KJNodes/text | `id`+`widget_name` → `STRING` | 读别节点 widget 值为字符串 | `id: 5, widget_name: "seed"` |
| `LazySwitchKJ` | KJNodes/misc | `switch`+双分支 → 透传 | 二选一，未选分支**不执行** | `switch: true` |
| `VRAM_Debug` | KJNodes/memory | 3 开关 → 5 输出 | 强制清显存 + 报告前后空闲 | `empty_cache: true, gc_collect: true` |

### 1.2 图像

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `ImageResizeKJv2` | KJNodes/image | `IMAGE` → `IMAGE, INT, INT, MASK` | **最常用**，智能缩放/填充/裁切 | `width:1024, height:1024, keep_proportion:"pad", divisible_by:8` |
| `ColorMatchV2` | KJNodes/image | `IMAGE×2` → `IMAGE` | 参考图色调迁移（7 种算法） | `method:"mkl", strength:1.0` |
| `ImageSharpenKJ` | KJNodes/image | `IMAGE/MASK` → 同类型 | 锐化（RCAS/USM/高通/反卷积） | `method.rcas, strength:0.8` |
| `ColorToMask` | KJNodes/masking | `IMAGE` → `MASK` | RGB 值转蒙版 | `red:255, green:0, blue:0, threshold:10` |
| `ImageBatchMulti` | KJNodes/image | N×`IMAGE` → `IMAGE` | 多图拼 batch | `inputcount: 3` |
| `LoadImagesFromFolderKJ` | KJNodes/image | 路径 → `IMAGE, MASK, INT, STRING` | 文件夹整批读图 | `folder:"/path", width:1024, height:1024` |
| `SaveImageKJ` | KJNodes/image | `IMAGE` → `STRING` | 存图（可指定子目录/字幕） | `filename_prefix:"out/a", output_folder:"output"` |
| `PreviewAnimation` | KJNodes/image | `IMAGE`+`fps` → 无 | WebP/H.264 动画预览 | `fps: 8.0` |
| `TransitionImagesInBatch` | KJNodes/image | `IMAGE` → `IMAGE` | batch 内帧间过渡特效 | `transitioning_frames:4, transition_type:"fade"` |
| `CrossFadeImages` | KJNodes/image | `IMAGE×2` → `IMAGE` | 两段 batch 交叉淡化 | `transitioning_frames:8, start_level:0.0, end_level:1.0` |
| `ImageTransformKJ` | KJNodes/image | `IMAGE` → 6 输出（含 `BBOX`） | 前端画布裁剪/旋转/填充 | `target_width:512, upscale_method:"lanczos"` |
| `HDRPreviewKJ` | KJNodes/image | `IMAGE` → `IMAGE` | HDR（LogC3）色调映射预览 | `exposure:0.0, saturation:1.0, input_space:"logc3"` |

### 1.3 遮罩 / 生成

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `GrowMaskWithBlur` | KJNodes/masking | `MASK` → `MASK, MASK` | 膨胀 + 羽化 | `expand:12, blur_radius:8, tapered_corners:true` |
| `RoundMask` | KJNodes/masking | `MASK` → `MASK` | 圆形蒙版 | — |
| `BatchCropFromMask` | KJNodes/masking | `IMAGE`+`MASK` → `IMAGE, IMAGE, BBOX, INT, INT` | 按蒙版批量裁出 | `crop_size_mult:1.0, bbox_smooth_alpha:0.5` |
| `BatchUncrop` | KJNodes/masking | `IMAGE×2`+`BBOX` → `IMAGE` | 裁出的图还原回原位 | `border_blending:0.25` |
| `CreateGradientMask` | KJNodes/masking/generate | 无 → `MASK` | 渐变蒙版 | `width:512, height:512, frames:0` |
| `CreateTextMask` | KJNodes/text | 无 → `IMAGE, MASK` | 文字蒙版 | `text:"HELLO!", font_size:64` |
| `CreateFluidMask` | KJNodes/masking/generate | 无 → `IMAGE, MASK` | 流体/烟雾蒙版 | `inflow_count:3, inflow_duration:60` |

### 1.4 权重 / 曲线

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `SplineEditor` | KJNodes/weights | 曲线点 → `MASK, STRING, FLOAT, INT, STRING` | 可视化曲线生成权重序列 | `points_to_sample:16, sampling_method:"time"` |
| `WeightScheduleConvert` | KJNodes/weights | `FLOAT` → `FLOAT, STRING, INT` | 权重序列类型转换/重映射 | `output_type:"list", repeat:1` |
| `WeightScheduleExtend` | KJNodes/weights | `FLOAT×2` → `FLOAT` | 两段权重拼接 | `output_type:"match_input"` |

### 1.5 LoRA

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `LoraExtractKJ` | KJNodes/lora | `MODEL/CLIP×2` → 落盘 | 从微调模型反推 LoRA | `rank:64, lora_type:"standard"` |
| `LoraReduceRankKJ` | KJNodes/lora | `lora_name` → 落盘 | LoRA 降秩 | `new_rank:8, dynamic_method:"sv_knee"` |

### 1.6 模型优化 / 采样

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| `TorchCompileModelAdvanced` | KJNodes/torchcompile | `MODEL` → `MODEL` | torch.compile 加速 UNet | `backend:"inductor", mode:"default"` |
| `TorchCompileVAE` | KJNodes/torchcompile | `VAE` → `VAE` | torch.compile 加速 VAE | `compile_encoder:true, compile_decoder:true` |
| `PathchSageAttentionKJ` | KJNodes/experimental | `MODEL` → `MODEL` | SageAttention 注意力补丁 | `sage_attention:"auto"` |
| `NABLA_AttentionKJ` | KJNodes/experimental | `MODEL`+`LATENT` → `MODEL` | 稀疏窗口注意力（省显存） | `window_time:11, sparsity:0.9` |
| `WanVideoTeaCacheKJ` | KJNodes/**deprecated** | `MODEL` → `MODEL` | Wan TeaCache（**已弃用**） | `rel_l1_thresh:0.275` |
| `WanVideoNAG` | KJNodes/wan | `MODEL`+`CONDITIONING` → `MODEL` | Wan 负向注意力引导 | `nag_scale:11.0, nag_alpha:0.25, nag_tau:2.5` |
| `ModelMemoryUseReportPatch` | KJNodes/memory | `MODEL` → `MODEL` | 打印模型显存占用 | 无参数 |
| `ModelPreviewOverrideKJ` | KJNodes/sampling | `MODEL` → `MODEL` | 采样时实时 latent 预览 | `max_resolution:1024, jpeg_quality:80` |

### 1.7 循环 / 虚拟连线

| 节点 ID | 分类 | 输入 → 输出 | 一句话用途 | 典型 Demo 取值 |
|---|---|---|---|---|
| ~~`TensorLoopOpen`~~ | advanced/looping | — | **v1.5.2 未注册，不可用**（见 2.7） | — |
| ~~`TensorLoopClose`~~ | advanced/looping | — | **v1.5.2 未注册，不可用**（见 2.7） | — |
| ~~`SetNode` / `GetNode`~~ | — | — | **v1.5.2 已移除，不存在**（见 2.7） | — |
| `VAEDecodeLoopKJ` | KJNodes/video | `VAE`+`LATENT` → `IMAGE` | 循环视频消接缝的解码 | 见 2.7 |

---

## 2. 分类详解（富参数表 + 输出槽位 + demo）

> demo 均为 ComfyUI **API 格式 JSON**（`class_type` + `inputs`），`["节点ID", 输出槽]` 表示连线。可直接复制到「API 格式」里调试。
> 部分 demo 里的上游节点（如 `"0"` 表示 CLIP、`"img"` 表示某图像源）用占位 ID，你替换成自己工作流里的实际节点 ID 即可。

### 2.1 核心常量与文本

#### INTConstant

**用途**：生成一个整数常量。常用于把同一个尺寸/数量喂给多个节点，改一处即可全局生效；也用于需要 INT 输入但不想真的连一个节点的地方。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `value` | INT（控件） | `0` | `-18446744073709551615` ~ `18446744073709551615`，step `1` | 要输出的整数。范围实质上不受限 | `1024` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `INT` | `value` | 常量值 |

**demo**
```json
{ "1": { "class_type": "INTConstant", "inputs": { "value": 1024 } } }
```

---

#### BOOLConstant

**用途**：布尔常量，常用来驱动 `LazySwitchKJ` 的 `switch`，或作为 `VRAM_Debug` 的开关来源。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `value` | BOOLEAN（控件） | `True` | `true` / `false` | 要输出的布尔值 | `true` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `BOOLEAN` | `value` | 常量值 |

**demo**
```json
{ "1": { "class_type": "BOOLConstant", "inputs": { "value": true } } }
```

---

#### StringConstant

**用途**：字符串常量，做提示词片段、路径、文件名标签。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `string` | STRING（控件，单行 `multiline=False`） | `''` | 任意字符串 | 要输出的字符串 | `"masterpiece"` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `STRING` | — | 常量字符串 |

**demo**
```json
{ "1": { "class_type": "StringConstant", "inputs": { "string": "masterpiece" } } }
```

---

#### ConditioningMultiCombine

**用途**：把 N 条 `CONDITIONING` 合成一条，替代一层层叠 `ConditioningCombine`，大幅省连线空间。
- `combine` = 逐元素**平均**（等价于把多条提示词融合）
- `concat` = **拼接**（token 维度接起来，总长度变长）

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `inputcount` | INT（控件） | `2` | `2` ~ `20`，step `1` | 要合并的条数，决定下面出现几个 `conditioning_N` 插槽 | `2` |
| `operation` | COMBO（控件） | `"combine"` | `combine` \| `concat` | 合并方式：平均 / 拼接 | `"combine"` |
| `conditioning_1` | CONDITIONING（插槽） | — | 连线 | 第 1 条条件 | `["1", 0]` ← |
| `conditioning_2` | CONDITIONING（插槽） | — | 连线 | 第 2 条条件 | `["2", 0]` ← |
| `conditioning_3…20` | CONDITIONING（插槽） | — | 由 `inputcount` 动态生成 | 更多条件 | — |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `CONDITIONING` | `combined` | 合并后的条件 |
| 1 | `INT` | `inputcount` | 回显条数，方便下游/debug |

**demo**（合并两条提示词）
```json
{
  "1": { "class_type": "CLIPTextEncode", "inputs": { "text": "a cat", "clip": ["0", 0] } },
  "2": { "class_type": "CLIPTextEncode", "inputs": { "text": "in watercolor", "clip": ["0", 0] } },
  "3": { "class_type": "ConditioningMultiCombine", "inputs": {
    "inputcount": 2, "operation": "combine",
    "conditioning_1": ["1", 0], "conditioning_2": ["2", 0] } }
}
```

---

#### WidgetToString

**用途**：把**另一个节点上某个 widget 的当前值**读成字符串。典型用法：读 `KSampler` 的 `seed` 拼进 `SaveImageKJ` 的文件名里，实现「文件名带种子」。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `id` | INT（控件） | `0` | `0` ~ `100000`，step `1` | **目标节点的数字 ID**。需在设置里开启「显示节点 ID（Show node ID）」才能看到 | `5` |
| `widget_name` | STRING（控件，单行） | — | 任意字符串 | 要读的 widget 名，如 `seed`、`steps`、`cfg` | `"seed"` |
| `return_all` | BOOLEAN（控件） | `False` | `true` / `false` | `true` 返回该节点全部 widget 拼成的串；`false` 只返回 `widget_name` 指定的一个 | `false` |
| `any_input`（可选） | ANY（插槽） | — | 连线 | 仅作**执行顺序触发器**，不参与取值 | — |
| `node_title`（可选） | STRING（控件，单行） | — | 任意字符串 | 用节点标题定位，替代 `id`（标题改了就会失效） | — |
| `allowed_float_decimals`（可选） | INT（控件） | `2` | `0` ~ `10` | 浮点值保留几位小数 | `2` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `STRING` | — | 读到的 widget 值 |

> ⚠️ **踩坑**：目标节点被删除重建、或工作流重载后 **节点 ID 会变**，需手动更新 `id`。用 `node_title` 相对稳一点（标题不会自动变）。

**demo**
```json
{ "1": { "class_type": "WidgetToString", "inputs": { "id": 5, "widget_name": "seed", "return_all": false, "allowed_float_decimals": 2 } } }
```

---

#### LazySwitchKJ

**用途**：根据 `switch` 在两个分支里二选一透传。**关键是 lazy**——未被选中的那个分支**根本不会被执行**，因此可以用来「关掉」一整条耗时的子图（如放大分支）而不付出任何计算代价。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `switch` | BOOLEAN（插槽/控件） | — | `true` / `false` | `true` → 走 `on_true`；`false` → 走 `on_false` | `["ctrl", 0]` ← |
| `on_true` | ANY（**lazy** 插槽） | — | 连线 | 真分支数据 | `["a", 0]` ← |
| `on_false` | ANY（**lazy** 插槽） | — | 连线 | 假分支数据 | `["b", 0]` ← |

**输出**：与所选分支**同类型透传**（`RETURN_TYPES` 在源码里是动态的）。

> ⚠️ **踩坑**：`on_true` / `on_false` 是 lazy 输入，用 `[节点ID, 槽位]` 连线即可；不要试图在这两个字段上填字面量。

**demo**
```json
{
  "1": { "class_type": "LazySwitchKJ", "inputs": {
    "switch": ["ctrl", 0], "on_true": ["a", 0], "on_false": ["b", 0] } }
}
```

---

#### VRAM_Debug

**用途**：在长工作流中途**强制清显存**，并报告清理前后的空闲显存（MB），用于定位 OOM 发生在哪一段。三个开关可任意组合。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `empty_cache` | BOOLEAN（控件） | `True` | `true` / `false` | 调用 `torch.cuda.empty_cache()` | `true` |
| `gc_collect` | BOOLEAN（控件） | `True` | `true` / `false` | 调用 Python `gc.collect()` | `true` |
| `unload_all_models` | BOOLEAN（控件） | `False` | `true` / `false` | 卸载全部已加载模型（**代价大**，之后要重新加载） | `false` |
| `any_input`（可选） | ANY（插槽） | — | 连线 | 触发/透传 | — |
| `image_pass`（可选） | IMAGE（插槽） | — | 连线 | 图像透传（不影响图像内容） | — |
| `model_pass`（可选） | MODEL（插槽） | — | 连线 | 模型透传 | `["ksampler", 0]` ← |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | ANY | `any_output` | 透传 |
| 1 | IMAGE | `image_pass` | 图像透传 |
| 2 | MODEL | `model_pass` | 模型透传 |
| 3 | INT | `freemem_before` | 清理前空闲显存 |
| 4 | INT | `freemem_after` | 清理后空闲显存 |

**demo**
```json
{ "1": { "class_type": "VRAM_Debug", "inputs": {
  "empty_cache": true, "gc_collect": true, "unload_all_models": false,
  "model_pass": ["ksampler", 0] } } }
```

---

### 2.2 图像节点

#### ImageResizeKJv2（最常用）

**用途**：比内置 `ImageScale` 智能得多的缩放节点。`keep_proportion` 提供 8 种保持比例策略（含 `pillarbox_blur` 模糊填充、`total_pixels` 按总像素约束），并能把输出尺寸自动对齐到 `divisible_by`。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `image` | IMAGE（插槽） | — | 连线 | 输入图 | `["img", 0]` ← |
| `width` | INT（控件） | `512` | `0` ~ ∞，step `1` | 目标宽。`keep_proportion` 非 `stretch` 时会被按比例调整 | `1024` |
| `height` | INT（控件） | `512` | `0` ~ ∞，step `1` | 目标高 | `1024` |
| `upscale_method` | COMBO（控件） | 无默认（必选） | `nearest-exact` \| `bilinear` \| `area` \| `bicubic` \| `lanczos` | 插值算法。缩图用 `area`，放图用 `lanczos`/`bicubic` | `"lanczos"` |
| `keep_proportion` | COMBO（控件） | 无默认（必选） | `stretch` \| `resize` \| `pad` \| `pad_edge` \| `pad_edge_pixel` \| `crop` \| `pillarbox_blur` \| `total_pixels` | **核心参数**，见下表详解 | `"pad"` |
| `pad_color` | STRING（控件） | `"0, 0, 0"` | 逗号分隔 RGB，如 `"255, 255, 255"` | 填充色（tooltip: Color to use for padding） | `"0, 0, 0"` |
| `crop_position` | COMBO（控件） | `"center"` | `center` \| `top` \| `bottom` \| `left` \| `right` | 仅 `crop` 模式生效：裁哪里 | `"center"` |
| `divisible_by` | INT（控件） | `2` | `0` ~ `512`，step `1` | 输出尺寸对齐到此整数。**接 UNet 前请设 8**（SD latent 需 8 的倍数）；设为 `0`/`1` 关闭对齐 | `8` |
| `mask`（可选） | MASK（插槽） | — | 连线 | 一并缩放的蒙版，保证图与蒙版同步 | — |
| `device`（可选） | COMBO（控件） | — | `cpu` \| `gpu` | 计算设备。大图可选 `cpu` 省显存 | — |

**`keep_proportion` 八种模式详解**

| 模式 | 行为 | 适合场景 |
|---|---|---|
| `stretch` | 直接拉伸到目标尺寸，**变形** | 不在意比例 |
| `resize` | 按比例缩放到**能装进**目标框（不填充） | 只限制上界 |
| `pad` | 按比例缩放 + 用 `pad_color` **纯色**填充空白处 | 需要固定尺寸且背景单一 |
| `pad_edge` | 缩放 + 用图像**边缘像素延伸**填充 | 背景延展，比纯色自然 |
| `pad_edge_pixel` | 缩放 + 边缘**像素级复制**填充 | 同上，另一种实现 |
| `crop` | 按比例放大到**铺满**再按 `crop_position` 裁掉多余 | 不想有黑边 |
| `pillarbox_blur` | 缩放 + 用**模糊后的自身**填充两侧（视频常用） | 竖图转横图、视频 pillar box |
| `total_pixels` | 按 `width×height` 作为**总像素数上限**约束缩放 | 只想控制显存/计算量 |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | `IMAGE` | 缩放后的图 |
| 1 | INT | `width` | **实际**输出宽（可能被 `divisible_by` 对齐过，别假设等于你填的 `width`） |
| 2 | INT | `height` | **实际**输出高 |
| 3 | MASK | `mask` | 同步缩放的蒙版（仅在接了 `mask` 时有意义） |

> 💡 **技巧**：输出槽 1/2 是**实际**尺寸，把它接到 `EmptyLatentImage` 上，就能保证图与 latent 尺寸严格一致，避免 VAE 编码时尺寸不匹配。

**demo**（把图 pad 到 1024×1024，黑边居中，对齐 8）
```json
{
  "1": { "class_type": "ImageResizeKJv2", "inputs": {
    "image": ["img", 0],
    "width": 1024, "height": 1024,
    "upscale_method": "lanczos",
    "keep_proportion": "pad",
    "pad_color": "0, 0, 0",
    "crop_position": "center",
    "divisible_by": 8 } }
}
```

**demo B**（竖图转横图，两侧用自身模糊填充，适合视频）
```json
{
  "1": { "class_type": "ImageResizeKJv2", "inputs": {
    "image": ["img", 0],
    "width": 1920, "height": 1088,
    "upscale_method": "lanczos",
    "keep_proportion": "pillarbox_blur",
    "divisible_by": 8 } }
}
```

---

#### ColorMatchV2

**用途**：把**参考图**的色调 / 直方图「搬」到**目标图**上，实现风格统一、参考图对齐、多镜头调色一致。提供 7 种算法。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `image_target` | IMAGE（插槽） | — | 连线 | **被改变**的那张图 | `["target", 0]` ← |
| `image_ref` | IMAGE（插槽） | — | 连线 | **提供参考色调**的那张图 | `["ref", 0]` ← |
| `method` | COMBO（控件） | `"mkl"` | `mkl` \| `hm` \| `reinhard` \| `mvgd` \| `hm-mvgd-hm` \| `hm-mkl-hm` \| `reinhard_lab_gpu` | 匹配算法，见下表 | `"mkl"` |
| `strength` | FLOAT（控件） | `1.0` | `0.0` ~ `10.0`，step `0.01` | 匹配强度。`1.0`=完全匹配，`0.0`=原图，可 >1 过冲 | `1.0` |
| `multithread` | BOOLEAN（控件） | `True` | `true` / `false` | 多线程加速（batch 大时开） | `true` |

**`method` 七种算法**

| 算法 | 原理 | 特点 |
|---|---|---|
| `mkl` | Monge-Kantorovich 线性（直方图传输） | **默认**，整体均衡，最通用 |
| `hm` | Histogram Matching 直方图匹配 | 经典，可能偏色 |
| `reinhard` | Reinhard 色彩迁移（Lab 空间均值方差对齐） | 温和、不易过冲 |
| `mvgd` | Multi-Variate Gaussian Distribution | 统计分布匹配 |
| `hm-mvgd-hm` | 先 HM 再 MVGD 再 HM | 组合，更强 |
| `hm-mkl-hm` | 先 HM 再 MKL 再 HM | 组合，最强，也最容易过冲 |
| `reinhard_lab_gpu` | Reinhard 的 GPU 版（Lab 空间） | **快**，大 batch 用 |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 匹配后的目标图 |

**demo**
```json
{
  "1": { "class_type": "ColorMatchV2", "inputs": {
    "image_target": ["target", 0], "image_ref": ["ref", 0],
    "method": "mkl", "strength": 1.0, "multithread": true } }
}
```

---

#### ImageSharpenKJ

**用途**：锐化。用 **DynamicCombo** 实现——选了不同 `method` 会**动态出现不同的子参数**，这是 ComfyUI V3 Schema 的一个特性。支持图像和蒙版（`MatchType` 自动匹配输入输出类型）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `image` | IMAGE 或 MASK（插槽，自动匹配） | — | 连线 | 输入图/蒙版 | `["img", 0]` ← |
| `method` | DynamicCombo（控件） | — | `rcas` \| `adaptive_usm` \| `high_pass` \| `deconvolution` | 锐化算法，选中后出现对应子参数 | `rcas` |

**`method` 各选项的子参数**

| method | 子参数 | 默认值 | 范围（step） | 说明 |
|---|---|---|---|---|
| `rcas` | `strength` | `0.8` | `0.0`~`1.0`（0.01） | AMD FSR 的 RCAS，5-tap 对比度自适应。`0`=不锐化，`1`=全强度 |
| `adaptive_usm` | `strength` | `0.5` | `0.0`~`3.0`（0.01） | 自适应 USM 强度，>1 激进锐化 |
| | `radius` | `1.0` | `0.5`~`5.0`（0.1） | 高斯模糊 sigma，越大增强越粗的 detail |
| | `threshold` | `0.05` | `0.0`~`1.0`（0.01） | 噪声门限，越高只锐化纹理多的区域；`0`=全锐化 |
| `high_pass` | `strength` | `0.5` | `0.0`~`3.0`（0.01） | 高频细节混合量，>1 更冲 |
| | `radius` | `1.0` | `0.5`~`5.0`（0.1） | 频率截止的 sigma，越大越粗 |
| `deconvolution` | `strength` | `0.5` | `0.0`~`1.0`（0.01） | 原图(0) 与 完全反卷积(1) 的混合 |
| | `radius` | `1.0` | `0.5`~`5.0`（0.1） | 假定的高斯模糊 sigma |
| | `iterations` | `10` | `1`~`100`（1） | Richardson-Lucy 迭代次数。越多越锐但越慢，**超过 ~20 收益递减** |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | 与输入同类型 | `output` | 锐化后的图/蒙版 |

> ⚠️ **API JSON 写法**：DynamicCombo 在 API 格式里是一个**对象**，key 是 `method` 的值 + 子参数名。见下方 demo。

**demo**（RCAS 锐化）
```json
{
  "1": { "class_type": "ImageSharpenKJ", "inputs": {
    "image": ["img", 0],
    "method": { "method": "rcas", "strength": 0.8 } } }
}
```

**demo B**（反卷积锐化，恢复真正丢失的细节）
```json
{
  "1": { "class_type": "ImageSharpenKJ", "inputs": {
    "image": ["img", 0],
    "method": { "method": "deconvolution", "strength": 0.5, "radius": 1.0, "iterations": 10 } } }
}
```

---

#### ColorToMask

**用途**：把图中**某个 RGB 颜色**的区域转成蒙版。典型场景：用绿幕/纯色背景拍的图、或分割模型输出的彩色 label 图，转成 MASK 供 inpaint 使用。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `images` | IMAGE（插槽） | — | 连线 | 输入图（支持 batch） | `["img", 0]` ← |
| `invert` | BOOLEAN（控件） | `False` | `true` / `false` | 反相蒙版（白↔黑） | `false` |
| `red` | INT（控件） | `0` | `0` ~ `255`，step `1` | 目标色 R 分量 | `0` |
| `green` | INT（控件） | `0` | `0` ~ `255`，step `1` | 目标色 G 分量 | `255` |
| `blue` | INT（控件） | `0` | `0` ~ `255`，step `1` | 目标色 B 分量 | `0` |
| `threshold` | INT（控件） | `10` | `0` ~ `255`，step `1` | 颜色容差。**纯色背景可设小（10）；照片级背景要设大（40~80）** | `10` |
| `per_batch` | INT（控件） | `16` | `1` ~ `4096`，step `1` | 每批处理的帧数，影响内存/速度 | `16` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MASK | — | 生成的蒙版（白色=`1.0` 为匹配到目标色的区域） |

**demo**（抠绿幕）
```json
{
  "1": { "class_type": "ColorToMask", "inputs": {
    "images": ["img", 0],
    "invert": false,
    "red": 0, "green": 255, "blue": 0,
    "threshold": 10,
    "per_batch": 16 } }
}
```

---

#### ImageBatchMulti

**用途**：把多张独立的 `IMAGE` 拼成一个 batch（沿 batch 维拼接），供需要 batch 输入的节点（如 `TransitionImagesInBatch`、视频编码）使用。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `inputcount` | INT（控件） | `2` | `2` ~ `1000`，step `1` | 要拼的图数量，决定 `image_N` 插槽个数 | `3` |
| `image_1` | IMAGE（插槽） | — | 连线 | 第 1 张 | `["a", 0]` ← |
| `image_2` | IMAGE（插槽） | — | 连线 | 第 2 张（源码里是 optional） | `["b", 0]` ← |
| `image_3…N` | IMAGE（插槽） | — | 由 `inputcount` 动态生成 | 更多图 | `["c", 0]` ← |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | `images` | 拼接后的 batch |

> ⚠️ **注意**：所有输入图的**尺寸必须一致**，否则会报错。先统一用 `ImageResizeKJv2` 缩到同尺寸。

**demo**
```json
{
  "1": { "class_type": "ImageBatchMulti", "inputs": {
    "inputcount": 3,
    "image_1": ["a", 0], "image_2": ["b", 0], "image_3": ["c", 0] } }
}
```

---

#### LoadImagesFromFolderKJ

**用途**：从**任意文件夹路径**整批读图（不限 ComfyUI 的 `input/` 目录），可选同时读 alpha 通道作为蒙版。做数据集批处理、图片序列转视频必备。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `folder` | STRING（控件） | `''` | 任意路径 | **绝对路径**或相对路径。空串则退化为默认 input 目录 | `"/data/frames"` |
| `width` | INT（控件） | `1024` | `-1` ~ ∞，step `1` | 统一缩放到的宽。**`-1` = 保持原尺寸** | `1024` |
| `height` | INT（控件） | `1024` | `-1` ~ ∞，step `1` | 统一缩放到的高。`-1` = 保持原尺寸 | `1024` |
| `keep_aspect_ratio` | COMBO（控件） | 无默认（必选） | `crop` \| `pad` \| `stretch` | 缩放时的比例策略（同 `ImageResizeKJv2` 的对应模式） | `"crop"` |
| `image_load_cap`（可选） | INT（控件） | `0` | `0` ~ ∞，step `1` | 最多读几张。**`0` = 不限制（全部读）** | `0` |
| `start_index`（可选） | INT（控件） | `0` | `0` ~ ∞，step `1` | 从第几张开始读（跳过前面的） | `0` |
| `include_subfolders`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 是否递归子目录 | `false` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | `image` | 读到的图 batch |
| 1 | MASK | `mask` | 从 alpha 通道提取的蒙版（无 alpha 时全 1 或全 0） |
| 2 | INT | `count` | **实际读到的张数**，下游循环常用 |
| 3 | STRING | `image_path` | 第一张图的路径（便于记录来源） |

> 💡 **技巧**：`count` 输出接 `INTConstant` 或直接喂给循环节点，可以做「读多少张就处理多少张」的动态循环。

**demo**
```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/frames",
    "width": 1024, "height": 1024,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0,
    "start_index": 0,
    "include_subfolders": false } }
}
```

---

#### SaveImageKJ

**用途**：比内置 `SaveImage` 灵活的存图——**可以指定输出子目录**，还能同时写一个字幕 `.txt` 文件（做训练数据集标注时极方便）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `images` | IMAGE（插槽） | — | 连线 | 要存的图（tooltip: The images to save） | `["img", 0]` ← |
| `filename_prefix` | STRING（控件） | `"ComfyUI"` | 任意字符串 | 文件名前缀。**支持格式化占位符**：`%date:yyyy-MM-dd%` 插日期、`%Empty Latent Image.width%` 插别的节点的 widget 值 | `"out/poster"` |
| `output_folder` | STRING（控件） | `"output"` | 任意目录名 | 输出到 `output/` 下的哪个**子目录**。不存在会自动创建 | `"output"` |
| `caption_file_extension`（可选） | STRING（控件） | `".txt"` | 任意扩展名 | 字幕文件扩展名（tooltip 提示限纯文本/数据格式） | `".txt"` |
| `caption`（可选） | STRING（控件） | — | 任意字符串 | 要写的字幕内容（tooltip: string to save as .txt file） | `"a cat"` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | STRING | `filename` | 实际保存的文件名（可继续传给下游） |

**demo**（存到 output/posters/ 并写字幕）
```json
{
  "1": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["img", 0],
    "filename_prefix": "posters/%date:yyyy-MM-dd%",
    "output_folder": "output",
    "caption_file_extension": ".txt",
    "caption": "a cat in watercolor" } }
}
```

---

#### PreviewAnimation

**用途**：把 IMAGE batch 预览成**动画**（WebP 或 H.264），而不是内置 PreviewImage 那样只显示一帧。做视频/动画时看效果必备。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `fps` | FLOAT（控件） | `8.0` | `0.01` ~ `1000.0`，step `0.01` | 播放帧率 | `8.0` |
| `images`（可选） | IMAGE（插槽） | — | 连线 | 要预览的图 batch | `["frames", 0]` ← |
| `masks`（可选） | MASK（插槽） | — | 连线 | 同时预览的蒙版 | — |

**输出**：**无输出**（`RETURN_TYPES = ()`），是纯输出节点。

> ⚠️ **依赖**：H.264 编码需要 `imageio-ffmpeg`。没装会回退或报错。

**demo**
```json
{ "1": { "class_type": "PreviewAnimation", "inputs": { "images": ["frames", 0], "fps": 8.0 } } }
```

---

#### TransitionImagesInBatch

**用途**：在一个 batch **内部**、相邻帧之间插入过渡效果（滑动/擦除/淡入淡出），把 N 张静态图变成带转场的动画。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `images` | IMAGE（插槽） | — | 连线 | 输入 batch | `["frames", 0]` ← |
| `interpolation` | COMBO（控件） | 无默认（必选） | `linear` \| `ease_in` \| `ease_out` \| `ease_in_out` \| `bounce` \| `elastic` \| `glitchy` \| `exponential_ease_out` | 缓动曲线（过渡的「节奏」） | `"ease_in_out"` |
| `transition_type` | COMBO（控件） | 无默认（必选） | `horizontal slide` \| `vertical slide` \| `box` \| `circle` \| `horizontal door` \| `vertical door` \| `fade` | 转场形式（注意**带空格**，JSON 里要原样写） | `"fade"` |
| `transitioning_frames` | INT（控件） | `1` | `0` ~ `4096`，step `1` | 每次转场插入几帧。`0`=不插帧（等于原 batch） | `4` |
| `blur_radius` | FLOAT（控件） | `0.0` | `0.0` ~ `100.0`，step `0.1` | 转场时的模糊半径，让切换更柔和 | `0.0` |
| `reverse` | BOOLEAN（控件） | `False` | `true` / `false` | 反转过渡方向 | `false` |
| `device` | COMBO（控件） | `"CPU"` | `CPU` \| `GPU`（**大写**） | 计算设备。帧多时用 `GPU` 快很多 | `"GPU"` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 插入转场后的 batch（长度 = 原长度 + 转场帧） |

**demo**
```json
{
  "1": { "class_type": "TransitionImagesInBatch", "inputs": {
    "images": ["frames", 0],
    "interpolation": "ease_in_out",
    "transition_type": "fade",
    "transitioning_frames": 4,
    "blur_radius": 0.0,
    "reverse": false,
    "device": "GPU" } }
}
```

---

#### CrossFadeImages

**用途**：把**两个 batch** 交叉淡化接在一起（A 淡出、B 淡入），用于两段视频/动画的衔接。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `images_1` | IMAGE（插槽） | — | 连线 | 第一段 batch | `["a", 0]` ← |
| `images_2` | IMAGE（插槽） | — | 连线 | 第二段 batch | `["b", 0]` ← |
| `interpolation` | COMBO（控件） | 无默认（必选） | `linear` \| `ease_in` \| `ease_out` \| `ease_in_out` \| `bounce` \| `elastic` \| `glitchy` \| `exponential_ease_out` | 缓动曲线 | `"linear"` |
| `transition_start_index` | INT（控件） | `1` | `-4096` ~ `4096`，step `1` | 从第几帧开始过渡。**负数**表示从第一段末尾往前数 | `1` |
| `transitioning_frames` | INT（控件） | `1` | `0` ~ `4096`，step `1` | 过渡持续帧数 | `8` |
| `start_level` | FLOAT（控件） | `0.0` | `0.0` ~ `1.0`，step `0.01` | 过渡起始混合量（`0`=纯 A） | `0.0` |
| `end_level` | FLOAT（控件） | `1.0` | `0.0` ~ `1.0`，step `0.01` | 过渡结束混合量（`1`=纯 B） | `1.0` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 交叉淡化后的 batch |

**demo**
```json
{
  "1": { "class_type": "CrossFadeImages", "inputs": {
    "images_1": ["a", 0], "images_2": ["b", 0],
    "interpolation": "linear",
    "transition_start_index": 1,
    "transitioning_frames": 8,
    "start_level": 0.0, "end_level": 1.0 } }
}
```

---

#### ImageTransformKJ

**用途**：**前端画布驱动**的交互式裁剪/旋转/填充——在节点上直接用鼠标框选区域、旋转、加填充，比手填坐标直观得多。输出 `BBOX` 可喂给 `BatchUncrop`。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `image` | IMAGE 或 MASK（插槽，自动匹配） | — | 连线 | 要变换的图/蒙版 | `["img", 0]` ← |
| `mask`（可选） | MASK（插槽） | — | 连线 | 随图一起变换的蒙版 | — |
| `target_width` | INT（控件） | `0` | `0` ~ ∞，step `1` | 目标宽。**`0` = 保持原尺寸** | `512` |
| `target_height` | INT（控件） | `0` | `0` ~ ∞，step `1` | 目标高。`0` = 保持原尺寸 | `512` |
| `upscale_method` | COMBO（控件） | `"lanczos"` | `nearest-exact` \| `bilinear` \| `area` \| `bicubic` \| `lanczos` | 缩放插值算法 | `"lanczos"` |
| `keep_proportion` | DynamicCombo（控件） | — | 由前端提供的选项（同 `ImageResizeKJv2` 系列） | 保持比例策略 | 前端选 |
| `divisible_by` | INT（控件） | `2` | `0` ~ `512`，step `1` | 尺寸对齐 | `8` |
| `extra_padding` | DynamicCombo（控件） | — | 由前端提供 | 额外填充方式 | 前端选 |
| `invert_crop` | DynamicCombo（控件） | — | 由前端提供 | 反相裁剪 | 前端选 |
| `bboxes` | STRING（控件） | `''` | 由前端画布写入 | **前端 JS 写入的裁剪框数据，不要手填** | `''` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | 同输入类型 | `cropped` | 裁剪/变换后的图 |
| 1 | MASK | `cropped_mask` | 同步裁剪的蒙版 |
| 2 | BBOX | `bbox` | 裁剪框，可喂 `BatchUncrop` |
| 3 | MASK | `bbox_mask` | 裁剪框的蒙版 |
| 4 | INT | `width` | 输出宽 |
| 5 | INT | `height` | 输出高 |

**demo**（前端交互为主，API 只填能填的）
```json
{
  "1": { "class_type": "ImageTransformKJ", "inputs": {
    "image": ["img", 0],
    "target_width": 512, "target_height": 512,
    "upscale_method": "lanczos",
    "divisible_by": 8,
    "bboxes": "" } }
}
```

---

#### HDRPreviewKJ

**用途**：把 **HDR** 图像（ARRI LogC3 压缩或线性 HDR）做色调映射（Reinhard）转成可预览/可保存的 sRGB。处理 HDR 视频管线时用它看效果。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `image` | IMAGE（插槽） | — | 连线 | LogC3 压缩的 HDR（值域 `[0,1]`）；若 `input_space` 选 `linear` 则直接吃线性 HDR | `["hdr", 0]` ← |
| `exposure` | FLOAT（控件） | `0.0` | `-10.0` ~ `10.0`，step `0.01` | 曝光（EV 档）。`0`=不变，`+1`=亮一倍 | `0.0` |
| `saturation` | FLOAT（控件） | `1.0` | `0.0` ~ `2.0`，step `0.01` | 饱和度倍数。`0`=灰度，`1`=不变，`2`=两倍 | `1.0` |
| `fps`（可选） | FLOAT（控件） | `24.0` | `1.0` ~ `120.0`，step `0.1` | batch（视频）输入的播放帧率 | `24.0` |
| `input_space`（可选） | COMBO（控件） | `"logc3"` | `logc3` \| `linear` \| `srgb` | 输入色彩空间。`logc3`=ARRI LogC3；`linear`=线性 HDR；`srgb`=已分级（**跳过 Reinhard 色调映射**） | `"logc3"` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 色调映射后的 sRGB 图，可直接预览/保存 |

**demo**
```json
{
  "1": { "class_type": "HDRPreviewKJ", "inputs": {
    "image": ["hdr", 0],
    "exposure": 0.0, "saturation": 1.0,
    "fps": 24.0, "input_space": "logc3" } }
}
```

---

### 2.3 遮罩与生成

#### GrowMaskWithBlur

**用途**：蒙版**膨胀 + 羽化**，做 inpaint 时让边缘柔和、避免硬边接缝。还能做锥形衰减（`decay_factor`）让边缘过渡更自然。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `mask` | MASK（插槽） | — | 连线 | 输入蒙版 | `["m", 0]` ← |
| `expand` | INT（控件） | `0` | step `1`（下限未限制） | 膨胀像素数 | `12` |
| `incremental_expandrate` | FLOAT（控件） | `0.0` | `0.0` ~ `100.0`，step `0.1` | 递增膨胀率（每帧多膨胀一点，视频用） | `0.0` |
| `tapered_corners` | BOOLEAN（控件） | `True` | `true` / `false` | 锥形圆角，避免方形膨胀的直角 | `true` |
| `flip_input` | BOOLEAN（控件） | `False` | `true` / `false` | 反相输入蒙版 | `false` |
| `blur_radius` | FLOAT（控件） | `0.0` | `0.0` ~ `100`，step `0.1` | **羽化**半径，越大边缘越柔 | `8.0` |
| `lerp_alpha` | FLOAT（控件） | `1.0` | `0.0` ~ `1.0`，step `0.01` | 与原蒙版的线性插值量（`1.0`=全用新蒙版） | `1.0` |
| `decay_factor` | FLOAT（控件） | `1.0` | `0.0` ~ `1.0`，step `0.01` | 衰减因子，让膨胀部分向外渐弱 | `1.0` |
| `fill_holes`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 填充蒙版内部空洞 | `false` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MASK | `mask` | 处理后的蒙版 |
| 1 | MASK | `mask_inverted` | **反相**后的蒙版，省一个 InvertMask 节点 |

**demo**
```json
{
  "1": { "class_type": "GrowMaskWithBlur", "inputs": {
    "mask": ["m", 0],
    "expand": 12,
    "incremental_expandrate": 0.0,
    "tapered_corners": true,
    "flip_input": false,
    "blur_radius": 8.0,
    "lerp_alpha": 1.0,
    "decay_factor": 1.0,
    "fill_holes": false } }
}
```

---

#### RoundMask

**用途**：把蒙版裁成圆形/圆角形状（如做圆形头像、圆形遮罩）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `mask` | MASK（插槽） | — | 连线 | 输入蒙版 | `["m", 0]` ← |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MASK | — | 圆形蒙版 |

**demo**
```json
{ "1": { "class_type": "RoundMask", "inputs": { "mask": ["m", 0] } } }
```

---

#### BatchCropFromMask / BatchUncrop（成对使用）

**用途**：**物体级编辑的利器**。
1. `BatchCropFromMask`：按蒙版把图中每个物体**裁出来**（小图，省显存、细节更好）
2. 中间对裁出的小图做任何处理（重绘 / 放大 / 换脸…）
3. `BatchUncrop`：把处理结果**按原坐标贴回**原图，并做边缘融合

**BatchCropFromMask 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `original_images` | IMAGE（插槽） | — | 连线 | 原图 batch | `["img", 0]` ← |
| `masks` | MASK（插槽） | — | 连线 | 每个物体一张蒙版 | `["m", 0]` ← |
| `crop_size_mult` | FLOAT（控件） | `1.0` | `0.0` ~ `10.0`，step `0.001` | 裁剪框放大倍数。`>1` 多带点上下文（**给重绘留空间，建议 1.1~1.5**） | `1.2` |
| `bbox_smooth_alpha` | FLOAT（控件） | `0.5` | `0.0` ~ `1.0`，step `0.01` | batch 间 bbox 的平滑系数（视频用，防抖动） | `0.5` |

**BatchCropFromMask 输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | `original_images` | 原图透传 |
| 1 | IMAGE | `cropped_images` | **裁出的小图**（真正要处理的） |
| 2 | BBOX | `bboxes` | 裁剪框坐标，**必须传给 BatchUncrop** |
| 3 | INT | `width` | 裁剪宽度 |
| 4 | INT | `height` | 裁剪高度 |

**BatchUncrop 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `original_images` | IMAGE（插槽） | — | 连线 | 原图（接 Crop 的槽 0） | `["crop", 0]` ← |
| `cropped_images` | IMAGE（插槽） | — | 连线 | **处理过**的裁出图 | `["processed", 0]` ← |
| `bboxes` | BBOX（插槽） | — | 连线 | Crop 的槽 2 | `["crop", 2]` ← |
| `border_blending` | FLOAT（控件） | `0.25` | `0.0` ~ `1.0`，step `0.01` | **边缘融合**比例。`0`=硬贴（有接缝），`0.25` 默认柔和 | `0.25` |
| `crop_rescale` | FLOAT（控件） | `1.0` | `0.0` ~ `10.0`，step `0.01` | 贴回时的缩放（处理时改了尺寸用） | `1.0` |
| `border_top` | BOOLEAN（控件） | `True` | `true` / `false` | 是否融合上边缘 | `true` |
| `border_bottom` | BOOLEAN（控件） | `True` | `true` / `false` | 下边缘 | `true` |
| `border_left` | BOOLEAN（控件） | `True` | `true` / `false` | 左边缘 | `true` |
| `border_right` | BOOLEAN（控件） | `True` | `true` / `false` | 右边缘 | `true` |

**BatchUncrop 输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 贴回后的完整图 |

> ⚠️ **关键**：`bboxes` 必须原样从 Crop 的**槽 2** 连到 Uncrop，丢了就贴不回去。

**demo**（完整「裁剪 → 处理 → 还原」骨架）
```json
{
  "1": { "class_type": "BatchCropFromMask", "inputs": {
    "original_images": ["img", 0], "masks": ["m", 0],
    "crop_size_mult": 1.2, "bbox_smooth_alpha": 0.5 } },
  "2": { "class_type": "ImageSharpenKJ", "inputs": {
    "image": ["1", 1], "method": { "method": "rcas", "strength": 0.8 } } },
  "3": { "class_type": "BatchUncrop", "inputs": {
    "original_images": ["1", 0], "cropped_images": ["2", 0], "bboxes": ["1", 2],
    "border_blending": 0.25, "crop_rescale": 1.0,
    "border_top": true, "border_bottom": true,
    "border_left": true, "border_right": true } }
}
```

---

#### CreateGradientMask

**用途**：生成线性渐变蒙版，用于做渐变过渡、软边遮罩、inpaint 的渐变权重。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `invert` | BOOLEAN（控件） | `False` | `true` / `false` | 反转渐变方向 | `false` |
| `frames` | INT（控件） | `0` | `0` ~ `255`，step `1` | 生成的帧数（batch）。`0`=单张 | `0` |
| `width` | INT（控件） | `256` | `16` ~ `4096`，step `1` | 蒙版宽 | `512` |
| `height` | INT（控件） | `256` | `16` ~ `4096`，step `1` | 蒙版高 | `512` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MASK | — | 渐变蒙版 |

**demo**
```json
{ "1": { "class_type": "CreateGradientMask", "inputs": {
  "invert": false, "frames": 0, "width": 512, "height": 512 } } }
```

---

#### CreateTextMask

**用途**：生成文字形状的蒙版（同时输出彩色图），可做文字遮罩、字幕遮罩、水印蒙版。支持旋转动画。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `invert` | BOOLEAN（控件） | `False` | `true` / `false` | 反相蒙版 | `false` |
| `frames` | INT（控件） | `1` | `1` ~ `4096`，step `1` | 帧数（做旋转动画用） | `1` |
| `text_x` | INT（控件） | `0` | `0` ~ `4096`，step `1` | 文字左上角 X | `0` |
| `text_y` | INT（控件） | `0` | `0` ~ `4096`，step `1` | 文字左上角 Y | `0` |
| `font_size` | INT（控件） | `32` | `8` ~ `4096`，step `1` | 字号 | `64` |
| `font_color` | STRING（控件） | `"white"` | 颜色名或十六进制 | 文字颜色 | `"white"` |
| `text` | STRING（控件，**多行**） | `"HELLO!"` | 任意字符串 | 文字内容 | `"HELLO!"` |
| `font` | COMBO（控件） | 无默认（必选） | **`models/kjnodes_fonts/` 下的字体文件列表**（`folder_paths.get_filename_list("kjnodes_fonts")`） | 字体。**要先把 .ttf/.otf 放进 `ComfyUI/models/kjnodes_fonts/`** | `"Arial.ttf"` |
| `width` | INT（控件） | `512` | `16` ~ `4096`，step `1` | 画布宽 | `512` |
| `height` | INT（控件） | `512` | `16` ~ `4096`，step `1` | 画布高 | `512` |
| `start_rotation` | INT（控件） | `0` | `0` ~ `359`，step `1` | 起始旋转角度 | `0` |
| `end_rotation` | INT（控件） | `0` | `-359` ~ `359`，step `1` | 结束旋转角度（≠start 则生成旋转动画） | `0` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 文字彩色图 |
| 1 | MASK | — | 文字蒙版 |

> ⚠️ **踩坑**：`font` 下拉来自 `models/kjnodes_fonts/` 目录。**目录不存在或为空时下拉是空的**，需手动建目录并放字体文件。

**demo**
```json
{ "1": { "class_type": "CreateTextMask", "inputs": {
  "invert": false, "frames": 1,
  "text_x": 0, "text_y": 0,
  "font_size": 64, "font_color": "white", "text": "HELLO!",
  "font": "Arial.ttf",
  "width": 512, "height": 512,
  "start_rotation": 0, "end_rotation": 0 } } }
```

---

#### CreateFluidMask

**用途**：模拟流体/烟雾扩散生成动态蒙版，做烟雾、墨水扩散、转场遮罩。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `invert` | BOOLEAN（控件） | `False` | `true` / `false` | 反相 | `false` |
| `frames` | INT（控件） | `1` | `1` ~ `4096`，step `1` | 帧数 | `60` |
| `width` | INT（控件） | `256` | `16` ~ `4096`，step `1` | 宽 | `512` |
| `height` | INT（控件） | `256` | `16` ~ `4096`，step `1` | 高 | `512` |
| `inflow_count` | INT（控件） | `3` | `0` ~ `255`，step `1` | 注入点数量 | `3` |
| `inflow_velocity` | INT（控件） | `1` | `0` ~ `255`，step `1` | 注入速度 | `1` |
| `inflow_radius` | INT（控件） | `8` | `0` ~ `255`，step `1` | 注入口半径 | `8` |
| `inflow_padding` | INT（控件） | `50` | `0` ~ `255`，step `1` | 注入点距边缘的内边距 | `50` |
| `inflow_duration` | INT（控件） | `60` | `0` ~ `255`，step `1` | 注入持续时间（帧） | `60` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | IMAGE | — | 流体的可视化彩图 |
| 1 | MASK | — | 流体蒙版 |

**demo**
```json
{ "1": { "class_type": "CreateFluidMask", "inputs": {
  "invert": false, "frames": 60, "width": 512, "height": 512,
  "inflow_count": 3, "inflow_velocity": 1,
  "inflow_radius": 8, "inflow_padding": 50,
  "inflow_duration": 60 } } }
```

---

### 2.4 权重 / 曲线

#### SplineEditor

**用途**：**前端可视化曲线编辑器**——在画布上拖点画出一条曲线，然后按不同采样方式把曲线转成权重序列（FLOAT 列表）或蒙版（MASK）。做动画权重调度、逐帧控制（如 LoRA 强度随时间变化）的核心工具。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `points_store` | STRING（控件，单行） | — | 由前端 JS 写入 | **前端存储的控制点数据，不要手填** | `""` |
| `coordinates` | STRING（控件，单行） | — | 由前端 JS 写入 | 同上 | `""` |
| `mask_width` | INT（控件） | `512` | `8` ~ `4096`，step `8` | 输出蒙版宽 | `512` |
| `mask_height` | INT（控件） | `512` | `8` ~ `4096`，step `8` | 输出蒙版高 | `512` |
| `points_to_sample` | INT（控件） | `16` | `2` ~ `1000`，step `1` | **沿曲线采样几个点**，即输出序列长度 | `16` |
| `sampling_method` | COMBO（控件） | `"time"` | `path` \| `time` \| `controlpoints` \| `speed` | 采样方式：`time`=按时间均匀；`path`=按曲线弧长；`controlpoints`=只取控制点；`speed`=按变化速度 | `"time"` |
| `interpolation` | COMBO（控件） | `"cardinal"` | `cardinal` \| `monotone` \| `basis` \| `linear` \| `step-before` \| `step-after` \| `polar` \| `polar-reverse` \| `bezier` | 曲线插值算法 | `"cardinal"` |
| `tension` | FLOAT（控件） | `0.5` | `0.0` ~ `1.0`，step `0.01` | Cardinal 插值的张力（平滑度） | `0.5` |
| `repeat_output` | INT（控件） | `1` | `1` ~ `4096`，step `1` | 输出序列重复几次 | `1` |
| `float_output_type` | COMBO（控件） | `"list"` | `list` \| `pandas series` \| `tensor` | 输出类型 | `"list"` |
| `min_value`（可选） | FLOAT（控件） | `0.0` | `-10000.0` ~ `10000.0`，step `0.01` | 输出值下限（归一化用） | `0.0` |
| `max_value`（可选） | FLOAT（控件） | `1.0` | `-10000.0` ~ `10000.0`，step `0.01` | 输出值上限 | `1.0` |
| `bg_image`（可选） | IMAGE（插槽） | — | 连线 | 画布背景参考图（对着图画曲线） | — |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MASK | `mask` | 曲线转成的蒙版 |
| 1 | STRING | `coord_str` | 控制点坐标字符串（可存下来复用） |
| 2 | FLOAT | `float` | **权重序列**（最常用） |
| 3 | INT | `count` | 序列长度 |
| 4 | STRING | `normalized_str` | 归一化后的字符串 |

**demo**（前端交互为主）
```json
{ "1": { "class_type": "SplineEditor", "inputs": {
  "points_store": "", "coordinates": "",
  "mask_width": 512, "mask_height": 512,
  "points_to_sample": 16,
  "sampling_method": "time",
  "interpolation": "cardinal",
  "tension": 0.5,
  "repeat_output": 1,
  "float_output_type": "list",
  "min_value": 0.0, "max_value": 1.0 } } }
```

---

#### WeightScheduleConvert / WeightScheduleExtend

**用途**：权重序列的**类型转换**与**拼接**。`Convert` 还能做重映射（remap）和反转。

**WeightScheduleConvert 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `input_values` | FLOAT（插槽/控件） | `0.0` | 任意 | 输入权重序列 | `["spline", 2]` ← |
| `output_type` | COMBO（控件） | `"list"` | `match_input` \| `list` \| `pandas series` \| `tensor` | 输出类型。`match_input`=与输入同类型 | `"list"` |
| `invert` | BOOLEAN（控件） | `False` | `true` / `false` | 反转序列（`1-x`） | `false` |
| `repeat` | INT（控件） | `1` | `1` ~ `255`，step `1` | 重复几次 | `1` |
| `remap_to_frames`（可选） | INT（控件） | `0` | 任意 | 重映射到指定帧数（`0`=不重映射） | `0` |
| `interpolation_curve`（可选） | FLOAT（控件） | — | 任意 | 重映射时的插值曲线 | — |
| `remap_values`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 是否把值重映射到新区间 | `false` |
| `remap_min`（可选） | FLOAT（控件） | `0.0` | `-100000` ~ `100000.0`，step `0.01` | 重映射后的最小值 | `0.0` |
| `remap_max`（可选） | FLOAT（控件） | `1.0` | `-100000` ~ `100000.0`，step `0.01` | 重映射后的最大值 | `1.0` |

**WeightScheduleConvert 输出槽位**：`FLOAT`（权重）、`STRING`、`INT`

**WeightScheduleExtend 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `input_values_1` | FLOAT（插槽） | `0.0` | 任意 | 第一段序列 | `["a", 0]` ← |
| `input_values_2` | FLOAT（插槽） | `0.0` | 任意 | 第二段序列 | `["b", 0]` ← |
| `output_type` | COMBO（控件） | `"match_input"` | `match_input` \| `list` \| `pandas series` \| `tensor` | 输出类型 | `"match_input"` |

**WeightScheduleExtend 输出槽位**：`FLOAT`

**demo**
```json
{
  "1": { "class_type": "WeightScheduleConvert", "inputs": {
    "input_values": ["spline", 2],
    "output_type": "list", "invert": false, "repeat": 1,
    "remap_to_frames": 0, "remap_values": false,
    "remap_min": 0.0, "remap_max": 1.0 } },
  "2": { "class_type": "WeightScheduleExtend", "inputs": {
    "input_values_1": ["1", 0], "input_values_2": ["other", 0],
    "output_type": "match_input" } }
}
```

---

### 2.5 LoRA 管理

#### LoraExtractKJ

**用途**：**反推 LoRA**——给一个微调后的模型和一个原始基座模型，用 SVD 分解出差值，存成 LoRA 文件。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `finetuned` | MODEL 或 CLIP（MultiType） | — | 连线 | **微调后**的模型 | `["ft", 0]` ← |
| `original` | MODEL 或 CLIP（MultiType） | — | 连线 | **原始基座**模型（用于做差） | `["base", 0]` ← |
| `filename_prefix` | STRING（控件） | `"loras/ComfyUI_extracted_lora"` | 任意路径前缀 | 保存路径（相对 `models/`） | `"loras/my_lora"` |
| `rank` | INT（控件） | `64` | `1` ~ `4096`，step `1` | LoRA 秩。对 adaptive 方法是**上限** | `64` |
| `lora_type` | COMBO（控件） | 无默认（必选） | `standard` \| `full` \| `adaptive_ratio` \| `adaptive_quantile` \| `adaptive_energy` \| `adaptive_fro` | LoRA 类型。`standard`=固定秩；`adaptive_*`=按奇异值分布自动定秩 | `"standard"` |
| `algorithm` | COMBO（控件） | `"svd_lowrank"` | `svd_linalg` \| `svd_lowrank` | SVD 算法。`svd_lowrank` **更快但精度略低** | `"svd_lowrank"` |
| `lowrank_iters` | INT（控件） | `7` | `1` ~ `100`，step `1` | lowrank SVD 的子空间迭代次数 | `7` |
| `output_dtype` | COMBO（控件） | `"fp16"` | `fp16` \| `bf16` \| `fp32` | 保存精度 | `"fp16"` |
| `bias_diff` | BOOLEAN（控件） | `True` | `true` / `false` | 是否对 bias 也做差 | `true` |
| `adaptive_param` | FLOAT（控件） | `0.15` | `0.0` ~ `1.0`，step `0.01` | adaptive 方法参数：`ratio`=最大奇异值的比例；`quantile`=奇异值分位数；`fro`=Frobenius 范数保留比 | `0.15` |
| `clamp_quantile` | BOOLEAN（控件） | `False` | `true` / `false` | 钳制分位数 | `false` |

**输出**：落盘到 `models/loras/`，无连线输出（在 UI 上会提示保存结果）。

**demo**
```json
{ "1": { "class_type": "LoraExtractKJ", "inputs": {
  "finetuned": ["ft", 0], "original": ["base", 0],
  "filename_prefix": "loras/my_lora",
  "rank": 64, "lora_type": "standard",
  "algorithm": "svd_lowrank", "lowrank_iters": 7,
  "output_dtype": "fp16", "bias_diff": true,
  "adaptive_param": 0.15, "clamp_quantile": false } } }
```

---

#### LoraReduceRankKJ（显示名 `LoraReduceRank`）

> ⚠️ **节点 ID 是 `LoraReduceRankKJ`**（带 KJ 后缀），显示名才是不带后缀的 `LoraReduceRank`。写 API JSON 时**必须用带后缀的 ID**，否则报 `Node not found`。

**用途**：给已有 LoRA **降秩**减小体积（如 rank 128 → 8），可用 `sv_knee` 等动态方法自动找「肘点」定秩。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `lora_name` | COMBO（控件） | — | `models/loras/` 下的 LoRA 文件列表 | 要处理的 LoRA | `"my_lora.safetensors"` |
| `new_rank` | INT（控件） | `8` | `1` ~ `4096`，step `1` | 新秩。用 `dynamic_method` 时是**上限** | `8` |
| `dynamic_method` | COMBO（控件） | `"disabled"` | `disabled` \| `sv_ratio` \| `sv_cumulative` \| `sv_fro` \| `sv_knee` | 动态定秩方法。`sv_knee` = 找奇异值曲线的**肘点** | `"sv_knee"` |
| `dynamic_param` | FLOAT（控件） | `0.2` | `0.0` ~ `2.0`，step `0.01` | 动态方法参数。对 `sv_knee`：`1.0`=标准肘点，`<1.0`=更激进（更低秩），`>1.0`=更保守 | `0.2` |
| `output_dtype` | COMBO（控件） | `"match_original"` | `match_original` \| `fp16` \| `bf16` \| `fp32` | 保存精度 | `"match_original"` |
| `verbose` | BOOLEAN（控件） | `True` | `true` / `false` | 打印详细信息 | `true` |

**输出**：落盘新 LoRA 文件。

**demo**
```json
{ "1": { "class_type": "LoraReduceRankKJ", "inputs": {
  "lora_name": "my_lora.safetensors",
  "new_rank": 8, "dynamic_method": "sv_knee",
  "dynamic_param": 0.2,
  "output_dtype": "match_original", "verbose": true } } }
```

---

### 2.6 模型优化 / 采样

#### TorchCompileModelAdvanced

**用途**：用 `torch.compile` 编译 UNet 提速（通常 20%~50%）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | 要编译的模型 | `["ckpt", 0]` ← |
| `backend` | COMBO（控件） | `"inductor"` | `inductor` \| `cudagraphs` | 编译后端。`inductor` 通用；`cudagraphs` 快但限制多 | `"inductor"` |
| `fullgraph` | BOOLEAN（控件） | `False` | `true` / `false` | 全图模式（tooltip: Enable full graph mode）。**容易因动态 shape 失败，一般保持 False** | `false` |
| `mode` | COMBO（控件） | `"default"` | `default` \| `max-autotune` \| `max-autotune-no-cudagraphs` \| `reduce-overhead` | 优化级别。`max-autotune` 最快但**编译极慢** | `"default"` |
| `dynamic` | COMBO（控件） | `"false"` | `auto` \| `true` \| `false` | 动态 shape 追踪。尺寸会变就选 `auto`/`true`，否则编译缓存会爆炸 | `"false"` |
| `compile_transformer_blocks_only` | BOOLEAN（控件） | `True` | `true` / `false` | **只编译 transformer block**（更快、更不易出错），建议保持 True | `true` |
| `dynamo_cache_size_limit` | INT（控件） | `64` | `0` ~ `1024`，step `1` | `torch._dynamo.config.cache_size_limit`。shape 变化多时调大 | `64` |
| `debug_compile_keys` | BOOLEAN（控件） | `False` | `true` / `false` | 打印 compile keys，排错用 | `false` |
| `disable_dynamic_vram`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 关闭动态 VRAM（它可能与 compile 冲突） | `false` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 编译后的模型 |

> ⚠️ **首次运行会慢很多**（编译可能几十秒到几分钟），之后才快。换模型/换尺寸会**重新编译**。

**demo**
```json
{ "1": { "class_type": "TorchCompileModelAdvanced", "inputs": {
  "model": ["ckpt", 0],
  "backend": "inductor", "fullgraph": false, "mode": "default",
  "dynamic": "false", "compile_transformer_blocks_only": true,
  "dynamo_cache_size_limit": 64, "debug_compile_keys": false,
  "disable_dynamic_vram": false } } }
```

---

#### TorchCompileVAE

**用途**：同上，但编译的是 VAE（编解码）。做大图 VAE 解码时提速明显。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `vae` | VAE（插槽） | — | 连线 | 要编译的 VAE | `["vae", 0]` ← |
| `backend` | COMBO（控件） | 无默认（必选） | `inductor` \| `cudagraphs` | 编译后端 | `"inductor"` |
| `fullgraph` | BOOLEAN（控件） | `False` | `true` / `false` | 全图模式 | `false` |
| `mode` | COMBO（控件） | `"default"` | `default` \| `max-autotune` \| `max-autotune-no-cudagraphs` \| `reduce-overhead` | 优化级别 | `"default"` |
| `compile_encoder` | BOOLEAN（控件） | `True` | `true` / `false` | 编译**编码器**（图→latent） | `true` |
| `compile_decoder` | BOOLEAN（控件） | `True` | `true` / `false` | 编译**解码器**（latent→图） | `true` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | VAE | — | 编译后的 VAE |

**demo**
```json
{ "1": { "class_type": "TorchCompileVAE", "inputs": {
  "vae": ["vae", 0], "backend": "inductor",
  "fullgraph": false, "mode": "default",
  "compile_encoder": true, "compile_decoder": true } } }
```

---

#### PathchSageAttentionKJ

**用途**：给模型的 attention 打 **SageAttention** 补丁，显著提速并省显存（几乎无损）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | 要打补丁的模型 | `["ckpt", 0]` ← |
| `sage_attention` | COMBO（控件） | `False`（即 `disabled`） | `disabled` \| `auto` \| `sageattn_qk_int8_pv_fp16_cuda` \| `sageattn_qk_int8_pv_fp16_triton` \| `sageattn_qk_int8_pv_fp8_cuda` \| `sageattn_qk_int8_pv_fp8_cuda++` \| `sageattn3` \| `sageattn3_per_block_mean` | SageAttention 模式。**不确定就选 `auto`**。要撤销补丁就再跑一次选 `disabled` | `"auto"` |
| `allow_compile`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 允许对 sage attention 函数用 torch.compile，需 sageattn ≥ 2.2.0 | `false` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 打补丁后的模型 |

> ⚠️ **依赖**：必须先 `pip install sageattention`，且要匹配你的 CUDA/PyTorch 版本，否则节点会报错。

**demo**
```json
{ "1": { "class_type": "PathchSageAttentionKJ", "inputs": {
  "model": ["ckpt", 0], "sage_attention": "auto", "allow_compile": false } } }
```

---

#### NABLA_AttentionKJ

**用途**：稀疏**窗口注意力**——限制 attention 只在时间/空间的局部窗口内计算，大幅省显存（长视频尤其明显）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | 要打补丁的模型 | `["ckpt", 0]` ← |
| `latent` | LATENT（插槽） | — | 连线 | **仅用于读取 latent shape**，内容不会被修改 | `["empty", 0]` ← |
| `window_time` | INT（控件） | `11` | `1` ~ ∞ | **时间维**窗口大小（帧数） | `11` |
| `window_width` | INT（控件） | `3` | `1` ~ ∞ | **空间宽**方向窗口大小 | `3` |
| `window_height` | INT（控件） | `3` | `1` ~ ∞ | **空间高**方向窗口大小 | `3` |
| `sparsity` | FLOAT（控件） | `0.9` | `0.0` ~ `1.0`，step `0.01` | 稀疏度。`0.9`=只算 10% 的 attention（**越高越省但质量越差**） | `0.9` |
| `torch_compile` | BOOLEAN（控件） | `True` | `true` / `false` | 是否编译（tooltip 说「大概率需要，否则显存占用不合理」），**建议保持 True** | `true` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 打补丁后的模型 |

**demo**
```json
{ "1": { "class_type": "NABLA_AttentionKJ", "inputs": {
  "model": ["ckpt", 0], "latent": ["empty", 0],
  "window_time": 11, "window_width": 3, "window_height": 3,
  "sparsity": 0.9, "torch_compile": true } } }
```

---

#### WanVideoTeaCacheKJ（已弃用）

**用途**：Wan 视频模型的 TeaCache——缓存相邻步的输出，跳过重复计算来提速。

> ⚠️ **该节点的 CATEGORY 已是 `KJNodes/deprecated`（已弃用）**。请改用 ComfyUI 原生或 Kijai 的 WanVideoWrapper 里的 TeaCache 节点。下面的参数仅作理解/兼容旧工作流用。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | Wan 模型 | `["wan", 0]` ← |
| `rel_l1_thresh` | FLOAT（控件） | `0.275` | `0.0` ~ `10.0`，step `0.001` | 触发缓存的相对 L1 阈值。**速度与精度的权衡点**。用 coefficients 时合理区间约 `0.2~0.4`（1.3B 模型要小约 10 倍） | `0.275` |
| `start_percent` | FLOAT（控件） | `0.1` | `0.0` ~ `1.0`，step `0.01` | 从第百分之几步开始用 TeaCache | `0.1` |
| `end_percent` | FLOAT（控件） | `1.0` | `0.0` ~ `1.0`，step `0.01` | 到百分之几步结束 | `1.0` |
| `cache_device` | COMBO（控件） | `"offload_device"` | `main_device` \| `offload_device` | 缓存放哪个设备。`offload_device`（CPU）省显存但慢 | `"offload_device"` |
| `coefficients` | COMBO（控件） | `"i2v_480"` | `disabled` \| `1.3B` \| `14B` \| `i2v_480` \| `i2v_720` | 相对 L1 距离的**重标定系数**。**选 `disabled` 时，阈值要设成用系数时的约 1/10** | `"i2v_480"` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | `model` | 打补丁后的模型 |

**demo**
```json
{ "1": { "class_type": "WanVideoTeaCacheKJ", "inputs": {
  "model": ["wan", 0],
  "rel_l1_thresh": 0.275,
  "start_percent": 0.1, "end_percent": 1.0,
  "cache_device": "offload_device",
  "coefficients": "i2v_480" } } }
```

---

#### WanVideoNAG

**用途**：Wan 视频的 **NAG（Normalized Attention Guidance，归一化注意力引导）**——用负向提示词的注意力去「拉」正向，提升对提示词的遵循度，且比高 CFG 更不易过饱和。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | Wan 模型 | `["wan", 0]` ← |
| `conditioning` | CONDITIONING（插槽） | — | 连线 | 条件（通常接负面条件） | `["neg", 0]` ← |
| `nag_scale` | FLOAT（控件） | `11.0` | `0.0` ~ `100.0`，step `0.001` | 负向引导强度（tooltip: Strength of negative guidance effect） | `11.0` |
| `nag_alpha` | FLOAT（控件） | `0.25` | `0.0` ~ `1.0`，step `0.001` | 混合系数——平衡「归一化引导表示」与「原始正向表示」 | `0.25` |
| `nag_tau` | FLOAT（控件） | `2.5` | `0.0` ~ `10.0`，step `0.001` | 裁剪阈值——限制引导后的 attention 能偏离正向 attention 多远 | `2.5` |
| `input_type`（可选） | COMBO（控件） | 无默认 | `default` \| `batch` | 模型输入类型 | — |
| `inplace`（可选） | BOOLEAN（控件） | `False` | `true` / `false` | 原地修改张量省显存。**数值结果会略变，输出可能有细微差别** | `false` |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | `model` | 打补丁后的模型 |

**demo**
```json
{ "1": { "class_type": "WanVideoNAG", "inputs": {
  "model": ["wan", 0], "conditioning": ["neg", 0],
  "nag_scale": 11.0, "nag_alpha": 0.25, "nag_tau": 2.5,
  "inplace": false } } }
```

---

#### ModelMemoryUseReportPatch

**用途**：给模型挂一个补丁，运行时**打印该模型各部分的显存占用**，用于诊断「到底是哪块吃显存」。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | 要分析的模型 | `["ckpt", 0]` ← |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 透传（带报告补丁） |

**demo**
```json
{ "1": { "class_type": "ModelMemoryUseReportPatch", "inputs": { "model": ["ckpt", 0] } } }
```

---

#### ModelPreviewOverrideKJ

**用途**：**采样过程中的实时 latent 预览**——不用等采样结束，每一步都能看到当前画面。可选接 tiny VAE 做真 RGB 预览（比内置的 Latent2RGB 准确得多）。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL（插槽） | — | 连线 | 要挂预览的模型 | `["ckpt", 0]` ← |
| `max_resolution` | INT（控件） | `1024` | `0` ~ `8192`，step `8` | 预览最大边长（像素）。**`0` = 用完整采样分辨率（不缩小）** | `1024` |
| `jpeg_quality` | INT（控件） | `80` | `30` ~ `100`，step `1` | 预览传输的 JPEG 质量（影响流畅度） | `80` |
| `suppress_default_preview` | BOOLEAN（控件） | `True` | `true` / `false` | 屏蔽采样器自带的预览浮层，只让本节点的帧更新（进度条照常走） | `true` |
| `preview_frames` | INT（控件） | `1` | `1` ~ `1024`，step `1` | 每步采样几帧做动画预览。`1`=单帧（最快）；`>1`=动图。**仅对视频模型（5D latent）生效**，图像模型忽略 | `1` |
| `preview_fps` | INT（控件） | `12` | `1` ~ `60`，step `1` | 动画预览播放帧率。`preview_frames=1` 时忽略；接了 `audio_vae` 时也忽略 | `12` |
| `vae`（可选） | VAE（插槽） | — | 连线 | 可选的 **LTX VAE** 做真 RGB 预览。`TAEHV-LTX`=快速 tiny 解码（VAE 常驻 GPU）；其他 LTX VAE=全质量解码（**每步慢很多**） | — |
| `tiny_vae`（可选） | COMBO（控件） | `"none"` | `models/vae_approx/` 下的 tiny VAE 列表 | Tiny VAE 解码器。**会覆盖 Latent2RGB 和 `vae` 输入** | `"none"` |
| `audio_vae`（可选） | VAE（插槽） | — | 连线 | 音频 VAE（MiniMax H3 等）。`preview_frames>1` 时每步解码音频并混进动画（按实时播放，`preview_fps` 忽略），频谱图画在曲线下方 | — |

**输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 挂了预览补丁的模型 |

**demo**
```json
{ "1": { "class_type": "ModelPreviewOverrideKJ", "inputs": {
  "model": ["ckpt", 0],
  "max_resolution": 1024, "jpeg_quality": 80,
  "suppress_default_preview": true,
  "preview_frames": 1, "preview_fps": 12,
  "tiny_vae": "none" } } }
```

---

### 2.7 循环与虚拟连线

> ### ⚠️ 重要更正：v1.5.2 里这两个节点**不可用**
>
> 我对 `kjrepo/__init__.py` 的 `NODE_CLASS_MAPPINGS` 做了全量核对（共 236 条注册），结果如下：
>
> | 节点 | 源码里有类 | 是否注册 | 结论 |
> |---|---|---|---|
> | `TensorLoopOpen` / `TensorLoopClose` | ✅ 在 `nodes/nodes_looping.py:37/121` | ❌ **未注册** | v1.5.2 **搜不到、不可用**，可能要等 Nodes 2.0 |
> | `SetNode` / `GetNode` | ❌ 整个仓库**没有这个类** | ❌ | **已被移除**，旧文档/旧教程里的写法已失效 |
> | `VAEDecodeLoopKJ` | ✅ | ✅ 已注册 | 想消循环视频接缝，**用这个** |
>
> 因此下面 2.7 的内容仅作**理解原理 / 兼容未来版本**参考，**不要照抄到 v1.5.2 的工作流里**。

#### TensorLoopOpen / TensorLoopClose（v1.5.2 未注册，仅供理解）

**用途**：**循环原语**——把「处理 N 段」变成一次连线。做长视频分段生成时必备（先生成 33 帧 → 回传 → 再生成下一段）。
- `TensorLoopOpen`：循环入口，产出 `flow_control`（循环控制信号）+ `previous_value`（上一轮结果）
- `TensorLoopClose`：循环出口，把本轮结果累积（或替换）并决定是否继续

**TensorLoopOpen 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `mode` | DynamicCombo（控件） | — | 由前端提供的循环终止模式（如按总帧数 / 按次数） | **循环终止条件** | 前端选 |
| `initial_value`（可选） | 任意（自动匹配） | — | 连线 | 第一轮时作为 `previous_value` 的初始值 | `["seed_img", 0]` ← |

**TensorLoopOpen 输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | FLOW_CONTROL | `flow_control` | **必须连到 Close 的 `flow_control`** |
| 1 | 同 initial_value 类型 | `previous_value` | 上一轮的值（第一轮是 `initial_value`） |
| 2 | INT | `accumulated_count` | 已收集的数量（第一轮为 `0`） |
| 3 | INT | `current_iteration` | 当前迭代序号（**从 1 开始**） |

**TensorLoopClose 参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `flow_control` | FLOW_CONTROL（插槽） | — | 连线 | Open 的槽 0 | `["open", 0]` ← |
| `processed` | 任意（自动匹配） | — | 连线 | **本轮产生的结果** | `["gen", 0]` ← |
| `accumulate` | BOOLEAN（控件） | `True` | `true` / `false` | `true`=把所有轮次收集成一个 batch；`false`=只输出最后一轮结果 | `true` |
| `overlap` | DynamicCombo（控件） | — | `disabled` \| `start` \| `end` \| `fade_linear` \| `fade_smooth`（由前端枚举） | 处理**相邻轮次重叠帧**（视频模型会重复生成上下文帧）：`disabled`=全保留；`start`/`end`=从开头/结尾裁掉重复；`fade_*`=交叉淡化衔接 | 前端选 |
| `stop`（可选） | BOOLEAN（插槽，`force_input=True`） | `False` | 连线 | 从循环体内部发出的**提前停止信号**。为 `true` 时本轮结束后立即停止 | — |

**TensorLoopClose 输出槽位**

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | 同 `processed` 类型 | `output` | 累积 batch 或最后一轮结果（取决于 `accumulate`） |

**demo**（循环骨架）
```json
{
  "1": { "class_type": "TensorLoopOpen", "inputs": { "initial_value": ["seed_img", 0] } },
  "2": { "class_type": "TensorLoopClose", "inputs": {
    "flow_control": ["1", 0],
    "processed": ["gen", 0],
    "accumulate": true } }
}
```

---

#### SetNode / GetNode（虚拟连线）—— v1.5.2 **已移除**

> ❌ **这个节点在 v1.5.2 里不存在了**。我在整个 `kjrepo/` 里搜索 `class SetNode` / `class GetNode` / `setget` **零命中**，且 `NODE_CLASS_MAPPINGS` 里也没有。
> 网上大量教程仍在讲 Set/Get 虚拟连线，那是**旧版本**的功能。如果你是从旧教程抄来的工作流，这里的节点会显示为红色「缺失节点」。
>
> **替代方案**：用 ComfyUI 内置的 **Reroute** 节点，或 ComfyUI 自带的 Nodes 2.0 虚拟连线（取决于你的 ComfyUI 版本）。

（以下为旧版行为的存档描述，仅供理解旧工作流用）

**用途**：**不打实线、按名字传数据**。Set 给数据起个名字存起来，Get 在别处按同名取出来。用来清理跨屏的长连线。

**参数表**

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `name` | STRING（控件） | — | 任意字符串（**Set 与 Get 必须完全一致**） | 数据名 | `"my_value"` |
| `value`（Set 侧） | 任意（动态类型） | — | 连线或字面量 | 要存的数据 | `["src", 0]` ← |
| `input`（Get 侧） | 任意（动态类型） | — | 通常留空或接触发 | 取出的出口 | — |

**输出**：Get 输出与 Set 存入的值**同类型**。

> ⚠️ **旧版三条硬规则**：① 不能与 reroute 节点相连；② 不能与 bypass 模式混用；③ 名字大小写敏感、前后空格也算。

---

## 3. 完整工作流示例

### 3.1 示例 A：参考图色调统一 + 智能缩放 + 存图

**场景**：一批产品图，要统一成参考图的色调，并全部 pad 到 1024×1024 存档。

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/products",
    "width": 1024, "height": 1024,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "ColorMatchV2", "inputs": {
    "image_target": ["1", 0], "image_ref": ["ref", 0],
    "method": "mkl", "strength": 1.0, "multithread": true } },
  "3": { "class_type": "ImageResizeKJv2", "inputs": {
    "image": ["2", 0],
    "width": 1024, "height": 1024,
    "upscale_method": "lanczos",
    "keep_proportion": "pad",
    "pad_color": "255, 255, 255",
    "crop_position": "center",
    "divisible_by": 8 } },
  "4": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["3", 0],
    "filename_prefix": "products/unified",
    "output_folder": "output",
    "caption_file_extension": ".txt",
    "caption": "color matched to reference" } }
}
```

**连线说明**

| 连线 | 含义 |
|---|---|
| `1.0 → 2.image_target` | 读到的图 batch 作为「被改色调」的一方 |
| `ref.0 → 2.image_ref` | 外部参考图（你自己的 LoadImage 节点） |
| `2.0 → 3.image` | 调色结果送去缩放 |
| `3.0 → 4.images` | 缩放结果存盘 |

---

### 3.2 示例 B：抠出对象 → 处理 → 还原（遮罩工作流骨架）

**场景**：一张合影，只把「人脸区域」锐化，其余保持原样，并且不能有接缝。

```json
{
  "1": { "class_type": "ColorToMask", "inputs": {
    "images": ["src", 0],
    "invert": false,
    "red": 255, "green": 0, "blue": 0,
    "threshold": 20, "per_batch": 16 } },
  "2": { "class_type": "GrowMaskWithBlur", "inputs": {
    "mask": ["1", 0],
    "expand": 12, "incremental_expandrate": 0.0,
    "tapered_corners": true, "flip_input": false,
    "blur_radius": 8.0, "lerp_alpha": 1.0,
    "decay_factor": 1.0, "fill_holes": true } },
  "3": { "class_type": "BatchCropFromMask", "inputs": {
    "original_images": ["src", 0], "masks": ["2", 0],
    "crop_size_mult": 1.2, "bbox_smooth_alpha": 0.5 } },
  "4": { "class_type": "ImageSharpenKJ", "inputs": {
    "image": ["3", 1],
    "method": { "method": "adaptive_usm", "strength": 0.8, "radius": 1.0, "threshold": 0.05 } } },
  "5": { "class_type": "BatchUncrop", "inputs": {
    "original_images": ["3", 0], "cropped_images": ["4", 0], "bboxes": ["3", 2],
    "border_blending": 0.25, "crop_rescale": 1.0,
    "border_top": true, "border_bottom": true,
    "border_left": true, "border_right": true } },
  "6": { "class_type": "PreviewImage", "inputs": { "images": ["5", 0] } }
}
```

**关键连线（容易接错）**

| 连线 | 说明 |
|---|---|
| `3.0 → 5.original_images` | Crop 的**槽 0** 是原图透传 |
| `3.1 → 4.image` | Crop 的**槽 1** 才是裁出的小图（真正要处理的） |
| `3.2 → 5.bboxes` | Crop 的**槽 2** 是 BBOX，**必须**连给 Uncrop |
| `4.0 → 5.cropped_images` | 处理过的小图 |

---

### 3.3 示例 C：模型加速 + 实时预览（文生图骨架）

**场景**：给 SDXL 挂 SageAttention + torch.compile，并开启实时 latent 预览。

```json
{
  "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" } },
  "2": { "class_type": "PathchSageAttentionKJ", "inputs": {
    "model": ["1", 0], "sage_attention": "auto", "allow_compile": false } },
  "3": { "class_type": "TorchCompileModelAdvanced", "inputs": {
    "model": ["2", 0],
    "backend": "inductor", "fullgraph": false, "mode": "default",
    "dynamic": "false", "compile_transformer_blocks_only": true,
    "dynamo_cache_size_limit": 64, "debug_compile_keys": false,
    "disable_dynamic_vram": false } },
  "4": { "class_type": "ModelPreviewOverrideKJ", "inputs": {
    "model": ["3", 0],
    "max_resolution": 1024, "jpeg_quality": 80,
    "suppress_default_preview": true,
    "preview_frames": 1, "preview_fps": 12,
    "tiny_vae": "none" } },
  "5": { "class_type": "CLIPTextEncode", "inputs": { "text": "a cat in watercolor", "clip": ["1", 1] } },
  "6": { "class_type": "CLIPTextEncode", "inputs": { "text": "blurry, low quality", "clip": ["1", 1] } },
  "7": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 1024, "batch_size": 1 } },
  "8": { "class_type": "KSampler", "inputs": {
    "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0],
    "seed": 12345, "steps": 25, "cfg": 7.0,
    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0 } },
  "9": { "class_type": "VAEDecode", "inputs": { "samples": ["8", 0], "vae": ["1", 2] } },
  "10": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["9", 0],
    "filename_prefix": "xlexp/accelerated",
    "output_folder": "output" } }
}
```

**加速链路顺序**：`CheckpointLoaderSimple → SageAttention → torch.compile → PreviewOverride → KSampler`。
> 💡 顺序有讲究：**先打 attention 补丁，再 compile**（否则 compile 会把补丁一起编译进去，缓存容易失效）。

---

## 4. 调试与注意事项

### 4.1 节点不显示 / 报错的排查顺序

| 现象 | 原因 | 解法 |
|---|---|---|
| 节点完全搜不到 | 目录结构错（`__init__.py` 不在包根，或多套了一层目录） | 检查 `custom_nodes/ComfyUI-KJNodes/__init__.py` 是否存在 |
| 启动报 `ModuleNotFoundError` | 依赖没装 | `pip install -r requirements.txt` |
| 启动时报某节点 import 失败 | 缺可选依赖（如 `sageattention`） | 按需 `pip install`，或忽略（仅该节点不可用） |
| `CreateTextMask` 的 `font` 下拉是空的 | `models/kjnodes_fonts/` 目录不存在或没放字体 | 建目录并放入 `.ttf`/`.otf` |
| 修改了代码但没生效 | 没重启 ComfyUI | **必须重启进程**，刷新页面无效 |
| 节点名字和本文对不上 | 版本差异 | KJNodes 更新频繁，用 `/object_info/<node_id>` 查实时 schema |

### 4.2 已知坑位汇总

| 节点 | 坑 | 说明 |
|---|---|---|
| `WanVideoTeaCacheKJ` | **已弃用** | CATEGORY = `KJNodes/deprecated`，改用原生 TeaCache |
| `ImageResizeKJv2` | 输出尺寸 ≠ 你填的尺寸 | `divisible_by` 会对齐；用**输出槽 1/2** 拿实际尺寸 |
| `ImageResizeKJv2` | `upscale_method` / `keep_proportion` 无默认值 | API JSON 里必须显式填，否则报错 |
| `TransitionImagesInBatch` | `device` 是**大写** `CPU`/`GPU` | 小写会报错（和 `ImageResizeKJv2` 的小写 `cpu`/`gpu` 不同！） |
| `transition_type` | 选项**带空格** | 如 `"horizontal slide"`，JSON 里必须原样包含空格 |
| `ImageSharpenKJ` / `ImageTransformKJ` | DynamicCombo 在 API 里是**对象** | 见 2.2 的 demo 写法，不是字符串 |
| `BatchCropFromMask` | `bboxes` 必须从**槽 2** 连出 | 接错槽位就贴不回去 |
| `WidgetToString` | 节点 ID 会变 | 目标节点重建后要手动更新 `id` |
| ~~`SetNode`/`GetNode`~~ | **v1.5.2 已移除** | 整仓搜不到类也没注册，改用内置 Reroute |
| ~~`TensorLoopOpen`/`Close`~~ | **v1.5.2 未注册** | 类在 `nodes_looping.py` 但没进 `NODE_CLASS_MAPPINGS`，搜不到 |
| `LoraReduceRank` | 节点 ID 实为 **`LoraReduceRankKJ`** | 显示名才是不带后缀的，API JSON 必须用带后缀的 ID |
| `torch.compile` 系列 | 首次运行极慢 | 编译几十秒~几分钟属正常，之后才快；换尺寸会重编译 |
| `PathchSageAttentionKJ` | 需匹配 CUDA 版本 | `sageattention` 装错版本会直接崩 |
| `ModelPreviewOverrideKJ` | `preview_frames>1` 对图像模型无效 | 仅 5D latent（视频模型）生效 |

### 4.3 版本差异提醒

- KJNodes **更新非常频繁**（几乎每周），节点名/参数会变。
- 本文档基于 **v1.5.2**。升级后请用 `GET /object_info/<node_id>` 查实时 schema 核对。
- 老工作流里的节点失效时，通常是作者做了重命名或移到 `deprecated` 分类。

---

## 5. 参考

- **仓库**：https://github.com/kijai/ComfyUI-KJNodes
- **下载 ZIP**：https://github.com/kijai/ComfyUI-KJNodes/archive/refs/heads/main.zip
- **安装位置**：`ComfyUI/custom_nodes/ComfyUI-KJNodes/`
- **本仓库中已上游合并的 KJ 节点**：`ImageStitch`（`comfy_extras/nodes_images.py:419`）
- **相关文档**：
  - `docs/BUILTIN_NODES_GUIDE.md` —— ComfyUI 内置节点详解
  - `docs/CUSTOM_DEV_TUTORIAL.md` —— 自定义节点二开完整项目教程
  - `docs/CUSTOM_NODES_SAMPLER_TUTORIAL.md` —— 采样组件类节点开发
  - `docs/CUSTOM_NODES_LOADER_TUTORIAL.md` —— 加载器/模型类节点开发
  - `docs/CUSTOM_NODES_CONDITIONING_TUTORIAL.md` —— 条件/提示词类节点开发

---

> **文档生成说明**：本文 40+ 个节点的参数表（`默认值` / `min`~`max` / `step` / 下拉全枚举 / tooltip）由脚本从 KJNodes v1.5.2 源码 AST 逐项提取后核对撰写，非凭记忆生成。
> 本文档中所有 JSON demo 块均已通过 `json.loads` 校验。
