# =============================================================================
# ComfyUI 主程序入口文件
# 作用：程序启动、初始化配置、启动Web服务器和执行引擎
# =============================================================================

# 1. 首先启用命令行参数解析（必须在其他导入之前）
import comfy.options

comfy.options.enable_args_parsing()  # 启用参数解析系统，其他模块可能依赖解析后的参数

# 2. 导入系统基础模块
import os  # 操作系统接口
import importlib.util  # 动态导入工具
import folder_paths  # 文件路径管理模块
import time  # 时间处理
import itertools  # 迭代工具
import logging  # 日志系统
import sys  # 系统相关功能

# 3. 导入ComfyUI核心模块
from comfy.cli_args import args  # 命令行参数对象
from app.logger import setup_logger  # 日志系统初始化
from utils.extra_config import load_extra_path_config  # 额外配置加载
from comfy_execution.progress import get_progress_state  # 执行进度管理
from comfy_execution.utils import get_executing_context  # 执行上下文
from comfy_api import feature_flags  # 功能标志

# =============================================================================
# 程序入口点 - 只有在直接运行此文件时才会执行
# =============================================================================
if __name__ == "__main__":
    # 4. 设置环境变量（隐私保护）
    # 注意：这些环境变量对核心ComfyUI没有影响，主要是为了自定义节点
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"  # 禁用Hugging Face Hub遥测
    os.environ["DO_NOT_TRACK"] = "1"  # 遵循DNT标准，禁用跟踪

# 5. 初始化日志系统（在程序启动早期就设置）
setup_logger(log_level=args.verbose, use_stdout=args.log_stdout)


# =============================================================================
# 路径配置函数 - 设置ComfyUI的各种文件路径
# =============================================================================
def apply_custom_paths():
    """
    配置ComfyUI的文件路径系统
    包括：模型路径、输入输出目录、用户目录等
    """
    # 6.1 加载额外模型路径配置
    # 首先尝试加载项目根目录下的配置文件
    extra_model_paths_config_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),  # 获取当前文件所在目录
        "extra_model_paths.yaml",  # 配置文件名称
    )
    if os.path.isfile(extra_model_paths_config_path):
        load_extra_path_config(extra_model_paths_config_path)

    # 6.2 加载命令行指定的额外配置
    if args.extra_model_paths_config:
        for config_path in itertools.chain(*args.extra_model_paths_config):
            load_extra_path_config(config_path)

    # 6.3 设置输出目录（--output-directory参数）
    if args.output_directory:
        output_dir = os.path.abspath(args.output_directory)  # 转换为绝对路径
        logging.info(f"设置输出目录为: {output_dir}")
        folder_paths.set_output_directory(output_dir)

    # 6.4 设置默认模型文件夹路径
    # 这些是ComfyUI默认的模型存储位置，当使用CheckpointSave等节点时会保存到这里
    base_output_dir = folder_paths.get_output_directory()
    folder_paths.add_model_folder_path(
        "checkpoints", os.path.join(base_output_dir, "checkpoints")
    )
    folder_paths.add_model_folder_path("clip", os.path.join(base_output_dir, "clip"))
    folder_paths.add_model_folder_path("vae", os.path.join(base_output_dir, "vae"))
    folder_paths.add_model_folder_path(
        "diffusion_models", os.path.join(base_output_dir, "diffusion_models")
    )
    folder_paths.add_model_folder_path("loras", os.path.join(base_output_dir, "loras"))

    # 6.5 设置输入目录（--input-directory参数）
    if args.input_directory:
        input_dir = os.path.abspath(args.input_directory)
        logging.info(f"设置输入目录为: {input_dir}")
        folder_paths.set_input_directory(input_dir)

    # 6.6 设置用户目录（--user-directory参数）
    if args.user_directory:
        user_dir = os.path.abspath(args.user_directory)
        logging.info(f"设置用户目录为: {user_dir}")
        folder_paths.set_user_directory(user_dir)


