# MiniMax H3 进阶实操手册：多帧锚定 + Fun ControlNet 视频修复

> 面向已经跑通基础 T2V / I2V / R2V 的人。基础内容见 `MINIMAX_H3_COMFYUI_GUIDE.md`。
> 本手册覆盖两块**只有读源码才能用对**的能力：
> - **Part I — 多帧锚定**（`MiniMaxH3AddGuide`）：在时间轴上钉住任意帧
> - **Part II — Fun ControlNet Union**（`MiniMaxH3FunControlNetApply`）：控制视频驱动 + 视频 inpainting
>
> 所有参数/常量/报错文案均取自本仓库源码；工作流层参数同步自 ComfyUI 官方文档
> （`docs.comfy.org/tutorials/video/minimax/minimax-h3-multiframe`、`.../minimax-h3-fun-controlnet`）。

---

## 0. 两块能力的共同底层：cond rows 是"钉住"的，不是"去噪"的

这是理解后面所有规则的关键。H3 把**所有东西打包成一条序列**（`PackedLayout`，`comfy/ldm/minimax/model.py:353`）：

```
[ text | ref blocks（仅 ref2va） | 关键帧 cond 行 | 目标音频 | 目标视频 ]
```

每一类 segment 有**自己的 timestep**：

```python
seg_t = {"text": t_v, "video": t_v, "audio": t_a,
         "cond": max(t_v, vis_aug),    "ref_img": max(t_v, vis_aug),
         "cond_audio": max(t_a, aud_aug), "ref_audio": max(t_a, aud_aug)}
```

其中 `VISUAL_COND_TIMESTEP = 0.999`、`AUDIO_COND_TIMESTEP = 1.0`，而 `t_v = 1 - sigma_v`。

**结论**：

1. 目标视频/音频行跑真实 sigma，**会被去噪**。
2. 关键帧 / 参考行被 pin 在 `≈1.0`（几乎完全干净），**永远不被去噪**。
3. 它们在**每一步都重新注入**（`_embed_and_pack` 每次 forward 都把 `cond_video_latents` 填回 `~img_update` 的位置）。
4. 所以"锚定"不是时序上的插值，而是**让模型每一步都看见这张图**——视频会自然穿过这个构图。

`img_update` / `audio_update` 布尔掩码就是"哪些行是目标、哪些行是条件"的开关：

```python
img_update.append(torch.zeros(n, dtype=torch.bool))    # 关键帧行 → 条件
...
img_update.append(torch.ones(n_video, dtype=torch.bool))  # 目标视频行 → 去噪
```

---

# Part I — 多帧锚定（Multiframe Reference）

## 1.1 它能干什么

| 玩法 | 做法 |
|---|---|
| 视频续写 | 把上一段的最后一帧钉在 `frame_idx=0`，生成下一段 |
| 多镜头短片 | 每个镜头首帧钉一个 `frame_idx`，模型自己补中间 |
| 中途构图控制 | 在片段中点钉一帧，强制构图经过它 |
| 音轨锚定 | 在某帧开始铺一段参考音频（音效/音乐），和画面一起对齐 |
| 首尾帧 + 中途锚 | `MiniMaxH3ImageToVideo` 给首尾，再串 `AddGuide` 补中间 |

## 1.2 模型与目录（官方 Multiframe 模板）

```
ComfyUI/models/
├── diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors
├── text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
├── vae/minimax_h3_video_vae_int8_convrot.safetensors      # 注意：这个模板用 int8_convrot 版，不是 fp16 版
├── vae/minimax_h3_audio_vae_fp32.safetensors
└── loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors
```

> ⚠️ 不同模板的视频 VAE 文件名不同：I2V 蓝图用 `minimax_h3_video_vae_fp16.safetensors`，Multiframe / FunCN 模板用 `minimax_h3_video_vae_int8_convrot.safetensors`。**别混**：VAE 和 DiT 的量化形态要匹配。
> ⚠️ Turbo LoRA 也分任务：`fl2v_turbo_8step`（I2V 蓝图）vs `ref2v_turbo_4step_v0.1`（Multiframe/FunCN）。

## 1.3 `MiniMaxH3AddGuide` 参数详解

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `positive` | CONDITIONING | — | — | 上游 conditioning。**串联多个 AddGuide 时把上一个的输出接到这里** | 节点连线 |
| `vae` | VAE (optional) | — | — | 视频 VAE。**接了 `image` 就必需**，否则抛 `anchoring guide frames needs the vae input` | 节点连线 |
| `audio_vae` | VAE (optional) | — | — | 音频 VAE。**接了 `audio` 就必需**，否则抛 `anchoring guide audio needs the audio_vae input` | 节点连线 |
| `latent` | LATENT | — | — | 目标 AV latent。用来取画布尺寸和总帧数 | R2V/I2V 的 latent 槽 |
| `image` | IMAGE (optional) | — | — | 锚定图或片段。多帧被裁到合法长度；**<5 帧只用第一张** | 可选 |
| `audio` | AUDIO (optional) | — | — | 从同一帧开始铺的音轨，按剩余时长裁剪 | 可选 |
| `frame_idx` | INT | 0 | -9999 ~ 9999 | 锚定帧号。**负数从结尾倒数**（-1 = 最后一帧） | `0` / `123` / `-1` |

