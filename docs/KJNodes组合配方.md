# KJNodes 玩法与常见搭配详解

> 配套文档：`KJNODES_NODES_GUIDE.md`（单节点参数字典）。
> **本文讲的是「怎么搭」**——哪些节点该凑在一起用、按什么顺序、为什么、参数怎么调。
> 节点 ID 与参数默认值全部以 **KJNodes v1.5.2**（共 236 个注册节点）源码核对为准。
>
> **demo 里的约定**：
> - `"0"` / `"ckpt"` / `"img"` 等是**占位节点 ID**，替换成你工作流里的真实 ID
> - `["节点ID", 槽位]` = 连线；字面量 = 控件值
> - 所有 JSON 块均已通过 `json.loads` 校验

---

## 0. 先看这一页：KJNodes 的五条心法

在具体玩法之前，先讲透 KJNodes 的设计哲学——理解这五条，你自己就能组合出新玩法。

### 心法 1：**「尺寸由上游决定，不要手填」**

内置 `EmptyLatentImage` 的宽高是手填的，一旦上游改了图尺寸，latent 就对不上。

**KJ 的解法**：`ImageResizeKJv2` 的**输出槽 1/2** 会吐出「**对齐后的实际宽高**」，把它接给 `EmptyLatentImage`：

```
ImageResizeKJv2.IMAGE  → VAEEncode
ImageResizeKJv2.width  → EmptyLatentImage.width    ← 保证严格一致
ImageResizeKJv2.height → EmptyLatentImage.height
```

> 为什么重要：`divisible_by=8` 会把 1023 改成 1024。如果你手填 1024 而实际是 1016，VAE 编码就会尺寸不匹配。

### 心法 2：**「裁出来 → 处理 → 贴回去」是通用范式**

不只适用于锐化。中间那一步可以是任何东西：重绘、换脸、放大、ControlNet、风格迁移……

```
BatchCropFromMask ─┬─(0) 原图 ────────────────┐
                   ├─(1) 裁出的小图 → [任意处理] ─┤
                   └─(2) BBOX ─────────────────┤
                                                ↓
                                          BatchUncrop
```

好处：**小图省显存 + 细节更集中**（同样的步数，注意力全在物体上）。

### 心法 3：**「清显存的节点要插在『断层』上」**

`VRAM_Debug` 不是随便放的。放在**两种重模型交替**的位置才有效——比如「UNet 采样结束 → VAE 解码开始」之间，此时 UNet 占的显存可以安全释放。

放错位置（比如放在同一模型的链路中间）只会拖慢，不省显存。

### 心法 4：**「加速补丁有先后顺序」**

```
CheckpointLoader
   ↓
PathchSageAttentionKJ     ← 先改 attention 实现
   ↓
TorchCompileModelAdvanced ← 再编译（把改过的图编译掉）
   ↓
ModelPreviewOverrideKJ    ← 最后挂预览（不参与编译）
   ↓
KSampler
```

**反了会怎样**：先 compile 再打补丁 → 补丁会让编译缓存失效，每次都重编译，比不加速还慢。

### 心法 5：**「Lazy 分支是免费的性能开关」**

`LazySwitchKJ` 未选中的分支**根本不执行**（不是执行完丢弃）。所以：

```
BOOLConstant(use_upscale)
   ↓ switch
LazySwitchKJ ─ on_true  → [整条放大链路]  ← 关掉时零开销
             └ on_false → 直连
```

这比「bypass 节点」更强——bypass 只是跳过，lazy 是连执行都不发起。

---

## 1. 玩法速查表

| # | 玩法 | 核心节点组合 | 解决什么 |
|---|---|---|---|
| 1 | 尺寸管家 | `ImageResizeKJv2` → `EmptyLatentImage` | 图与 latent 尺寸永远一致 |
| 2 | 批量调色流水线 | `LoadImagesFromFolderKJ` → `ColorMatchV2` → `SaveImageKJ` | 一批图统一成参考图色调 |
| 3 | 物体级精修回环 | `BatchCLIPSeg` → `GrowMaskWithBlur` → `BatchCropFromMask` → 处理 → `BatchUncrop` | 只精修画面里某个物体 |
| 4 | 批量高清放大 | `ImageUpscaleWithModelBatched` + `VRAM_Debug` | 一批图放大不爆显存 |
| 5 | 图序列转动画 | `LoadImagesFromFolderKJ` → `TransitionImagesInBatch` / `CrossFadeImages` → `PreviewAnimation` | 静态图做成带转场的动画 |
| 6 | 遮罩可视化调试 | `DrawMaskOnImage` + `GetMaskSizeAndCount` + `BboxVisualize` | 蒙版看不见、对不对无从判断 |
| 7 | 曲线驱动权重 | `SplineEditor` → `WeightScheduleConvert` → `FloatToMask` | 用曲线控制逐帧强度 |
| 8 | 图/蒙版转权重 | `MaskOrImageToWeight` | 反向：从画面亮度生成权重序列 |
| 9 | 显存救急三件套 | `VRAM_Debug` + `ModelMemoryUseReportPatch` + CUDAMemory 系列 | 定位 OOM 出在哪 |
| 10 | 加速链路 | `PathchSageAttentionKJ` → `TorchCompileModelAdvanced` → `ModelPreviewOverrideKJ` | 提速 + 实时预览 |
| 11 | 懒分支开关 | `BOOLConstant` → `LazySwitchKJ` | 一键开关整条子图 |
| 12 | 多条件/区域提示词 | `ConditioningMultiCombine` + `ConditioningSetMaskAndCombine` | 多提示词、分区控制 |
| 13 | 循环视频消接缝 | `VAEDecodeLoopKJ` | 首尾帧接不上的接缝 |
| 14 | 探针与自动化 | `GetImageSizeAndCount` + `SimpleCalculatorKJ` + `INTConstant` | 尺寸/数量自动传给下游 |
| 15 | 外扩作画 | `ImagePadForOutpaintMasked` → inpaint | 给图加边再补内容 |
| 16 | 批量网格预览 | `ImageConcatFromBatch` / `ImageGridComposite2x2` | 一眼看完整个 batch |

