# MiniMax H3 节点完全参考手册

> 适用版本：**ComfyUI v0.39.0**（`comfyui_version.py`）
> 依据源码：`comfy_extras/nodes_minimax_h3.py`、`comfy_extras/nodes_audio.py`、`comfy_extras/nodes_video.py`、
> `comfy_extras/nodes_lt.py`、`comfy_extras/nodes_sparse_attention.py`、`comfy_extras/nodes_model_patch.py`、`nodes.py`
>
> 本手册所有参数、默认值、取值范围、槽位顺序均从源码逐行提取，未采用二手整理口径。
> 配套阅读：`docs/MINIMAX_H3_COMFYUI_GUIDE.md`（部署与基础工作流）、`docs/MINIMAX_H3_ADVANCED_GUIDE.md`（多帧锚定与 Fun ControlNet 原理）。

---

## 0. 阅读须知

### 0.1 三个圈层

H3 在 ComfyUI 里没有"插件包"，它的能力由三层节点拼出来：

| 圈层 | 数量 | 说明 | 是否需要额外安装 |
|---|---|---|---|
| **A. H3 专属节点** | 6 | 只服务 H3，节点 ID 以 `MiniMaxH3` 开头 | 否（内置） |
| **B. 为 H3 开了专用分支的通用节点** | 3 | 通用节点，但源码里显式写了 MiniMax-H3 分支 | 否（内置） |
| **C. 配套通用节点** | ~20 | 加载 / 采样 / 解码 / 输出 / 遮罩，任何模型都用 | 否（内置） |

**结论：一个自定义节点都不用装。** 需要的是模型权重文件（见 0.3）。

### 0.2 30 秒自检

```bash
cd /path/to/ComfyUI

# 1) A 层：6 个专属节点是否都在
grep -n "node_id=\"MiniMax" comfy_extras/nodes_minimax_h3.py
# 期望输出 5 行（EmptyMiniMaxH3LatentAV 用的是 io.Schema 但同样带 node_id，共 6 行）

# 2) 加载器是否认得 H3
grep -n "minimax" nodes.py            # CLIPLoader 的 type 列表
grep -n "class MiniMaxH3" comfy/supported_models.py
grep -n "class MiniMaxH3AV" comfy/latent_formats.py

# 3) 官方蓝图是否存在
ls blueprints/ | grep -i minimax
# 期望：Image to Video (MiniMax H3).json

# 4) 模型目录是否已建
ls models/diffusion_models models/text_encoders models/vae models/model_patches 2>/dev/null
```

### 0.3 模型文件与目录映射

| 模型 | 放到 | 由哪个节点读 |
|---|---|---|
| `minimax_h3_fl2va_bf16.safetensors` | `models/diffusion_models/` | `UNETLoader` |
| `minimax_h3_ref2va_bf16.safetensors` | `models/diffusion_models/` | `UNETLoader` |
| Qwen3-VL-32B（含自带 tokenizer） | `models/text_encoders/` | `CLIPLoader`（`type=minimax`） |
| `minimax_h3_video_vae_fp16.safetensors` | `models/vae/` | `VAELoader` |
| `minimax_h3_video_vae_int8_convrot.safetensors` | `models/vae/` | `VAELoader` |
| `minimax_h3_audio_vae_bf16.safetensors` | `models/vae/` | `VAELoader` |
| `minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors` | `models/model_patches/` | `ModelPatchLoader` |
| `*_turbo_*.safetensors`（加速 LoRA） | `models/loras/` | `LoraLoaderModelOnly` |

> **别混 VAE**：I2V 官方蓝图用 `..._video_vae_fp16`；Multiframe / FunCN 官方模板用 `..._video_vae_int8_convrot`。
> 两者在 `models/vae/` 共存即可，靠 `VAELoader` 的下拉框选。

### 0.4 表格约定

- **参数表六列**：`参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值`
- **类型**列用的是 ComfyUI 的槽位类型（`CLIP`、`VAE`、`LATENT`、`IMAGE`、`MASK`、`AUDIO`、`CONDITIONING`、`MODEL`、`MODEL_PATCH`、`INT`、`FLOAT`、`STRING`、`COMBO`、`BOOLEAN`）。
- **可选**输入在源码里是 `optional=True`，UI 上表现为空心圆点；API JSON 里可直接省略。
- **Demo 取值**列给的是本手册配套 demo 里实际填的值，不是"推荐值"。

---

## 1. 节点总览速查表

### A 层：H3 专属（6 个）

| # | 节点 ID | 界面显示名 | 分类 | 一句话 | 关键输出 |
|---|---|---|---|---|---|
| 1 | `EmptyMiniMaxH3LatentAV` | Empty MiniMax H3 AV Latent | `model/latent/minimax` | 造一个空的"画面+声音"联合 latent | `LATENT` |
| 2 | `MiniMaxH3ImageToVideo` | MiniMax H3 Image to Video | `model/conditioning/minimax` | t2va / fl2va：提示词（+可选首尾帧）→ conditioning + latent | `CONDITIONING`, `LATENT` |
| 3 | `MiniMaxH3AddGuide` | Add Guide for MiniMax H3 | `model/conditioning/minimax` | 在任意帧位置钉一张图 / 一段视频 / 一条音轨 | `CONDITIONING` |
| 4 | `MiniMaxH3ReferenceToVideo` | MiniMax H3 Reference to Video | `model/conditioning/minimax` | ref2va：图 / 视频 / 音频做参考，用 `<Picture i>` 等标签引用 | `CONDITIONING`, `LATENT` |
| 5 | `MiniMaxH3SigmaShift` | **ModelSamplingMiniMaxH3** | `model/patch/minimax` | 同步设置画面流与音频流的 shift | `MODEL` |
| 6 | `MiniMaxH3FunControlNetApply` | Apply MiniMax H3 Fun ControlNet | `model/patch/minimax` | 挂 Fun ControlNet（Canny/Depth/Pose/视频重绘） | `MODEL` |

> ⚠️ **5 号节点的 ID 和显示名不一致**：ID 是 `MiniMaxH3SigmaShift`，界面上显示 **ModelSamplingMiniMaxH3**。
> 写 API JSON 必须用 ID；在 UI 里搜索要输显示名（或它注册的别名 `sigma shift` / `minimax shift`）。

### B 层：为 H3 开了专用分支的通用节点（3 个）

| 节点 ID | 界面显示名 | 分类 | 与 H3 的关系 |
|---|---|---|---|
| `LTXVConcatAVLatent` | Concat AV Latent | `model/latent/ltxv` | 描述里明写 "any AV model, e.g. LTXV or MiniMax H3" |
| `LTXVSeparateAVLatent` | Separate AV Latent | `model/latent/ltxv` | 同上，把联合 latent 拆回画面 / 声音两路 |
| `BlockSparseAttention` | Model Sparse Attention | `model/patch` | `sink_conditioning` 参数整条 tooltip 只讲 MiniMax-H3 |

### C 层：配套通用节点

见第 4 章速查表。

---

## 2. A 层：H3 专属节点逐详解

---

### 2.1 `EmptyMiniMaxH3LatentAV`

**界面显示名**：Empty MiniMax H3 AV Latent
**分类**：`model/latent/minimax`
**源码**：`comfy_extras/nodes_minimax_h3.py:94-113`
**职责**：只造 latent，不做任何 conditioning。想走"自己用 `CLIPTextEncode` 编提示词"的路线时用这个。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `width` | INT | `1344` | 32 – 16384，步进 32 | 生成宽度（像素）。会被 VAE 压缩 16 倍进 latent，**建议为 32 的倍数**，否则 latent 尺寸会向下取整导致解码尺寸对不上 | `1344` |
| `height` | INT | `768` | 32 – 16384，步进 32 | 生成高度（像素），同上 | `768` |
| `length` | INT | `124` | 5 – 3600，步进 17 | **帧数**（24 fps）。输入值会被**向上**吸附到 `17k+5` 网格（见 6.1）。124 帧 ≈ 5.17 s；训练覆盖 ~124–362 帧，更长未验证 | `124` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `LATENT` | — | `NestedTensor`，内部两个张量：画面 `[B,24,T_lat,H/16,W/16]` + 音频 `[B,32,2,T40]` |

#### 源码要点

```python
def align_frame_count(n):
    while n % 17 != 5:
        n += 1
    return n

def video_latent_t(frame_count):
    return 2 if frame_count <= 5 else ((frame_count - 5) // 17) * 5 + 2
```