**输出**：槽 0 = CONDITIONING（追加了一条 keyframe）。

## 1.4 三条硬规则（源码级）

### 规则 1：latent 必须是 H3 的 AV latent

```python
if not samples.is_nested or len(samples.tensors) != 2 \
   or samples.tensors[0].ndim != 5 or samples.tensors[0].shape[1] != 24:
    raise ValueError("MiniMaxH3AddGuide expects a MiniMax H3 AV latent")
```

四个条件全要满足：是 `NestedTensor`、恰好 2 个张量、视频张量 5 维、通道数 = 24。
接 `EmptyLatentImage` 或别的模型的 latent 直接崩。

### 规则 2：片段长度会被**向下**裁到 17k+5

```python
guide_frames = image.shape[0]
if guide_frames < 5:
    guide_frames = 1          # 少于 5 帧 → 只当单图用
else:
    while guide_frames % 17 != 5:
        guide_frames -= 1     # 向下吸附
```

| 合法片段长度（帧） | 秒数 @24fps |
|---|---|
| 5, 22, 39, 56, 73, 90, 107, 124, 141, 158, 175, 192, 209, 226, 243, 260, 277, 294, 311, 328, 345, 362 | 0.21s ~ 15.08s |

**上限 362 帧**跟目标视频一样（训练范围）。传 100 帧进去实际只用 90 帧。

### 规则 3：`frame_idx` + 片段长度必须落在视频内

```python
resolved_frame_index = frame_idx if frame_idx >= 0 else frame_count + frame_idx
if resolved_frame_index < 0 or resolved_frame_index + guide_frames > frame_count: raise ...
```

其中 `frame_count = sum(FRAME_PER_TOKEN[k % 5] for k in range(video.shape[2]))`，`FRAME_PER_TOKEN = (1,4,4,4,4)`。

**音轨还有额外限制**：

```python
max_rt = math.floor(samples.tensors[1].shape[-1] - FRAME_RESCALE * resolved_frame_index)
```

`FRAME_RESCALE = 5/3`。以 124 帧为例：`audio_t = round(124/24 × 40) = 207`，
`max_rt(123) = floor(207 - 206.67) = 0` → 抛 `frame_idx {} is past the end of the video's audio track`。
实际可用上限约 **`frame_count - 1`**。

> 也就是说：**画面锚点可以钉到最后一帧，音轨锚点最多钉到倒数第二帧附近**。

## 1.5 时间轴是怎么算的（PackedLayout 源码）

```python
cursor = float(text_len)
for blk in refs or ():
    cursor += _ref_t_span(blk)          # ref2va：先让参考块占据时间轴

for kf in keyframes:
    cond_t = cursor + FRAME_RESCALE * kf["resolved_frame_index"]
```

- 关键帧的**时间坐标由 `frame_idx` 决定**（不是由串联顺序决定）。
- 每像素帧在时间轴上是 `5/3` 个单位，每个音频 latent 帧是 `1.0`（`_audio_grid` 里 `t` 每次 +1）。
- 关键帧 cond 行排在 **text 之后、目标之前**；ref2va 下排在 **refs 之后**。
- 每条关键帧的视频行占 `vt × frame_rows` 行，其中
  `frame_rows = (latent_h // 2) × (latent_w // 2)`。

**算一笔账**（1344×768，124 帧）：

| 项 | 值 |
|---|---|
| latent 尺寸 | `84 × 48`（1344/16, 768/16） |
| 每帧行数 `frame_rows` | `(48//2) × (84//2)` = **1008** |
| 视频 latent 帧数 `latent_t` | `((124-5)//17)×5+2` = **37** |
| 视频总行数 | 37 × 1008 = **37,296** |
| 音频 latent 长度 `audio_t` | `round(124/24 × 40)` = **207** |
| 音频总行数 | 207 × 2 = **414** |
| 序列总长 | ≈ **37.7k + 文本长度** |

> 每多钉一帧，序列就多 `vt × 1008` 行。**锚定是拿序列长度换控制力**，钉太多会明显吃显存和速度。

## 1.6 完整工作流：R2V + 串联 AddGuide