---

## 2. 玩法详解

### 玩法 1｜尺寸管家：让图和 latent 永不脱节

**问题**：内置 `EmptyLatentImage` 手填宽高，一旦上游缩放节点改了实际输出（尤其开了 `divisible_by`），latent 尺寸就对不上 → VAE 编码报错或结果错位。

**解法**：用 `ImageResizeKJv2` 的**输出槽 1（width）/ 2（height）**直接驱动 `EmptyLatentImage`。

```
源图 → ImageResizeKJv2 ─┬─(0) IMAGE  → VAEEncode.pixels
                        ├─(1) width  → EmptyLatentImage.width
                        ├─(2) height → EmptyLatentImage.height
                        └─(3) mask   → SetLatentNoiseMask.mask (可选)
```

**完整 demo**（图生图，尺寸全链路自动）

```json
{
  "1": { "class_type": "ImageResizeKJv2", "inputs": {
    "image": ["img", 0],
    "width": 1024, "height": 1024,
    "upscale_method": "lanczos",
    "keep_proportion": "pad",
    "pad_color": "0, 0, 0",
    "crop_position": "center",
    "divisible_by": 8 } },
  "2": { "class_type": "VAEEncode", "inputs": {
    "pixels": ["1", 0], "vae": ["ckpt", 2] } },
  "3": { "class_type": "EmptyLatentImage", "inputs": {
    "width": ["1", 1], "height": ["1", 2], "batch_size": 1 } },
  "4": { "class_type": "KSampler", "inputs": {
    "model": ["ckpt", 0], "positive": ["pos", 0], "negative": ["neg", 0],
    "latent_image": ["2", 0],
    "seed": 42, "steps": 20, "cfg": 7.0,
    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 0.6 } }
}
```

**调优**
- `divisible_by` 接 SD 系模型用 **8**；接某些视频模型可能需要 **16** 或 **32**，看模型要求。
- `keep_proportion` 选 `pad` 时，黑边会被 VAE 编码进去。若不想把黑边当内容，改选 `crop`。

**踩坑**
- 输出槽 1/2 是 **INT**，能直接接 `EmptyLatentImage.width`。但**不能**接给需要 INT 的 `INTConstant`（那是个控件不是插槽）。
- 一定要 `divisible_by ≥ 8`，否则 latent 尺寸可能是小数。

---

### 玩法 2｜批量调色流水线：一张参考图统一整个文件夹

**问题**：一批产品图/剧照来自不同来源，色调不一致，要统一成某一张的调子。

**链路**

```
LoadImagesFromFolderKJ ─┬─(0) image ─→ ColorMatchV2.image_target
参考图 (LoadImage) ─────┴───────────→ ColorMatchV2.image_ref
                                            ↓
                                      ImageResizeKJv2
                                            ↓
                                        SaveImageKJ
```

**完整 demo**

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/products",
    "width": 1024, "height": 1024,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "ColorMatchV2", "inputs": {
    "image_target": ["1", 0], "image_ref": ["ref", 0],
    "method": "mkl", "strength": 0.85, "multithread": true } },
  "3": { "class_type": "ImageResizeKJv2", "inputs": {
    "image": ["2", 0],
    "width": 1024, "height": 1024,
    "upscale_method": "lanczos",
    "keep_proportion": "pad",
    "pad_color": "255, 255, 255",
    "divisible_by": 8 } },
  "4": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["3", 0],
    "filename_prefix": "products/unified",
    "output_folder": "output",
    "caption_file_extension": ".txt",
    "caption": "color matched to reference" } }
}
```

**参数调优**

| 场景 | `method` | `strength` | 说明 |
|---|---|---|---|
| 通用/拿不准 | `mkl` | `0.8 ~ 1.0` | 默认，最稳 |
| 参考图与目标图色差极大 | `reinhard` | `0.6 ~ 0.8` | Lab 空间，温和不易过冲 |
| 想强力拉过去 | `hm-mkl-hm` | `0.7 ~ 0.9` | 组合算法，最强也最容易过冲 |
| batch 很大（几百张） | `reinhard_lab_gpu` | `1.0` | GPU 加速版，快很多 |

**踩坑**
- `strength` 设 `1.0` 有时会让暗部死黑。**先试 0.85**，不够再加。
- 参考图与目标图的**分辨率不必相同**，算法会处理；但**长宽比差太远**效果会变差。
- `keep_aspect_ratio` 只在 `LoadImagesFromFolderKJ` 里叫这个名字，在 `ImageResizeKJv2` 里叫 `keep_proportion` —— 别搞混。

---

### 玩法 3｜物体级精修回环：只精修画面里的某个物体 ★最实用

**问题**：一张合影里只想让「人脸」更清晰，直接全图锐化会让背景也变脏；直接全图重绘会改掉不想改的地方。

**解法**：用 CLIPSeg（文本抠图）拿到蒙版 → 裁出物体 → 只在小图上处理 → 贴回去。

```
图片 ─→ BatchCLIPSeg(text="face") ─(0) MASK
                                      ↓
                              GrowMaskWithBlur (膨胀+羽化)
                                      ↓
BatchCropFromMask(original_images=图, masks=蒙版)
   ├─(0) 原图 ──────────────────────────────┐
   ├─(1) 裁出的小图 → ImageSharpenKJ ───────┤
   └─(2) BBOX ─────────────────────────────┤
                                            ↓
                                       BatchUncrop
                                            ↓
                                    DrawMaskOnImage (检查蒙版对不对)