# =============================================================================
# 自定义节点预启动函数 - 在主要系统启动前执行自定义节点的初始化脚本
# =============================================================================
def execute_prestartup_script():
    """
    执行自定义节点的预启动脚本
    这些脚本在ComfyUI主系统启动前运行，用于初始化自定义节点
    """
    # 7.1 检查是否禁用所有自定义节点
    if args.disable_all_custom_nodes and len(args.whitelist_custom_nodes) == 0:
        logging.info("所有自定义节点已被禁用")
        return

    def execute_script(script_path):
        """
        执行单个预启动脚本
        使用动态导入机制加载并执行Python脚本
        """
        module_name = os.path.splitext(script_path)[0]  # 获取模块名（去掉.py扩展名）
        try:
            # 动态导入：从文件路径创建模块规范
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)  # 创建模块对象
            spec.loader.exec_module(module)  # 执行模块代码
            return True
        except Exception as e:
            logging.error(f"执行预启动脚本失败: {script_path} / {e}")
        return False

    # 7.2 扫描自定义节点目录
    node_paths = folder_paths.get_folder_paths("custom_nodes")
    for custom_node_path in node_paths:
        possible_modules = os.listdir(custom_node_path)  # 列出目录中的所有项目
        node_prestartup_times = []  # 记录每个节点的启动时间

        for possible_module in possible_modules:
            module_path = os.path.join(custom_node_path, possible_module)

            # 跳过文件、禁用的模块和缓存目录
            if (
                os.path.isfile(module_path)
                or module_path.endswith(".disabled")
                or module_path == "__pycache__"
            ):
                continue

            # 查找预启动脚本
            script_path = os.path.join(module_path, "prestartup_script.py")
            if os.path.exists(script_path):
                # 7.3 检查是否在禁用列表中
                if (
                    args.disable_all_custom_nodes
                    and possible_module not in args.whitelist_custom_nodes
                ):
                    logging.info(
                        f"跳过预启动脚本 {possible_module}，因为禁用了所有自定义节点且不在白名单中"
                    )
                    continue

                # 7.4 执行预启动脚本并记录时间
                time_before = time.perf_counter()  # 记录开始时间
                success = execute_script(script_path)
                node_prestartup_times.append(
                    (time.perf_counter() - time_before, module_path, success)
                )

    # 7.5 输出预启动时间统计
    if len(node_prestartup_times) > 0:
        logging.info("\n自定义节点预启动时间:")
        for n in sorted(node_prestartup_times):
            if n[2]:  # 如果执行成功
                import_message = ""
            else:  # 如果执行失败
                import_message = " (预启动失败)"
            logging.info("{:6.1f} 秒{}: {}".format(n[0], import_message, n[1]))
        logging.info("")


# =============================================================================
# 执行初始化函数
# =============================================================================
apply_custom_paths()  # 配置文件路径
execute_prestartup_script()  # 执行自定义节点预启动脚本

# =============================================================================
# 导入主要功能模块
# =============================================================================
import asyncio  # 异步编程支持
import shutil  # 文件操作工具
import threading  # 多线程支持
import gc  # 垃圾回收

# =============================================================================
# Windows系统特殊配置
# =============================================================================
if os.name == "nt":  # 如果是Windows系统
    os.environ["MIMALLOC_PURGE_DELAY"] = "0"  # 设置内存分配器延迟为0

