#!/usr/bin/env bash
#
# ComfyUI 一键启动脚本(适配当前系统:Ubuntu 22.04 + RTX 4060)
#
# 用法:
#   ./start.sh                          # 默认启动(自动检测设备)
#   ./start.sh --listen --port 9000     # 透传额外参数给 main.py
#   ./start.sh --cpu                    # 强制 CPU 模式
#   ./start.sh --setup                   # 仅检查并修复依赖,不启动
#
# 环境变量(可选):
#   COMFYUI_PORT=8188        监听端口
#   COMFYUI_HOST=127.0.0.1   监听地址(设为 0.0.0.0 可局域网访问)
#   COMFYUI_PYTHON           指定 python 可执行文件
#   COMFYUI_NO_DEPS=1         跳过依赖检查
#   COMFYUI_NO_BROWSER=1      不自动打开浏览器
#   COMFYUI_OFFLINE=1         离线启动(等同 --offline)
#
# 注意:
#   如果 nvidia-smi 或 CUDA 初始化报错(error 304),
#   可能是沙箱/容器限制了 GPU 访问。请用以下方式解除:
#     sudo bash start.sh
#   或在非沙箱终端中运行。
#

set -euo pipefail

# ---------- 定位 ComfyUI 根目录 ----------
SCRIPT_PATH="$(readlink -f "$0")"
COMFYUI_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$COMFYUI_DIR"

# ---------- 颜色 ----------
if [[ -t 1 ]]; then
    C_BOLD=$'\033[1m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m'; C_BLUE=$'\033[34m'; C_RESET=$'\033[0m'
else
    C_BOLD=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_BLUE=""; C_RESET=""
fi
log()  { printf "%s[ComfyUI]%s %s\n" "$C_BLUE" "$C_RESET" "$*"; }
ok()   { printf "%s[ OK ]%s %s\n" "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf "%s[WARN]%s %s\n" "$C_YELLOW" "$C_RESET" "$*" >&2; }
err()  { printf "%s[ERR ]%s %s\n" "$C_RED" "$C_RESET" "$*" >&2; }

# ---------- 选择 Python ----------
pick_python() {
    if [[ -n "${COMFYUI_PYTHON:-}" ]] && command -v "$COMFYUI_PYTHON" >/dev/null 2>&1; then
        echo "$COMFYUI_PYTHON"; return
    fi
    for p in "$COMFYUI_DIR/venv/bin/python" "$COMFYUI_DIR/.venv/bin/python"; do
        [[ -x "$p" ]] && { echo "$p"; return; }
    done
    if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
        echo "$CONDA_PREFIX/bin/python"; return
    fi
    for c in python3 python; do
        command -v "$c" >/dev/null 2>&1 && { echo "$c"; return; }
    done
    return 1
}

PYTHON_BIN="$(pick_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    err "未找到 Python,请安装 Python 3.10+ 后重试。"
    exit 1
fi

PY_VER="$("$PYTHON_BIN" -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")')"
PY_MAJOR="${PY_VER%%.*}"
PY_MINOR="${PY_VER##*.}"
log "Python: $PYTHON_BIN ($PY_VER)  |  目录: $COMFYUI_DIR"

if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 10) )); then
    err "Python $PY_VER 版本过低,ComfyUI 需要 3.10+。"
    exit 1
fi
if (( PY_MAJOR == 3 && PY_MINOR < 12 )); then
    warn "Python $PY_VER 可用,但官方推荐 3.13。部分依赖(如 comfyui-workflow-templates)需要 3.11+。"
fi

