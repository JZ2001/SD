import os
import sys
import json
import subprocess
import platform
import psutil
import shutil
import datetime
import threading
import webbrowser
import logging
from pathlib import Path
import re
import time

# GUI库：使用PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QPushButton, 
                            QLabel, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit,
                            QCheckBox, QComboBox, QGroupBox, QTextEdit, QFileDialog,
                            QProgressBar, QMessageBox, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette
import qdarkstyle

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("launcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SDWebUILauncher")

class SystemChecker:
    """系统环境检测类"""
    
    def __init__(self):
        self.system_info = {}
        self.gpu_info = {}
        self.python_info = {}
        self.cuda_info = {}
        
    def check_system(self):
        """检查系统基本信息"""
        self.system_info['os'] = platform.system() + " " + platform.release()
        self.system_info['architecture'] = platform.architecture()[0]
        # 尝试获取更详细的CPU名称
        try:
             if platform.system() == "Windows":
                 # 使用wmic获取CPU名称，可能比platform.processor()更准确
                 cpu_name = subprocess.check_output(['wmic', 'cpu', 'get', 'name'], text=True).strip().split('\n')[-1]
                 self.system_info['cpu'] = cpu_name
             else: # Linux/macOS
                 # 尝试从/proc/cpuinfo读取 (Linux)
                 # macOS 可能需要 sysctl -n machdep.cpu.brand_string
                 # 这里简化处理
                 self.system_info['cpu'] = platform.processor() if platform.processor() else "未知"
        except Exception:
            self.system_info['cpu'] = platform.processor() if platform.processor() else "未知"

        self.system_info['cpu_count'] = psutil.cpu_count(logical=True)
        self.system_info['memory'] = round(psutil.virtual_memory().total / (1024**3), 2)
        
        logger.info(f"系统信息: {self.system_info}")
        return self.system_info
    
    def check_gpu(self):
        """检查GPU信息，优先使用nvidia-smi"""
        self.gpu_info = {}
        self.cuda_info = {}
        
        try:
            # 检查NVIDIA GPU
            # 增加查询cuda版本
            nvidia_smi_output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version,cuda_version', '--format=csv,noheader,nounits'],
                text=True,
                stderr=subprocess.DEVNULL # 隐藏可能的错误输出
            )
            
            lines = nvidia_smi_output.strip().split('\n')
            if not lines:
                 raise ValueError("nvidia-smi did not return GPU info.")

            for i, line in enumerate(lines):
                if not line.strip(): continue
                parts = [item.strip() for item in line.split(',')]
                if len(parts) < 4:
                    logger.warning(f"nvidia-smi 输出格式不完整: {line}")
                    continue # 跳过格式不正确的行

                name, memory_mb, driver, cuda_v = parts

                # 转换内存为GB
                memory_gb = round(float(memory_mb) / 1024, 2) if memory_mb.isdigit() else "未知"

                self.gpu_info[f'gpu_{i}'] = {
                    'name': name,
                    'memory': f"{memory_gb} GB" if memory_gb != "未知" else "未知",
                    'driver': driver,
                    'type': 'NVIDIA'
                }
                # 从nvidia-smi获取的CUDA版本通常更准确反映驱动支持
                if i == 0 and cuda_v and cuda_v != '[Not Supported]':
                    self.cuda_info['version'] = cuda_v

            # 如果nvidia-smi没有提供CUDA版本，尝试nvcc（可能不在PATH中）
            if 'version' not in self.cuda_info:
                try:
                    nvcc_output = subprocess.check_output(['nvcc', '--version'], text=True, stderr=subprocess.DEVNULL)
                    cuda_version_match = re.search(r'release (\d+\.\d+)', nvcc_output)
                    if cuda_version_match:
                        self.cuda_info['version'] = cuda_version_match.group(1)
                    else:
                         self.cuda_info['version'] = "未知 (nvcc)"
                except (subprocess.SubprocessError, FileNotFoundError):
                     self.cuda_info['version'] = "未知 (nvcc未找到)"

        except (subprocess.SubprocessError, FileNotFoundError, ValueError) as e:
            logger.warning(f"通过 nvidia-smi 检测NVIDIA GPU失败: {e}")
            # 尝试WMI作为后备 (仅Windows)
            if platform.system() == "Windows":
                 logger.info("尝试使用 WMI 检测 GPU...")
                 try:
                     import wmi # 需要 pip install wmi
                     computer = wmi.WMI()
                     gpu_info_raw = computer.Win32_VideoController()
                     
                     for i, gpu in enumerate(gpu_info_raw):
                         if "NVIDIA" in gpu.Name or "GeForce" in gpu.Name:
                            # WMI不直接提供显存和CUDA版本，仅记录名称和驱动
                             self.gpu_info[f'gpu_{i}'] = {
                                 'name': gpu.Name,
                                 'memory': "未知 (WMI)",
                                 'driver': gpu.DriverVersion if hasattr(gpu, 'DriverVersion') else "未知 (WMI)",
                                 'type': 'NVIDIA'
                             }
                         elif "AMD" in gpu.Name or "Radeon" in gpu.Name:
                            self.gpu_info[f'gpu_{i}'] = {
                                'name': gpu.Name,
                                'memory': "未知 (WMI)",
                                'driver': gpu.DriverVersion if hasattr(gpu, 'DriverVersion') else "未知 (WMI)",
                                'type': 'AMD'
                             }
                 except ImportError:
                     logger.error("WMI模块未安装，无法使用WMI检测GPU。请运行 'pip install wmi'")
                 except Exception as wmi_e:
                     logger.error(f"使用 WMI 检测 GPU 失败: {wmi_e}")

            # 如果所有方法都失败
            if not self.gpu_info:
                 self.gpu_info['gpu_0'] = {
                    'name': '未检测到支持的GPU',
                    'memory': 'N/A',
                    'driver': 'N/A',
                    'type': 'unknown'
                 }
                 self.cuda_info['version'] = "N/A"

        logger.info(f"GPU信息: {self.gpu_info}")
        logger.info(f"CUDA信息: {self.cuda_info}")
        return self.gpu_info, self.cuda_info

    def check_python(self, python_exe):
        """检查Python信息，传入指定的Python解释器路径"""
        self.python_info = {}
        if not os.path.exists(python_exe):
             logger.error(f"指定的Python路径不存在: {python_exe}")
             self.python_info['version'] = "错误: 路径无效"
             self.python_info['executable'] = python_exe
             self.python_info['packages'] = {}
             self.python_info['torch_cuda'] = False
             return self.python_info

        try:
            # 获取Python版本
            version_output = subprocess.check_output([python_exe, '--version'], text=True, stderr=subprocess.PIPE)
            self.python_info['version'] = version_output.strip().split()[-1]
        except subprocess.SubprocessError as e:
            logger.error(f"获取Python版本失败 ({python_exe}): {e}")
            self.python_info['version'] = "获取失败"

        self.python_info['executable'] = python_exe
        
        # 检查关键包
        packages = ['torch', 'torchvision', 'gradio', 'transformers', 'xformers'] # 添加xformers
        self.python_info['packages'] = {}
        
        pip_cmd = [python_exe, '-m', 'pip', 'show']

        for package in packages:
            try:
                # 使用指定的python环境的pip
                version_info = subprocess.check_output(pip_cmd + [package], text=True, stderr=subprocess.DEVNULL)
                version_match = re.search(r'Version:\s*([\d\.a-zA-Z+-]+)', version_info)
                if version_match:
                    self.python_info['packages'][package] = version_match.group(1)
                else:
                    self.python_info['packages'][package] = "已安装(版本未知)"
            except subprocess.SubprocessError:
                self.python_info['packages'][package] = "未安装"
        
        # 检查PyTorch是否支持CUDA
        if self.python_info['packages'].get('torch') not in ["未安装", None]:
            try:
                # 使用指定的python环境执行检查
                torch_cuda_output = subprocess.check_output(
                    [python_exe, '-c', 'import torch; print(torch.cuda.is_available())'],
                    text=True, stderr=subprocess.PIPE
                ).strip()
                self.python_info['torch_cuda'] = torch_cuda_output.lower() == "true"
            except subprocess.SubprocessError as e:
                logger.warning(f"检查torch CUDA支持失败: {e.stderr}")
                self.python_info['torch_cuda'] = False
        else:
            self.python_info['torch_cuda'] = False
            
        logger.info(f"Python信息 ({python_exe}): {self.python_info}")
        return self.python_info