- `align_frame_count` 是**向上**吸附：填 125 → 实际 133；填 124 → 124（已经合规）。
- `video_latent_t`：`frame_count ≤ 5` 时 latent 时间维恒为 2，否则 `(n-5)//17*5 + 2`。
- 音频 latent 长度 = `round(帧数 / 24 * 40)`，即 40 Hz 采样。124 帧 → 207。
- 两个张量都建在 `intermediate_device()` 上（通常是 CPU），不占显存。

#### 什么时候用它而不是 `MiniMaxH3ImageToVideo`

| 场景 | 用哪个 |
|---|---|
| 纯文生视频，且不需要关键帧 | 两者都行；`ImageToVideo` 更省事（一次出 conditioning+latent） |
| 想手动控制 `CLIPTextEncode` / `ConditioningConcat` / 面积条件 | `EmptyMiniMaxH3LatentAV` |
| 想给同一份 latent 换不同提示词批量出图 | `EmptyMiniMaxH3LatentAV`（latent 可复用） |
| 需要首尾帧 | 必须 `MiniMaxH3ImageToVideo` |

#### Demo D1：纯文生视频（Empty latent + CLIPTextEncode）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "Qwen3-VL-32B-Instruct", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_audio_vae_bf16.safetensors"}},

  "10": {"class_type": "EmptyMiniMaxH3LatentAV",
         "inputs": {"width": 1344, "height": 768, "length": 124}},
  "11": {"class_type": "CLIPTextEncode",
         "inputs": {"text": "A lone fox trots across a snowfield at dawn, breath misting in the cold air, low camera angle.",
                    "clip": ["2", 0]}},

  "20": {"class_type": "BasicGuider",
         "inputs": {"model": ["1", 0], "conditioning": ["11", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 30, "denoise": 1.0}},
  "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1234567890}},
  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["10", 0]}},

  "30": {"class_type": "VAEDecode", "inputs": {"samples": ["24", 0], "vae": ["3", 0]}},
  "31": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["24", 0], "vae": ["4", 0]}},
  "32": {"class_type": "CreateVideo",
         "inputs": {"images": ["30", 0], "fps": 24, "audio": ["31", 0],
                    "bit_depth": "auto", "color_space": "sRGB", "codec": "none"}},
  "33": {"class_type": "SaveVideo", "inputs": {"video": ["32", 0], "filename_prefix": "h3/t2va_empty"}}
}
```

> 注意 `24` 号节点的输出：**槽 0 = 采样结果**（用来解码），**槽 1 = denoised_output**。别接错。
> `30` 和 `31` 吃的是**同一个** latent：画面走 `VAEDecode`（内部 `unbind()[0]`），声音走 `VAEDecodeAudio`（内部 `unbind()[-1]`）。

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 出图尺寸和填的 width/height 不一致 | 填了非 32 倍数 | 改成 32 的倍数 |
| 视频时长和预期不符 | `length` 被向上吸附到 17k+5 | 查 6.1 的帧数对照表 |
| 只有画面没有声音 | 漏了 `VAEDecodeAudio` | 两个解码节点都要接 |
| 声音和画面对不上 | `CreateVideo` 的 `fps` 填错 | H3 训练在 24 fps，填 `24` |

---

### 2.2 `MiniMaxH3ImageToVideo`

**界面显示名**：MiniMax H3 Image to Video
**分类**：`model/conditioning/minimax`
**源码**：`comfy_extras/nodes_minimax_h3.py:116-163`
**职责**：t2va（纯文生）与 fl2va（首帧 / 首尾帧）的主力节点，一次输出 conditioning + latent。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `clip` | CLIP | 必填 | — | **必须是 `CLIPLoader` 里 `type=minimax` 的 Qwen3-VL**，选错类型 conditioning 会直接崩 | `["2",0]` |
| `vae` | VAE | 必填 | — | 视频 VAE。只在接了 `first_frame` / `last_frame` 时才真正用到（编码关键帧） | `["3",0]` |
| `prompt` | STRING | 必填 | 多行，支持 dynamic prompts | 提示词。用 `ImageToVideo` 时不支持 `<Picture i>` 标签（那是 ref2va 的） | 见 Demo |
| `width` | INT | `1344` | 32 – 16384，步进 32 | 生成宽度 | `1344` |
| `height` | INT | `768` | 32 – 16384，步进 32 | 生成高度 | `768` |
| `length` | INT | `124` | 5 – 3600，步进 17 | 帧数（24 fps），向上吸附到 17k+5 | `124` |
| `first_frame` | IMAGE | 可选 | — | 首帧。**几何锚点**：直接拉伸到画布（`crop="disabled"`），不保持比例 | `["40",0]` |
| `last_frame` | IMAGE | 可选 | — | 尾帧。**跟随者**：保持比例的中心裁切（`crop="center"`） | `["41",0]` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `CONDITIONING` | positive | 已带 `minimax_keyframes`（若接了首尾帧） |
| 1 | `LATENT` | — | AV 联合 latent（与 `EmptyMiniMaxH3LatentAV` 同构） |

#### 源码要点：首帧与尾帧的缩放策略不同

```python
if first_frame is not None:
    img = _resize(first_frame[:1], width, height, "disabled")   # 硬拉伸
    keyframes.append({"resolved_frame_index": 0, "image": img})
if last_frame is not None:
    img = _resize(last_frame[:1], width, height, "center")      # 保比例中心裁切
    keyframes.append({"resolved_frame_index": frame_count - 1, "image": img})
```

- 首帧是**几何锚点**——它决定了整段视频的构图，所以允许变形去填满画布。
- 尾帧是**跟随者**——只提供"往哪走"的方向，所以保比例裁切，避免二次扭曲构图。
- 两者都只取 `[:1]`，即**只吃 batch 的第一张**，传多帧也只用第一帧。
- 关键帧只影响 DiT，**不会**传给 Qwen 文本编码器（`clip.tokenize` 只在 ref2va 里带图）。
- 关键帧的时间坐标：首帧 = `0`，尾帧 = `frame_count - 1`（吸附后的真实帧数，不是你填的 `length`）。

#### Demo D2：t2va（不接任何图）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "Qwen3-VL-32B-Instruct", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_audio_vae_bf16.safetensors"}},

  "10": {"class_type": "MiniMaxH3ImageToVideo",
         "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                    "prompt": "Close-up of a barista pouring latte art, steam rising, warm morning light through the window.",
                    "width": 1344, "height": 768, "length": 124}},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["10", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 30, "denoise": 1.0}},
  "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["10", 1]}},

  "30": {"class_type": "VAEDecode", "inputs": {"samples": ["24", 0], "vae": ["3", 0]}},
  "31": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["24", 0], "vae": ["4", 0]}},
  "32": {"class_type": "CreateVideo",
         "inputs": {"images": ["30", 0], "fps": 24, "audio": ["31", 0],
                    "bit_depth": "auto", "color_space": "sRGB", "codec": "none"}},
  "33": {"class_type": "SaveVideo", "inputs": {"video": ["32", 0], "filename_prefix": "h3/t2va"}}
}
```

#### Demo D3：fl2va（首尾帧）

只在 `10` 号节点上加两个输入，其余与 D2 完全相同：

```json
{
  "40": {"class_type": "LoadImage", "inputs": {"image": "h3_start.png"}},
  "41": {"class_type": "LoadImage", "inputs": {"image": "h3_end.png"}},

  "10": {"class_type": "MiniMaxH3ImageToVideo",
         "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                    "prompt": "The camera slowly pushes in as the seasons turn from winter to spring.",
                    "width": 1344, "height": 768, "length": 124,
                    "first_frame": ["40", 0], "last_frame": ["41", 0]}}
}
```

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动时报 conditioning 维度错 | `CLIPLoader.type` 选了 `qwen_image` 或其它 | 必须是 `minimax` |
| 首帧被压扁 / 拉伸 | 设计如此 | 预先把图裁成目标宽高比再喂 |
| 尾帧内容没出现在结尾 | 尾帧是"方向"不是"硬约束" | 提高步数或改用 `AddGuide` 硬钉 |
| 传了 10 张图只生效 1 张 | `[:1]` 只取首帧 | 多帧锚定改用 `MiniMaxH3AddGuide` |

---

### 2.3 `MiniMaxH3AddGuide`