```

**完整 demo**（用文本抠出人脸并锐化）

```json
{
  "1": { "class_type": "DownloadAndLoadCLIPSeg", "inputs": {
    "model": "Kijai/clipseg-rd64-refined-fp16" } },
  "2": { "class_type": "BatchCLIPSeg", "inputs": {
    "images": ["img", 0], "opt_model": ["1", 0],
    "text": "a face",
    "threshold": 0.5, "binary_mask": true, "combine_mask": false, "use_cuda": true,
    "blur_sigma": 2.0, "invert": false, "image_bg_level": 0.5 } },
  "3": { "class_type": "GrowMaskWithBlur", "inputs": {
    "mask": ["2", 0],
    "expand": 12, "incremental_expandrate": 0.0,
    "tapered_corners": true, "flip_input": false,
    "blur_radius": 8.0, "lerp_alpha": 1.0,
    "decay_factor": 1.0, "fill_holes": true } },
  "4": { "class_type": "BatchCropFromMask", "inputs": {
    "original_images": ["img", 0], "masks": ["3", 0],
    "crop_size_mult": 1.3, "bbox_smooth_alpha": 0.5 } },
  "5": { "class_type": "ImageSharpenKJ", "inputs": {
    "image": ["4", 1],
    "method": { "method": "adaptive_usm", "strength": 0.8, "radius": 1.0, "threshold": 0.05 } } },
  "6": { "class_type": "BatchUncrop", "inputs": {
    "original_images": ["4", 0], "cropped_images": ["5", 0], "bboxes": ["4", 2],
    "border_blending": 0.3, "crop_rescale": 1.0,
    "border_top": true, "border_bottom": true,
    "border_left": true, "border_right": true } },
  "7": { "class_type": "DrawMaskOnImage", "inputs": {
    "image": ["6", 0], "mask": ["3", 0],
    "color": "255, 0, 0, 128", "device": "cpu" } }
}
```

**为什么这么搭**

| 环节 | 必要性 |
|---|---|
| `GrowMaskWithBlur` | 蒙版**必须**膨胀羽化，否则贴回去时有硬边接缝。`expand=12` + `blur_radius=8` 是常用起手 |
| `crop_size_mult=1.3` | 裁的时候多带 30% 上下文，给处理留余地；**设 1.0 会裁得贴边，容易切掉物体** |
| `BatchUncrop.border_blending=0.3` | 边缘融合，比默认 0.25 更柔。设 0 会有明显接缝 |
| `DrawMaskOnImage` | **调试用**——把蒙版以半透明红色画在图上，一眼看出抠得对不对 |

**调优**

| 现象 | 调什么 |
|---|---|
| 抠多了（背景也被选中） | 调高 `BatchCLIPSeg.threshold`（0.5 → 0.7） |
| 抠少了（物体缺一块） | 调低 `threshold`（0.5 → 0.3） |
| 蒙版边缘有锯齿 | 调大 `blur_sigma`（2.0 → 4.0） |
| 贴回去有接缝 | 调大 `border_blending`（0.25 → 0.4）和 `blur_radius` |
| 裁出来的图太糊 | 说明原图分辨率不够，先整体放大再走这条链路 |

**踩坑**
- `BatchCropFromMask` 的**槽位千万别接错**：槽 0=原图、槽 1=裁出图、槽 2=BBOX。接错就贴不回去。
- `BatchCLIPSeg` 需要**下载模型**（`DownloadAndLoadCLIPSeg` 会自动下），首次运行要联网。
- 不想用 CLIPSeg 也可以用 `ColorToMask`（纯色抠图）或手绘蒙版替代，链路完全一样。

---

### 玩法 4｜批量高清放大：不爆显存地放大一整批

**问题**：内置 `ImageUpscaleWithModel` 一次吃整个 batch，图多就直接 OOM。

**解法**：`ImageUpscaleWithModelBatched` 的 `per_batch` 参数**分块处理**，前后插 `VRAM_Debug`。

```
LoadImagesFromFolderKJ
        ↓
  VRAM_Debug (清一次，腾地方)   ← 断层 1
        ↓
ImageUpscaleWithModelBatched (per_batch=4)
        ↓
  VRAM_Debug (再清一次)         ← 断层 2
        ↓
    SaveImageKJ
```

**完整 demo**

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/lowres",
    "width": -1, "height": -1,
    "keep_aspect_ratio": "stretch",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "VRAM_Debug", "inputs": {
    "empty_cache": true, "gc_collect": true, "unload_all_models": false,
    "image_pass": ["1", 0] } },
  "3": { "class_type": "ImageUpscaleWithModelBatched", "inputs": {
    "upscale_model": ["upscale_model", 0],
    "images": ["2", 1],
    "per_batch": 4,
    "downscale_ratio": 1.0,
    "downscale_method": "lanczos",
    "precision": "float32" } },
  "4": { "class_type": "VRAM_Debug", "inputs": {
    "empty_cache": true, "gc_collect": true, "unload_all_models": false,
    "image_pass": ["3", 0] } },
  "5": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["4", 1],
    "filename_prefix": "upscaled/4x",
    "output_folder": "output" } }
}
```

**参数调优**

| 现象 | 调整 |
|---|---|
| 还是 OOM | 调小 `per_batch`（4 → 2 → 1） |
| 太慢 | 调大 `per_batch`（4 → 8），或 `precision` 改 `float16` |
| 显存够但想更快 | `precision=bfloat16`（需显卡支持） |
| 放大后整体偏软 | 后接 `ImageSharpenKJ`（`rcas`, `strength=0.5`） |

**踩坑**
- `VRAM_Debug` 的 `image_pass` 是**槽 1**（槽 0 是 `any_output`）。上面 demo 里 `["2", 1]` 就是取图像透传。
- `unload_all_models=True` 会把放大模型也卸掉，**别开**，否则每批都要重新加载。
- `width/height` 填 `-1` 表示**保持原尺寸**（只在 `LoadImagesFromFolderKJ` 里 -1 有效）。

