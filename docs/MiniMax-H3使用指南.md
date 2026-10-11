# MiniMax H3 在 ComfyUI 中的完整使用与源码详解

> 文档对象：`MiniMax-AI/MiniMax-H3`（开源权重）+ 当前仓库 `github_2026/ComfyUI`（`comfyui_version.__version__ = 0.39.0`）
> 所有参数、节点 ID、目录、常量均从**本仓库源码**逐项核对，非二手转述。
> 对照的上游仓库源码已克隆到 `.workbuddy/h3repo`（用于核对架构描述与 `model_index.json`）。

---

## 0. 结论先行

| 问题 | 答案 |
|---|---|
| 当前项目支持 MiniMax H3 吗？ | **支持，且是核心内置**。无需安装任何自定义节点。 |
| 支持哪些能力？ | t2va（文生音视频）、fl2va（首尾帧生视频）、ref2va（全参考生成）、多帧引导锚定、Fun ControlNet / 视频 inpainting、稀疏注意力加速 |
| 需要装 KJNodes 吗？ | **不必须用**。只有想用 `Patch Sage Attention KJ` 加速时才需要（第 9 章）。 |
| 权重要下哪些、放哪？ | 见第 3 章，5 类文件分别落到 `models/` 下 5 个子目录。 |
| 需要联网吗？ | 本地推理全程离线。只有 2K 再生成（H3-Regenerate-2K）和复杂指令解析（H3-Context-IR）是托管 API，需联网。 |

---

## 1. H3 是什么（以及"开源"的真实边界）

MiniMax H3 是**通用全模态生成系统**，不是 LLM。它的核心特征是：**同一个 33B 稠密单流 Transformer 联合预测视频 latent 和音频 latent**，所以"音画同步"是模型内建的，不是先出画面再配音。

### 1.1 三模块与开源状态

| 模块 | 作用 | 是否开源 |
|---|---|---|
| `H3-Context-IR` | 把自由形式的多模态指令解析/补全成结构化中间表示 | ❌ 未开源，仅提供托管 API |
| `H3-Base` | 根据上下文生成 768p + 32kHz 立体声 | ✅ **开源**（FL2VA / Ref2VA 两个 checkpoint） |
| `H3-Regenerate-2K` | 把 768p 结果和原始上下文一起送回模型，再生成 2K | ❌ 未开源，仅提供 API |

> 划重点：**H3 官方仓库里没有 ComfyUI 节点代码**。ComfyUI 侧的实现完全由 Comfy-Org 自己写在核心里（`comfy/ldm/minimax/`、`comfy_extras/nodes_minimax_h3.py`）。所以"H3 的 ComfyUI 支持"要看 ComfyUI 仓库，不是看 H3 仓库。

### 1.2 上游仓库结构（`.workbuddy/h3repo`）

```
MiniMax-H3/
├── model_index.json            -> MiniMaxH3ModularPipeline（diffusers 入口）
├── modular_model_index.json
├── FL2VA/                      -> t2va / fl2va 任务
│   ├── model_index.json        -> MiniMaxH3Pipeline, partition="fl2va"
│   ├── transformer/  processor/  tokenizer/  text_encoder/
│   ├── video_vae/    audio_vae/
├── Ref2VA/                     -> ref2va 任务
│   └── (同上)
├── transformer/ transformer_ref/ vae/ audio_vae/   # 顶层 diffusers 格式
├── scheduler/ audio_scheduler/
└── skills/                     # 8 个 prompt 写作 / 生成 skill（非 ComfyUI 用）
```

`FL2VA/model_index.json` 里的私有字段值得注意：

```json
{
  "_minimax_h3": {
    "schema_version": 1,
    "partition": "fl2va",
    "tasks": ["t2va", "fl2va"],
    "sigma_shift_scales": { "video": 12.0, "audio": 3.0 }
  }
}
```

**`shift=12.0 / audio_shift=3.0` 就是 ComfyUI 里那两个 sigma shift 的来源**，两个仓库口径一致（见第 7 章）。

### 1.3 输出规格

| 项 | 值 |
|---|---|
| 时长 | 4–15 秒（ComfyUI 侧 `length` 帧数训练范围约 124–362，见 6.2） |
| 帧率 | 24 FPS |
| 分辨率 | 短边 768 像素（约 1MP）；**2K 需要走官方 API 再生成** |
| 音频 | 32 kHz 原生立体声 |
| 对白语言 | 官方稳定支持 11 种：中/英/阿/法/德/意/日/韩/葡/俄/西 |

---

## 2. 当前仓库的内置支持清单

全部是核心文件，无外部依赖：

| 文件 | 职责 |
|---|---|
| `comfy_extras/nodes_minimax_h3.py` | **6 个 H3 节点**（V3 `io.ComfyNode` 范式） |
| `comfy/ldm/minimax/model.py` | H3 音视频 DiT（`MiniMaxH3Model`）、packed layout、RoPE、时间网格 |
| `comfy/ldm/minimax/vae.py` | H3-VisualVAE（视频 VAE） |
| `comfy/ldm/minimax/audio_vae.py` | H3-AudioVAE（音频 VAE，DAC encoder + BigVGAN decoder） |
| `comfy/ldm/minimax/controlnet.py` | Fun ControlNet（`MiniMaxH3FunControl`） |
| `comfy/text_encoders/minimax.py` | Qwen3-VL-32B（截断到 50 层）tokenizer / TE，含 H3 presentation 拼装 |
| `comfy/supported_models.py:964` | `class MiniMaxH3`（unet_config / sampling_settings / dtype 白名单） |
| `comfy/model_detection.py:390` | 权重探测：`video_patch_proj.weight` + `audio_patch_proj.weight` |
| `comfy/latent_formats.py:622,659` | `MiniMaxH3Video` / `MiniMaxH3AV` latent 格式 |
| `comfy/model_sampling.py:338` | `ModelSamplingAV`（音视频双 shift 的流采样） |
| `comfy/model_base.py` | `model_base.MiniMaxH3` |
| `comfy_extras/nodes_model_patch.py:306` | `ModelPatchLoader` 对 H3 Fun ControlNet 的自动识别分支 |
| `comfy_extras/nodes_sparse_attention.py` | `BlockSparseAttention`，对 H3 走 chunked qkv producer |
| `comfy_extras/nodes_model_advanced.py:374` | `ModelAttentionBackend`（切换注意力后端） |
| `comfy_extras/nodes_audio.py:98` | `vae_decode_audio()`，从 AV latent 取音频流 |
| `nodes.py:340` | `VAEDecode` 对 nested latent 取 `unbind()[0]`（视频流） |
| `comfy_extras/nodes_lt.py:901,977` | `LTXVConcatAVLatent` / `LTXVSeparateAVLatent`（通用 AV latent 拼拆，H3 可用） |
| `blueprints/Image to Video (MiniMax H3).json` | **官方蓝图工作流**（可直接加载） |
| `tests-unit/comfy_test/test_minimax_h3_model.py` | DiT forward / mask 单测 |
| `tests-unit/comfy_test/test_minimax_h3_vae.py` | VAE offload 相关单测 |