```
UNETLoader(ref2va) ──┐
CLIPLoader(minimax) ─┤
VAELoader(视频) ──────┼─> MiniMaxH3ReferenceToVideo ──> positive(槽0) ──┐
VAELoader(音频) ──────┘        └─> latent(槽1) ─────────────────┐      │
                                                                │      │
LoadImage(锚A) ──> MiniMaxH3AddGuide(frame_idx=0, latent=槽1) ───┘      │
                        └─> positive ──┐                                │
LoadImage(锚B) ──> MiniMaxH3AddGuide(frame_idx=123, latent=槽1) ────────┤
                        └─> positive ──┘                                │
                                                                        │
BasicGuider(model, conditioning=最后一条 positive) <────────────────────┘
SamplerCustomAdvanced(noise, guider, sampler, sigmas, latent_image=槽1)
        │
        ├─> VAEDecode(视频VAE)      ──> CreateVideo.images
        └─> VAEDecodeAudio(音频VAE) ──> CreateVideo.audio
```

### API JSON：双锚点多镜头（含 Turbo LoRA）

```json
{
  "1":  {"class_type": "UNETLoader",
         "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
  "2":  {"class_type": "LoraLoaderModelOnly",
         "inputs": {"model": ["1", 0],
                    "lora_name": "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
                    "strength_model": 1.0}},
  "3":  {"class_type": "CLIPLoader",
         "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
  "4":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
  "5":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
  "6":  {"class_type": "LoadImage", "inputs": {"image": "shot1_start.png"}},
  "7":  {"class_type": "LoadImage", "inputs": {"image": "shot2_start.png"}},
  "8":  {"class_type": "MiniMaxH3ReferenceToVideo",
         "inputs": {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["5", 0],
                    "prompt": "<Picture 1> walks down a neon alley, then the shot cuts to <Picture 2> on a rooftop at dawn. Audio: rain, then distant wind.",
                    "width": 1344, "height": 768, "length": 124,
                    "ref_image_size": "match",
                    "ref_image_1": ["6", 0], "ref_image_2": ["7", 0]}},
  "9":  {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["8", 0], "vae": ["4", 0], "latent": ["8", 1],
                    "image": ["6", 0], "frame_idx": 0}},
  "10": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["9", 0], "vae": ["4", 0], "latent": ["8", 1],
                    "image": ["7", 0], "frame_idx": 123}},
  "11": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
  "12": {"class_type": "BasicScheduler",
         "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": 4, "denoise": 1.0}},
  "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": 20261008}},
  "14": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["10", 0]}},
  "15": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["13", 0], "guider": ["14", 0], "sampler": ["11", 0],
                    "sigmas": ["12", 0], "latent_image": ["8", 1]}},
  "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["4", 0]}},
  "17": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["15", 0], "vae": ["5", 0]}},
  "18": {"class_type": "CreateVideo",
         "inputs": {"images": ["16", 0], "fps": 24, "audio": ["17", 0],
                    "bit_depth": 8, "color_space": "sRGB"}}
}
```

### API JSON：音轨锚定（第 60 帧起铺一段音效）

```json
{
  "20": {"class_type": "LoadAudio", "inputs": {"audio": "impact_ripple.flac"}},
  "21": {"class_type": "MiniMaxH3AddGuide",
         "inputs": {"positive": ["8", 0], "audio_vae": ["5", 0], "latent": ["8", 1],
                    "audio": ["20", 0], "frame_idx": 60}}
}
```

> `LoadAudio` 是内置节点（`comfy_extras/nodes_audio.py:366`，输入键 `audio`，输出 `AUDIO`）。
> 也可以从视频里取音轨：`LoadVideo` → `GetVideoComponents` 的 `audio` 槽。

### `Canny` 参数提醒

`Canny`（`comfy_extras/nodes_canny.py:9`，display name "Detect Edges (Canny)"）的两个阈值是 **0.01–0.99 的归一化浮点**（默认 `0.4 / 0.8`），
不是 0–255 的像素阈值。写 100/200 会被前端拒绝。

## 1.7 官方给出的五条提示词/工作流要点

1. **按标签引用**：`<Picture 1>` = 第一个 `ref_images` 槽的图，以此类推。
2. **锚定 ≠ 参考**：**只接 `AddGuide` 的图对文本编码器不可见**。想让提示词也"看见"它，要**同时**接到 `ref_images` 槽里，才能用 `<Picture N>` 指代。
3. **`frame_idx` 用帧计数**（24fps）。官方模板用 `round(seconds * 24)` 换算。负数从结尾数。索引 + 片段长度必须落在时长内。
4. **加更多锚点**：整块复制（Load Image + Frame Index + Math Expression + Add Guide），把 `positive` **串成一条链**最后进 `BasicGuider`。
5. **Turbo 可选**：4 步 turbo LoRA 快很多，但音频和运动质量略降。

## 1.8 多帧锚定坑位表