# ---------- 依赖检查与修复 ----------
check_and_install_deps() {
    if [[ "${COMFYUI_NO_DEPS:-0}" == "1" ]]; then
        log "跳过依赖检查(COMFYUI_NO_DEPS=1)"
        return 0
    fi

    log "检查依赖..."

    # 检查 torch
    if ! "$PYTHON_BIN" -c 'import torch' 2>/dev/null; then
        err "未安装 PyTorch。请先安装:"
        err "  $PYTHON_BIN -m pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130"
        return 1
    fi

    # 检查 torch 版本(comfy-kitchen 需要 torch 2.4+ 的 torch.library.custom_op)
    TORCH_VER="$("$PYTHON_BIN" -c 'import torch; print(torch.__version__)' 2>/dev/null)"
    TORCH_OK="$("$PYTHON_BIN" -c 'import torch; ok=hasattr(torch.library,"custom_op") if hasattr(torch,"library") else False; print(ok)' 2>/dev/null)"
    if [[ "$TORCH_OK" != "True" ]]; then
        warn "PyTorch $TORCH_VER 版本过旧,comfy-kitchen 需要 torch 2.4+。正在升级..."
        set +e
        "$PYTHON_BIN" -m pip install --upgrade "torch>=2.7" torch torchvision torchaudio 2>&1 | tail -5
        set -e
        ok "PyTorch 已升级"
    fi

    # 检查核心依赖
    MISSING="$("$PYTHON_BIN" - <<'PY'
import importlib.util
mods = ["torch","torchvision","numpy","PIL","yaml","safetensors","transformers",
        "tokenizers","scipy","tqdm","psutil","aiohttp","sentencepiece","einops",
        "filelock","av","blake3","cryptography","simpleeval","sqlalchemy",
        "alembic","comfy_kitchen","comfy_aimdo","comfy_angle","pydantic_settings",
        "spandrel","kornia","comfyui_frontend_package","comfyui_workflow_templates"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
print(" ".join(missing))
PY
)"
    if [[ -n "$MISSING" ]]; then
        warn "缺失依赖: $MISSING"
        log "安装 requirements.txt ..."
        set +e
        "$PYTHON_BIN" -m pip install -r "$COMFYUI_DIR/requirements.txt" 2>&1 | tail -5
        PIP_RC=${PIPESTATUS[0]}
        set -e
        if [[ $PIP_RC -ne 0 ]]; then
            # 某些子依赖(如 comfyui-workflow-templates-media-assets-02)可能要求 Python 3.11+,
            # 用 --no-deps 安装 workflow-templates 并单独装其他核心包
            warn "完整安装失败(可能是 Python 版本限制),尝试分步安装..."
            "$PYTHON_BIN" -m pip install --no-deps comfyui-workflow-templates==0.11.77 \
                comfyui-workflow-templates-core comfyui-embedded-docs==0.5.13 2>&1 | tail -3
            "$PYTHON_BIN" -m pip install --no-deps \
                comfyui-workflow-templates-media-image \
                comfyui-workflow-templates-media-video \
                comfyui-workflow-templates-media-other \
                comfyui-workflow-templates-media-assets-01 2>&1 | tail -3
            "$PYTHON_BIN" -m pip install blake3 simpleeval "SQLAlchemy>=2.0.0" "av>=17.0.0" \
                comfy-aimdo==0.5.5 comfy-kitchen==0.2.37 comfy-angle PyOpenGL \
                "pydantic-settings~=2.0" 2>&1 | tail -3
        fi
        ok "依赖安装完成"
    fi

    # 检查 pydantic-settings 兼容性
    if ! "$PYTHON_BIN" -c 'from pydantic_settings import TomlConfigSettingsSource' 2>/dev/null; then
        warn "pydantic-settings 版本过旧,升级中..."
        "$PYTHON_BIN" -m pip install --upgrade "pydantic-settings~=2.0" 2>&1 | tail -2
        ok "pydantic-settings 已升级"
    fi

    # 检查 comfy_kitchen 导入
    if ! "$PYTHON_BIN" -c 'import comfy_kitchen' 2>/dev/null; then
        err "comfy_kitchen 导入失败,请手动运行:"
        err "  $PYTHON_BIN -m pip install comfy-kitchen==0.2.37"
        return 1
    fi

    # 检查 SQLAlchemy DeclarativeBase
    if ! "$PYTHON_BIN" -c 'from sqlalchemy.orm import DeclarativeBase' 2>/dev/null; then
        err "SQLAlchemy 版本过旧(需要 2.0+),请手动运行:"
        err "  $PYTHON_BIN -m pip install 'SQLAlchemy>=2.0.0'"
        return 1
    fi

    ok "依赖完整"
}

# 仅修复依赖模式
if [[ "${1:-}" == "--setup" ]]; then
    check_and_install_deps
    exit $?
fi

check_and_install_deps

# ---------- GPU / 设备检测 ----------
detect_device() {
    if "$PYTHON_BIN" -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null; then
        local name
        name="$("$PYTHON_BIN" -c 'import torch; print(torch.cuda.get_device_name(0))' 2>/dev/null)"
        # 实际 CUDA 初始化测试(error 304 在沙箱中出现)
        if "$PYTHON_BIN" -c 'import torch; torch.cuda.current_device(); x=torch.tensor([1.0]).cuda(); assert (x*2).item()==2.0' 2>/dev/null; then
            echo "cuda|${name:-NVIDIA GPU}"
        else
            warn "CUDA 可用但初始化失败(可能是沙箱/容器限制 GPU 访问)"
            warn "请尝试: sudo bash start.sh  或在非沙箱终端中运行"
            echo "cpu|CPU(CUDA 初始化失败,回退)"
        fi
        return
    fi
    if "$PYTHON_BIN" -c 'import torch; assert hasattr(torch.version,"hip") and torch.version.hip' 2>/dev/null; then
        echo "rocm|AMD ROCm"; return
    fi
    if "$PYTHON_BIN" -c 'import torch; assert torch.backends.mps.is_available()' 2>/dev/null; then
        echo "mps|Apple Silicon"; return
    fi
    if "$PYTHON_BIN" -c 'import torch; assert hasattr(torch,"xpu") and torch.xpu.is_available()' 2>/dev/null; then
        echo "xpu|Intel XPU"; return
    fi
    echo "cpu|CPU"
}