# =============================================================================
# 设备配置和GPU设置
# =============================================================================
if __name__ == "__main__":
    # 8.1 启用实验性ROCm功能（AMD GPU支持）
    os.environ["TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL"] = "1"

    # 8.2 设置默认GPU设备（--default-device参数）
    if args.default_device is not None:
        default_dev = args.default_device
        devices = list(range(32))  # 假设最多32个GPU设备
        devices.remove(default_dev)  # 移除默认设备
        devices.insert(0, default_dev)  # 将默认设备放在首位
        devices = ",".join(map(str, devices))  # 转换为逗号分隔的字符串
        os.environ["CUDA_VISIBLE_DEVICES"] = str(devices)  # 设置CUDA可见设备
        os.environ["HIP_VISIBLE_DEVICES"] = str(devices)  # 设置HIP可见设备（AMD GPU）

    # 8.3 设置特定CUDA设备（--cuda-device参数）
    if args.cuda_device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.cuda_device)
        os.environ["HIP_VISIBLE_DEVICES"] = str(args.cuda_device)
        os.environ["ASCEND_RT_VISIBLE_DEVICES"] = str(args.cuda_device)  # 华为昇腾设备
        logging.info(f"设置CUDA设备为: {args.cuda_device}")

    # 8.4 设置OneAPI设备选择器（--oneapi-device-selector参数）
    if args.oneapi_device_selector is not None:
        os.environ["ONEAPI_DEVICE_SELECTOR"] = args.oneapi_device_selector
        logging.info(f"设置OneAPI设备选择器为: {args.oneapi_device_selector}")

    # 8.5 启用确定性计算（--deterministic参数）
    if args.deterministic:
        if "CUBLAS_WORKSPACE_CONFIG" not in os.environ:
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = (
                ":4096:8"  # 设置CUDA BLAS工作空间配置
            )

    # 8.6 导入CUDA内存管理模块
    import cuda_malloc

# =============================================================================
# 检查PyTorch导入状态
# =============================================================================
if "torch" in sys.modules:
    logging.warning(
        "警告：代码中可能存在错误：PyTorch已经被导入，PyTorch不应该在此时被导入。"
    )

# =============================================================================
# 导入ComfyUI核心模块
# =============================================================================
import comfy.utils  # ComfyUI工具函数
import execution  # 执行引擎模块
import server  # Web服务器模块
from protocol import BinaryEventTypes  # 二进制事件类型
import nodes  # 节点系统模块
import comfy.model_management  # 模型管理模块
import comfyui_version  # 版本信息
import app.logger  # 日志模块
import hook_breaker_ac10a0  # 钩子破坏器（用于修复某些兼容性问题）


# =============================================================================
# CUDA内存分配警告函数
# =============================================================================
def cuda_malloc_warning():
    """
    检查当前GPU是否支持cuda-malloc异步内存分配
    某些GPU不支持此功能，会导致CUDA错误
    """
    device = comfy.model_management.get_torch_device()  # 获取当前PyTorch设备
    device_name = comfy.model_management.get_torch_device_name(device)  # 获取设备名称
    cuda_malloc_warning = False

    # 检查设备名称是否包含cudaMallocAsync
    if "cudaMallocAsync" in device_name:
        # 检查设备是否在黑名单中
        for b in cuda_malloc.blacklist:
            if b in device_name:
                cuda_malloc_warning = True
                break

        # 如果在黑名单中，发出警告
        if cuda_malloc_warning:
            logging.warning(
                '\n警告：此显卡很可能不支持cuda-malloc，如果遇到"CUDA error"错误，请使用 --disable-cuda-malloc 参数运行ComfyUI\n'
            )