### 2.1 版本门槛（对照官方文档）

| 能力 | 最低 ComfyUI 版本 | 本仓库 0.39.0 |
|---|---|---|
| T2V / I2V / R2V 基础模板 | 0.30.0 | ✅ |
| 多帧参考（`MiniMaxH3AddGuide`） | 0.34.0 | ✅ |
| Fun ControlNet Union、稀疏注意力节点、`Model Attention Backend` | 0.35.0 | ✅ |
| FastH3（FastVideo VSA 稀疏注意力权重） | 0.36.0 | ✅ |

### 2.2 自检命令

```bash
# 1) 确认 H3 节点文件在加载清单里
grep -n "nodes_minimax_h3" nodes.py

# 2) 确认模型探测分支存在
grep -n "minimax_h3" comfy/model_detection.py

# 3) 列出全部 6 个 H3 节点 ID
grep -n 'node_id="' comfy_extras/nodes_minimax_h3.py
```

---

## 3. 模型下载与放置目录

权重托管在 Hugging Face 的 **`Comfy-Org/MiniMax-H3`** 仓库（不是 `MiniMaxAI/MiniMax-H3`——后者是 diffusers 原始格式，给 SGLang/vLLM/diffusers 用的）。模板首次加载会弹窗引导下载，也可以手动下。

### 3.1 目录映射表

| 模型 | 文件名（蓝图默认值） | 放到 |
|---|---|---|
| DiT（T2V / I2V / 续写） | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `models/diffusion_models/`（或 `models/unet/`） |
| DiT（R2V / 多帧 / FunCN） | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 同上 |
| DiT（bf16 对应版） | `minimax_h3_fl2va_pruned_bf16.safetensors` / `minimax_h3_ref2va_pruned_bf16.safetensors` | 同上 |
| DiT（全量非 pruned） | `minimax_h3_fl2va_int8_convrot.safetensors` / `minimax_h3_ref2va_int8_convrot.safetensors` | 同上 |
| 文本编码器（Qwen3-VL-32B） | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `models/text_encoders/`（或 `models/clip/`） |
| 视频 VAE | `minimax_h3_video_vae_fp16.safetensors` | `models/vae/` |
| 音频 VAE | `minimax_h3_audio_vae_fp32.safetensors` | `models/vae/` |
| Turbo LoRA（8 步） | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | `models/loras/` |
| Fun ControlNet | 以 `Comfy-Org/MiniMax-H3` 仓库实际文件名为准 | `models/model_patches/` |

目录常量出处（`folder_paths.py`）：

```
line 29: "vae"             -> models/vae
line 30: "text_encoders"   -> models/text_encoders, models/clip
line 31: "diffusion_models"-> models/unet, models/diffusion_models
line 55: "model_patches"   -> models/model_patches
line 28: "loras"           -> models/loras
```

### 3.2 pruned 构建与 LoRA 的匹配坑（官方文档明确警告）

- `pruned` 构建把时间嵌入器和全宽 adaln 权重换成共享曲线基（`adaln_t_table`，1025 采样 × 8 基列），ComfyUI 会从 checkpoint 自己读。
- **模板默认加载 pruned 构建**。若某个 LoRA 是在**全量构建**上蒸馏的，它带的 adaln 权重在 pruned 构建里没有对应张量 → ComfyUI 报 shape mismatch 并**跳过这部分**（不致命，但 LoRA 效果打折）。
- Turbo LoRA 不带 adaln 张量，两种构建都能正常加载。
- 结论：**LoRA 必须匹配它被蒸馏的那个 checkpoint 构建**；仓库同时发布 pruned 和非 pruned 时，优先 pruned。

### 3.3 加载节点与参数