| 现象 | 原因 | 处理 |
|---|---|---|
| `expects a MiniMax H3 AV latent` | 接了非 H3 latent | 接 R2V / I2V 节点的 latent 槽 |
| `needs an image or an audio to anchor` | 两个输入都空 | 至少接一个 |
| `anchoring guide frames needs the vae input` | 有 image 无 vae | 补视频 VAE |
| `anchoring guide audio needs the audio_vae input` | 有 audio 无 audio_vae | 补音频 VAE |
| `frame_idx N is outside the video's M frames` | 锚点越界 | 减小 idx 或改负数 |
| `a N frame guide clip at frame_idx M does not fit` | 锚点 + 片段超出时长 | 缩短片段或前移锚点 |
| `frame_idx N is past the end of the video's audio track` | 音轨锚点太靠后 | 音轨最多约 `frame_count - 1` |
| 锚定的图没起作用 | 图被裁到 <5 帧只取首帧 / resize 成 center crop 丢了构图 | 保证 ≥5 帧；先手动裁成目标比例 |
| 提示词里 `<Picture 1>` 没反应 | 图只接了 AddGuide 没接 `ref_images` | 两处都接 |
| 显存爆 / 极慢 | 每帧锚定多 1008×vt 行 | 减少锚点数量或降分辨率 |
| 锚点之间过渡生硬 | H3 本来就是"经过"而非插值 | 提示词里显式写时间轴分段（见基础文档 6.4） |

---

# Part II — Fun ControlNet Union / 视频 Inpainting

## 2.1 它能干什么

一个 checkpoint 同时支持 **Canny / Depth / HED / MLSD / Pose** 五种控制视频，另外支持 **mask 视频修复（inpainting）**。
官方明确：**`fl2va` 和 `ref2va` 两种 transformer 都能用**。

## 2.2 模型与目录

```
ComfyUI/models/
├── diffusion_models/
│   ├── minimax_h3_ref2va_pruned_int8_convrot.safetensors
│   └── rt_detr_v4-x-hgnet_fp16.safetensors        # SDPose 子图的人体检测
├── text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
├── vae/
│   ├── minimax_h3_video_vae_int8_convrot.safetensors
│   └── minimax_h3_audio_vae_fp32.safetensors
├── loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors
├── model_patches/
│   └── minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors
└── checkpoints/sdpose_wholebody_fp16.safetensors   # 官方 Pose 示例用
```

- Fun ControlNet 走 **`ModelPatchLoader`**（category `model/loaders`，标记 `EXPERIMENTAL`）→ 输出 `MODEL_PATCH`。
- 识别逻辑在 `comfy_extras/nodes_model_patch.py:306` 的 `is_minimax_h3_fun_state_dict(sd)`，要求同时命中 8 个键：
  `control_proj_in.weight`、`control_blocks.0.{adaln_proj.linear,after_proj,before_proj}.weight`、
  `control_blocks.0.attn.{qkv_proj,q_norm}.weight`、`control_blocks.0.mlp.fc1.weight`。
- 上游来源：`alibaba-pai/MiniMax-H3-Fun-Controlnet-Union`，Comfy-Org 重新打包在 `Comfy-Org/MiniMax-H3`。

## 2.3 `MiniMaxH3FunControlNetApply` 参数详解

| 参数 | 类型 | 默认值 | 范围/可选值 | 说明 | Demo 取值 |
|---|---|---|---|---|---|
| `model` | MODEL | — | — | 基础模型（UNETLoader 或 LoRA 之后） | 节点连线 |
| `model_patch` | MODEL_PATCH | — | — | `ModelPatchLoader` 的输出 | 节点连线 |
| `vae` | VAE | — | — | 视频 VAE，用来编码控制视频 / 被遮罩的源 | 节点连线 |
| `strength` | FLOAT | 1.0 | 0.0 ~ 10.0，step 0.01 | 控制强度。**官方：只在输出跑偏时才 >1** | `1.0` |
| `start_percent` | FLOAT (advanced) | 0.0 | 0.0 ~ 1.0 | 生效起点 | `0.0` |
| `end_percent` | FLOAT (advanced) | 1.0 | 0.0 ~ 1.0 | 生效终点 | `1.0` |
| `control_video` | IMAGE (optional) | — | — | 控制视频（Canny/Depth/HED/MLSD/Pose 预处理结果） | 可选 |
| `mask` | MASK (optional) | — | — | **`1` = 要重新生成的区域** | 可选 |
| `source_video` | IMAGE (optional) | — | — | 遮罩背后的原视频。**只有给了 mask 才读** | 可选 |

**输出**：槽 0 = MODEL（已注册 block patch）。

**提前返回**：`strength == 0` 或 `control_video` 与 `mask` 都为空时，原样返回输入模型（相当于没挂）。

## 2.4 工作原理：49 = 24 + 1 + 24

```python
control_in_dim = 49
patch_dim = 49 * 1 * 2 * 2 = 196        # patch_size = (1, 2, 2)
self.control_proj_in = Linear(196, hidden_size)
```