# =============================================================================
# 提示词工作线程函数 - 在后台线程中处理工作流执行
# =============================================================================
def prompt_worker(q, server_instance):
    """
    工作线程主函数，负责从队列中获取并执行工作流
    参数:
        q: 提示词队列
        server_instance: 服务器实例
    """
    current_time: float = 0.0  # 当前时间戳

    # 9.1 根据参数设置缓存类型
    cache_type = execution.CacheType.CLASSIC  # 默认经典缓存
    if args.cache_lru > 0:
        cache_type = execution.CacheType.LRU  # LRU缓存
    elif args.cache_none:
        cache_type = execution.CacheType.NONE  # 无缓存

    # 9.2 创建执行器实例
    e = execution.PromptExecutor(
        server_instance, cache_type=cache_type, cache_size=args.cache_lru
    )

    # 9.3 垃圾回收相关变量
    last_gc_collect = 0  # 上次垃圾回收时间
    need_gc = False  # 是否需要垃圾回收
    gc_collect_interval = 10.0  # 垃圾回收间隔（秒）

    # 9.4 主工作循环
    while True:
        # 计算超时时间
        timeout = 1000.0  # 默认超时时间
        if need_gc:
            timeout = max(gc_collect_interval - (current_time - last_gc_collect), 0.0)

        # 从队列获取工作项
        queue_item = q.get(timeout=timeout)
        if queue_item is not None:
            item, item_id = queue_item
            execution_start_time = time.perf_counter()  # 记录执行开始时间
            prompt_id = item[1]  # 获取提示词ID
            server_instance.last_prompt_id = prompt_id  # 更新服务器最后处理的提示词ID

            # 9.5 执行工作流
            e.execute(item[2], prompt_id, item[3], item[4])
            need_gc = True  # 标记需要垃圾回收

            # 9.6 标记任务完成
            q.task_done(
                item_id,
                e.history_result,
                status=execution.PromptQueue.ExecutionStatus(
                    status_str="success" if e.success else "error",
                    completed=e.success,
                    messages=e.status_messages,
                ),
            )

            # 9.7 通知客户端执行完成
            if server_instance.client_id is not None:
                server_instance.send_sync(
                    "executing",
                    {"node": None, "prompt_id": prompt_id},
                    server_instance.client_id,
                )

            # 9.8 计算并记录执行时间
            current_time = time.perf_counter()
            execution_time = current_time - execution_start_time

            # 如果执行时间超过10分钟，使用更易读的格式
            if execution_time > 600:
                execution_time = time.strftime("%H:%M:%S", time.gmtime(execution_time))
                logging.info(f"提示词执行完成，耗时: {execution_time}")
            else:
                logging.info("提示词执行完成，耗时: {:.2f} 秒".format(execution_time))

        # 9.9 处理队列标志
        flags = q.get_flags()
        free_memory = flags.get("free_memory", False)

        # 9.10 卸载模型以释放内存
        if flags.get("unload_models", free_memory):
            comfy.model_management.unload_all_models()
            need_gc = True
            last_gc_collect = 0

        # 9.11 重置执行器
        if free_memory:
            e.reset()
            need_gc = True
            last_gc_collect = 0

        # 9.12 执行垃圾回收
        if need_gc:
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > gc_collect_interval:
                gc.collect()  # Python垃圾回收
                comfy.model_management.soft_empty_cache()  # 清空GPU缓存
                last_gc_collect = current_time
                need_gc = False
                hook_breaker_ac10a0.restore_functions()  # 恢复被破坏的函数


# =============================================================================
# 异步运行函数 - 启动服务器并运行事件循环
# =============================================================================
async def run(server_instance, address="", port=8188, verbose=True, call_on_start=None):
    """
    异步启动ComfyUI服务器
    参数:
        server_instance: 服务器实例
        address: 监听地址（支持多个地址，用逗号分隔）
        port: 监听端口
        verbose: 是否显示详细信息
        call_on_start: 启动时回调函数
    """
    # 10.1 解析监听地址
    addresses = []
    for addr in address.split(","):  # 支持多个地址
        addresses.append((addr, port))

    # 10.2 并发运行服务器启动和发布循环
    await asyncio.gather(
        server_instance.start_multi_address(
            addresses, call_on_start, verbose
        ),  # 启动多地址服务器
        server_instance.publish_loop(),  # 运行发布循环
    )