class WebUILauncher:
    """WebUI启动管理类"""
    
    def __init__(self, webui_dir=None):
        self.webui_dir = os.path.abspath(webui_dir or os.getcwd())
        # **关键修改：指定使用内嵌的Python**
        # self.python_exe = os.path.join(self.webui_dir, 'python', 'python.exe')
        self.python_exe = sys.executable
        self.process = None
        self.config = self.load_config()
        # 更新配置中的python_path
        self.config['python_path'] = self.python_exe
        
    def load_config(self):
        """加载配置"""
        config_path = os.path.join(self.webui_dir, 'launcher_config.json')
        default_config = self._get_default_config()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置，以防缺少某些键
                    default_config.update(loaded_config)
                    return default_config
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}, 使用默认配置")
                return default_config
        else:
            logger.info("未找到配置文件，使用默认配置")
            return default_config
            
    def _get_default_config(self):
        """获取默认配置，参考成功日志"""
        # 确保python_path在初始化后设置
        # python_exe_path = os.path.join(self.webui_dir, 'python', 'python.exe') if hasattr(self, 'webui_dir') else sys.executable
        python_exe_path = sys.executable
        return {
            'python_path': python_exe_path, # 将在 __init__ 中被覆盖
            # 参考成功日志的参数，并移除可能由 .exe 自动处理的参数如 --theme, --autolaunch
            # 'launch_args': '--medvram --xformers --api --listen --skip-python-version-check',
            'launch_args': '--medvram --api --listen --skip-python-version-check --skip-torch-cuda-test', #mac原因
            'auto_launch_browser': True, # 保留此项，因为Python脚本需要明确控制
            'port': 7860,
            'use_gpu': True,
            'gpu_index': 0,
            'offline_mode': False,
            'proxy_address': "", # 添加代理设置
            'force_reinstall': False # 添加强制重装选项
        }
        
    def save_config(self):
        """保存配置"""
        # 确保python_path始终是内嵌路径
        self.config['python_path'] = self.python_exe
        config_path = os.path.join(self.webui_dir, 'launcher_config.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("配置保存成功")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            
    def prepare_environment(self):
        """准备环境，使用内嵌的Python和pip"""
        logger.info(f"使用Python环境: {self.python_exe}")
        if not os.path.exists(self.python_exe):
             logger.error(f"错误：找不到内嵌Python环境: {self.python_exe}")
             return False

        # **关键修改：使用内嵌Python对应的pip**
        pip_cmd_base = [self.python_exe, '-m', 'pip']
        
        # 设置代理 (如果配置了)
        proxy = self.config.get('proxy_address', '')
        pip_options = []
        if proxy:
            pip_options.extend(['--proxy', proxy])
            logger.info(f"使用代理: {proxy}")

        pip_install_cmd = pip_cmd_base + ['install'] + pip_options
        pip_show_cmd = pip_cmd_base + ['show']
        
        try:
            # 检查是否需要安装或强制重装torch
            install_torch = self.config.get('force_reinstall', False)
            if not install_torch:
                result = subprocess.run(pip_show_cmd + ['torch'], capture_output=True, text=True)
                if result.returncode != 0:
                    install_torch = True
                    logger.info("未检测到 PyTorch，将进行安装。")
                else:
                    logger.info("检测到已安装 PyTorch。")

            if install_torch:
                logger.info(f"{'强制' if self.config.get('force_reinstall') else ''}安装/更新 PyTorch...")
                
                # **重要：根据检测到的CUDA版本选择合适的PyTorch命令**
                # 假设 SystemChecker 已经运行并将cuda版本存储在 cuda_info 中
                cuda_version_str = self.config.get('detected_cuda_version', 'N/A')
                torch_install_url = "https://download.pytorch.org/whl/cu118" # 默认或备选 CUDA 11.8
                
                if cuda_version_str.startswith("12."):
                     # CUDA 12.x 驱动通常能兼容为 12.1 构建的 PyTorch
                     torch_install_url = "https://download.pytorch.org/whl/cu121"
                     logger.info("检测到 CUDA 12.x，选择 PyTorch for cu121。")
                elif cuda_version_str.startswith("11."):
                     torch_install_url = "https://download.pytorch.org/whl/cu118"
                     logger.info("检测到 CUDA 11.x，选择 PyTorch for cu118。")
                else:
                     logger.warning(f"无法确定合适的CUDA版本 ({cuda_version_str})，默认使用 cu118 URL。如果失败，请手动安装。")

                # 使用与原始启动器日志一致的版本，但使用推断的CUDA URL
                torch_package = "torch==2.1.2" # 或者使用日志中的 2.5.1
                torchvision_package = "torchvision==0.16.2" # 或对应 2.5.1 的版本 0.20.1
                # 为了保险起见，先用回 2.1.2 和 0.16.2
                
                # 安装 xformers (如果配置了)
                xformers_package = "xformers==0.0.23.post1" # 或尝试更新的版本
                
                # 组合安装命令
                # 先尝试安装 torch 和 torchvision
                torch_cmd_list = pip_install_cmd + [torch_package, torchvision_package, '--extra-index-url', torch_install_url]
                
                logger.info(f"执行命令: {' '.join(torch_cmd_list)}")
                retry_count = 2 # 减少重试次数
                success = False
                while retry_count > 0:
                    try:
                        # 设置超时，例如 10 分钟
                        result = subprocess.run(torch_cmd_list, check=True, capture_output=True, text=True, timeout=600)
                        logger.info("PyTorch 和 torchvision 安装成功。")
                        logger.debug(f"Pip 输出:\n{result.stdout}")
                        success = True
                        break
                    except subprocess.TimeoutExpired:
                         logger.error("PyTorch 安装超时。")
                         retry_count = 0 # 不再重试
                    except subprocess.CalledProcessError as e:
                        retry_count -= 1
                        logger.error(f"PyTorch 安装失败 (Exit Code: {e.returncode})，剩余重试次数: {retry_count}")
                        logger.error(f"错误输出:\n{e.stderr}\n标准输出:\n{e.stdout}")
                        if retry_count == 0:
                            logger.error("PyTorch 安装失败次数过多。")
                            # return False # 暂时不返回False，继续尝试安装其他依赖
                        else:
                            time.sleep(3)
                
                # 如果配置了xformers且torch安装成功(或至少尝试过)
                if '--xformers' in self.config.get('launch_args', '') and success:
                     logger.info("安装 xformers...")
                     xformers_cmd_list = pip_install_cmd + [xformers_package]
                     logger.info(f"执行命令: {' '.join(xformers_cmd_list)}")
                     try:
                          subprocess.run(xformers_cmd_list, check=True, capture_output=True, text=True, timeout=300)
                          logger.info("xformers 安装成功。")
                     except subprocess.TimeoutExpired:
                          logger.error("xformers 安装超时。")
                     except subprocess.CalledProcessError as e:
                          logger.error(f"xformers 安装失败: {e.stderr}")
                          # xformers 安装失败通常不阻塞启动，只记录错误

            # 安装其他依赖 (requirements_versions.txt)
            req_file = os.path.join(self.webui_dir, 'requirements_versions.txt')
            if os.path.exists(req_file):
                logger.info("检查/安装 requirements_versions.txt 中的依赖...")
                try:
                    req_cmd_list = pip_install_cmd + ['-r', req_file]
                    logger.info(f"执行命令: {' '.join(req_cmd_list)}")
                    subprocess.run(req_cmd_list, check=True, capture_output=True, text=True, timeout=600)
                    logger.info("依赖安装成功。")
                except subprocess.TimeoutExpired:
                     logger.error("依赖安装超时。")
                except subprocess.CalledProcessError as e:
                    logger.error(f"安装依赖失败: {e.stderr}")
                    # return False # 根据需要决定是否在此处返回失败

            # 重置强制重装标志
            if self.config.get('force_reinstall'):
                 self.config['force_reinstall'] = False
                 self.save_config()

            logger.info("环境准备完成。")
            return True
        except Exception as e: # 捕获更广泛的异常
            logger.error(f"环境准备过程中发生意外错误: {e}", exc_info=True)
            return False
            
    def get_launch_command(self):
        """获取启动命令"""
        # **关键修改：始终使用内嵌Python**
        python_path = self.python_exe 
        launch_script = os.path.join(self.webui_dir, 'launch.py')
        args = self.config.get('launch_args', '')
        
        # 确保基本参数存在
        required_args = {'--listen'} # 根据需要添加其他必须参数
        current_args = set(arg for arg in args.split() if arg.startswith('--'))
        
        for req_arg in required_args:
             if req_arg not in current_args:
                  args += f" {req_arg}".strip()
                  logger.info(f"自动添加缺失的参数: {req_arg}")
                  
        # 移除可能冲突或多余的参数 (示例)
        args_list = args.split()
        # args_list = [arg for arg in args_list if arg != '--autolaunch'] # Python脚本不应处理autolaunch
        # args_list = [arg for arg in args_list if arg != '--theme'] # theme 通常由Gradio处理
        args = " ".join(args_list)
        
        # 处理设备ID (如果需要)
        if self.config.get('use_gpu', True):
            gpu_index = self.config.get('gpu_index', 0)
            if gpu_index != 0:
                 # 检查是否已存在 device-id 参数
                 if '--device-id' not in args:
                      args += f" --device-id {gpu_index}"
                 else:
                      # 更新现有的 device-id 参数 (如果需要)
                      args = re.sub(r'--device-id\s+\d+', f'--device-id {gpu_index}', args)
        else: # 如果禁用GPU
            if '--use-cpu' not in args: # 假设有 --use-cpu 参数
                args += " all" # 或者添加适合CPU模式的参数

        cmd = f'"{python_path}" "{launch_script}" {args}'
        logger.info(f"最终启动命令: {cmd}")
        return cmd
        
    def launch(self):
        """启动WebUI"""
        if self.process and self.process.poll() is None:
            logger.warning("WebUI已经在运行中")
            return True
            
        cmd = self.get_launch_command()
        cwd = self.webui_dir
        
        try:
            # 使用Popen启动进程
            self.process = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            logger.info("WebUI启动成功")
            
            # 如果配置了自动打开浏览器
            if self.config.get('auto_launch_browser', True):
                port = self.config.get('port', 7860)
                url = f"http://127.0.0.1:{port}"
                
                # 等待5秒后打开浏览器
                def open_browser():
                    time.sleep(5)
                    webbrowser.open(url)
                    
                threading.Thread(target=open_browser).start()
                
            return True
        except Exception as e:
            logger.error(f"启动WebUI失败: {e}")
            return False
            
    def stop(self):
        """停止WebUI"""
        if self.process and self.process.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
                else:
                    self.process.terminate()
                    
                self.process.wait(timeout=5)
                logger.info("WebUI已停止")
                return True
            except Exception as e:
                logger.error(f"停止WebUI失败: {e}")
                return False
        else:
            logger.info("WebUI未在运行")
            return True
            
    def is_running(self):
        """检查WebUI是否在运行"""
        return self.process is not None and self.process.poll() is None
        
    def get_log_output(self):
        """获取日志输出"""
        if not self.process:
            return None
            
        output = []
        
        # 非阻塞方式读取输出
        if self.process.stdout:
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                output.append(line.strip())
                
        return output if output else None

    def set_proxy(self, proxy_address):
        """设置网络代理"""
        os.environ['http_proxy'] = proxy_address
        os.environ['https_proxy'] = proxy_address
        logger.info(f"已设置代理: {proxy_address}")

class LauncherMainWindow(QMainWindow):
    """启动器主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SD-WebUI启动器")
        self.setMinimumSize(800, 600)
        
        # 初始化系统检测器和启动器
        self.system_checker = SystemChecker()
        # **修改：传递 WebUI 根目录**
        self.webui_launcher = WebUILauncher(os.path.dirname(os.path.abspath(__file__))) 
        
        # 设置UI
        self.setup_ui()
        
        # 执行初始检查
        self.run_system_check()
        
    def setup_ui(self):
        """设置UI"""
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # === 状态选项卡 ===
        status_tab = QWidget()
        status_layout = QVBoxLayout()
        
        # 系统信息组
        system_group = QGroupBox("系统信息")
        system_layout = QVBoxLayout()
        
        self.os_label = QLabel("操作系统: 检测中...")
        self.cpu_label = QLabel("CPU: 检测中...")
        self.memory_label = QLabel("内存: 检测中...")
        
        system_layout.addWidget(self.os_label)
        system_layout.addWidget(self.cpu_label)
        system_layout.addWidget(self.memory_label)
        system_group.setLayout(system_layout)
        
        # GPU信息组
        gpu_group = QGroupBox("GPU信息")
        gpu_layout = QVBoxLayout()
        
        self.gpu_label = QLabel("GPU: 检测中...")
        self.gpu_memory_label = QLabel("GPU内存: 检测中...")
        self.driver_label = QLabel("驱动版本: 检测中...")
        self.cuda_label = QLabel("CUDA版本: 检测中...")
        
        gpu_layout.addWidget(self.gpu_label)
        gpu_layout.addWidget(self.gpu_memory_label)
        gpu_layout.addWidget(self.driver_label)
        gpu_layout.addWidget(self.cuda_label)
        gpu_group.setLayout(gpu_layout)
        
        # Python信息组
        python_group = QGroupBox("Python环境")
        python_layout = QVBoxLayout()
        python_layout.setObjectName("python_layout") # 添加 objectName
        
        self.python_version_label = QLabel("Python版本: 检测中...")
        self.torch_label = QLabel("PyTorch: 检测中...")
        self.gradio_label = QLabel("Gradio: 检测中...")
        
        python_layout.addWidget(self.python_version_label)
        python_layout.addWidget(self.torch_label)
        python_layout.addWidget(self.gradio_label)
        python_group.setLayout(python_layout)
        
        # 状态和操作组
        action_group = QGroupBox("WebUI状态")
        action_layout = QHBoxLayout()
        
        self.status_label = QLabel("状态: 未运行")
        self.start_button = QPushButton("启动WebUI")
        self.start_button.clicked.connect(self.start_webui)
        self.stop_button = QPushButton("停止WebUI")
        self.stop_button.clicked.connect(self.stop_webui)
        self.stop_button.setEnabled(False)
        
        action_layout.addWidget(self.status_label)
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.stop_button)
        action_group.setLayout(action_layout)
        
        # 日志组
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # 添加所有组到状态布局
        status_layout.addWidget(system_group)
        status_layout.addWidget(gpu_group)
        status_layout.addWidget(python_group)
        status_layout.addWidget(action_group)
        status_layout.addWidget(log_group)
        
        status_tab.setLayout(status_layout)
        
        # === 设置选项卡 ===
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        
        # WebUI目录设置
        dir_group = QGroupBox("WebUI目录")
        dir_layout = QHBoxLayout()
        
        self.webui_dir_edit = QLineEdit(self.webui_launcher.webui_dir)
        self.webui_dir_edit.setReadOnly(True)
        self.webui_dir_button = QPushButton("浏览...")
        self.webui_dir_button.clicked.connect(self.browse_webui_dir)
        
        dir_layout.addWidget(self.webui_dir_edit)
        dir_layout.addWidget(self.webui_dir_button)
        dir_group.setLayout(dir_layout)
        
        # 启动参数设置
        args_group = QGroupBox("启动参数")
        args_layout = QVBoxLayout()
        
        self.args_edit = QLineEdit(self.webui_launcher.config.get('launch_args', ''))
        args_layout.addWidget(self.args_edit)
        
        # 常用参数复选框
        params_layout = QHBoxLayout()
        
        self.xformers_check = QCheckBox("--xformers")
        self.xformers_check.setChecked('--xformers' in self.args_edit.text())
        
        self.medvram_check = QCheckBox("--medvram")
        self.medvram_check.setChecked('--medvram' in self.args_edit.text())
        
        self.listen_check = QCheckBox("--listen")
        self.listen_check.setChecked('--listen' in self.args_edit.text())
        
        self.api_check = QCheckBox("--api")
        self.api_check.setChecked('--api' in self.args_edit.text())
        
        params_layout.addWidget(self.xformers_check)
        params_layout.addWidget(self.medvram_check)
        params_layout.addWidget(self.listen_check)
        params_layout.addWidget(self.api_check)
        
        args_layout.addLayout(params_layout)
        args_group.setLayout(args_layout)
        
        # 其他设置
        other_group = QGroupBox("其他设置")
        other_layout = QVBoxLayout()
        
        self.autolaunch_check = QCheckBox("自动打开浏览器")
        self.autolaunch_check.setChecked(self.webui_launcher.config.get('auto_launch_browser', True))
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_edit = QLineEdit(str(self.webui_launcher.config.get('port', 7860)))
        port_layout.addWidget(self.port_edit)
        
        other_layout.addWidget(self.autolaunch_check)
        other_layout.addLayout(port_layout)
        other_group.setLayout(other_layout)
        
        # 网络设置组
        network_group = QGroupBox("网络设置")
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("HTTP代理地址:"))
        self.proxy_edit = QLineEdit(self.webui_launcher.config.get('proxy_address', ''))
        self.proxy_edit.setPlaceholderText("例如: http://127.0.0.1:1080")
        network_layout.addWidget(self.proxy_edit)
        network_group.setLayout(network_layout)

        # 强制重装组
        reinstall_group = QGroupBox("维护")
        reinstall_layout = QHBoxLayout()
        self.force_reinstall_check = QCheckBox("强制重新安装依赖 (下次启动时)")
        self.force_reinstall_check.setChecked(self.webui_launcher.config.get('force_reinstall', False))
        reinstall_layout.addWidget(self.force_reinstall_check)
        reinstall_group.setLayout(reinstall_layout)

        # 添加新组到设置布局 (在 other_group 和 save_button 之间)
        settings_layout.insertWidget(settings_layout.indexOf(other_group), network_group)
        settings_layout.insertWidget(settings_layout.indexOf(other_group), reinstall_group)

        # 保存按钮
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        
        # 添加所有组到设置布局
        settings_layout.addWidget(dir_group)
        settings_layout.addWidget(args_group)
        settings_layout.addWidget(other_group)
        settings_layout.addWidget(self.save_button)
        settings_layout.addStretch()
        
        settings_tab.setLayout(settings_layout)
        
        # 添加选项卡到选项卡控件
        tab_widget.addTab(status_tab, "状态")
        tab_widget.addTab(settings_tab, "设置")
        
        # 添加选项卡控件到主布局
        main_layout.addWidget(tab_widget)
        
        # 创建中央窗口部件并设置布局
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 设置状态栏
        self.statusBar().showMessage("就绪")
        
        # 设置计时器用于更新UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(1000)  # 每秒更新一次
        
    def run_system_check(self):
        """运行系统检查"""
        self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始系统检查...")
        self.statusBar().showMessage("正在检查系统...")
        QApplication.processEvents() # 允许UI更新

        # 检查系统信息
        system_info = self.system_checker.check_system()
        self.os_label.setText(f"操作系统: {system_info.get('os', '未知')}")
        self.cpu_label.setText(f"CPU: {system_info.get('cpu', '未知')} ({system_info.get('cpu_count', 0)}核)")
        self.memory_label.setText(f"内存: {system_info.get('memory', 0)} GB")
        
        # 检查GPU信息
        gpu_info, cuda_info = self.system_checker.check_gpu()
        
        if gpu_info and 'gpu_0' in gpu_info and gpu_info['gpu_0'].get('type') != 'unknown':
            gpu_0 = gpu_info.get('gpu_0', {})
            self.gpu_label.setText(f"GPU: {gpu_0.get('name', '未知')}")
            self.gpu_memory_label.setText(f"GPU内存: {gpu_0.get('memory', '未知')}")
            self.driver_label.setText(f"驱动版本: {gpu_0.get('driver', '未知')}")
            detected_cuda_version = cuda_info.get('version', 'N/A')
            self.cuda_label.setText(f"CUDA版本: {detected_cuda_version}")
            
            # 保存检测到的GPU和CUDA信息到配置，供prepare_environment使用
            self.webui_launcher.config['detected_gpus'] = gpu_info
            self.webui_launcher.config['detected_cuda_version'] = detected_cuda_version
        else:
            self.gpu_label.setText("GPU: 未检测到支持的GPU")
            self.gpu_memory_label.setText("GPU内存: N/A")
            self.driver_label.setText("驱动版本: N/A")
            self.cuda_label.setText("CUDA版本: N/A")
            self.webui_launcher.config['detected_gpus'] = {}
            self.webui_launcher.config['detected_cuda_version'] = 'N/A'

        # **修改：传入正确的python_exe路径**
        python_info = self.system_checker.check_python(self.webui_launcher.python_exe)
        self.python_version_label.setText(f"Python版本: {python_info.get('version', '未知')}")
        
        packages = python_info.get('packages', {})
        torch_version = packages.get('torch', '未安装')
        torch_cuda_support = python_info.get('torch_cuda', False)
        self.torch_label.setText(f"PyTorch: {torch_version} (CUDA: {'支持' if torch_cuda_support else '不支持'})")
        self.gradio_label.setText(f"Gradio: {packages.get('gradio', '未安装')}")
        self.xformers_label = QLabel(f"Xformers: {packages.get('xformers', '未安装')}") # 添加Xformers显示

        # 将xformers标签添加到python_group
        python_group_layout = self.findChild(QVBoxLayout, "python_layout") # 需要给布局命名或通过查找
        if python_group_layout:
             if not hasattr(self, 'xformers_label_widget'): # 防止重复添加
                 self.xformers_label_widget = self.xformers_label
                 python_group_layout.addWidget(self.xformers_label_widget)
        else: # 如果找不到布局，尝试添加到 group box
             python_group = self.findChild(QGroupBox, "Python环境")
             if python_group and python_group.layout() and not hasattr(self, 'xformers_label_widget'):
                 self.xformers_label_widget = self.xformers_label
                 python_group.layout().addWidget(self.xformers_label_widget)

        # 更新日志
        log_entry = f"""
[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 系统检查完成
操作系统: {system_info.get('os', '未知')}
CPU: {system_info.get('cpu', '未知')} ({system_info.get('cpu_count', 0)}核)
内存: {system_info.get('memory', 0)} GB
GPU: {gpu_info.get('gpu_0', {}).get('name', '未检测到')}
GPU内存: {gpu_info.get('gpu_0', {}).get('memory', 'N/A')}
驱动版本: {gpu_info.get('gpu_0', {}).get('driver', 'N/A')}
CUDA版本: {cuda_info.get('version', 'N/A')}
Python路径: {python_info.get('executable', '未知')}
Python版本: {python_info.get('version', '未知')}
PyTorch: {torch_version} (CUDA: {'支持' if torch_cuda_support else '不支持'})
Gradio: {packages.get('gradio', '未安装')}
Xformers: {packages.get('xformers', '未安装')}
-----------------------------
"""
        self.log_text.append(log_entry.strip())
        self.statusBar().showMessage("系统检查完成", 3000)

    def update_ui(self):
        """更新UI状态"""
        # 检查WebUI是否在运行
        is_running = self.webui_launcher.is_running()
        
        self.status_label.setText(f"状态: {'运行中' if is_running else '未运行'}")
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        
        # 更新日志
        log_output = self.webui_launcher.get_log_output()
        if log_output:
            for line in log_output:
                self.log_text.append(line)
            # 滚动到底部
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def browse_webui_dir(self):
        """浏览WebUI目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择WebUI目录", self.webui_dir_edit.text())
        if dir_path:
            self.webui_dir_edit.setText(dir_path)
            self.webui_launcher.webui_dir = dir_path
            self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WebUI目录已更改为: {dir_path}")
    
    def save_settings(self):
        """保存设置"""
        # 收集启动参数
        # 使用 strip() 移除前后空格
        args = self.args_edit.text().strip() 
        args_set = set(args.split()) # 使用集合方便检查

        # 处理复选框 (简化逻辑)
        checkboxes = {
             '--xformers': self.xformers_check,
             '--medvram': self.medvram_check,
             '--listen': self.listen_check,
             '--api': self.api_check
        }

        for arg, checkbox in checkboxes.items():
            if checkbox.isChecked():
                args_set.add(arg)
            else:
                args_set.discard(arg) # 从集合中移除（如果存在）

        # 重构 args 字符串
        # 保持一定顺序，例如将优化参数放前面
        ordered_args = []
        # 优化参数
        if '--xformers' in args_set: ordered_args.append('--xformers')
        if '--medvram' in args_set: ordered_args.append('--medvram')
        # 网络参数
        if '--listen' in args_set: ordered_args.append('--listen')
        if '--api' in args_set: ordered_args.append('--api')
        # 添加其他不在复选框中的参数
        other_args = [a for a in args.split() if a not in checkboxes and a]
        ordered_args.extend(other_args)

        final_args = " ".join(ordered_args)
        self.args_edit.setText(final_args) # 更新文本框显示
        
        # 更新配置
        self.webui_launcher.config['launch_args'] = final_args
        self.webui_launcher.config['auto_launch_browser'] = self.autolaunch_check.isChecked()
        self.webui_launcher.config['proxy_address'] = self.proxy_edit.text().strip() if hasattr(self, 'proxy_edit') else "" # 读取代理设置
        self.webui_launcher.config['force_reinstall'] = self.force_reinstall_check.isChecked() if hasattr(self, 'force_reinstall_check') else False # 读取强制重装
        
        try:
            port = int(self.port_edit.text())
            if 1024 <= port <= 65535:
                self.webui_launcher.config['port'] = port
            else:
                QMessageBox.warning(self, "端口无效", "端口必须在1024-65535之间")
                return
        except ValueError:
            QMessageBox.warning(self, "端口无效", "请输入有效的端口号")
            return
        
        # 保存配置
        self.webui_launcher.save_config()
        
        self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 设置已保存")
        self.statusBar().showMessage("设置已保存", 3000)
    
    def start_webui(self):
        """启动WebUI"""
        self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始启动WebUI...")
        self.statusBar().showMessage("正在准备环境...")
        QApplication.processEvents() # 更新UI

        # 检查 launch.py 是否存在
        if not os.path.exists(os.path.join(self.webui_launcher.webui_dir, 'launch.py')):
            QMessageBox.critical(self, "错误", "无效的WebUI目录，找不到launch.py文件。请在设置中指定正确的目录。")
            self.statusBar().showMessage("启动失败：目录无效")
            return

        # **步骤1：准备环境 (安装依赖)**
        # 使用线程执行，避免UI卡死
        self.env_thread = EnvironmentPrepThread(self.webui_launcher)
        self.env_thread.log_signal.connect(self.append_log)
        self.env_thread.finished_signal.connect(self.on_env_prepared)
        self.start_button.setEnabled(False) # 禁用启动按钮直到环境准备完成
        self.stop_button.setEnabled(False)
        self.env_thread.start()

    def on_env_prepared(self, success):
        """环境准备完成后的回调"""
        if success:
            self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 环境准备完成，开始启动WebUI进程...")
            self.statusBar().showMessage("正在启动WebUI进程...")
            QApplication.processEvents()

            # **步骤2：启动WebUI进程**
            if self.webui_launcher.launch():
                self.statusBar().showMessage("WebUI已启动", 3000)
                # 启动成功后才启用停止按钮
                self.stop_button.setEnabled(True)
            else:
                QMessageBox.critical(self, "错误", "启动WebUI进程失败，请检查日志。")
                self.statusBar().showMessage("启动失败：进程启动错误")
                # 启动失败，重新启用启动按钮
                self.start_button.setEnabled(True)
        else:
            QMessageBox.critical(self, "错误", "环境准备失败，无法启动WebUI。请检查日志和网络连接。")
            self.statusBar().showMessage("启动失败：环境准备错误")
            # 环境准备失败，重新启用启动按钮
            self.start_button.setEnabled(True)

    def append_log(self, message):
         """安全地追加日志到 QTextEdit"""
         self.log_text.append(message)
         self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def stop_webui(self):
        """停止WebUI"""
        self.log_text.append(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在停止WebUI...")
        
        if self.webui_launcher.stop():
            self.statusBar().showMessage("WebUI已停止", 3000)
        else:
            QMessageBox.warning(self, "警告", "停止WebUI失败，可能需要手动终止进程")
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.webui_launcher.is_running():
            reply = QMessageBox.question(
                self, "确认退出", 
                "WebUI正在运行。是否停止WebUI并退出?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.webui_launcher.stop()
                event.accept()
            else:
                event.ignore()

# **添加用于环境准备的线程类**
class EnvironmentPrepThread(QThread):
     log_signal = pyqtSignal(str)
     finished_signal = pyqtSignal(bool)

     def __init__(self, launcher_instance):
         super().__init__()
         self.launcher = launcher_instance

     def run(self):
         # 重定向 subprocess 的输出到日志信号
         # (注意：subprocess.run 本身不直接支持实时流式输出到信号，
         #  更复杂的实现可以用 Popen + threading 读取 stdout/stderr)
         # 这里简化处理，只在开始和结束时发信号，错误信息通过logger记录
         self.log_signal.emit(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始环境准备...")
         success = self.launcher.prepare_environment()
         status_msg = "成功" if success else "失败"
         self.log_signal.emit(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 环境准备 {status_msg}")
         self.finished_signal.emit(success)

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # 设置应用图标和样式
    window = LauncherMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()