DEVICE_INFO="$(detect_device)"
DEVICE_TYPE="${DEVICE_INFO%%|*}"
DEVICE_NAME="${DEVICE_INFO##*|}"

case "$DEVICE_TYPE" in
    cuda) ok "GPU: $DEVICE_NAME" ;;
    rocm) ok "设备: AMD ROCm" ;;
    mps)  ok "设备: Apple Silicon MPS" ;;
    xpu)  ok "设备: Intel XPU" ;;
    cpu)  warn "未检测到可用 GPU,以 CPU 模式运行(速度较慢)" ;;
esac

# ---------- torch 版本与 VRAM ----------
TORCH_VER="$("$PYTHON_BIN" -c 'import torch; print(torch.__version__)' 2>/dev/null)"
log "PyTorch: $TORCH_VER"
if [[ "$DEVICE_TYPE" == "cuda" ]]; then
    VRAM_MB="$("$PYTHON_BIN" -c 'import torch; p=torch.cuda.get_device_properties(0); print(round(p.total_memory/1024/1024))' 2>/dev/null)"
    log "VRAM: ${VRAM_MB:-?} MB"
fi

# ---------- 模型文件检查 ----------
CKPT_COUNT="$(find "$COMFYUI_DIR/models/checkpoints" "$COMFYUI_DIR/models/diffusion_models" "$COMFYUI_DIR/models/unet" \
    -type f \( -name '*.safetensors' -o -name '*.ckpt' -o -name '*.gguf' -o -name '*.pth' \) 2>/dev/null | wc -l)"
if [[ "$CKPT_COUNT" -eq 0 ]]; then
    warn "models/ 下未找到模型文件,请将 .safetensors/.ckpt 放入 models/checkpoints/ 或 models/diffusion_models/"
else
    ok "发现 $CKPT_COUNT 个模型文件"
fi

# ---------- 端口检查 ----------
HOST="${COMFYUI_HOST:-127.0.0.1}"
PORT="${COMFYUI_PORT:-8188}"

if ss -tln 2>/dev/null | grep -q ":$PORT "; then
    warn "端口 $PORT 被占用,自动切换"
    while ss -tln 2>/dev/null | grep -q ":$PORT "; do
        PORT=$((PORT + 1))
    done
    ok "使用端口: $PORT"
fi

# ---------- 构建启动参数 ----------
ARGS=()

# 设备模式
case "$DEVICE_TYPE" in
    cpu) ARGS+=(--cpu) ;;
esac

# 预览(默认开启,低成本查看生成进度)
ARGS+=(--preview-method auto)

# 自动打开浏览器
if [[ -z "${COMFYUI_NO_BROWSER:-}" ]]; then
    ARGS+=(--auto-launch)
fi

# 离线模式
if [[ "${COMFYUI_OFFLINE:-0}" == "1" ]]; then
    ARGS+=(--offline)
fi

# 监听地址
if [[ "$HOST" != "127.0.0.1" ]]; then
    ARGS+=(--listen "$HOST")
fi
ARGS+=(--port "$PORT")

# 透传用户参数
ARGS+=("$@")

# ---------- 启动 ----------
echo
printf "%s══════════════════════════════════════%s\n" "$C_BOLD" "$C_RESET"
printf "%s  ComfyUI 启动中%s\n" "$C_BOLD" "$C_RESET"
printf "%s  访问地址: http://%s:%d%s\n" "$C_GREEN" "$HOST" "$PORT" "$C_RESET"
printf "%s  设备: %s (%s)%s\n" "$C_BOLD" "$DEVICE_TYPE" "$DEVICE_NAME" "$C_RESET"
printf "%s  Python: %s (%s)%s\n" "$C_BOLD" "$PYTHON_BIN" "$PY_VER" "$C_RESET"
printf "%s  PyTorch: %s%s\n" "$C_BOLD" "$TORCH_VER" "$C_RESET"
printf "%s  参数: %s%s\n" "$C_BOLD" "${ARGS[*]}" "$C_RESET"
printf "%s══════════════════════════════════════%s\n" "$C_BOLD" "$C_RESET"
echo

exec "$PYTHON_BIN" "$COMFYUI_DIR/main.py" "${ARGS[@]}"