# =============================================================================
# 进度钩子函数 - 拦截并处理执行进度更新
# =============================================================================
def hijack_progress(server_instance):
    """
    设置全局进度钩子，用于拦截和转发执行进度信息
    参数:
        server_instance: 服务器实例
    """

    def hook(value, total, preview_image, prompt_id=None, node_id=None):
        """
        进度钩子函数，在每次进度更新时被调用
        参数:
            value: 当前进度值
            total: 总进度值
            preview_image: 预览图像
            prompt_id: 提示词ID
            node_id: 节点ID
        """
        # 11.1 获取执行上下文
        executing_context = get_executing_context()

        # 11.2 从执行上下文获取ID（如果未提供）
        if prompt_id is None and executing_context is not None:
            prompt_id = executing_context.prompt_id
        if node_id is None and executing_context is not None:
            node_id = executing_context.node_id

        # 11.3 检查是否被中断
        comfy.model_management.throw_exception_if_processing_interrupted()

        # 11.4 使用服务器实例的ID作为后备
        if prompt_id is None:
            prompt_id = server_instance.last_prompt_id
        if node_id is None:
            node_id = server_instance.last_node_id

        # 11.5 构建进度信息
        progress = {
            "value": value,
            "max": total,
            "prompt_id": prompt_id,
            "node": node_id,
        }
        get_progress_state().update_progress(node_id, value, total, preview_image)

        # 11.6 发送进度更新到客户端
        server_instance.send_sync("progress", progress, server_instance.client_id)

        # 11.7 发送预览图像（如果存在且客户端支持）
        if preview_image is not None:
            # 只有当客户端不支持预览元数据时才使用旧方法
            if not feature_flags.supports_feature(
                server_instance.sockets_metadata,
                server_instance.client_id,
                "supports_preview_metadata",
            ):
                server_instance.send_sync(
                    BinaryEventTypes.UNENCODED_PREVIEW_IMAGE,
                    preview_image,
                    server_instance.client_id,
                )

    # 11.8 设置全局进度钩子
    comfy.utils.set_progress_bar_global_hook(hook)


# =============================================================================
# 清理临时文件函数
# =============================================================================
def cleanup_temp():
    """
    清理临时目录
    在程序启动和退出时调用，确保临时文件被正确清理
    """
    temp_dir = folder_paths.get_temp_directory()  # 获取临时目录路径
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)  # 递归删除临时目录，忽略错误


# =============================================================================
# 数据库设置函数
# =============================================================================
def setup_database():
    """
    初始化数据库系统
    用于存储用户数据、模型信息等
    """
    try:
        from app.database.db import init_db, dependencies_available

        if dependencies_available():  # 检查数据库依赖是否可用
            init_db()  # 初始化数据库
    except Exception as e:
        logging.error(
            f"数据库初始化失败。请确保已安装最新依赖。如果错误持续存在，请报告此问题，因为将来数据库将是必需的: {e}"
        )