控制 latent 是三路拼接（`prepare_control_latent`）：

| 分量 | 通道数 | 来源 |
|---|---|---|
| 控制视频 latent（`hint`） | 24 | `control_video` 经 VAE 编码；没接时用 `zeros_like(masked_latent)` |
| 可见度图（`visibility_latent`） | 1 | `1 - mask`，trilinear 插值到 `(latent_t, latent_h, latent_w)` |
| 被遮罩的源 latent（`masked_latent`） | 24 | `source_video × visibility` 后编码；没给 source 时是全零 |

注入流程（`MiniMaxH3FunControlPatch`）：

```python
# 1) 每步判断是否生效
self.active = self.sigma_end <= sigma <= self.sigma_start

# 2) 首层建流：只有"目标视频行"填控制，cond/ref 行填零控制行
rows = torch.zeros(img_update.shape[0], patch_dim)
rows[img_update] = target_rows
c = h.clone()
c[layout.img_pos] = self.control_proj_in(rows)
self.control_stream = model.init_stream(pristine, control_latent, layout, t_emb)   # = before_proj(c) + h

# 3) 每个注入层跑一遍控制 block，取 skip 残差加回去
for block_index in injection_layers:
    control_stream, skip = model.step(i, control_stream, t_emb, mod_segments, rope_freqs, ...)
    skip[layout.audio_pos] = 0          # 音频位置强制清零
    out["img"].add_(skip, alpha=strength)
```

三个关键点：

1. **控制只作用于画面**：`skip[audio_pos] = 0`，音频流不受控制网影响。
2. **控制网和基模型共享 AdaLN 形态**：`init_stream` 会检查宽度，不匹配直接抛：
   ```
   MiniMax H3 controlnet adaln width {} does not match the base model's timestep embedding width {}:
   the controlnet and base checkpoint use different adaln forms (curve basis vs full),
   convert the controlnet to match the base model.
   ```
   → **pruned 基座必须配 pruned 控制网**。
3. **注入层由 checkpoint 决定**（`nodes_model_patch.py:312`）：
   ```python
   injection_layers = tuple(range(0, 50, 50 // num_blocks))
   # metadata["control_blocks_places"] 优先
   ```
   v1（5 块）→ `(0,10,20,30,40)`；v2（10 块）→ `(0,5,10,...,45)`。
   控制网代码强制 `injection_layers[0] == 0` 且严格递增。

## 2.5 尺寸与长度对齐（源码规则）

```python
latent_frames, latent_height, latent_width = target_shape[2:]
frame_count = max((latent_frames - 2) // 5, 0) * 17 + 5
width  = latent_width  * vae.spacial_compression_encode()
height = latent_height * vae.spacial_compression_encode()
```

| 目标长度 | latent_t | 反推 pixel frame_count | 控制视频处理方式 |
|---|---|---|---|
| 124 | 37 | `(37-2)//5×17+5` = **124** ✅ | 自洽 |
| 245 | 57 | `(57-2)//5×17+5` = 192 ⚠️ | 与 245 不一致时按下面规则处理 |

**控制视频长度不匹配时**（`_fit_frames`）：

```python
indices = torch.arange(frame_count, device=frames.device).clamp(max=frames.shape[0] - 1)
frames = common_upscale(frames[indices], width, height, "bilinear", "center")
```

- **比目标长** → 取前 `frame_count` 帧（后面被 clamp 掉）。
- **比目标短** → 最后一帧被重复（clamp 到 `shape[0]-1`），即"定格最后一帧"。
- resize 用 **bilinear + center crop**（对比：关键帧锚定用 lanczos + center）。

> 官方建议：想让控制视频长度精确匹配，把它的 `batch_size`（帧数）输出接到 `MiniMaxH3ReferenceToVideo` 的 `length` 输入。

编码后形状必须精确匹配，否则：
```
MiniMax H3 Fun VAE output shape {} does not match the target {}
```

## 2.6 五种控制类型怎么接

| 类型 | 预处理 | 提示 |
|---|---|---|
| Canny（边缘） | 内置 `Canny`（`comfy_extras/nodes_canny.py`） | 保结构，弱语义 |
| Depth（深度） | Depth Anything 3 教程链路 | 控空间层次 |
| HED（软边缘） | 对应预处理器 | 比 Canny 柔和 |
| MLSD（直线） | 对应预处理器 | 建筑/透视 |
| Pose（姿态） | 官方示例：SDPose 子图（需 `sdpose_wholebody_fp16.safetensors` + `rt_detr_v4-x-hgnet_fp16.safetensors`） | 人体动作复刻 |

取帧链路：`LoadVideo` → `GetVideoComponents`（`images` 槽）→ 预处理 → `control_video`。
或者 `LoadVideo` → `Video Slice`（Trim）→ `GetVideoComponents`。