| 节点 | 关键参数 | 值 |
|---|---|---|
| `UNETLoader` | `unet_name` | 上表 DiT 文件名 |
| | `weight_dtype` | `default`（推荐）；可选 `fp8_e4m3fn` / `fp8_e4m3fn_fast` / `fp8_e5m2` |
| `CLIPLoader` | `clip_name` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` |
| | `type` | **`minimax`**（必须选这个，`nodes.py:1021` 的 combo 里有） |
| | `device` | `default`（可选 `cpu` 卸载） |
| `VAELoader` ×2 | `vae_name` | 视频 VAE / 音频 VAE 各一个实例 |

> `CLIPLoader` 的 `type` 一旦选错（比如留在 `stable_diffusion`），Qwen3-VL 不会被识别，conditioning 直接崩。这是新手第一大坑。

---

## 4. 六个内置节点总览

全部定义在 `comfy_extras/nodes_minimax_h3.py`，走 V3 范式（`io.ComfyNode` + `define_schema` + `execute`）：

| node_id（JSON 里的 class_type） | display_name | category | 用途 |
|---|---|---|---|
| `EmptyMiniMaxH3LatentAV` | Empty MiniMax H3 AV Latent | `model/latent/minimax` | 造空的音视频联合 latent |
| `MiniMaxH3ImageToVideo` | MiniMax H3 Image to Video | `model/conditioning/minimax` | **t2va + fl2va**（文生 / 首尾帧） |
| `MiniMaxH3AddGuide` | Add Guide for MiniMax H3 | `model/conditioning/minimax` | 在任意帧锚定图像 / 片段 / 音轨 |
| `MiniMaxH3ReferenceToVideo` | MiniMax H3 Reference to Video | `model/conditioning/minimax` | **ref2va** 全参考生成 |
| `MiniMaxH3SigmaShift` | ModelSamplingMiniMaxH3 | `model/patch/minimax` | 设置 video/audio 流 shift |
| `MiniMaxH3FunControlNetApply` | Apply MiniMax H3 Fun ControlNet | `model/patch/minimax` | 控制视频 / 视频 inpainting |

> 注意 `MiniMaxH3SigmaShift` 的 **node_id 和 display_name 不一致**：JSON 里写 `MiniMaxH3SigmaShift`，界面上显示 `ModelSamplingMiniMaxH3`。写 API 脚本时别搞混。

---

## 5. 节点逐项详解

### 5.1 `EmptyMiniMaxH3LatentAV`

直接造一个 `(video, audio)` 的 `NestedTensor` latent，等价于其他模型的 `EmptyLatentImage`。一般不直接用——`MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` 内部已经调了同一个 `_empty_av_latent()`，并顺手输出 latent。只有在你想自己拼 conditioning（比如手写 `CLIPTextEncode` 路线）时才用。

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `width` | INT | 1344 | 32 ~ MAX_RESOLUTION，step 32 | 画布宽，需 32 倍数 | `1344` |
| `height` | INT | 768 | 32 ~ MAX_RESOLUTION，step 32 | 画布高，需 32 倍数 | `768` |
| `length` | INT | 124 | 5 ~ 3600，step 17 | 24fps 下的帧数，**向上吸附到 17k+5 网格** | `124` |

| 输出槽 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | LATENT | — | `{"samples": NestedTensor((video, audio))}` |

**源码要点**（`nodes_minimax_h3.py:85`）：

```python
def _empty_av_latent(width, height, length, batch_size=1):
    frame_count, latent_t, audio_t = temporal_shape(length)
    video = torch.zeros([batch_size, 24, latent_t, height // 16, width // 16])
    audio = torch.zeros([batch_size, 32, 2, audio_t])
    return {"samples": comfy.nested_tensor.NestedTensor((video, audio))}, frame_count
```

- 视频 latent：`[B, 24, T, H/16, W/16]`（24 通道，空间 16×）
- 音频 latent：`[B, 32, 2, T40]`（32 通道 × 2 声道，40 Hz 时间率）

---

### 5.2 `MiniMaxH3ImageToVideo`（t2va / fl2va）

**主力节点**。一条节点同时覆盖三种模式：

| 输入图数量 | 模式 | 说明 |
|---|---|---|
| 0 张 | `t2va` | 纯文生音视频 |
| 1 张（接 `first_frame`） | 首帧生视频 | |
| 1 张（接 `last_frame`） | 尾帧生视频 | |
| 2 张 | `fl2va` | 首尾帧生视频 |

#### 输入参数表

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `clip` | CLIP | — | — | `CLIPLoader` type=minimax 的输出 | 节点连线 |
| `vae` | VAE | — | — | **视频 VAE** | 节点连线 |
| `prompt` | STRING (multiline) | — | — | 支持 dynamic prompts；不用 chat 模板 | 见 5.2.3 |
| `width` | INT | 1344 | 32~MAX，step 32 | 生成画布宽 | `1344` |
| `height` | INT | 768 | 32~MAX，step 32 | 生成画布高 | `768` |
| `length` | INT | 124 | 5~3600，step 17 | 帧数，吸附到 17k+5；124≈5.17s；训练范围约 124–362，更长未测 | `124` |
| `first_frame` | IMAGE (optional) | — | — | 首帧。**直接拉伸**到画布（`crop="disabled"`），作为几何锚点 | 可选 |
| `last_frame` | IMAGE (optional) | — | — | 尾帧。**保持比例居中裁切**（`crop="center"`），跟随首帧构图 | 可选 |

#### 输出槽位表

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | CONDITIONING | `positive` | 已写入 `minimax_keyframes` 的 conditioning |
| 1 | LATENT | — | 对应的空 AV latent |

#### 5.2.3 源码要点

```python
if first_frame is not None:
    img = _resize(first_frame[:1], width, height, "disabled")   # 拉伸
    keyframes.append({"resolved_frame_index": 0, "image": img})
if last_frame is not None:
    img = _resize(last_frame[:1], width, height, "center")      # 居中裁切
    keyframes.append({"resolved_frame_index": frame_count - 1, "image": img})

tokens = clip.tokenize(prompt, images=images)
cond = clip.encode_from_tokens_scheduled(tokens)
for kf in keyframes:
    kf["latent"] = vae.encode(kf.pop("image"))
cond = node_helpers.conditioning_set_values(cond, {"minimax_keyframes": keyframes})
```

三个容易忽略的点：

1. **只取 batch 的第一张**（`first_frame[:1]`）——传一组图进来不会变成参考视频。
2. **首尾帧的 resize 策略不同**：首帧是几何锚点所以硬拉伸，尾帧是跟随者所以保持比例裁切。想让尾帧也精确控制构图，就先手动裁成目标比例再接进来。
3. **关键帧 latent 每一步都重新注入，从不参与去噪**。这是 H3 fl2va 的工作原理，不是 ComfyUI 的 hack。

#### 5.2.4 提示词怎么写（源码级事实）

`comfy/text_encoders/minimax.py` 顶部注释明确写了 H3 的 presentation **不走 chat 模板**，token id 就是原始文本 + 显式插入的视觉块：

```
t2va:   <prompt>
fl2va:  "<Picture 1>: " <vision block> ["<Picture 2>: " <vision block>] <prompt>
```

并且：`Qwen3-VL` 的第 50 层隐藏状态被作为 conditioning，视觉 pad 位置在 DiT 里带 token tag 0（video modality），文本位置带 tag 1 —— 标签随 embedding 一起以 `minimax_token_tags` 返回。

tokenizer 额外 token（H3 release 固定 id）：

```
<d> 151669      </d> 151670        <|cutoff|> 151671
<|lyrics_start|> 151672   <|lyrics_end|> 151673
<|caption_start|> 151674  <|caption_end|> 151675
```

**所以不要套 Qwen 的 chat template 提示词**，直接写自然语言。官方仓库 `skills/h3-prompt-writing/` 下有完整写作指南（含时间轴分段写法），蓝图里的示范提示词见 6.4。

---

### 5.3 `MiniMaxH3AddGuide`（多帧锚定）

把图像 / 片段 / 音轨锚定到目标视频的**任意像素帧**上。可串联多个节点锚定多个位置。

#### 输入参数表

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `positive` | CONDITIONING | — | — | 上游 conditioning（可串联） | 节点连线 |
| `vae` | VAE (optional) | — | — | **视频 VAE**，接了 image 时必需 | 节点连线 |
| `audio_vae` | VAE (optional) | — | — | **音频 VAE**，接了 audio 时必需 | 节点连线 |
| `latent` | LATENT | — | — | 目标 AV latent（用来取画布尺寸和总帧数） | 节点连线 |
| `image` | IMAGE (optional) | — | — | 图像或视频帧组。多帧会被裁到合法长度 5/22/39…（17k+5）；少于 5 帧只用第一张 | 可选 |
| `audio` | AUDIO (optional) | — | — | 从同一帧开始锚定的音轨，按剩余时长裁剪 | 可选 |
| `frame_idx` | INT | 0 | -9999 ~ 9999 | 锚定帧号；**负数表示从结尾倒数** | `0` |

#### 输出槽位表

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | CONDITIONING | `positive` | 追加了一条 keyframe 的 conditioning |

#### 源码要点与坑位

```python
if not samples.is_nested or len(samples.tensors) != 2 \
   or samples.tensors[0].ndim != 5 or samples.tensors[0].shape[1] != 24:
    raise ValueError("MiniMaxH3AddGuide expects a MiniMax H3 AV latent")
```

- **必须接 H3 的 AV latent**，普通视频 latent 会直接抛错。
- `image` 和 `audio` **至少要接一个**，两个都不接会抛错。
- 片段长度吸附：`<5 帧 → 只取首帧`；`≥5 帧 → 向下裁到 17k+5`。
- 越界检查很严格，两种报错文案不同（源码 213–218 行）：
  - 单图：`frame_idx {} is outside the video's {} frames`
  - 片段：`a {} frame guide clip at frame_idx {} does not fit in the video's {} frames`
- 音轨时间轴换算：`max_rt = floor(audio_T - FRAME_RESCALE * resolved_frame_index)`，`FRAME_RESCALE = 5/3`。锚点越靠后，能放的音轨越短。

---

### 5.4 `MiniMaxH3ReferenceToVideo`（ref2va）

全参考生成：一次能吃进 **≤9 张图 + ≤3 段视频（各带音轨）+ ≤3 段独立音频**，混合文件总数 ≤12。

#### 输入参数表

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `clip` | CLIP | — | — | type=minimax | 节点连线 |
| `vae` | VAE (optional) | — | — | 视频 VAE。不接则参考图/视频**只进文本编码器**，不进 DiT | 节点连线 |
| `audio_vae` | VAE (optional) | — | — | 音频 VAE。不接则参考音频只进文本编码器 | 节点连线 |
| `prompt` | STRING (multiline) | — | — | 用 `<Picture i>` / `<Video k>` / `<Audio j>` 指代参考 | 见下 |
| `width` | INT | 1344 | 32~MAX，step 32 | 生成画布宽 | `1344` |
| `height` | INT | 768 | 32~MAX，step 32 | 生成画布高 | `768` |
| `length` | INT | 124 | 5~3600，step 17 | 帧数（124≈5s，训练范围约 124–362） | `124` |
| `ref_image_size` | COMBO | `match` | `match` / `max` | `match`：等比缩到生成像素面积（只缩不放）；`max`：用参考管线的 **2048px 短边**，身份保真最好但**慢好几倍** | `match` |
| `ref_images` | Autogrow IMAGE | — | 0 ~ 9 个（`ref_image_1..9`） | 参考图 | 可选 |
| `ref_videos` | Autogrow IMAGE | — | 0 ~ 3 个（`ref_video_1..3`） | 参考视频帧（24fps，2–15s） | 可选 |
| `ref_video_audios` | Autogrow AUDIO | — | 0 ~ 3 个（`ref_video_audio_1..3`） | **同名编号视频的音轨**（`ref_video_audio_2` 配 `ref_video_2`） | 可选 |
| `ref_audios` | Autogrow AUDIO | — | 0 ~ 3 个（`ref_audio_1..3`） | 独立参考音频 | 可选 |

#### 输出槽位表

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | CONDITIONING | `positive` | 已写入 `minimax_refs` 的 conditioning |
| 1 | LATENT | — | 对应空 AV latent |

#### 参考顺序与标签（源码注释原文逻辑）

写入 presentation 的**固定顺序**是：图像 → 视频 → 独立音频；每个类型序号各自从 1 开始：

```
image  -> "<Picture i>: " <vision block>
audio  -> "<Audio j>: "                    # 音频从不进 Qwen
video  -> "<Video k>: " 然后每 2 帧一个时间块 "<T.T seconds>" <vision block>
最后接 <prompt>
```

每条视频的**音轨标签 `<Audio j>` 排在它自己的 `<Video k>` 之前**。所以提示词里写 `<Picture 1>`、`<Video 1>`、`<Audio 1>` 就能指到对应素材。

#### 源码要点

```python
# Qwen 以 2 fps 看视频，并带时间戳
sample_idx = list(range(0, frames.shape[0], FPS // 2))
qwen_frames = frames[sample_idx]
ref_items.append({"type": "video", "data": qwen_frames,
                  "timestamps": [i / 2.0 for i in range(len(sample_idx))]})
```

- 参考视频**至少 5 帧**（<5 帧抛 `MiniMax H3 reference videos need at least 5 frames`），并向下裁到 17k+5。
- 参考视频会被 `adapt_canvas()` 重算画布：768 短边 + 768×1344 面积上限，各轴取整到 32。
- 参考视频超过目标帧数会被截断到 `frame_count`。
- **不接 `vae` 时参考仍生效**（只作用于文本编码器），只是 DiT 侧没有 latent 注入——适合"只要语义参考、不要像素级复刻"的场景，还更快。

---

### 5.5 `MiniMaxH3SigmaShift`（界面名 `ModelSamplingMiniMaxH3`）

#### 输入参数表

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | — | — | 待 patch 的模型 | 节点连线 |
| `shift_video` | FLOAT | 12.0 | 0.01 ~ 100.0，step 0.01 | 视频流 shift | `12.0` |
| `shift_audio` | FLOAT | 3.0 | 0.01 ~ 100.0，step 0.01 | 音频流 shift | `3.0` |

#### 输出槽位表

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 打了 `model_sampling` object patch 的模型 |

#### 源码要点

```python
class ModelSamplingAdvanced(comfy.model_sampling.ModelSamplingAV, comfy.model_sampling.CONST): pass
model_sampling.set_parameters(shift=shift_video, audio_shift=shift_audio)
m.add_object_patch("model_sampling", model_sampling)
to["minimax_h3_sigma_shift_video"] = shift_video
to["minimax_h3_sigma_shift_audio"] = shift_audio
```

- `ModelSamplingAV`（`comfy/model_sampling.py:338`）把音频 latent 按 `audio_scale = shift / audio_shift` 缩放后挂到视频 schedule 上，使整个 pack 表现为**单一 schedule 的普通 flow latent**。
- **默认工作流不需要这个节点**：`supported_models.MiniMaxH3` 的 `sampling_settings` 已经是 `{shift: 12.0, audio_shift: 3.0}`，所有模板（FastH3 除外）都直接读这两个值。
- **什么时候要加**：加载了要求不同 shift 对的 checkpoint。官方例子是 FastH3 模板用 `shift_video=10 / shift_audio=3`。
- **警告**：在 8 步蒸馏构建上把 `shift_video` 从 10 改到 3，画面会出现网格状伪影。别乱调。

---

### 5.6 `MiniMaxH3FunControlNetApply`

用控制视频驱动 H3，或用 mask 做视频 inpainting。

#### 输入参数表

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | — | — | 基础模型 | 节点连线 |
| `model_patch` | MODEL_PATCH | — | — | `ModelPatchLoader` 加载的 Fun ControlNet | 节点连线 |
| `vae` | VAE | — | — | 视频 VAE（编码控制视频/被遮罩源） | 节点连线 |
| `strength` | FLOAT | 1.0 | 0.0 ~ 10.0，step 0.01 | 控制强度 | `1.0` |
| `start_percent` | FLOAT (advanced) | 0.0 | 0.0 ~ 1.0 | 生效起点（百分比） | `0.0` |
| `end_percent` | FLOAT (advanced) | 1.0 | 0.0 ~ 1.0 | 生效终点 | `1.0` |
| `control_video` | IMAGE (optional) | — | — | 控制视频 | 可选 |
| `mask` | MASK (optional) | — | — | **1 标记"要重绘"的区域** | 可选 |
| `source_video` | IMAGE (optional) | — | — | 遮罩背后的原视频；**只有给了 mask 才读** | 可选 |

#### 输出槽位表

| 槽位 | 类型 | 名称 | 说明 |
|---|---|---|---|
| 0 | MODEL | — | 注册了 block patch 的模型 |

#### 源码要点

- 提前返回：`strength == 0` 或 `control_video` 与 `mask` 都为空时，直接返回原模型。
- 注入层由 checkpoint 决定（`nodes_model_patch.py:306`）：
  ```python
  num_blocks = 0
  while "control_blocks.{}.after_proj.weight".format(num_blocks) in sd: num_blocks += 1
  injection_layers = tuple(range(0, 50, 50 // num_blocks))   # v1 有 5 块（每 10 层），v2 有 10 块（每 5 层）
  if metadata 有 "control_blocks_places": 以 metadata 为准
  ```
- **mask 语义是反直觉的**：`1` = 要重新生成的区域（`visibility = 1 - mask`）。
- `inpaint_post_norm`：开启时被遮罩区域填 **ImageNet 均值灰**（`IMAGENET_MEAN = (0.485, 0.456, 0.406)`）而不是黑色，因为 VAE 把中灰归一化到零。
- 控制分支的 skip 会**把音频位置清零**（`skip[layout.audio_pos] = 0`），保证控制只作用于画面。
- 控制状态放在 `pause_malloc_graph()` 作用域外，避免和基础 block 的权重暂存互相踩踏。

---

## 6. 官方蓝图逐节点拆解：`Image to Video (MiniMax H3)`

文件：`blueprints/Image to Video (MiniMax H3).json`（21 个节点，封装成一个 subgraph）。

### 6.1 完整拓扑（按执行序）

```
[加载]
  UNETLoader(135)   unet_name=minimax_h3_fl2va_pruned_int8_convrot.safetensors, weight_dtype=default
  CLIPLoader(136)   clip_name=qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors, type=minimax
  VAELoader(127)    minimax_h3_video_vae_fp16.safetensors
  VAELoader(128)    minimax_h3_audio_vae_fp32.safetensors

[Turbo 开关]
  LoraLoaderModelOnly(142)  lora=minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors, strength=1
  PrimitiveBoolean(147)     Enable Lightning LoRA = false
  ComfySwitchNode(143)      Model:  false→UNETLoader, true→LoraLoader
  ComfySwitchNode(144)      Steps:  false→20,          true→6

[条件]
  PrimitiveFloat(141)  duration = 2 (秒，蓝图对外暴露成 "duration")
  ComfyMathExpression(140)  max(5, round(a*24)) + (5 - (max(5, round(a*24)) % 17)) % 17
  MiniMaxH3ImageToVideo(139)
      clip ← CLIPLoader, vae ← 视频VAE
      first_frame/last_frame/prompt/width/height ← 蓝图输入
      length ← ComfyMathExpression

[采样]
  RandomNoise(137)          noise_seed
  BasicGuider(134)          model ← Switch(Model), conditioning ← I2V.positive(槽0)
  KSamplerSelect(131)       res_multistep
  BasicScheduler(132)       scheduler=simple, steps ← Switch(Steps), denoise=1
  SamplerCustomAdvanced(133)
      noise ← RandomNoise, guider ← BasicGuider, sampler ← KSamplerSelect,
      sigmas ← BasicScheduler, latent_image ← I2V.LATENT(槽1)

[解码]
  VAEDecode(130)       samples ← SCA.output(槽0),  vae ← 视频VAE  → IMAGE
  VAEDecodeAudio(129)  samples ← SCA.output(槽0),  vae ← 音频VAE  → AUDIO
  CreateVideo(138)     images ← VAEDecode, audio ← VAEDecodeAudio, fps=24, bit_depth=8, color_space=sRGB
                       → VIDEO（蓝图输出）
```

### 6.2 时间网格：17k+5 是什么

H3 的 DiT 里 `FRAME_PER_TOKEN = (1, 4, 4, 4, 4)`，即第 1 个 latent token 管 1 帧、之后每个管 4 帧。所以**合法帧数必须满足 `n ≡ 5 (mod 17)`**（一个 17 帧周期 = 1 + 4×4）。

```python
def align_frame_count(n):
    while n % 17 != 5:
        n += 1
    return n

def video_latent_t(frame_count):
    return 2 if frame_count <= 5 else ((frame_count - 5) // 17) * 5 + 2
```

蓝图用 `ComfyMathExpression` 在**画布上**做换算，让用户输入秒数：

```
max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17
```

即 `seconds → round(×24) → 向上吸附到最近的 17k+5`。

| 秒数 | round(×24) | 吸附后 | 实际时长 |
|---|---|---|---|
| 2 | 48 | 56 | 2.33 s |
| 5 | 120 | 124 | 5.17 s |
| 10 | 240 | 245 | 10.21 s |
| 15 | 360 | 362 | 15.08 s |

> 节点 tooltip 原文：`124 = ~5s; trained range is ~124-362, longer is untested`。**超过 362 帧（约 15 秒）属于未测试区域。**

音频 latent 长度由 `FRAME_RESCALE = 5/3` 换算：`audio_t = round((frame_count / 24) * 40) = round(frame_count * 5/3)`。

### 6.3 采样参数

| 项 | 值 | 出处 |
|---|---|---|
| Sampler | `res_multistep` | `KSamplerSelect` |
| Scheduler | `simple` | `BasicScheduler` |
| Steps（非 turbo） | 20 | `PrimitiveInt(145)` |
| Steps（turbo LoRA） | 6（蓝图默认）/ 8（对外暴露值） | `PrimitiveInt(146)` / 蓝图 widget |
| denoise | 1.0 | `BasicScheduler` |
| shift video / audio | 12.0 / 3.0 | 来自 `supported_models.MiniMaxH3.sampling_settings`，**工作流里没有 shift 节点** |

`res_multistep` 是二阶多步采样器：每一步复用上一步的去噪估计；第一步没有历史可用，退化为普通一阶（Euler）步，从第二步才开始二阶。

**重要**：多步历史存在于**单次采样运行内部**，不在 latent 里。所以如果把一个 schedule 拆成两个 sampler（比如先 base 再放大后二次采样），第二个 sampler 的历史是空的，第一步会掉回一阶 —— 步数很少的尾巴段会明显掉质量。

### 6.4 蓝图示范提示词（可直接抄结构）

```
Vaporwave title sequence look: pink and blue gradient palette, VHS tracking artifacts,
Greek statue motifs, chrome palm trees, RGB chromatic aberration, lo-fi retro atmosphere,
mood languid and nostalgic.

Timeline:
[0s-1s] VHS static opens the frame, the title "COMFYUI" appears with RGB split and a slight horizontal jitter.
[1s-2.5s] Hard cut, a Greek plaster bust close-up, pink-purple gradient sky, a pixelated sun.
[2.5s-4s] Clean "STARRING" credits appear, "LATENT" and "CONTROLNET" each shown exactly once.
[4s-5s] Final card "DIRECTED BY COMFYUI" holds, one VHS tracking glitch settling into stability.

Hard cuts only, transitions landing with tape jumps, no push-ins, no dissolves.

Audio: lo-fi vaporwave score, slow drum machine with soft bass, VHS tape-noise sample joins at 2.5s,
melody fading for the last 1s.

All text must be clearly legibly, do not misspell English, no Chinese characters,
do not repeat names or job titles, no soft dissolves, no subtitle bars.
```

写法要点：**总风格 → 时间轴分段 → 剪辑语法 → 音频描述 → 负向约束**。音频是和画面一起生成的，所以提示词里要写声音。

---

## 7. 采样链路原理（为什么不需要 shift 节点）

```
SamplerCustomAdvanced
  ├── noise      RandomNoise
  ├── guider     BasicGuider (model + conditioning)
  ├── sampler    KSamplerSelect -> res_multistep
  ├── sigmas     BasicScheduler -> simple
  └── latent_image  NestedTensor(video, audio)
```

- `supported_models.MiniMaxH3.sampling_settings = {"shift": 12.0, "audio_shift": 3.0}`
- `ModelSamplingAV.audio_scale = shift / audio_shift = 12 / 3 = 4.0`
- 采样器只看到**视频 sigma**；DiT 的 `forward()` 拿到视频 sigma 后，用 `time_shift_sigma()` 在共享 base grid 上反解，闭式推导出音频 sigma：

```python
def time_shift_sigma(sigma, from_shift, to_shift):
    base = sigma / (from_shift + sigma * (1.0 - from_shift))
    return to_shift * base / (1.0 + (to_shift - 1.0) * base)
```

- 模型内部 per-token timestep：`t = 1 - sigma`
- 音频流的 `VISUAL_COND_TIMESTEP = 0.999`、`AUDIO_COND_TIMESTEP = 1.0`

**结论**：随便用哪个标准 sampler 都行（H3 自己处理音频流的调度），只要 shift 对。

---

## 8. 可运行的 API JSON 示例

以下 4 个都可以直接 `POST /prompt`。节点 ID 与 `class_type` 已与源码注册表核对过。

### 8.1 文生视频（t2va，最小可用链）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader",
        "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
  "5": {"class_type": "MiniMaxH3ImageToVideo",
        "inputs": {"clip": ["2", 0], "vae": ["3", 0],
                   "prompt": "A lone courier bike crosses a rain-soaked neon alley at night, reflections rippling in puddles. Audio: deep engine hum, rain hiss, distant sirens fading.",
                   "width": 1344, "height": 768, "length": 124}},
  "6": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
  "7": {"class_type": "BasicScheduler",
        "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}},
  "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": 757358688076805}},
  "9": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["5", 0]}},
  "10": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["8", 0], "guider": ["9", 0], "sampler": ["6", 0],
                    "sigmas": ["7", 0], "latent_image": ["5", 1]}},
  "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
  "12": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["10", 0], "vae": ["4", 0]}},
  "13": {"class_type": "CreateVideo",
         "inputs": {"images": ["11", 0], "fps": 24, "audio": ["12", 0],
                    "bit_depth": 8, "color_space": "sRGB"}}
}
```

### 8.2 首尾帧生视频（fl2va）+ Turbo LoRA

```json
{
  "1":  {"class_type": "UNETLoader",
         "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
  "2":  {"class_type": "LoraLoaderModelOnly",
         "inputs": {"model": ["1", 0],
                    "lora_name": "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
                    "strength_model": 1.0}},
  "3":  {"class_type": "CLIPLoader",
         "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
  "4":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "5":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
  "6":  {"class_type": "LoadImage", "inputs": {"image": "h3_first_frame.png"}},
  "7":  {"class_type": "LoadImage", "inputs": {"image": "h3_last_frame.png"}},
  "8":  {"class_type": "MiniMaxH3ImageToVideo",
         "inputs": {"clip": ["3", 0], "vae": ["4", 0],
                    "prompt": "The camera holds on the same alley: the bike leaves frame left, the neon sign flickers out. Audio: engine receding, rain thinning to drips.",
                    "width": 1344, "height": 768, "length": 124,
                    "first_frame": ["6", 0], "last_frame": ["7", 0]}},
  "9":  {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
  "10": {"class_type": "BasicScheduler",
         "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": 8, "denoise": 1.0}},
  "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": 1234567890}},
  "12": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["8", 0]}},
  "13": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["11", 0], "guider": ["12", 0], "sampler": ["9", 0],
                    "sigmas": ["10", 0], "latent_image": ["8", 1]}},
  "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}},
  "15": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["13", 0], "vae": ["5", 0]}},
  "16": {"class_type": "CreateVideo",
         "inputs": {"images": ["14", 0], "fps": 24, "audio": ["15", 0],
                    "bit_depth": 8, "color_space": "sRGB"}}
}
```

### 8.3 多帧锚定（AddGuide 串联）

在 8.2 的基础上，把第 8 号节点的输出 conditioning 串两个 `MiniMaxH3AddGuide`：

```json
{
  "20": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["8", 0], "vae": ["4", 0], "latent": ["8", 1],
                    "image": ["6", 0], "frame_idx": 0}},
  "21": {"class_type": "LoadImage", "inputs": {"image": "h3_mid_anchor.png"}},
  "22": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["20", 0], "vae": ["4", 0], "latent": ["8", 1],
                    "image": ["21", 0], "frame_idx": -1}},
  "12": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["22", 0]}}
}
```

> `frame_idx: -1` 表示"最后一帧"，从结尾倒数。

### 8.4 全参考生成（ref2va）

```json
{
  "1": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
  "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
  "5": {"class_type": "LoadImage", "inputs": {"image": "ref_character.png"}},
  "6": {"class_type": "MiniMaxH3ReferenceToVideo",
        "inputs": {"clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
                   "prompt": "<Picture 1> walks through a sunlit market, greeting vendors. Audio: ambient market chatter, footsteps on stone.",
                   "width": 1344, "height": 768, "length": 124,
                   "ref_image_size": "match", "ref_image_1": ["5", 0]}},
  "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
  "8": {"class_type": "BasicScheduler",
        "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}},
  "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
  "10": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["6", 0]}},
  "11": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["7", 0],
                    "sigmas": ["8", 0], "latent_image": ["6", 1]}},
  "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
  "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
  "14": {"class_type": "CreateVideo",
         "inputs": {"images": ["12", 0], "fps": 24, "audio": ["13", 0],
                    "bit_depth": 8, "color_space": "sRGB"}}
}
```

> Autogrow 输入在 API JSON 里就是普通的 `ref_image_1`、`ref_video_1`、`ref_video_audio_1`、`ref_audio_1` 键名。

---

## 9. 加速与显存

### 9.1 官方口径的两条加速路线

| 方案 | 做法 | 注意 |
|---|---|---|
| Sage Attention | 装 `sageattention` wheel；用 KJNodes 的 `Patch Sage Attention KJ` 串在 `UNETLoader` 和 `BasicGuider` 之间，`sage_attention=auto`；或启动加 `--use-sage-attention` | 只 patch guider 那一路即可，scheduler 不用动 |
| Comfy Kitchen Attention | 加内置 `Model Attention Backend` 节点，backend 选 `comfy kitchen attention`；或启动加 `--use-ck-attention`（0.32.0+） | 接在 `LoraLoaderModelOnly` 之后、进 `BasicGuider` 之前 |

### 9.2 INT8 注意力的质量陷阱（必读）

**现象**：开启 Sage Attention 后，片段末尾出现 morphing、画面文字变成乱码。

**原因**：H3 最后几个 block 把大部分 attention-key 信号集中在少数通道上，INT8 核按行共享单一 scale 做量化会丢掉这部分信号。

**按 checkpoint 分两种处理**：

| Checkpoint | 处理 |
|---|---|
| `*_int8_convrot`（模板默认） | **Comfy Kitchen attention 不支持**，采样会崩（alignment error，ComfyUI issue #15529）。保持默认注意力；或者改用 bf16 版本 `minimax_h3_fl2va_pruned_bf16.safetensors` / `minimax_h3_ref2va_pruned_bf16.safetensors`（更吃显存）再换后端 |
| bf16 版本 | 换成 Comfy Kitchen attention 可消除伪影——它的 INT8 核在量化前做通道旋转，速度接近 Sage Attention 但保住了信号 |

Sage Attention 要求 fp16/bf16 张量，H3 有些层跑别的 dtype，控制台会打
`Input tensors must be in dtype of torch.float16 or torch.bfloat16, using pytorch attention instead`
——**这是预期内的**，那些层回退到标准注意力，生成照常。

### 9.3 稀疏注意力（内置，无需自定义节点）

`comfy_extras/nodes_sparse_attention.py` 提供 `BlockSparseAttention`，对 H3 走 chunked qkv producer（而不是通用 attention override）：

- Sol-Attn 自适应阈值 / SLA 风格 top-k / FastVideo VSA（3D video-cube tiling）
- `VSA_CUBE = (4, 4, 4)`，`PRODUCER_CHUNK = 4096`，`BLOCK_SIZE = 64`，`HEAD_DIM = 128`
- H3 的 conditioning 行作为 sink：packed prefix 对每个 query 保持精确
- VSA 需要 **FastH3 权重**（0.36.0+）

### 9.4 显存参考

- `supported_models.MiniMaxH3.memory_usage_factor = 0.114`
- `supported_inference_dtypes = [bfloat16, float32]` —— **不支持 fp8 推理 dtype**（`weight_dtype` 的 fp8 选项是"加载时量化"，不是推理 dtype）
- 33B 稠密 + Qwen3-VL-32B 文本编码器 → 多卡 / 大显存级别。CLIP 用 `nvfp4_awq` 版本可显著降低编码器占用
- DiT 的 ~13B AdaLN 分支在纯推理时可预计算缓存（上游 README 说法），但 ComfyUI 目前加载的是完整权重

---

## 10. 常见错误与排查

| 报错 / 现象 | 原因 | 处理 |
|---|---|---|
| `MiniMaxH3AddGuide expects a MiniMax H3 AV latent` | 接了普通视频 latent | 必须接 `MiniMaxH3ImageToVideo` / `ReferenceToVideo` 输出的 latent |
| `MiniMaxH3AddGuide needs an image or an audio to anchor` | image 和 audio 都没接 | 至少接一个 |
| `anchoring guide frames needs the vae input` | 接了 image 但没接 `vae` | 补上视频 VAE |
| `anchoring guide audio needs the audio_vae input` | 接了 audio 但没接 `audio_vae` | 补上音频 VAE |
| `frame_idx N is outside the video's M frames` | 锚点越界 | 减小 `frame_idx` 或用负数从尾部数 |
| `MiniMax H3 reference videos need at least 5 frames` | 参考视频太短 | 至少给 5 帧（24fps 下约 0.2s） |
| CLIP 加载后 conditioning 崩 / 维度不对 | `CLIPLoader.type` 没选 `minimax` | 改成 `minimax` |
| LoRA 报 shape mismatch | LoRA 与 pruned / 非 pruned 构建不匹配 | 用与 checkpoint 同构建蒸馏的 LoRA；Turbo LoRA 两者通吃 |
| 采样崩溃（alignment error） | int8_convrot checkpoint + Comfy Kitchen attention | 回退默认注意力，或换 bf16 checkpoint |
| 画末尾变形 / 文字乱码 | Sage Attention 的 INT8 量化 | 换 bf16 + Comfy Kitchen attention |
| 画面出现网格伪影 | shift 与 checkpoint 不匹配 | 8 步蒸馏构建保持 `shift_video=10`（FastH3）；常规构建 12.0 |
| 提示词里的 `<Picture 1>` 不生效 | 用了 R2V 节点但没接 `ref_image_1`，或用了 I2V 节点 | 参考标签只在 `MiniMaxH3ReferenceToVideo` 下有效 |
| 视频没声音 | 没接 `VAEDecodeAudio` → `CreateVideo.audio` | 补齐音频解码链 |
| 帧数被悄悄改了 | 17k+5 网格吸附 | 这是设计行为；用 6.2 的公式自己算 |