---

### 玩法 5｜图序列转动画：静态图做成带转场的视频

**问题**：手里有一堆静态图，想做成有转场效果的动画/视频。

**三种转场节点的分工**

| 节点 | 作用 | 用在哪 |
|---|---|---|
| `TransitionImagesInBatch` | 在**一个 batch 内部**相邻帧之间插转场 | 一组图 → 一段连续动画 |
| `CrossFadeImages` | 把**两个 batch** 交叉淡化衔接 | 两段动画拼接 |
| `ImageBatchJoinWithTransition` | 先拼接两个 batch，再在**接缝处**插转场 | 两段图接起来并加特效 |

**链路 A**：一组图 → 连续动画
```
LoadImagesFromFolderKJ → TransitionImagesInBatch → PreviewAnimation
```

**链路 B**：两段动画拼接
```
段A ─┐
     ├─→ CrossFadeImages → PreviewAnimation
段B ─┘
```

**链路 C**：两段图接起来 + 接缝处加转场特效
```
段A ─┐
     ├─→ ImageBatchJoinWithTransition → FastPreviewBatch
段B ─┘
```

**完整 demo**（链路 A，淡入淡出，8fps）

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/frames",
    "width": 1280, "height": 720,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "TransitionImagesInBatch", "inputs": {
    "images": ["1", 0],
    "interpolation": "ease_in_out",
    "transition_type": "fade",
    "transitioning_frames": 6,
    "blur_radius": 0.0,
    "reverse": false,
    "device": "GPU" } },
  "3": { "class_type": "PreviewAnimation", "inputs": {
    "images": ["2", 0], "fps": 8.0 } },
  "4": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["2", 0],
    "filename_prefix": "anim/transition",
    "output_folder": "output" } }
}
```

**转场效果速查**

| `transition_type` | 效果 | 适合 |
|---|---|---|
| `fade` | 淡入淡出 | 万能，最不容易出错 |
| `horizontal slide` | 横向推移 | 图片轮播 |
| `vertical slide` | 纵向推移 | 竖屏/滚动感 |
| `box` | 方形擦除 | 有设计感 |
| `circle` | 圆形擦除 | 聚焦/强调 |
| `horizontal door` | 左右开门 | 揭晓感 |
| `vertical door` | 上下开门 | 揭晓感 |

| `interpolation` | 节奏 |
|---|---|
| `linear` | 匀速 |
| `ease_in_out` | **最常用**，两头慢中间快，自然 |
| `bounce` / `elastic` | 弹跳/弹性，活泼 |
| `glitchy` | 故障风 |

**踩坑**
- `device` 是**大写** `CPU`/`GPU`（`TransitionImagesInBatch` 和 `ImageBatchJoinWithTransition` 都是大写）。
- `transition_type` 的值**带空格**（`"horizontal slide"`），JSON 必须原样。
- `transitioning_frames` 越大，输出 batch 越长（= 原长度 + 转场帧数 × 间隔数），显存占用线性上升。
- `PreviewAnimation` 输出是**空**的（无输出槽），别试图连它。

---

### 玩法 6｜遮罩可视化与调试：让蒙版「看得见」

**问题**：蒙版是灰度张量，界面上只能看到一个黑白的缩略图，很难判断「抠得准不准、大小对不对」。

**三个调试工具**

| 节点 | 作用 | 输出 |
|---|---|---|
| `DrawMaskOnImage` | 把蒙版以半透明色**画在原图上** | `IMAGE` |
| `GetMaskSizeAndCount` | 输出蒙版的宽/高/数量 | `MASK, INT, INT, INT` |
| `BboxVisualize` | 把 BBOX 框画出来 | `IMAGE`（推测，用于调试裁剪框） |

**完整 demo**（蒙版叠加检查）

```json
{
  "1": { "class_type": "ColorToMask", "inputs": {
    "images": ["img", 0],
    "invert": false,
    "red": 0, "green": 255, "blue": 0,
    "threshold": 20, "per_batch": 16 } },
  "2": { "class_type": "GrowMaskWithBlur", "inputs": {
    "mask": ["1", 0],
    "expand": 8, "incremental_expandrate": 0.0,
    "tapered_corners": true, "flip_input": false,
    "blur_radius": 5.0, "lerp_alpha": 1.0,
    "decay_factor": 1.0, "fill_holes": true } },
  "3": { "class_type": "DrawMaskOnImage", "inputs": {
    "image": ["img", 0], "mask": ["2", 0],
    "color": "255, 0, 0, 128", "device": "cpu" } },
  "4": { "class_type": "GetMaskSizeAndCount", "inputs": { "mask": ["2", 0] } },
  "5": { "class_type": "PreviewImage", "inputs": { "images": ["3", 0] } }
}
```

**`DrawMaskOnImage.color` 写法**

| 值 | 效果 |
|---|---|
| `"255, 0, 0, 128"` | 半透明红（最常用，既能看清又不挡住底图） |
| `"0, 255, 0, 128"` | 半透明绿 |
| `"255, 0, 0"` | 不透明红（会完全盖住蒙版区域） |
| `"1.0, 0.0, 0.0, 0.5"` | 0.0~1.0 浮点写法也可 |

**调试心法**：在处理链路的**每一个环节后面都挂一个 `DrawMaskOnImage`**，一次性看到「原始蒙版 → 膨胀后 → 羽化后」的差异，比反复猜快得多。

---

### 玩法 7｜曲线驱动权重：用可视化曲线控制逐帧强度

**问题**：想让某个效果（LoRA 强度、CFG、噪声量）**随帧数变化**，手填一串数字太痛苦。

**解法**：`SplineEditor` 画曲线 → 转成 FLOAT 序列 → 下游用。

```
SplineEditor(画曲线) ─(2) float ─→ WeightScheduleConvert ─→ [下游 FLOAT 输入]
                                          │
                                          └─→ FloatToMask (想看曲线长什么样)