**界面显示名**：Add Guide for MiniMax H3
**分类**：`model/conditioning/minimax`
**源码**：`comfy_extras/nodes_minimax_h3.py:166-240`
**职责**：在目标视频的**任意帧位置**钉一张图、一段视频片段、一条音轨，或"视频+音轨"。可串联多个。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `positive` | CONDITIONING | 必填 | — | 上游 conditioning（`ImageToVideo` 或上一个 `AddGuide` 的输出槽 0） | `["10",0]` |
| `vae` | VAE | 可选 | — | 视频 VAE。**接了 `image` 就必填**，否则报 `anchoring guide frames needs the vae input` | `["3",0]` |
| `audio_vae` | VAE | 可选 | — | 音频 VAE。**接了 `audio` 就必填**，否则报 `anchoring guide audio needs the audio_vae input` | `["4",0]` |
| `latent` | LATENT | 必填 | — | 必须是 H3 的 AV latent，节点会做 4 项校验（见下） | `["10",1]` |
| `image` | IMAGE | 可选 | — | 图或视频帧序列。`B<5` 帧按单图处理；`B≥5` 帧按片段处理并**向下**裁到 17k+5 | `["50",0]` |
| `audio` | AUDIO | 可选 | — | 从同一 `frame_idx` 开始钉的音轨，超出部分会被裁掉 | `["51",0]` |
| `frame_idx` | INT | `0` | -9999 – 9999 | 锚定的帧下标。**负数从结尾倒着数**（-1 = 最后一帧） | `0` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `CONDITIONING` | positive | 在原 conditioning 的 `minimax_keyframes` 列表尾部追加一条 |

#### 源码要点 1：latent 的四项校验

```python
if not samples.is_nested or len(samples.tensors) != 2 \
   or samples.tensors[0].ndim != 5 or samples.tensors[0].shape[1] != 24:
    raise ValueError("MiniMaxH3AddGuide expects a MiniMax H3 AV latent")
```

必须同时满足：① 是 `NestedTensor`；② 恰好 2 个张量；③ 画面张量是 5 维；④ 画面通道 = 24。
用普通 `EmptyLatentImage` 或 LTXV latent 接进来会直接这条报错。

#### 源码要点 2：片段长度向下裁

```python
guide_frames = image.shape[0]
if guide_frames < 5:
    guide_frames = 1          # 退化成单图
else:
    while guide_frames % 17 != 5:
        guide_frames -= 1    # 向下裁：100 -> 90
```

与 `EmptyMiniMaxH3LatentAV` 的**向上吸附**相反，这里**向下裁**。传 100 帧进去实际只钉 90 帧。

#### 源码要点 3：音轨锚点比画面锚点短

```python
max_rt = math.floor(samples.tensors[1].shape[-1] - FRAME_RESCALE * resolved_frame_index)
```

`FRAME_RESCALE = 5/3`。124 帧视频的音轨 latent 长度 207：

| frame_idx | max_rt（音频 latent 剩余） | 音轨可用 |
|---|---|---|
| 0 | 207 | ✅ |
| 60 | 207 - 100 = 107 | ✅ |
| 123 | 207 - 205 = 2 | ⚠️ 只剩 2 个 latent 帧 |
| 124 | 207 - 206.7 → 0 | ❌ 报 "past the end of the video's audio track" |

所以**画面能钉到最后一帧，音轨钉不到**——这是两条独立的报错分支，别混淆。

#### 源码要点 4：接这里的图对文本编码器不可见

`AddGuide` 只往 conditioning dict 里塞 `minimax_keyframes`，**不走 `clip.tokenize`**。
想在提示词里用 `<Picture 1>` 指代这张图，必须**同时**接到 `MiniMaxH3ReferenceToVideo` 的 `ref_images`。

#### Demo D4：单帧锚定（在第 0 帧钉一张图）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "Qwen3-VL-32B-Instruct", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_audio_vae_bf16.safetensors"}},

  "10": {"class_type": "MiniMaxH3ImageToVideo",
         "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                    "prompt": "The character turns her head and smiles.",
                    "width": 1344, "height": 768, "length": 124}},

  "50": {"class_type": "LoadImage", "inputs": {"image": "character_A.png"}},
  "51": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["10", 0], "vae": ["3", 0], "latent": ["10", 1],
                    "image": ["50", 0], "frame_idx": 0}},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["51", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 30, "denoise": 1.0}},
  "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": 7}},
  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["10", 1]}},

  "30": {"class_type": "VAEDecode", "inputs": {"samples": ["24", 0], "vae": ["3", 0]}},
  "31": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["24", 0], "vae": ["4", 0]}},
  "32": {"class_type": "CreateVideo",
         "inputs": {"images": ["30", 0], "fps": 24, "audio": ["31", 0],
                    "bit_depth": "auto", "color_space": "sRGB", "codec": "none"}},
  "33": {"class_type": "SaveVideo", "inputs": {"video": ["32", 0], "filename_prefix": "h3/guide_1frame"}}
}
```

#### Demo D5：双锚点 + 音轨（串联两个 AddGuide）

把 D4 的 `51` 换成下面这段（第 0 帧钉图，第 90 帧钉图+音轨）：

```json
{
  "50": {"class_type": "LoadImage", "inputs": {"image": "shot_A.png"}},
  "52": {"class_type": "LoadImage", "inputs": {"image": "shot_B.png"}},
  "53": {"class_type": "LoadAudio", "inputs": {"audio": "footsteps.mp3"}},

  "51": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["10", 0], "vae": ["3", 0], "latent": ["10", 1],
                    "image": ["50", 0], "frame_idx": 0}},
  "54": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["51", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
                    "latent": ["10", 1], "image": ["52", 0], "audio": ["53", 0],
                    "frame_idx": 90}}
}
```

再把 `20` 号 `BasicGuider` 的 conditioning 改接 `["54", 0]`。

> **串联顺序**：`AddGuide` 是往列表尾部 `append`，所以先串的先钉。两个锚点的 `frame_idx` 不需要有序，但建议按时间顺序串，便于阅读。

#### 常见坑

| 报错原文 | 原因 | 处理 |
|---|---|---|
| `expects a MiniMax H3 AV latent` | latent 不是 H3 的 AV 二元组 | 确认 latent 来自 `ImageToVideo` / `ReferenceToVideo` / `EmptyMiniMaxH3LatentAV` |
| `needs an image or an audio to anchor` | 两个可选输入都没接 | 至少接一个 |
| `anchoring guide frames needs the vae input` | 接了 image 没接 vae | 补 `vae` |
| `anchoring guide audio needs the audio_vae input` | 接了 audio 没接 audio_vae | 补 `audio_vae` |
| `frame_idx {n} is outside the video's {m} frames` | 单图锚点越界 | 检查 `frame_idx + 1 ≤ frame_count` |
| `a {g} frame guide clip at frame_idx {n} does not fit` | 片段锚点放不下 | 减小 `frame_idx` 或缩短片段 |
| `frame_idx {n} is past the end of the video's audio track` | 音轨锚点越界 | 见 6.3，音轨比画面短 |

---

### 2.4 `MiniMaxH3ReferenceToVideo`

**界面显示名**：MiniMax H3 Reference to Video
**分类**：`model/conditioning/minimax`
**源码**：`comfy_extras/nodes_minimax_h3.py:243-364`
**职责**：ref2va 全参考生成。图 / 视频 / 音频作为参考，提示词里用 `<Picture i>` / `<Video k>` / `<Audio j>` 指代。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `clip` | CLIP | 必填 | — | `type=minimax` 的 Qwen3-VL | `["2",0]` |
| `vae` | VAE | 可选 | — | 视频 VAE。不接则参考图/视频**只喂文本编码器**，不进 DiT（条件弱很多） | `["3",0]` |
| `audio_vae` | VAE | 可选 | — | 音频 VAE。不接则参考音频**只喂文本编码器** | `["4",0]` |
| `prompt` | STRING | 必填 | 多行，dynamic prompts | 用 `<Picture 1>` 等标签引用参考 | 见 Demo |
| `width` | INT | `1344` | 32 – 16384，步进 32 | 生成宽度 | `1344` |
| `height` | INT | `768` | 32 – 16384，步进 32 | 生成高度 | `768` |
| `length` | INT | `124` | 5 – 3600，步进 17 | 帧数，向上吸附 17k+5 | `124` |
| `ref_image_size` | COMBO | `match` | `match` / `max` | 见下方详解 | `match` |
| `ref_images` | Autogrow(IMAGE) | 可选 | `ref_image_1` … `ref_image_9`，**最多 9 张** | 参考图 | 见 Demo |
| `ref_videos` | Autogrow(IMAGE) | 可选 | `ref_video_1` … `ref_video_3`，**最多 3 段** | 参考视频帧序列 | 见 Demo |
| `ref_video_audios` | Autogrow(AUDIO) | 可选 | `ref_video_audio_1` … `ref_video_audio_3` | 与**同号**参考视频配套的音轨 | 见 Demo |
| `ref_audios` | Autogrow(AUDIO) | 可选 | `ref_audio_1` … `ref_audio_3`，**最多 3 条** | 独立参考音频 | 见 Demo |