## 2.7 视频 Inpainting：两条机制，别搞混

这是最容易踩的坑。ComfyUI 里"局部重绘"有**两套独立机制**，H3 都支持：

| | 机制 A：FunCN 的 `mask` + `source_video` | 机制 B：`SetLatentNoiseMask` |
|---|---|---|
| 节点 | `MiniMaxH3FunControlNetApply` | `SetLatentNoiseMask`（`nodes.py:1567`） |
| 语义 | `1` = 重绘区；`0` 区由 `source_video` 提供内容 | `1` = 重绘区（常规 ComfyUI 语义），一致 |
| 原理 | 把可见度图 + 遮罩后的源 latent 送进控制网作为**条件** | 给 latent 打 `noise_mask`，模型把保留行 pin 在 cond timestep |
| 是否需控制网 | **是** | **否**，单独可用 |
| 源码 | `prepare_control_latent` 的 visibility 分支 | `scale_latent_inpaint`（`model_base.py:2264`）+ `mask_row_values` |
| 官方模板用法 | ✅ 推荐路径 | 进阶/自定义 |

**机制 B 的源码路径**（`model_base.py:2271`）：

```python
def scale_latent_inpaint(self, sigma, noise, latent_image, ...):
    aug = VISUAL_COND_TIMESTEP   # 0.999
    cleans[0] = aug * cleans[0] + (1.0 - aug) * noises[0]
```

被保留区域按 `0.999` 的强度注入噪声（等价于条件行），所以不会被完全重画。
遮罩会被池化到 token 网格：视频按 `2×2` DiT patch 做 `amax`，音频按 latent 帧做 `amax`（`_pool_masks_to_token_grid`）。

**结论**：
- 只是"按遮罩重画一块" → **机制 B 就够**，不需要控制网。
- 要"重画的同时还被控制视频约束" → **机制 A**（或 A+B 一起）。
- 官方模板走 A。

### Inpainting 的 `inpaint_post_norm` 细节

v2 checkpoint（metadata `inpaint_masked_pixel_mode == "post_norm"`）在 VAE 归一化**之后**才遮罩，
于是洞里填的是 **ImageNet 均值灰**而不是黑色：

```python
IMAGENET_MEAN = (0.485, 0.456, 0.406)
masked += (1.0 - visibility) * torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1)
```

原因：VAE 把中灰归一化到 0，填中灰 = latent 空间的"空"。这是 checkpoint 自带属性，不用手动设。

## 2.8 完整工作流：Pose 控制视频

```
LoadVideo ──> GetVideoComponents ──> images ──> [SDPose 子图] ──> control_video
                                                                      │
UNETLoader(ref2va) ──> LoraLoaderModelOnly ──> MiniMaxH3FunControlNetApply <── ModelPatchLoader
                                                       │                          (model_patches)
                                                       ↓ MODEL
MiniMaxH3ReferenceToVideo ──> positive ──> BasicGuider(model=上面那个 MODEL)
                          └─> latent ────────────────> SamplerCustomAdvanced.latent_image
```

### API JSON：控制视频驱动（Canny 示例）

```json
{
  "1":  {"class_type": "UNETLoader",
         "inputs": {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
  "2":  {"class_type": "CLIPLoader",
         "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
  "3":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
  "4":  {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
  "5":  {"class_type": "ModelPatchLoader",
         "inputs": {"name": "minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors"}},
  "6":  {"class_type": "LoadVideo", "inputs": {"file": "dancer_source.mp4"}},
  "7":  {"class_type": "GetVideoComponents", "inputs": {"video": ["6", 0]}},
  "8":  {"class_type": "Canny",
         "inputs": {"image": ["7", 0], "low_threshold": 0.4, "high_threshold": 0.8}},
  "9":  {"class_type": "MiniMaxH3FunControlNetApply",
         "inputs": {"model": ["1", 0], "model_patch": ["5", 0], "vae": ["3", 0],
                    "strength": 1.0, "start_percent": 0.0, "end_percent": 1.0,
                    "control_video": ["8", 0]}},
  "10": {"class_type": "MiniMaxH3ReferenceToVideo",
         "inputs": {"clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0],
                    "prompt": "A dancer performs the same routine on a rain-slick rooftop at night. Audio: muffled music, wet footsteps.",
                    "width": 1344, "height": 768, "length": 124,
                    "ref_image_size": "match"}},
  "11": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
  "12": {"class_type": "BasicScheduler",
         "inputs": {"model": ["9", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}},
  "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": 7}},
  "14": {"class_type": "BasicGuider", "inputs": {"model": ["9", 0], "conditioning": ["10", 0]}},
  "15": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["13", 0], "guider": ["14", 0], "sampler": ["11", 0],
                    "sigmas": ["12", 0], "latent_image": ["10", 1]}},
  "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 0]}},
  "17": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["15", 0], "vae": ["4", 0]}},
  "18": {"class_type": "CreateVideo",
         "inputs": {"images": ["16", 0], "fps": 24, "audio": ["17", 0],
                    "bit_depth": 8, "color_space": "sRGB"}}
}
```