---

## 11. 进阶：与其他节点混用

| 场景 | 接法 |
|---|---|
| 拆解 / 重组 AV latent | `LTXVSeparateAVLatent`（拆成 video/audio 两条）、`LTXVConcatAVLatent`（拼回去）——这两个是通用的，`nodes_lt.py:901,977`，描述里明确写了 "any AV model, e.g. LTXV or MiniMax H3" |
| 只看画面不要声音 | `VAEDecode` 拿 `unbind()[0]`，`VAEDecodeAudio` 那一路不接即可 |
| 音频响度 | `vae_decode_audio()` 内部做了归一化：`std = torch.std(audio, dim=[1,2], keepdim=True) * 5.0; std[std<1.0]=1.0; audio /= std`。想自己控制响度就用 `LTXVSeparateAVLatent` 拆出来自己解码 |
| 换注意力后端 | `ModelAttentionBackend`（category `model/patch`），串在 LoRA 之后、guider 之前 |
| 768p → 2K | 本地模型只出 768p。2K 要么走官方 H3-Regenerate-2K API，要么自己在 ComfyUI 里接常规视频放大链路（如 `Upscale Video (SeedVR2 3B Int8)` 蓝图） |
| TAESD 快速预览 | `MiniMaxH3Video.taesd_decoder_name = "taeh3"`，把 `taeh3` 放到 `models/vae_approx/` |