#### `ref_image_size` 的两种策略

源码（`nodes_minimax_h3.py:301-307`）：

```python
if ref_image_size == "match":
    scale = min(1.0, math.sqrt((width * height) / (w * h)))   # 按生成面积等比缩（只缩不放）
else:  # "max"
    scale = min(1.0, REF_IMAGE_SHORT_EDGE / min(w, h))         # 短边 2048（只缩不放）
```

| 模式 | 参考图尺寸 | 代价 | 适用 |
|---|---|---|---|
| `match` | 缩到**与生成画面同像素面积**（如 1344×768 ≈ 103 万像素） | 快 | 参考"风格/色调/构图"，不追求人脸还原 |
| `max` | 短边拉到 **2048**（`REF_IMAGE_SHORT_EDGE = 2048`） | **慢好几倍** | 追求身份一致性（人物/商品） |

> 为什么 `max` 慢：参考 token 会**贯穿每一个采样步**（`cond` 段跑 `max(t, 0.999)`，永不去噪），
> token 数随参考面积线性涨，且每步都重算。

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `CONDITIONING` | positive | 带 `minimax_refs`（若接了 vae/audio_vae） |
| 1 | `LATENT` | — | AV 联合 latent |

#### 源码要点 1：参考的呈现顺序是固定的

```python
# ref_items 顺序：图 → (视频音轨, 视频) → 独立音频
```

- 所有**图**先排，编号 `<Picture 1>` … `<Picture 9>`（1-based）
- 然后**视频**：每个视频的**音轨标签 `<Audio j>` 排在它自己的 `<Video k>` 之前**
- 最后**独立音频**：`<Audio j>`

所以 1 图 + 1 带音轨视频 + 1 独立音频 = `<Picture 1>`、`<Audio 1>`、`<Video 1>`、`<Audio 2>`。
**编号不是你连接的顺序，是类型分组后的顺序。**

#### 源码要点 2：Qwen 看视频是 2 fps

```python
sample_idx = list(range(0, frames.shape[0], FPS // 2))   # FPS=24 -> 每 12 帧取 1
qwen_frames = frames[sample_idx]
ref_items.append({"type": "video", "data": qwen_frames,
                  "timestamps": [i / 2.0 for i in range(len(sample_idx))]})
```

Qwen 文本编码器以 **2 fps** 看参考视频并带时间戳；但喂给 DiT 的 latent 用的是**完整帧率**。

#### 源码要点 3：视频参考的画板是"768 短边 + 面积上限"

```python
cw, ch = adapt_canvas(vw, vh)        # 768 短边、768*1344 面积上限、逐轴 32 取整
if vw * vh < cw * ch:                # 源比画板还小，就用源尺寸
    cw, ch = round32(vw), round32(vh)
```

与 `ref_image_size` 无关，参考**视频**走的是另一套 `adapt_canvas` 逻辑。

#### 源码要点 4：视频参考至少 5 帧

```python
if n < 5:
    raise ValueError("MiniMax H3 reference videos need at least 5 frames (~0.2s at 24 fps)")
```

且同样会**向下裁**到 17k+5；超过 `frame_count` 的部分直接截掉。

#### Demo D6：全参考（1 图 + 1 带音轨视频 + 1 独立音频）

> ⚠️ **Autogrow 输入的 API 键名规则**：写成 `"父键名.子键名"`。
> 例如 `ref_images` 的第一张图，键是 **`ref_images.ref_image_1`**，不是 `ref_image_1`。

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_ref2va_bf16.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "Qwen3-VL-32B-Instruct", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_audio_vae_bf16.safetensors"}},

  "60": {"class_type": "LoadImage", "inputs": {"image": "actor_face.png"}},
  "61": {"class_type": "LoadVideo", "inputs": {"file": "dance_ref.mp4"}},
  "62": {"class_type": "GetVideoComponents", "inputs": {"video": ["61", 0]}},
  "63": {"class_type": "LoadAudio", "inputs": {"audio": "bgm.wav"}},

  "10": {"class_type": "MiniMaxH3ReferenceToVideo",
         "inputs": {
           "clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
           "prompt": "<Picture 1> dances with the choreography of <Video 1>, to the rhythm of <Audio 2>, spotlight stage.",
           "width": 1344, "height": 768, "length": 124,
           "ref_image_size": "match",
           "ref_images.ref_image_1": ["60", 0],
           "ref_videos.ref_video_1": ["62", 0],
           "ref_video_audios.ref_video_audio_1": ["62", 1],
           "ref_audios.ref_audio_1": ["63", 0]
         }},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["10", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 35, "denoise": 1.0}},
  "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": 2024}},
  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["10", 1]}},

  "30": {"class_type": "VAEDecode", "inputs": {"samples": ["24", 0], "vae": ["3", 0]}},
  "31": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["24", 0], "vae": ["4", 0]}},
  "32": {"class_type": "CreateVideo",
         "inputs": {"images": ["30", 0], "fps": 24, "audio": ["31", 0],
                    "bit_depth": "auto", "color_space": "sRGB", "codec": "none"}},
  "33": {"class_type": "SaveVideo", "inputs": {"video": ["32", 0], "filename_prefix": "h3/ref2va_full"}}
}
```

> `GetVideoComponents` 的输出：槽 0 = `IMAGE`（帧），槽 1 = `AUDIO`（音轨）。
> 用它把视频拆成"帧序列 + 音轨"，正好对应 `ref_video_1` 和 `ref_video_audio_1`。
>
> ⚠️ `LoadVideo` 不重采样，帧序列就是源文件的全部帧。源视频不是 24 fps 时建议先用
> `Video Slice` / `VideoTrim` 裁到 2–15 s 再喂；节点内部会按 `frame_count`（124 帧）截断超长部分。

#### Demo D6b：只做身份一致的图参考（`ref_image_size = max`）

```json
{
  "10": {"class_type": "MiniMaxH3ReferenceToVideo",
         "inputs": {
           "clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
           "prompt": "<Picture 1> walks through a rainy neon street at night, handheld camera.",
           "width": 1344, "height": 768, "length": 124,
           "ref_image_size": "max",
           "ref_images.ref_image_1": ["60", 0],
           "ref_images.ref_image_2": ["64", 0]
         }}
}
```

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 标签指代错对象 | 编号是"类型分组后"的顺序，不是连线顺序 | 按 2.4 的顺序规则重排标签 |
| `<Video 1>` 被当成图 | 视频参考至少要 5 帧，少于 5 帧会报错不会降级 | 补帧或改走 `AddGuide` |
| 参考图完全不起作用 | 没接 `vae` | 接上 `vae`（不接则只喂文本编码器） |
| 音频参考不起作用 | 没接 `audio_vae` | 接上 `audio_vae` |
| 慢得离谱 | `ref_image_size="max"` 且参考很多 | 改 `match`，或减少参考数量 |
| 参考视频音轨没生效 | `ref_video_audio_N` 必须和 `ref_video_N` **同号** | 对齐下标 |

---

### 2.5 `MiniMaxH3SigmaShift`

**界面显示名**：**ModelSamplingMiniMaxH3**
**分类**：`model/patch/minimax`
**搜索别名**：`sigma shift`、`minimax shift`
**源码**：`comfy_extras/nodes_minimax_h3.py:367-408`
**职责**：同时设置画面流与音频流的 shift。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | 必填 | — | 要打补丁的模型（一般接 `UNETLoader` 出来、可能已经过 LoRA 的 MODEL） | `["1",0]` |
| `shift_video` | FLOAT | `12.0` | 0.01 – 100.0，步进 0.01 | 画面流的 flow shift | `10.0` |
| `shift_audio` | FLOAT | `3.0` | 0.01 – 100.0，步进 0.01 | 音频流的 flow shift | `3.0` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `MODEL` | — | 打了 `model_sampling` 补丁 + `transformer_options` 参数的模型 |

#### 源码要点

```python
class ModelSamplingAdvanced(comfy.model_sampling.ModelSamplingAV, comfy.model_sampling.CONST):
    pass