```

**完整 demo**

```json
{
  "1": { "class_type": "SplineEditor", "inputs": {
    "points_store": "", "coordinates": "",
    "mask_width": 512, "mask_height": 512,
    "points_to_sample": 24,
    "sampling_method": "time",
    "interpolation": "cardinal",
    "tension": 0.5,
    "repeat_output": 1,
    "float_output_type": "list",
    "min_value": 0.0, "max_value": 1.0 } },
  "2": { "class_type": "WeightScheduleConvert", "inputs": {
    "input_values": ["1", 2],
    "output_type": "list", "invert": false, "repeat": 1,
    "remap_to_frames": 0, "remap_values": false,
    "remap_min": 0.0, "remap_max": 1.0 } },
  "3": { "class_type": "FloatToMask", "inputs": {
    "input_values": ["2", 0],
    "width": 512, "height": 512 } }
}
```

**关键参数**

| 参数 | 作用 |
|---|---|
| `points_to_sample` | 决定**序列长度**（= 帧数）。24 → 生成 24 个值 |
| `sampling_method` | `time`=按时间均匀采样（最常用）；`path`=按弧长；`controlpoints`=只取控制点 |
| `interpolation` | `cardinal` 平滑；`linear` 折线；`step-before/after` 阶梯（突变效果） |
| `tension` | `cardinal` 的平滑度，`0`=直线，`1`=很弯 |
| `min_value` / `max_value` | 输出值域，默认 0~1 |

**典型曲线形状 → 用途**

| 曲线形状 | 用途 |
|---|---|
| 从 0 升到 1 | 效果淡入（如 LoRA 逐渐生效） |
| 中间高两头低 | 只在中段加强（如中段加细节） |
| 正弦波 | 周期性脉动（呼吸感、闪烁） |
| 阶梯 | 分段切换（前 10 帧一个值，后 10 帧另一个） |

**踩坑**
- `SplineEditor` 的 `points_store` / `coordinates` 是**前端 JS 写入**的，手填无效。API 调用时留空串，曲线数据要在 UI 里画好后导出。
- 输出槽 **2 才是 float**（槽 0=mask、1=coord_str、2=float、3=count、4=normalized_str）。

---

### 玩法 8｜反向玩法：从图/蒙版生成权重序列

**问题**：反过来——我有一张明暗渐变的图（或蒙版），想把它变成一串权重数字。

**解法**：`MaskOrImageToWeight`。

```json
{
  "1": { "class_type": "CreateGradientMask", "inputs": {
    "invert": false, "frames": 16, "width": 512, "height": 512 } },
  "2": { "class_type": "MaskOrImageToWeight", "inputs": {
    "output_type": "list", "masks": ["1", 0] } }
}
```

**用途举例**：用一段视频的**亮度变化**去驱动另一个效果的强度——比如画面越亮，锐化越强。

| `output_type` | 结果 |
|---|---|
| `list` | Python 列表 |
| `pandas series` | pandas Series（可做统计） |
| `tensor` | torch 张量 |
| `string` | 逗号分隔字符串（可直接看/存） |

---

### 玩法 9｜显存救急三件套：定位 OOM 出在哪

**问题**：跑大工作流 OOM，但不知道是哪一步吃的显存。

**三件套分工**

| 节点 | 作用 | 输入 | 输出 | 代价 |
|---|---|---|---|---|
| `VRAM_Debug` | 主动清缓存 + 报告清理前后空闲显存 | 3 开关 + 可选透传 | 5 槽（含 `freemem_before/after`） | 很小 |
| `ModelMemoryUseReportPatch` | 打印**模型各部分显存占用** | `model` | `MODEL` | 无（只打日志） |
| `StartRecordCUDAMemoryHistory` | **开始**记录 CUDA 分配历史 | `input`(ANY) + 4 选项 | `ANY` | 较大，仅调试 |
| `EndRecordCUDAMemoryHistory` | **结束**并导出 `.pt` 快照 | `input`(ANY) + `output_path` | `ANY, STRING(path)` | 较大，仅调试 |
| `VisualizeCUDAMemoryHistory` | 把 `.pt` 生成**可视化 HTML** | `snapshot_path`(STRING) | `STRING(path)` | 输出节点，自动给链接 |

**完整 demo**（诊断模式）

```json
{
  "1": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" } },
  "2": { "class_type": "ModelMemoryUseReportPatch", "inputs": { "model": ["1", 0] } },
  "3": { "class_type": "StartRecordCUDAMemoryHistory", "inputs": {
    "input": ["2", 0],
    "enabled": "all", "context": "all", "stacks": "all",
    "max_entries": 100000 } },
  "4": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 1024, "batch_size": 1 } },
  "5": { "class_type": "KSampler", "inputs": {
    "model": ["3", 0], "positive": ["pos", 0], "negative": ["neg", 0],
    "latent_image": ["4", 0],
    "seed": 1, "steps": 20, "cfg": 7.0,
    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0 } },
  "6": { "class_type": "VRAM_Debug", "inputs": {
    "empty_cache": true, "gc_collect": true, "unload_all_models": false,
    "model_pass": ["5", 0] } },
  "7": { "class_type": "VAEDecode", "inputs": { "samples": ["6", 2], "vae": ["1", 2] } },
  "8": { "class_type": "EndRecordCUDAMemoryHistory", "inputs": {
    "input": ["7", 0],
    "output_path": "comfy_cuda_memory_history" } },
  "9": { "class_type": "VisualizeCUDAMemoryHistory", "inputs": {
    "snapshot_path": ["8", 1] } }
}
```

**`StartRecordCUDAMemoryHistory` 选项**

| 参数 | 默认 | 说明 |
|---|---|---|
| `enabled` | `"all"` | `None`=关闭；`state`=保留已分配内存信息；`all`=记录全部 alloc/free 调用 |
| `context` | `"all"` | `None`=不记堆栈；`state`/`alloc`/`all`=不同程度的调用栈 |
| `stacks` | `"all"` | `python`=只 Python 帧；`all`=含 C++ 帧 |
| `max_entries` | `100000`（1000~10000000） | 最多记多少条 |

**`EndRecordCUDAMemoryHistory.output_path`**
- 默认 `"comfy_cuda_memory_history"`，实际文件名会自动**加时间戳和 `.pt`**，如 `comfy_cuda_memory_history20261008_163000.pt`。
- 输出的**槽 1** 才是真实路径，要喂给 `VisualizeCUDAMemoryHistory.snapshot_path`。

**读日志的心法**
- `VRAM_Debug` 的 **`freemem_before` / `freemem_after`**（槽 3/4）差值大 → 说明那一步之前堆积了很多缓存。
- 把 `VRAM_Debug` **逐个往后挪**，看哪一段的 `freemem_before` 特别低 → OOM 就在那附近。
- `VisualizeCUDAMemoryHistory` 会生成 HTML 到 `output/memory_history/`，并在 UI 上给一个 `/api/view?...` 链接。

**踩坑**
- ⚠️ **这三个显存记录节点的输入是 `input`（ANY），不是 `model`** —— 它们对任意类型透传，靠 `input` 触发执行顺序。这点很容易写错。
- `StartRecord...` 源码描述里写着 **"THIS NODE ALWAYS RUNS"**（不受缓存影响，每次都执行）。
- 三件套**只在调试时开**，正式跑要关掉（十万条记录会拖慢很多）。

---

### 玩法 10｜加速链路：提速 + 实时预览（正确顺序）

**问题**：想给工作流提速，并能实时看到采样中间结果。

**顺序（关键）**

```
CheckpointLoaderSimple
   ↓