---

## 12. 源码速查索引

```
comfy_extras/nodes_minimax_h3.py
  :30-35    CANVAS_MULTIPLE=32, BASE_SHORT_EDGE=768, MAX_PIXELS=768*1344,
            REF_IMAGE_SHORT_EDGE=2048, FPS=24, AUDIO_LATENT_FPS=40
  :38-51    align_frame_count / video_latent_t / temporal_shape（17k+5 网格）
  :54-65    adapt_canvas（768 短边 + 面积上限）
  :85-91    _empty_av_latent（video [B,24,T,H/16,W/16] + audio [B,32,2,T40]）
  :94       EmptyMiniMaxH3LatentAV
  :116      MiniMaxH3ImageToVideo（t2va / fl2va）
  :166      MiniMaxH3AddGuide
  :243      MiniMaxH3ReferenceToVideo（ref2va）
  :367      MiniMaxH3SigmaShift（display: ModelSamplingMiniMaxH3）
  :411      MiniMaxH3FunControlPatch
  :579      MiniMaxH3FunControlNetApply
  :624      MiniMaxH3Extension.get_node_list（注册表，6 个节点）

comfy/ldm/minimax/model.py
  :30-32    FRAME_PER_TOKEN=(1,4,4,4,4), FRAME_RESCALE=5/3,
            VISUAL_COND_TIMESTEP=0.999, AUDIO_COND_TIMESTEP=1.0
  :37-40    time_shift_sigma（音视频 schedule 互转）
  :474      MiniMaxH3Model
  :604      MiniMaxH3Model.forward（含 denoise_mask / audio_denoise_mask）

comfy/ldm/minimax/controlnet.py
  :20       MiniMaxH3FunControl（control_in_dim=49, injection_layers, inpaint_post_norm）
comfy/ldm/minimax/vae.py        :17 IMAGENET_MEAN / IMAGENET_STD
comfy/model_sampling.py         :338 ModelSamplingAV（audio_scale = shift/audio_shift）
comfy/supported_models.py       :964 MiniMaxH3（shift 12.0 / audio_shift 3.0）
comfy/model_detection.py        :390 H3 权重探测
comfy/latent_formats.py         :622 MiniMaxH3Video, :659 MiniMaxH3AV
comfy/text_encoders/minimax.py  :1-20 H3 presentation 说明（非 chat 模板）
nodes.py                        :340 VAEDecode 取 unbind()[0];  :1021 CLIPLoader type 列表
comfy_extras/nodes_audio.py     :98 vae_decode_audio 取 unbind()[-1]
comfy_extras/nodes_model_patch.py :306 Fun ControlNet 自动识别分支
blueprints/Image to Video (MiniMax H3).json   官方蓝图
```

---

## 13. 许可提醒

- 权重用 **MiniMax H3 Community License**，不是 MIT / Apache。
- 允许使用、修改、分发、做衍生模型；**商业使用有条件**（有年收入门槛 + 需署名 + 适用地区限制）。
- 本地生成内容的商用授权需通过 Comfy（官方转售方）取得；Comfy Cloud 上的生成已含商用权。
- 用在任何商业项目前，请读一遍 H3 仓库里的 LICENSE 原文。第三方整理的条款口径不完全一致，别以二手转述为准。