model_sampling = ModelSamplingAdvanced(model.model.model_config)
model_sampling.set_parameters(shift=shift_video, audio_shift=shift_audio)
if hasattr(original, "noise_scale"):
    model_sampling.set_noise_scale(original.noise_scale)
m.add_object_patch("model_sampling", model_sampling)

to["minimax_h3_sigma_shift_video"] = shift_video
to["minimax_h3_sigma_shift_audio"] = shift_audio
```

做了两件事：
1. 换 `model_sampling` 为 `ModelSamplingAV + CONST`，影响采样器的 sigma 序列；
2. 往 `transformer_options` 里塞两个值，DiT 会**反推**画面 schedule 到共享基础网格，再从中推导出音频 schedule。

**关键点：默认工作流不需要这个节点。**
`comfy/supported_models.py` 里 `MiniMaxH3.sampling_settings = {"shift": 12.0, "audio_shift": 3.0}`，
模型加载时就已经设好了，与上游 `model_index.json` 的 `sigma_shift_scales` 完全一致。

| 场景 | 是否需要该节点 | 取值 |
|---|---|---|
| 常规 t2va / fl2va / ref2va | ❌ 不需要 | — |
| FastH3 加速采样 | ✅ 需要 | `10.0` / `3.0` |
| 想手动微调画面噪声分配 | ✅ 可选 | 见下 |

#### shift 的直觉

| shift_video | 效果 |
|---|---|
| 偏小（如 6） | 前期步子小，细节打磨多；画面偏"精修"，但可能过饱和 |
| 12（默认） | 官方平衡值 |
| 偏大（如 20） | 前期步子大，构图变化剧烈；容易出大动态但细节会糊 |

`shift_audio` 建议保持 `3.0`，改动会明显影响音频清晰度。

#### Demo D7：FastH3 加速（shift 10 + 8 步 + Turbo LoRA）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "LoraLoaderModelOnly",
        "inputs": {"model": ["1", 0], "lora_name": "fl2v_turbo_8step.safetensors", "strength_model": 1.0}},

  "70": {"class_type": "MiniMaxH3SigmaShift",
         "inputs": {"model": ["2", 0], "shift_video": 10.0, "shift_audio": 3.0}},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["70", 0], "conditioning": ["10", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["70", 0], "scheduler": "simple", "steps": 8, "denoise": 1.0}}
}
```

> `BasicScheduler` 的 `model` 要接**打过补丁的** MODEL（`70` 号），否则 sigma 序列不会跟着变。

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 加了节点反而变差 | 默认值已经是最优，重复设置成了别的数 | 删掉节点，或填 `12.0` / `3.0` |
| 加了 shift 但速度没变 | `BasicScheduler` 还接在原始 MODEL 上 | 改接补丁后的 MODEL |
| Turbo LoRA 用了错的文件 | I2V 用 `fl2v_turbo_8step`，Multiframe/FunCN 用 `ref2v_turbo_4step_v0.1` | 按任务选 |

---

### 2.6 `MiniMaxH3FunControlNetApply`

**界面显示名**：Apply MiniMax H3 Fun ControlNet
**分类**：`model/patch/minimax`
**搜索别名**：`minimax controlnet`、`h3 controlnet`、`video inpaint controlnet`
**源码**：`comfy_extras/nodes_minimax_h3.py:579-621`（补丁类 `411-576`）
**职责**：把 Fun ControlNet 挂到模型上。一个 checkpoint 通吃 Canny / Depth / HED / MLSD / Pose。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | 必填 | — | 基座模型 | `["1",0]` |
| `model_patch` | MODEL_PATCH | 必填 | — | 来自 `ModelPatchLoader`（目录 `models/model_patches/`） | `["80",0]` |
| `vae` | VAE | 必填 | — | 视频 VAE，用来编码控制视频和源视频 | `["3",0]` |
| `strength` | FLOAT | `1.0` | 0.0 – 10.0，步进 0.01 | 控制强度（残差叠加的 alpha）。**填 0 直接返回原模型** | `1.0` |
| `start_percent` | FLOAT | `0.0` | 0.0 – 1.0，步进 0.001（高级） | 从哪个采样进度开始生效 | `0.0` |
| `end_percent` | FLOAT | `1.0` | 0.0 – 1.0，步进 0.001（高级） | 到哪个采样进度结束 | `1.0` |
| `control_video` | IMAGE | 可选 | — | 控制信号（Canny 图 / 深度图 / 骨架图…） | `["81",0]` |
| `mask` | MASK | 可选 | — | **1 = 要重新生成的区域**（注意不是"保留区"） | `["82",1]` |
| `source_video` | IMAGE | 可选 | — | mask 背后的原视频。**只有接了 `mask` 才会被读取** | `["83",0]` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `MODEL` | — | 挂了控制网补丁的 MODEL |

#### 源码要点 1：`control_video` 与 `mask` 都为空时直接放行

```python
if strength == 0 or (control_video is None and mask is None):
    return io.NodeOutput(model)
```

`strength=0` 或两个条件输入都没接 → 原样返回，不产生开销。

#### 源码要点 2：`control_in_dim = 49` 的构成

```python
hint = torch.cat([hint, visibility_latent, masked_latent], dim=1)
#                 24          1                  24
```

| 成分 | 通道 | 来源 |
|---|---|---|
| 控制视频 latent | 24 | `control_video` 经 VAE 编码 |
| 可见度图 | 1 | `visibility = 1 - (mask > 0.5)`，三线性插值到 latent 时空尺寸 |
| 遮罩后的源 latent | 24 | `source_video * visibility`（+ ImageNet 均值灰，若启用 `inpaint_post_norm`） |

不全接也没关系：只接 `control_video` 时后两项不拼；只接 `mask` 时 `hint` 填零。

#### 源码要点 3：mask 语义是反的

```python
visibility = 1.0 - (mask > 0.5).to(torch.float32)
```

你在 UI 里画**白色（1）** = 要重画的洞。如果你习惯"白=保留"，结果会整段反过来。

#### 源码要点 4：帧数不匹配时的行为

```python
indices = torch.arange(frame_count, device=frames.device).clamp(max=frames.shape[0] - 1)
```

| 情况 | 行为 |
|---|---|
| 控制视频比目标长 | 截掉后面多余的 |
| 控制视频比目标短 | **定格最后一帧**（`clamp` 的效果，不是补黑也不是循环） |

空间上用 `bilinear + center crop` 对齐。

#### 源码要点 5：音频不受控制

```python
skip[args["layout"].audio_pos.to(skip.device)] = 0
```

控制残差在音频位置被强制清零。**只管画面**，音频照常由模型自由生成。

#### 源码要点 6：注入层

```python
for block_index in self.model_patch.model.injection_layers:
```

`injection_layers` 优先读 checkpoint metadata 里的 `control_blocks_places`，
否则用 `range(0, 50, 50 // num_blocks)`：v1（5 块）→ `0,10,20,30,40`；v2（10 块）→ 每 5 层。

#### 源码要点 7：adaLN 宽度不匹配直接报错

pruned 基座 **必须**配 pruned 控制网（反之亦然）。adaLN 是 curve basis 还是 full 不一致时抛 `RuntimeError`，
报错信息会直接告诉你是哪种不匹配。