# =============================================================================
# ComfyUI主启动函数 - 整个系统的核心启动逻辑
# =============================================================================
def start_comfyui(asyncio_loop=None):
    """
    启动ComfyUI服务器的主函数
    这是整个ComfyUI系统的核心启动逻辑，负责初始化所有组件

    参数:
        asyncio_loop: 可选的事件循环，如果为None则创建新的

    返回:
        (event_loop, prompt_server, start_all_func):
        - event_loop: 事件循环
        - prompt_server: 服务器实例
        - start_all_func: 启动函数
    """
    # 🔍 调试断点1：主启动函数开始
    # 在这里设置断点可以观察启动过程的开始
    # 在VS Code中点击行号左侧设置断点，或取消下面注释使用pdb
    # import pdb; pdb.set_trace()
    
    # 12.1 设置临时目录
    if args.temp_directory:
        temp_dir = os.path.join(os.path.abspath(args.temp_directory), "temp")
        logging.info(f"设置临时目录为: {temp_dir}")
        folder_paths.set_temp_directory(temp_dir)
    cleanup_temp()  # 清理旧的临时文件

    # 12.2 Windows独立构建更新
    if args.windows_standalone_build:
        try:
            import new_updater

            new_updater.update_windows_updater()  # 更新Windows独立版本
        except:
            pass  # 忽略更新错误

    # 12.3 创建或使用提供的事件循环
    if not asyncio_loop:
        asyncio_loop = asyncio.new_event_loop()  # 创建新的事件循环
        asyncio.set_event_loop(asyncio_loop)  # 设置为当前线程的事件循环

    # 12.4 创建服务器实例
    # 🔍 调试断点2：服务器实例创建
    # 在这里设置断点可以观察服务器实例的创建过程
    # 在VS Code中点击行号左侧设置断点，或取消下面注释使用pdb
    # import pdb; pdb.set_trace()
    prompt_server = server.PromptServer(asyncio_loop)

    # 12.5 保存函数状态并初始化节点系统
    hook_breaker_ac10a0.save_functions()  # 保存函数状态
    asyncio_loop.run_until_complete(
        nodes.init_extra_nodes(
            init_custom_nodes=(not args.disable_all_custom_nodes)
            or len(args.whitelist_custom_nodes) > 0,
            init_api_nodes=not args.disable_api_nodes,
        )
    )
    hook_breaker_ac10a0.restore_functions()  # 恢复函数状态

    # 12.6 执行系统检查和初始化
    cuda_malloc_warning()  # 检查CUDA内存分配支持
    setup_database()  # 初始化数据库

    # 12.7 配置服务器
    prompt_server.add_routes()  # 添加路由
    hijack_progress(prompt_server)  # 设置进度钩子

    # 12.8 启动工作线程
    # 🔍 调试断点3：工作线程启动
    # 在这里设置断点可以观察工作线程的启动过程
    # 在VS Code中点击行号左侧设置断点，或取消下面注释使用pdb
    # import pdb; pdb.set_trace()
    threading.Thread(
        target=prompt_worker,
        daemon=True,  # 守护线程，主程序退出时自动结束
        args=(
            prompt_server.prompt_queue,
            prompt_server,
        ),
    ).start()

    # 12.9 CI测试快速退出
    if args.quick_test_for_ci:
        exit(0)

    # 12.10 创建临时目录
    os.makedirs(folder_paths.get_temp_directory(), exist_ok=True)

    # 12.11 设置自动启动回调
    call_on_start = None
    if args.auto_launch:

        def startup_server(scheme, address, port):
            """启动时自动打开浏览器"""
            import webbrowser

            if os.name == "nt" and address == "0.0.0.0":  # Windows系统特殊处理
                address = "127.0.0.1"
            if ":" in address:  # IPv6地址处理
                address = "[{}]".format(address)
            webbrowser.open(f"{scheme}://{address}:{port}")

        call_on_start = startup_server

    # 12.12 定义异步启动函数
    async def start_all():
        """异步启动所有服务"""
        await prompt_server.setup()  # 设置服务器
        await run(
            prompt_server,
            address=args.listen,
            port=args.port,
            verbose=not args.dont_print_server,
            call_on_start=call_on_start,
        )

    # 12.13 返回组件供外部集成使用
    return asyncio_loop, prompt_server, start_all


# =============================================================================
# 主程序入口点 - 程序启动的最终入口
# =============================================================================
if __name__ == "__main__":
    """
    当直接运行此文件时，启动ComfyUI服务器
    这是程序的最终入口点，负责启动整个ComfyUI系统
    """
    # 13.1 输出版本信息
    logging.info("Python版本: {}".format(sys.version))
    logging.info("ComfyUI版本: {}".format(comfyui_version.__version__))

    # 13.2 检查Python版本兼容性
    if sys.version_info.major == 3 and sys.version_info.minor < 10:
        logging.warning(
            "警告：您正在使用低于3.10的Python版本，请升级到更新版本。推荐使用3.12及以上版本。"
        )

    # 13.3 启动ComfyUI系统
    event_loop, _, start_all_func = start_comfyui()

    try:
        # 13.4 运行异步启动函数
        x = start_all_func()
        app.logger.print_startup_warnings()  # 打印启动警告
        event_loop.run_until_complete(x)  # 运行事件循环直到完成
    except KeyboardInterrupt:
        # 13.5 处理用户中断（Ctrl+C）
        logging.info("\n服务器已停止")

    # 13.6 清理临时文件
    cleanup_temp()