PathchSageAttentionKJ       ① 先换 attention 实现
   ↓
TorchCompileModelAdvanced   ② 再编译（编译的是 ① 之后的图）
   ↓
ModelPreviewOverrideKJ      ③ 最后挂预览（不进编译）
   ↓
KSampler
```

**完整 demo**

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
    "filename_prefix": "xlexp/fast",
    "output_folder": "output" } }
}
```

**调优决策表**

| 目标 | 怎么做 |
|---|---|
| 只想简单提速且不装额外库 | 只用 `TorchCompileModelAdvanced`，跳过 SageAttention |
| 想最大提速 | 两个都上 + `mode="max-autotune"`（**但首次编译可能几分钟**） |
| 尺寸经常变 | `dynamic="auto"`，否则每个新尺寸都要重编译 |
| 编译报错 | `compile_transformer_blocks_only=False` 试试；或 `backend="cudagraphs"` |
| 想看真 RGB 而非 Latent2RGB | `ModelPreviewOverrideKJ.tiny_vae` 选一个 `models/vae_approx/` 下的 tiny VAE |

**踩坑**
- **首次运行会慢很多**（编译），这是正常的，别以为失败了。
- 换模型 / 换尺寸 → **重新编译**。
- `PathchSageAttentionKJ` 需要 `pip install sageattention`，版本要匹配 CUDA。
- `ModelPreviewOverrideKJ` 的 `preview_frames>1` **只对视频模型（5D latent）生效**，图模型会忽略。

---

### 玩法 11｜懒分支开关：一键关掉整条子图

**问题**：工作流里有条「放大后处理」链路，平时想关掉省时间，但又不想删连线。

**解法**：`BOOLConstant` → `LazySwitchKJ.switch`，未选中的分支**根本不执行**。

```json
{
  "1": { "class_type": "BOOLConstant", "inputs": { "value": false } },
  "2": { "class_type": "VAEDecode", "inputs": { "samples": ["sampler", 0], "vae": ["ckpt", 2] } },
  "3": { "class_type": "ImageUpscaleWithModelBatched", "inputs": {
    "upscale_model": ["upscale_model", 0],
    "images": ["2", 0],
    "per_batch": 2, "downscale_ratio": 1.0,
    "downscale_method": "lanczos", "precision": "float32" } },
  "4": { "class_type": "LazySwitchKJ", "inputs": {
    "switch": ["1", 0],
    "on_true": ["3", 0],
    "on_false": ["2", 0] } },
  "5": { "class_type": "SaveImageKJ", "inputs": {
    "images": ["4", 0],
    "filename_prefix": "out/result",
    "output_folder": "output" } }
}
```

**效果**：`BOOLConstant.value=false` → 走 `on_false`（直连 VAE 结果），放大链路**完全不执行**，耗时为 0。改成 `true` 就走放大。

**为什么比 bypass 强**

| 方式 | 未选中分支 |
|---|---|
| 手动断开连线 | 要手动改，麻烦 |
| ComfyUI bypass 模式 | 节点被跳过，但**上游仍可能执行** |
| **`LazySwitchKJ`** | **整条分支不发起执行**，真正零开销 |

**踩坑**
- `on_true` / `on_false` 是 **lazy 插槽**，只能接连线 `[id, slot]`，不能填字面量。
- 两个分支的**类型要一致**（或下游能接受），否则类型不匹配。

---

### 玩法 12｜多条件与区域提示词

**问题**：想同时用多条提示词，或让不同提示词作用于画面的不同区域。

**两个节点的分工**

| 节点 | 作用 |
|---|---|
| `ConditioningMultiCombine` | 把 **N 条条件**合成一条（`combine` 平均 / `concat` 拼接） |
| `ConditioningSetMaskAndCombine` / `...3` / `...4` / `...5` | 给条件**绑定蒙版**并合并 → 实现**区域提示词** |