#### Demo D8：Canny 控制（结构控制）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
  "80": {"class_type": "ModelPatchLoader",
         "inputs": {"name": "minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors"}},

  "81": {"class_type": "LoadVideo", "inputs": {"file": "source.mp4"}},
  "84": {"class_type": "GetVideoComponents", "inputs": {"video": ["81", 0]}},
  "85": {"class_type": "Canny",
         "inputs": {"image": ["84", 0], "low_threshold": 0.4, "high_threshold": 0.8}},

  "86": {"class_type": "MiniMaxH3FunControlNetApply",
         "inputs": {"model": ["1", 0], "model_patch": ["80", 0], "vae": ["3", 0],
                    "strength": 1.0, "start_percent": 0.0, "end_percent": 1.0,
                    "control_video": ["85", 0]}},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["86", 0], "conditioning": ["10", 0]}},
  "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
  "22": {"class_type": "BasicScheduler",
         "inputs": {"model": ["86", 0], "scheduler": "simple", "steps": 30, "denoise": 1.0}},
  "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": 99}},
  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["10", 1]}}
}
```

#### Demo D9：视频 inpainting（mask + source_video）

```json
{
  "83": {"class_type": "LoadVideo", "inputs": {"file": "source.mp4"}},
  "87": {"class_type": "GetVideoComponents", "inputs": {"video": ["83", 0]}},
  "88": {"class_type": "LoadImageMask", "inputs": {"image": "hole_mask.png", "channel": "alpha"}},

  "86": {"class_type": "MiniMaxH3FunControlNetApply",
         "inputs": {"model": ["1", 0], "model_patch": ["80", 0], "vae": ["3", 0],
                    "strength": 1.0, "start_percent": 0.0, "end_percent": 1.0,
                    "mask": ["88", 0], "source_video": ["87", 0]}}
}
```

> `LoadImageMask` 只有一个输出槽（0 = `MASK`，`nodes.py:1841` 的 `RETURN_TYPES = ("MASK",)`）。
> 若改用 `LoadImage` 取 alpha 当遮罩，mask 在**槽 1**（`LoadImage` 是 `IMAGE`(0) / `MASK`(1)）——两者槽位不同，别照抄。

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `RuntimeError` 提到 adaLN / curve basis | pruned 与非 pruned 混用 | 基座和控制网必须同为 pruned 或同为完整 |
| 控制完全没效果 | `strength=0` 或 `control_video`/`mask` 都没接 | 检查这两个短路条件 |
| 洞的位置反了 | mask 语义是 1=重绘 | 反转 mask |
| 控制视频短导致后半段静止 | 短的会定格末帧 | 补齐帧数或接受 |
| `inpaint_post_norm` 的洞是中灰不是黑 | 设计如此（VAE 把中灰归一化到 0） | 正常现象 |
| 音频被控制网影响 | 不会，`skip[audio_pos]=0` | 无需处理 |

---

## 3. B 层：为 H3 开了专用分支的通用节点

---

### 3.1 `LTXVSeparateAVLatent`

**界面显示名**：Separate AV Latent
**分类**：`model/latent/ltxv`
**源码**：`comfy_extras/nodes_lt.py:974-987`
**描述原文**："Split a joint AV latent into its video and audio latents (any AV model, e.g. LTXV or MiniMax H3)."

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `av_latent` | LATENT | 必填 | — | H3 的 AV 联合 latent（NestedTensor 二元组） | `["10",1]` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `LATENT` | video_latent | 画面 latent `[B,24,T,H/16,W/16]` |
| 1 | `LATENT` | audio_latent | 音频 latent `[B,32,2,T40]` |

#### 用途

把联合 latent 拆开后，可以：
- 单独对画面 latent 做 `SetLatentNoiseMask`（见 D10）
- 单独上采样 / 裁剪其中一路
- 单独送入不同的 VAE

#### Demo D10：只用 SetLatentNoiseMask 做遮罩重绘（不需要控制网）

```json
{
  "10": {"class_type": "MiniMaxH3ImageToVideo",
         "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                    "prompt": "Replace the sky with a swirling aurora.",
                    "width": 1344, "height": 768, "length": 124,
                    "first_frame": ["40", 0]}},

  "90": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["10", 1]}},
  "91": {"class_type": "LoadImageMask", "inputs": {"image": "sky_mask.png", "channel": "alpha"}},
  "92": {"class_type": "SetLatentNoiseMask",
         "inputs": {"samples": ["90", 0], "mask": ["91", 0]}},
  "93": {"class_type": "LTXVConcatAVLatent",
         "inputs": {"video_latent": ["92", 0], "audio_latent": ["90", 1]}},

  "24": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["23", 0], "guider": ["20", 0], "sampler": ["21", 0],
                    "sigmas": ["22", 0], "latent_image": ["93", 0]}}
}
```

> 这条链路 **完全不需要 Fun ControlNet**。原理是 `scale_latent_inpaint` 按 0.999 给保留行注入噪声把钉住，
> 只有遮罩区域真正参与去噪。

---

### 3.2 `LTXVConcatAVLatent`

**界面显示名**：Concat AV Latent
**分类**：`model/latent/ltxv`
**源码**：`comfy_extras/nodes_lt.py:896-973`

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `video_latent` | LATENT | 必填 | — | 画面 latent | `["92",0]` |
| `audio_latent` | LATENT | 必填 | — | 音频 latent | `["90",1]` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `LATENT` | latent | 合并后的 AV 联合 latent |

#### 源码要点：`fit_audio` 的补齐规则

```python
if audio.shape[dim] > length:
    audio = audio.narrow(dim, 0, length)        # 长的截掉
else:
    # 短的补零，且补的尾部【不加 mask】——让模型去生成它