### API JSON：视频 Inpainting（遮罩重绘右下角字幕区）

```json
{
  "20": {"class_type": "LoadImageMask", "inputs": {"image": "burnin_mask.png", "channel": "alpha"}},
  "21": {"class_type": "MiniMaxH3FunControlNetApply",
         "inputs": {"model": ["1", 0], "model_patch": ["5", 0], "vae": ["3", 0],
                    "strength": 1.0, "start_percent": 0.0, "end_percent": 1.0,
                    "mask": ["20", 0], "source_video": ["7", 0]}},
  "22": {"class_type": "BasicGuider", "inputs": {"model": ["21", 0], "conditioning": ["10", 0]}},
  "23": {"class_type": "BasicScheduler",
         "inputs": {"model": ["21", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}}
}
```

> `source_video` 用 `GetVideoComponents` 的 `images` 槽（原视频帧）。
> 若不给 `source_video`，源码会填全零（`torch.zeros(frame_count, 3, height, width)`），
> 配合 `inpaint_post_norm` 就是"灰底重绘"——通常不是你想要的，所以**inpainting 一定要接 `source_video`**。

### API JSON：不用控制网的纯遮罩重绘（机制 B）

```json
{
  "30": {"class_type": "SetLatentNoiseMask",
         "inputs": {"samples": ["10", 1], "mask": ["20", 0]}},
  "31": {"class_type": "SamplerCustomAdvanced",
         "inputs": {"noise": ["13", 0], "guider": ["14", 0], "sampler": ["11", 0],
                    "sigmas": ["12", 0], "latent_image": ["30", 0]}}
}
```

> 注意：`SetLatentNoiseMask` 的 `samples` 要接 **AV latent**（R2V 的槽 1），
> 源码 `comfy/samplers.py:1298` 会处理 `denoise_mask.is_nested`。

## 2.9 官方给出的五条要点

1. **视频长度**：目标 5–15 秒，走 17n+5 网格（124 帧 = 5 秒）。控制视频比目标长→截前帧；比目标短→定格末帧。想精确匹配就把 `batch_size` 接到 `length`。
2. **引导与强度**：`guidance_scale` 保持 **1.0**；只有输出跑离控制时，才把 `strength` 调到 >1。
3. **视频修复**：`mask` 里 `1` = 重绘区，其余区域保持不动（由 `source_video` 提供内容）。
4. **Turbo 可选**：4 步 LoRA 更快，音频和运动质量略降。
5. **控制视频预处理**：ComfyUI 内置了各类型的预处理器（Canny 节点、Depth Anything 3 等）。

> 关于 `guidance_scale`：H3 是 **CFG 蒸馏** checkpoint，`BasicGuider` 本身也没有 cfg 输入
> （只有 `model` + `conditioning`）。所以默认就是 cfg=1。**如果你换成 `CFGGuider`，务必把 cfg 设为 1.0**，
> 否则会双重引导把画面打死。

## 2.10 Fun ControlNet 坑位表

| 现象 | 原因 | 处理 |
|---|---|---|
| `controlnet adaln width ... does not match ... curve basis vs full` | 控制网与基座的 adaln 形态不一致 | pruned 基座配 pruned 控制网 |
| `MiniMax H3 Fun VAE output shape ... does not match the target ...` | 控制视频/源编码后形状不符 | 检查分辨率是否被 16 整除、帧数网格 |
| 控制网完全没生效 | `strength=0` 或 control_video+mask 都空 → 提前返回 | 至少接一个，strength > 0 |
| 控制生效但很弱 | `strength` 太低 / `end_percent` 太早 | 提高 strength（官方：必要时 >1）；end_percent 保持 1.0 |
| 音频被控制网搞乱 | 不会——`skip[audio_pos]=0` | 若真有问题，检查是否误用了别的 patch |
| inpainting 后非遮罩区也变了 | 没接 `source_video`，源被填成全零/灰 | 接 `source_video` |
| inpainting 边缘有灰块 | `inpaint_post_norm`（v2 checkpoint）按中灰填洞 | 正常行为；给足 `source_video` 并羽化遮罩 |
| Pose 示例报缺模型 | 少了 `sdpose_wholebody_fp16.safetensors` / `rt_detr_v4-x-hgnet_fp16.safetensors` | 按 2.2 补齐 |
| `MiniMax H3 supports batch size 1` | 传了 batch > 1 | H3 只支持 batch 1 |
| 遮罩语义搞反 | `1` 是重绘区，不是保留区 | 用 `InvertMask` 翻过来 |

---

# Part III — 两者组合与排错

## 3.1 组合：多帧锚定 + 控制视频