**完整 demo**（多提示词合并 + 区域控制）

```json
{
  "1": { "class_type": "CLIPTextEncode", "inputs": { "text": "a cat", "clip": ["ckpt", 1] } },
  "2": { "class_type": "CLIPTextEncode", "inputs": { "text": "in watercolor style", "clip": ["ckpt", 1] } },
  "3": { "class_type": "CLIPTextEncode", "inputs": { "text": "soft lighting", "clip": ["ckpt", 1] } },
  "4": { "class_type": "ConditioningMultiCombine", "inputs": {
    "inputcount": 3, "operation": "combine",
    "conditioning_1": ["1", 0], "conditioning_2": ["2", 0], "conditioning_3": ["3", 0] } },
  "5": { "class_type": "CreateGradientMask", "inputs": {
    "invert": false, "frames": 0, "width": 1024, "height": 1024 } },
  "6": { "class_type": "ConditioningSetMask", "inputs": {
    "conditioning": ["4", 0], "mask": ["5", 0],
    "strength": 1.0, "set_cond_area": "default" } },
  "7": { "class_type": "EmptyLatentImage", "inputs": { "width": 1024, "height": 1024, "batch_size": 1 } },
  "8": { "class_type": "KSampler", "inputs": {
    "model": ["ckpt", 0], "positive": ["6", 0], "negative": ["neg", 0],
    "latent_image": ["7", 0],
    "seed": 7, "steps": 25, "cfg": 7.0,
    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0 } }
}
```

**`operation` 怎么选**

| 值 | 行为 | 用在哪 |
|---|---|---|
| `combine` | 逐元素**平均**（权重叠加） | 想让三条提示词**融合**（默认，最常用） |
| `concat` | token 维度**拼接**（总长变长） | 提示词太长被截断时，或想保留各自独立性 |

**踩坑**
- `concat` 会让 token 数变多，**可能超过 77/225 token 上限**，注意模型限制。
- 区域提示词更简单的做法是直接用内置 `ConditioningSetMask`（如上 demo），`ConditioningSetMaskAndCombine` 系列是把「设蒙版+合并」打包成一步。

---

### 玩法 13｜循环视频消接缝

**问题**：做的循环视频首尾帧接不上，有个明显的跳变。

**解法**：`VAEDecodeLoopKJ` —— 解码时把首尾若干帧**混合**，得到真正无缝的循环。

```json
{
  "1": { "class_type": "VAEDecodeLoopKJ", "inputs": {
    "samples": ["sampler", 0], "vae": ["ckpt", 2],
    "overlap_latent_frames": 4 } }
}
```

**`overlap_latent_frames` 怎么选**（来自源码 tooltip）

| 模型 | 推荐值 |
|---|---|
| Wan 2.1 / 2.2 | `2` |
| HunyuanVideo 1.5 | `4` |
| 其他 | 从 `2` 试起，不够再加大（上限 8） |

> 注意这是 **latent 帧**数，不是像素帧。值太大会让首尾过渡过长显得糊。

---

### 玩法 14｜探针与自动化：把尺寸/数量传给下游

**问题**：想知道 batch 里有多少张图、每张多大，并把这个数字传给别的节点。