```

音频比画面短时，尾部补零**且不加噪声遮罩**，交给模型自由生成——这正是"短音频配长视频"该有的行为。

---

### 3.3 `BlockSparseAttention`

**界面显示名**：Model Sparse Attention
**分类**：`model/patch`（`is_experimental=True`）
**搜索别名**：Block Sparse Attention
**源码**：`comfy_extras/nodes_sparse_attention.py:352-415`
**与 H3 的关系**：`sink_conditioning` 参数整条 tooltip 只讲 MiniMax-H3；H3 走的是 block patches 路径（chunked qkv producer），其它模型走 attention override。

#### 输入参数

| 参数 | 类型 | 默认值 | 范围 / 可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | 必填 | — | 要打补丁的模型 | `["1",0]` |
| `selection` | DynamicCombo | — | `sol-attn` / `sla` / `vsa` | 稀疏块选择方法 | `vsa` |
| `selection.tau` | FLOAT | `1.3` | 0.0 – 4.0，步进 0.05 | 仅 `sol-attn`。分数分布的 sigma 阈值：1.0 保留 ~16%，1.5 ~7%，2.0 ~2.7% | — |
| `selection.keep_percent` | FLOAT | `10.0` | 0.5 – 95.0，步进 0.5 | 仅 `sla`/`vsa`。每个 query 块保留的 key 块百分比 | `10.0` |
| `start_percent` | FLOAT | `0.2` | 0.0 – 1.0，步进 0.01 | 从哪个采样进度开始用稀疏 | `0.2` |
| `end_percent` | FLOAT | `1.0` | 0.0 – 1.0，步进 0.01 | 到哪个进度恢复稠密 | `1.0` |
| `dense_blocks` | STRING | `""` | 如 `"0, 1, 47-49"`（高级） | 始终跑稠密的 transformer 块 | `""` |
| `min_tokens` | INT | `12288` | 0 – 1048576，步进 512（高级） | 序列短于此值就保持稠密 | `12288` |
| `extra_tokens` | INT | `256` | 0 – 256，步进 64（高级） | 每块额外关注的 top token 数；256 推荐，0 关闭；**VSA 忽略此项** | `256` |
| `sink_conditioning` | COMBO | `exact_kv_and_rows` | `exact_kv` / `exact_kv_and_rows` / `off`（高级） | **H3 专用**，见下 | `exact_kv_and_rows` |
| `verbose` | BOOLEAN | `False` | True/False（高级） | 日志打印每层到底用了稀疏还是稠密、为什么 | `True` |

#### 输出槽位

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | `MODEL` | — | 打了块稀疏注意力补丁的 MODEL |

#### `sink_conditioning` 三档（H3 专用）

| 档位 | 行为 | 开销 |
|---|---|---|
| `exact_kv` | 每个 query 都精确 attend 打包前缀（文本/音频/参考行） | ~3% |
| `exact_kv_and_rows` | 在上述基础上，额外让**目标音频**的 query 行跑稠密 | 略高，但保住生成的音频 |
| `off` | 不做保护 | 0，但可能掉质量 |

#### 源码要点

```python
def sinks(self, transformer_options, tokens):
    layout = transformer_options.get("minimax_h3_layout")
    if self.sink_conditioning == "off" or layout is None or layout.seq_len != tokens:
        return (0, 0), (0, 0)
    ...
    blocks = (0, (video[0] + BLOCK_SIZE - 1) // BLOCK_SIZE)
```

保护区间 = 打包序列里 video 段**之前**的所有内容（即文本 + 参考 + 关键帧 + 目标音频），按 64 的 block size 向上取整。

#### Demo D11：H3 加速（VSA）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_bf16.safetensors", "weight_dtype": "default"}},

  "95": {"class_type": "BlockSparseAttention",
         "inputs": {"model": ["1", 0],
                    "selection": "vsa",
                    "selection.keep_percent": 10.0,
                    "start_percent": 0.2, "end_percent": 1.0,
                    "dense_blocks": "", "min_tokens": 12288,
                    "extra_tokens": 256,
                    "sink_conditioning": "exact_kv_and_rows",
                    "verbose": true}},

  "20": {"class_type": "BasicGuider", "inputs": {"model": ["95", 0], "conditioning": ["10", 0]}}
}
```

> DynamicCombo 在 API 里的写法：主值 `"selection": "vsa"`，子参数 `"selection.keep_percent": 10.0`。

#### 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 开了没加速 | 序列长度低于 `min_tokens`（默认 12288） | 调大分辨率/帧数，或调小 `min_tokens` |
| VSA 报错说缺 `to_gate_compress` | VSA 需要 FastH3 权重 | 换 `sla` 或 `sol-attn` |
| 音频变糊 | 用了 `exact_kv` 或 `off` | 改 `exact_kv_and_rows` |
| 需要 comfy_kitchen | 该节点依赖 `comfy_kitchen` 包 | 装依赖，否则节点不可用 |

---

## 4. C 层：配套通用节点速查表

### 4.1 加载类

| 节点 ID | 显示名 | 关键输入 | 输出 | 与 H3 相关的注意事项 |
|---|---|---|---|---|
| `UNETLoader` | Load Diffusion Model | `unet_name`, `weight_dtype`(`default`/`fp8_e4m3fn`/`fp8_e4m3fn_fast`/`fp8_e5m2`) | `MODEL` | 读 `models/diffusion_models/`。H3 是 bf16 原生，fp8 会掉质量 |
| `CLIPLoader` | Load CLIP | `clip_name`, `type`, `device`(`default`/`cpu`) | `CLIP` | **`type` 必须选 `minimax`**，第一大坑 |
| `VAELoader` | Load VAE | `vae_name` | `VAE` | 视频 VAE 和音频 VAE 都用它，靠文件名区分 |
| `ModelPatchLoader` | Load Model Patch | `name` | `MODEL_PATCH` | 读 `models/model_patches/`；`EXPERIMENTAL=True`，需在设置里打开实验节点显示 |
| `LoraLoaderModelOnly` | Load LoRA (model only) | `model`, `lora_name`, `strength_model` | `MODEL` | Turbo LoRA 走这个；H3 不需要 CLIP 侧 LoRA |
| `LoadImage` | Load Image | `image` | `IMAGE`(0), `MASK`(1) | 首帧/尾帧/遮罩来源 |
| `LoadImageMask` | Load Image Mask | `image`, `channel`(`alpha`/`red`/`green`/`blue`) | `MASK`(0) —— **只有一个输出** | `nodes.py:1824`；与 `LoadImage` 不同，它没有 IMAGE 槽 |
| `LoadVideo` | Load Video | `file` | `VIDEO` | `nodes_video.py:348`；**没有** `force_rate`/`force_size`，配 `GetVideoComponents` 拆帧 |
| `LoadAudio` | Load Audio | `audio` | `AUDIO` | `nodes_audio.py:366` |

### 4.2 采样类

| 节点 ID | 显示名 | 输入（按槽位顺序） | 输出 |
|---|---|---|---|
| `RandomNoise` | RandomNoise | `noise_seed` | `NOISE` |
| `BasicGuider` | Basic Guider | `model`, `conditioning` | `GUIDER` |
| `KSamplerSelect` | KSamplerSelect | `sampler_name` | `SAMPLER` |
| `BasicScheduler` | BasicScheduler | `model`, `scheduler`, `steps`, `denoise` | `SIGMAS` |
| `SamplerCustomAdvanced` | SamplerCustomAdvanced | `noise`, `guider`, `sampler`, `sigmas`, `latent_image` | `LATENT`(0 输出), `LATENT`(1 denoised) |

> H3 推荐：`sampler_name=euler`、`scheduler=simple`、`steps=30`（Turbo 时 8）。
> `BasicScheduler` 的 `model` 要接**最终** MODEL（含 shift 补丁 / 控制网 / LoRA）。

### 4.3 解码与输出类

| 节点 ID | 显示名 | 输入 | 输出 | 说明 |
|---|---|---|---|---|
| `VAEDecode` | VAE Decode | `samples`, `vae` | `IMAGE` | 内部取 `unbind()[0]` —— **画面** |
| `VAEDecodeAudio` | VAE Decode Audio | `samples`, `vae` | `AUDIO` | 内部取 `unbind()[-1]` —— **音频** |
| `CreateVideo` | Create Video | `images`, `fps`, `audio`, `bit_depth`, `color_space`, `codec` | `VIDEO` | `fps` 填 **24**；`codec=none` 留给 `SaveVideo` 决定 |
| `SaveVideo` | Save Video | `video`, `filename_prefix`, `format` | — | 输出节点 |

### 4.4 遮罩与预处理类

| 节点 ID | 显示名 | 输入 | 输出 | 用途 |
|---|---|---|---|---|
| `SetLatentNoiseMask` | Set Latent Noise Mask | `samples`, `mask` | `LATENT` | 机制 B 的遮罩重绘（无需控制网） |
| `Canny` | Detect Edges (Canny) | `image`, `low_threshold`, `high_threshold` | `IMAGE` | **阈值是 0.01–0.99 归一化浮点**，默认 0.4 / 0.8，不是像素值 |
| `GetVideoComponents` | Get Video Components | `video` | `IMAGE`(0), `AUDIO`(1), `FLOAT`(2 fps), `COMBO`(3 bit_depth), `COMBO`(4 color_space) | 拆视频成帧+音轨 |

---

## 5. 完整 Demo 索引

| Demo | 场景 | 主角节点 | 关键参数 |
|---|---|---|---|
| D1 | 纯文生视频（Empty latent） | `EmptyMiniMaxH3LatentAV` + `CLIPTextEncode` | 1344×768, 124 帧, 30 步 |
| D2 | t2va | `MiniMaxH3ImageToVideo` | 无图 |
| D3 | fl2va 首尾帧 | `MiniMaxH3ImageToVideo` | `first_frame` + `last_frame` |
| D4 | 单帧锚定 | `MiniMaxH3AddGuide` | `frame_idx=0` |
| D5 | 双锚点 + 音轨 | `MiniMaxH3AddGuide` ×2 | `frame_idx=0` 与 `90` |
| D6 | 全参考 ref2va | `MiniMaxH3ReferenceToVideo` | 1 图 + 1 带音轨视频 + 1 独立音频 |
| D6b | 身份一致的图参考 | `MiniMaxH3ReferenceToVideo` | `ref_image_size=max` |
| D7 | FastH3 加速 | `MiniMaxH3SigmaShift` | 10.0 / 3.0 + `fl2v_turbo_8step` + 8 步 |
| D8 | Canny 结构控制 | `MiniMaxH3FunControlNetApply` | `control_video` |
| D9 | 视频 inpainting | `MiniMaxH3FunControlNetApply` | `mask` + `source_video` |
| D10 | 纯遮罩重绘（无控制网） | `LTXVSeparateAVLatent` + `SetLatentNoiseMask` | 机制 B |
| D11 | VSA 稀疏加速 | `BlockSparseAttention` | `selection=vsa`, `keep_percent=10` |

> 所有 demo 的公共加载链（节点 1–4）与采样链（20–24）见 D1，其它 demo 只列差异部分。

---

## 6. 参数联动速查

### 6.1 帧数网格：17k + 5

`FRAME_PER_TOKEN = (1,4,4,4,4)` → 一个周期 1+4×4 = **17** 帧，初始锚 5 帧。
合法帧数满足 `n ≡ 5 (mod 17)`。

| 你填 `length` | 实际帧数 | 时长 @24fps | latent 时间维 T | 音频 latent 长度 |
|---|---|---|---|---|
| 5 | 5 | 0.21 s | 2 | 8 |
| 22 | 22 | 0.92 s | 7 | 37 |
| 39 | 39 | 1.63 s | 12 | 65 |
| 56 | 56 | 2.33 s | 17 | 93 |
| 73 | 73 | 3.04 s | 22 | 122 |
| 90 | 90 | 3.75 s | 27 | 150 |
| 107 | 107 | 4.46 s | 32 | 178 |
| **124** | **124** | **5.17 s** | **37** | **207** |
| 141 | 141 | 5.88 s | 42 | 235 |
| 158 | 158 | 6.58 s | 47 | 263 |
| 175 | 175 | 7.29 s | 52 | 292 |
| 226 | 226 | 9.42 s | 67 | 377 |
| 293 | 293 | 12.21 s | 87 | 488 |
| 362 | 362 | 15.08 s | 107 | 603 |

- 训练覆盖约 **124 – 362 帧**，超出未验证。
- `EmptyMiniMaxH3LatentAV` / `ImageToVideo` / `ReferenceToVideo` 都是**向上**吸附。
- `AddGuide` 的片段长度是**向下**裁。

秒转帧公式（蓝图里用 `ComfyMathExpression`）：
```
max(5, round(a*24)) + (5 - (max(5, round(a*24)) % 17)) % 17
```

### 6.2 尺寸

| 约束 | 值 | 来源 |
|---|---|---|
| 宽度/高度步进 | 32 | `CANVAS_MULTIPLE = 32` |
| 推荐基准短边 | 768 | `BASE_SHORT_EDGE = 768` |
| 面积上限 | 768 × 1344 = 1,032,192 | `MAX_PIXELS` |
| 参考图 `max` 模式短边 | 2048 | `REF_IMAGE_SHORT_EDGE = 2048` |

### 6.3 音轨锚点上限

```
max_rt = floor(audio_T - 5/3 * frame_idx)
```

124 帧（audio_T=207）时：

| frame_idx | 可用音频 latent 帧 |
|---|---|
| 0 | 207 |
| 30 | 157 |
| 60 | 107 |
| 90 | 57 |
| 120 | 7 |
| 123 | 2 |
| 124 | 0 → 报错 |

### 6.4 shift 对照

| 场景 | shift_video | shift_audio | 是否需要节点 |
|---|---|---|---|
| 默认（模型自带） | 12.0 | 3.0 | ❌ |
| FastH3 | 10.0 | 3.0 | ✅ |
| 自定义 | 0.01 – 100 任意 | 建议 3.0 | ✅ |

### 6.5 序列行数账本（1344×768, 124 帧）

| 项 | 计算 | 行数 |
|---|---|---|
| 每帧 patch 行 | (1344/32) × (768/32) = 42 × 24 | 1,008 |
| latent 时间维 | `(124-5)//17*5 + 2` | 37 |
| 画面总行 | 1008 × 37 | 37,296 |
| 音频总行 | 2 × 207 | 414 |
| **合计（不含文本）** | | **≈ 37,710** |

**每多钉一帧关键帧，就多 1008 × vt 行。** 这是拿序列长度换控制力——序列越长，`min_tokens=12288` 的稀疏阈值越容易触发。

---

## 7. 报错对照表

| 报错原文（关键字） | 出自节点 | 原因 | 处理 |
|---|---|---|---|
| `expects a MiniMax H3 AV latent` | AddGuide | latent 不是 AV 二元组 | 用 H3 自己的 latent |
| `needs an image or an audio to anchor` | AddGuide | 两个可选输入都空 | 至少接一个 |
| `anchoring guide frames needs the vae input` | AddGuide | 接 image 没接 vae | 补 `vae` |
| `anchoring guide audio needs the audio_vae input` | AddGuide | 接 audio 没接 audio_vae | 补 `audio_vae` |
| `frame_idx {} is outside the video's {} frames` | AddGuide | 单图锚点越界 | 减小 frame_idx |
| `a {} frame guide clip at frame_idx {} does not fit` | AddGuide | 片段放不下 | 缩短片段或前移 |
| `past the end of the video's audio track` | AddGuide | 音轨锚点越界 | 见 6.3 |
| `reference videos need at least 5 frames` | ReferenceToVideo | 参考视频 <5 帧 | 补帧 |
| `Fun VAE output shape {} does not match` | FunControlNetApply | VAE 输出与目标形状不符 | 检查 VAE 是否 H3 视频 VAE |
| adaLN / curve basis vs full（RuntimeError） | FunControlNetApply | pruned 与非 pruned 混用 | 配对使用 |
| conditioning 维度错（启动即崩） | ImageToVideo / ReferenceToVideo | `CLIPLoader.type` 选错 | 选 `minimax` |
| 画面正常但音频全静音 | 解码链 | 漏 `VAEDecodeAudio` | 补节点 |
| 片段末尾变形 / 文字乱码 | 采样 | Sage Attention 的 INT8 | 换 bf16 + CK attention |
| 直接崩溃（int8_convrot VAE） | 加载 | int8_convrot + Comfy Kitchen attention（issue #15529） | 换 fp16 VAE 或换 attention backend |

---

## 8. 源码索引

| 内容 | 文件:行 |
|---|---|
| 6 个 H3 节点定义 | `comfy_extras/nodes_minimax_h3.py:94 / 116 / 166 / 243 / 367 / 579` |
| 节点注册列表 | `comfy_extras/nodes_minimax_h3.py:624-633` |
| 常量（32 / 768 / 1344 / 2048 / 24 / 40） | `comfy_extras/nodes_minimax_h3.py:30-35` |
| 帧数吸附与 latent 时间维 | `comfy_extras/nodes_minimax_h3.py:38-51` |
| 参考视频画板计算 | `comfy_extras/nodes_minimax_h3.py:54-65` |
| Fun ControlNet 补丁类 | `comfy_extras/nodes_minimax_h3.py:411-576` |
| `FRAME_PER_TOKEN` / `FRAME_RESCALE` | `comfy/ldm/minimax/model.py` |
| `IMAGENET_MEAN` | `comfy/ldm/minimax/vae.py` |
| 模型注册（shift 12 / 3） | `comfy/supported_models.py:964` |
| 模型识别 | `comfy/model_detection.py:390` |
| latent 格式 | `comfy/latent_formats.py:622, 659` |
| `ModelSamplingAV` | `comfy/model_sampling.py:338` |
| 文本编码器（Qwen3-VL 截断 50 层） | `comfy/text_encoders/minimax.py` |
| DiT（PackedLayout / seg_t） | `comfy/ldm/minimax/model.py:340-700` |
| Fun ControlNet 模型 | `comfy/ldm/minimax/controlnet.py` |
| `CLIPLoader` 类型列表 | `nodes.py:1021` |
| `VAELoader` | `nodes.py:776` |
| `UNETLoader` | `nodes.py:992` |
| `VAEDecode` | `nodes.py:321` |
| `LoadImage` | `nodes.py:1747` |
| `LoadImageMask` | `nodes.py:1824` |
| `SetLatentNoiseMask` | `nodes.py:1567` |
| `LoraLoaderModelOnly` | `nodes.py:761` |
| `ModelPatchLoader` | `comfy_extras/nodes_model_patch.py:247` / 注册 `:1125` |
| `VAEDecodeAudio` | `comfy_extras/nodes_audio.py:119` |
| `LoadAudio` | `comfy_extras/nodes_audio.py:366` |
| `CreateVideo` | `comfy_extras/nodes_video.py:210` |
| `SaveVideo` | `comfy_extras/nodes_video.py:139` |
| `GetVideoComponents` | `comfy_extras/nodes_video.py:312` |
| `Canny` | `comfy_extras/nodes_canny.py:11` |
| `LTXVConcatAVLatent` | `comfy_extras/nodes_lt.py:896` |
| `LTXVSeparateAVLatent` | `comfy_extras/nodes_lt.py:974` |
| `BlockSparseAttention` | `comfy_extras/nodes_sparse_attention.py:352` |
| `BasicScheduler` | `comfy_extras/nodes_custom_sampler.py:21` |
| `KSamplerSelect` | `comfy_extras/nodes_custom_sampler.py:383` |
| `BasicGuider` | `comfy_extras/nodes_custom_sampler.py:805` |
| `RandomNoise` | `comfy_extras/nodes_custom_sampler.py:1007` |
| `SamplerCustomAdvanced` | `comfy_extras/nodes_custom_sampler.py:1020` |
| 官方蓝图 | `blueprints/Image to Video (MiniMax H3).json` |
| 单元测试 | `tests-unit/comfy_test/test_minimax_h3_model.py`、`test_minimax_h3_vae.py` |

---

## 9. 许可提醒

H3 权重使用 **MiniMax H3 Community License**，不是 MIT/Apache。
允许修改、分发、做衍生模型；商用有年收入门槛与署名要求，且适用地区有限制。
**商用前请自行阅读仓库根目录 LICENSE 原文**，第三方整理口径不完全一致。