两者**互不冲突**，因为作用于不同层面：

| | 作用层 | 注入位置 |
|---|---|---|
| 多帧锚定 | conditioning（`minimax_keyframes`）→ cond 行 | 序列里作为 `cond` / `cond_audio` segment |
| Fun ControlNet | model patch（block 残差） | `out["img"].add_(skip)`，且 `skip[audio_pos]=0` |

串联顺序：

```
UNETLoader ──> (LoRA) ──> MiniMaxH3FunControlNetApply ──> BasicGuider.model
MiniMaxH3ReferenceToVideo ──> AddGuide ×N ──> BasicGuider.conditioning
```

> 注意 `BasicScheduler` 的 `model` 也要接**打完 patch 的模型**（和 `BasicGuider` 同一个），
> 否则 sigma 调度用的是未 patch 模型的 shift（虽然 H3 的 shift 来自模型定义，通常一致，但保持同一个更安全）。

## 3.2 排错速查（按报错文案反查源码）

| 报错文案 | 出处 |
|---|---|
| `MiniMaxH3AddGuide expects a MiniMax H3 AV latent` | `nodes_minimax_h3.py:193` |
| `MiniMaxH3AddGuide needs an image or an audio to anchor` | `nodes_minimax_h3.py:196` |
| `anchoring guide frames needs the vae input` | `nodes_minimax_h3.py:205` |
| `anchoring guide audio needs the audio_vae input` | `nodes_minimax_h3.py:227` |
| `frame_idx {} is outside the video's {} frames` | `nodes_minimax_h3.py:216` |
| `a {} frame guide clip at frame_idx {} does not fit in the video's {} frames` | `nodes_minimax_h3.py:217` |
| `frame_idx {} is past the end of the video's audio track` | `nodes_minimax_h3.py:232` |
| `MiniMax H3 Fun VAE output shape {} does not match the target {}` | `nodes_minimax_h3.py:434` |
| `MiniMax H3 Fun control injection layers must start at layer 0` | `controlnet.py:32` |
| `MiniMax H3 Fun control injection layers must be unique and increasing` | `controlnet.py:34` |
| `MiniMax H3 controlnet adaln width ... curve basis vs full` | `controlnet.py:49` |
| `MiniMax H3 control input has {} columns but the model patch expects {}` | `controlnet.py:60` |
| `MiniMax H3 supports batch size 1` | `model.py:652` |
| `MiniMax H3 reference videos need at least 5 frames` | `nodes_minimax_h3.py:330` |

## 3.3 源码索引

```
comfy_extras/nodes_minimax_h3.py
  :166-241   MiniMaxH3AddGuide（校验 / 片段吸附 / 音轨裁剪 / keyframes 追加）
  :411-577   MiniMaxH3FunControlPatch（prepare_control_latent / before_block / after_block）
  :579-621   MiniMaxH3FunControlNetApply

comfy/ldm/minimax/controlnet.py
  :20-44     MiniMaxH3FunControl（control_in_dim=49, injection_layers, inpaint_post_norm）
  :46-69     init_stream（控制行填充：只填 img_update 行）
  :71-74     step（跑控制 block，返回 after_proj 残差）
  :77-87     is_minimax_h3_fun_state_dict（8 键识别）

comfy/ldm/minimax/model.py
  :30-32     FRAME_PER_TOKEN / FRAME_RESCALE / VISUAL_COND_TIMESTEP / AUDIO_COND_TIMESTEP
  :353-472   PackedLayout（segment 划分、img_update/audio_update、cursor 时间轴）
  :535-560   _cond_video_rows / _cond_audio_rows（条件噪声增强 aug）
  :562-601   _embed_and_pack（每次 forward 把 cond 行填回 ~img_update 位置）
  :647-...   _forward（seg_t 分配、mask 行 timestep、layout 复用）

comfy/model_base.py
  :2194-2229 extra_conds（payload 组装、PackedLayout 预建）
  :2231-2248 _pool_masks_to_token_grid / _token_grid_masks
  :2264-2273 scale_latent_inpaint（机制 B 的保留区噪声注入）
  :2162-2177 process_latent_in/out（audio_scale 缩放与还原）

comfy_extras/nodes_model_patch.py
  :247-259   ModelPatchLoader（读 models/model_patches）
  :306-334   H3 Fun ControlNet 识别与构造（injection_layers 推导、metadata 读取）

comfy/ldm/minimax/vae.py   :17 IMAGENET_MEAN / IMAGENET_STD
nodes.py                   :1567 SetLatentNoiseMask
comfy_extras/nodes_video.py :312 GetVideoComponents, :348 LoadVideo, :448 Video Slice
comfy_extras/nodes_mask.py  :184 SolidMask, :207 InvertMask, :307 FeatherMask, :355 GrowMask
comfy_extras/nodes_canny.py :13 Canny
```