**解法**：`GetImageSizeAndCount`（图）/ `GetMaskSizeAndCount`（蒙版），输出 `IMAGE, INT(width), INT(height), INT(count)`。

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/frames",
    "width": 1024, "height": 1024,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "GetImageSizeAndCount", "inputs": { "image": ["1", 0] } },
  "3": { "class_type": "SimpleCalculatorKJ", "inputs": {
    "expression": "count * 2" } },
  "4": { "class_type": "PreviewAnimation", "inputs": {
    "images": ["2", 0], "fps": 8.0 } }
}
```

**输出槽位**

| 节点 | 槽 0 | 槽 1 | 槽 2 | 槽 3 |
|---|---|---|---|---|
| `GetImageSizeAndCount` | IMAGE | width | height | **count** |
| `GetMaskSizeAndCount` | MASK | width | height | **count** |

**用途**
- `count` 接给循环次数、帧数、或作为文件名的一部分
- `width`/`height` 接给 `EmptyLatentImage`，实现「按输入图的尺寸生成」

**踩坑**
- `SimpleCalculatorKJ` 用 `Autogrow.Input` 的 `variables`，API 里变量怎么填要看实际 schema；简单场景直接用 `INTConstant` 更稳。

---

### 玩法 15｜外扩作画（Outpainting）：给图加边再补内容

**问题**：想把一张 512×512 的图扩成 1024×1024，扩展部分要 AI 补出来。

**解法**：`ImagePadForOutpaintMasked` —— 一次性输出「扩展后的图」+「对应的蒙版」（蒙版白色区域 = 需要重绘的部分），比内置的 `ImagePadForOutpaint` 更省事。

```json
{
  "1": { "class_type": "ImagePadForOutpaintMasked", "inputs": {
    "image": ["img", 0],
    "left": 256, "top": 256, "right": 256, "bottom": 256,
    "feathering": 40 } },
  "2": { "class_type": "VAEEncode", "inputs": {
    "pixels": ["1", 0], "vae": ["ckpt", 2] } },
  "3": { "class_type": "SetLatentNoiseMask", "inputs": {
    "samples": ["2", 0], "mask": ["1", 1] } },
  "4": { "class_type": "KSampler", "inputs": {
    "model": ["ckpt", 0], "positive": ["pos", 0], "negative": ["neg", 0],
    "latent_image": ["3", 0],
    "seed": 99, "steps": 30, "cfg": 7.0,
    "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0 } },
  "5": { "class_type": "VAEDecode", "inputs": { "samples": ["4", 0], "vae": ["ckpt", 2] } }
}
```

**参数**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `left` / `top` / `right` / `bottom` | `0`，step `8` | 四边各扩多少像素。**必须是 8 的倍数**（latent 对齐） |
| `feathering` | `0`，step `1` | 蒙版边缘羽化像素数。**建议 32~64**，否则新旧内容有明显接缝 |

**踩坑**
- 四边扩展量**必须是 8 的倍数**（`step=8`），否则 latent 尺寸对不齐。
- `feathering=0` 几乎必然出现硬边接缝，**一定要设**。
- 这是内置分类（`image`）的节点，不是 `KJNodes/` 前缀，但同样来自 KJNodes 包。

---

### 玩法 16｜批量网格预览：一眼看完整个 batch

**问题**：batch 有 50 张图，一张张翻太慢。

**解法**：`ImageConcatFromBatch`（拼成网格）或 `ImageGridComposite2x2` / `ImageGridComposite3x3`（固定 2×2 / 3×3）。

```json
{
  "1": { "class_type": "LoadImagesFromFolderKJ", "inputs": {
    "folder": "/data/frames",
    "width": 512, "height": 512,
    "keep_aspect_ratio": "crop",
    "image_load_cap": 0, "start_index": 0, "include_subfolders": false } },
  "2": { "class_type": "ImageConcatFromBatch", "inputs": {
    "images": ["1", 0],
    "num_columns": 5,
    "match_image_size": false,
    "max_resolution": 4096 } },
  "3": { "class_type": "PreviewImage", "inputs": { "images": ["2", 0] } }
}
```

**参数**

| 参数 | 默认值 | 说明 |
|---|---|---|
| `num_columns` | `3`（1~255） | 一行几张。batch 50 张设 5 → 10 行 |
| `match_image_size` | `false` | 是否先把所有图统一尺寸（尺寸不一致时开） |
| `max_resolution` | `4096` | 输出图的最大边长上限，防爆炸 |

**替代工具**

| 节点 | 适合 |
|---|---|
| `ImageConcatFromBatch` | batch 数**任意**，自定义列数 |
| `ImageGridComposite2x2` / `3x3` | 固定 4 张 / 9 张，做对比图 |
| `FastPreviewBatch` | 生成 **mp4** 缩略图条 + 网格，帧数极大时最快（会 stride 采样） |

---

## 3. 可复用的「套路」总结

把上面 16 个玩法抽象成 8 个可迁移的套路：

| 套路 | 结构 | 迁移到 |
|---|---|---|
| **A. 尺寸闭环** | 缩放节点输出尺寸 → 驱动 latent | 任何图生图 / inpaint |
| **B. 裁剪回环** | 裁出 → 处理 → 贴回 + BBOX | 局部重绘、局部放大、局部换风格 |
| **C. 断层清显存** | 重模型 A 结束 → `VRAM_Debug` → 重模型 B 开始 | 采样→解码、放大→保存 |
| **D. 补丁有序** | 改实现 → 编译 → 挂无关补丁 | 任何加速链路 |
| **E. 懒分支** | 常量 → LazySwitch → 两分支 | A/B 对比、可选后处理 |
| **F. 探针** | 取尺寸/数量 → 驱动下游参数 | 自适应循环、动态文件名 |
| **G. 可视化调试** | 每个环节后挂 DrawMaskOnImage / Preview | 任何蒙版链路 |
| **H. 曲线驱动** | SplineEditor → 权重序列 → 下游 FLOAT | 逐帧强度、周期性效果 |

---

## 4. 排错速查

| 现象 | 原因 | 解法 |
|---|---|---|
| `Node not found: LoraReduceRank` | **ID 错**，实际是 `LoraReduceRankKJ` | 用带 `KJ` 后缀的 ID |
| `Node not found: SetNode/GetNode` | **v1.5.2 已移除** | 用内置 Reroute 替代 |
| `TensorLoopOpen` 搜不到 | **v1.5.2 未注册** | 循环视频用 `VAEDecodeLoopKJ` |
| `device` 报枚举错误 | 大小写写反 | `TransitionImagesInBatch` 用大写 `GPU`；`ImageResizeKJv2` 用小写 `gpu` |
| `transition_type` 无效 | 值带空格 | 必须写 `"horizontal slide"` 全串 |
| VAE 编码尺寸不匹配 | latent 尺寸 ≠ 图尺寸 | 用玩法 1，把缩放节点的输出槽 1/2 接给 `EmptyLatentImage` |
| 贴回原图有接缝 | `border_blending` 太小 / 蒙版没羽化 | `border_blending=0.3` + `blur_radius=8` |
| CLIPSeg 抠不准 | `threshold` 不合适 | 抠多了调高、抠少了调低 |
| torch.compile 后更慢 | 补丁顺序反了 / 尺寸每次都变 | 先打补丁再编译；`dynamic="auto"` |
| 蒙版看不见 | 蒙版是灰度张量 | 用 `DrawMaskOnImage`（玩法 6） |
| batch 操作 OOM | 一次性吃太多 | `per_batch` 调小 + `VRAM_Debug`（玩法 4） |
| `CreateTextMask` 字体下拉空 | 没建字体目录 | 建 `models/kjnodes_fonts/` 放 `.ttf` |

---

## 5. 参考

- **节点参数字典**：`docs/KJNODES_NODES_GUIDE.md`
- **安装位置**：`ComfyUI/custom_nodes/ComfyUI-KJNodes/`
- **仓库**：https://github.com/kijai/ComfyUI-KJNodes
- **内置节点对照**：`docs/BUILTIN_NODES_GUIDE.md`
- **想自己写这类节点**：`docs/CUSTOM_DEV_TUTORIAL.md`

---

> **说明**：本文所有节点 ID 已与 `kjrepo/__init__.py` 的 236 条 `NODE_CLASS_MAPPINGS` 注册逐条核对；参数默认值/范围来自源码 AST 提取。
> 文中所有 JSON demo 块均已通过 `json.loads` 校验。
