# Stable Diffusion web UI
一个使用 Gradio 库实现的 Stable Diffusion 网页界面。

![](screenshot.png)

## 功能
[详细功能展示（含图片）](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features)：
- 原始的 txt2img 和 img2img 模式
- 一键安装和运行脚本（但你仍需安装 Python 和 Git）
- 外绘（Outpainting）
- 内绘（Inpainting）
- 彩色草图
- 提示词矩阵
- Stable Diffusion 放大
- 注意力机制，指定模型应更加关注的文本部分
    - 西装男 `((西装))` - 将更加关注西装
    - 西装男 `(西装:1.21)` - 替代语法
    - 选择文本并按 `Ctrl+上箭头` 或 `Ctrl+下箭头`（MacOS上为 `Command+上箭头` 或 `Command+下箭头`）自动调整对所选文本的关注度（由匿名用户贡献的代码）
- 循环回馈，多次运行 img2img 处理
- X/Y/Z 图表，一种绘制具有不同参数的三维图像图表的方式
- 文本反转（Textual Inversion）
    - 拥有任意数量的嵌入并为它们使用任何你喜欢的名称
    - 使用具有每个标记不同向量数的多个嵌入
    - 适用于半精度浮点数
    - 可在 8GB 显存上训练嵌入（也有报告称 6GB 可用）
- 附加选项卡，包含：
    - GFPGAN，修复面部的神经网络
    - CodeFormer，作为 GFPGAN 替代品的面部修复工具
    - RealESRGAN，神经网络放大器
    - ESRGAN，具有许多第三方模型的神经网络放大器
    - SwinIR 和 Swin2SR（[参见此处](https://github.com/AUTOMATIC1111/stable-diffusion-webui/pull/2092)），神经网络放大器
    - LDSR，潜在扩散超分辨率放大
- 调整宽高比选项
- 采样方法选择
    - 调整采样器 eta 值（噪声乘数）
    - 更高级的噪声设置选项
- 随时中断处理
- 支持 4GB 显存的显卡（也有报告称 2GB 可用）
- 批处理的正确种子
- 实时提示词标记长度验证
- 生成参数
     - 用于生成图像的参数会与图像一起保存
     - PNG 的 PNG 块中，JPEG 的 EXIF 中
     - 可以将图像拖到 PNG 信息选项卡以恢复生成参数并自动将它们复制到界面中
     - 可以在设置中禁用
     - 将图像/文本参数拖放到提示框
- 读取生成参数按钮，将提示框中的参数加载到界面
- 设置页面
- 从界面运行任意 Python 代码（必须使用 `--allow-code` 运行以启用）
- 大多数界面元素的鼠标悬停提示
- 通过文本配置可更改界面元素的默认值/混合值/最大值/步长值
- 平铺支持，创建可像纹理一样平铺的图像的复选框
- 进度条和实时图像生成预览
    - 可以使用单独的神经网络生成预览，几乎不需要额外显存或计算资源
- 负面提示，一个额外的文本字段，允许你列出你不想在生成图像中看到的内容
- 样式，一种保存部分提示并通过下拉菜单稍后轻松应用的方法
- 变化，一种生成相同图像但有微小差异的方法
- 种子调整大小，一种在略微不同分辨率下生成相同图像的方法
- CLIP 查询器，一个尝试从图像猜测提示的按钮
- 提示编辑，一种在生成过程中更改提示的方法，例如开始制作西瓜并在中途切换到动漫女孩
- 批处理处理，使用 img2img 处理一组文件
- img2img 替代方法，交叉注意力控制的反向 Euler 方法
- 高分辨率修复，一种一键生成高分辨率图像而没有常见失真的便捷选项
- 动态重载检查点
- 检查点合并器，一个允许你将最多 3 个检查点合并为一个的选项卡
- [自定义脚本](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Custom-Scripts)，包含社区的许多扩展
- [组合式扩散](https://energy-based-model.github.io/Compositional-Visual-Generation-with-Composable-Diffusion-Models/)，一种同时使用多个提示的方法
     - 使用大写 `AND` 分隔提示
     - 也支持提示权重：`猫 :1.2 AND 狗 AND 企鹅 :2.2`
- 提示词没有标记限制（原始 Stable Diffusion 最多允许使用 75 个标记）
- DeepDanbooru 集成，为动漫提示创建 Danbooru 风格的标签
- [xformers](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Xformers)，特定显卡的主要速度提升：（添加 `--xformers` 到命令行参数）
- 通过扩展：[历史选项卡](https://github.com/yfszzx/stable-diffusion-webui-images-browser)：在界面内方便地查看、导向和删除图像
- 永久生成选项
- 训练选项卡
     - 超网络和嵌入选项
     - 预处理图像：裁剪、镜像、使用 BLIP 或 deepdanbooru（用于动漫）自动标记
- Clip 跳过
- 超网络
- Loras（与超网络相同但更美观）
- 一个单独的界面，可以选择并预览要添加到提示中的嵌入、超网络或 Loras
- 可以从设置界面选择加载不同的 VAE
- 进度条中的预计完成时间
- API
- 支持 RunwayML 的专用[内绘模型](https://github.com/runwayml/stable-diffusion#inpainting-with-stable-diffusion)
- 通过扩展：[美学梯度](https://github.com/AUTOMATIC1111/stable-diffusion-webui-aesthetic-gradients)，一种通过使用 clip 图像嵌入生成具有特定美感的图像的方法（实现自 [https://github.com/vicgalle/stable-diffusion-aesthetic-gradients](https://github.com/vicgalle/stable-diffusion-aesthetic-gradients)）
- [Stable Diffusion 2.0](https://github.com/Stability-AI/stablediffusion) 支持 - 查看 [wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#stable-diffusion-20) 获取指导
- [Alt-Diffusion](https://arxiv.org/abs/2211.06679) 支持 - 查看 [wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#alt-diffusion) 获取指导
- 现在没有任何不良字母！
- 以 safetensors 格式加载检查点
- 放宽分辨率限制：生成图像的尺寸必须是 8 的倍数，而不是 64
- 现在有许可证了！
- 从设置界面重新排序界面元素
- [Segmind Stable Diffusion](https://huggingface.co/segmind/SSD-1B) 支持

## 安装和运行
确保满足所需的[依赖项](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Dependencies)并按照以下适用的说明操作：
- [NVidia](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Install-and-Run-on-NVidia-GPUs)（推荐）
- [AMD](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Install-and-Run-on-AMD-GPUs) GPU
- [Intel CPU、Intel GPU（集成和独立）](https://github.com/openvinotoolkit/stable-diffusion-webui/wiki/Installation-on-Intel-Silicon)（外部 wiki 页面）
- [昇腾 NPU](https://github.com/wangshuai09/stable-diffusion-webui/wiki/Install-and-run-on-Ascend-NPUs)（外部 wiki 页面）

或者，使用在线服务（如 Google Colab）：

- [在线服务列表](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Online-Services)

### 在 Windows 10/11 上使用发布包和 NVidia-GPU 安装
1. 从 [v1.0.0-pre](https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases/tag/v1.0.0-pre) 下载 `sd.webui.zip` 并解压其内容。
2. 运行 `update.bat`。
3. 运行 `run.bat`。
> 更多详情请参阅 [Install-and-Run-on-NVidia-GPUs](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Install-and-Run-on-NVidia-GPUs)

### Windows 上的自动安装
1. 安装 [Python 3.10.6](https://www.python.org/downloads/release/python-3106/)（较新版本的 Python 不支持 torch），并勾选"Add Python to PATH"。
2. 安装 [git](https://git-scm.com/download/win)。
3. 下载 stable-diffusion-webui 仓库，例如通过运行 `git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git`。
4. 从 Windows 资源管理器中以普通非管理员用户身份运行 `webui-user.bat`。

### Linux 上的自动安装
1. 安装依赖项：
```bash
# 基于 Debian：
sudo apt install wget git python3 python3-venv libgl1 libglib2.0-0
# 基于 Red Hat：
sudo dnf install wget git python3 gperftools-libs libglvnd-glx
# 基于 openSUSE：
sudo zypper install wget git python3 libtcmalloc4 libglvnd
# 基于 Arch：
sudo pacman -S wget git python3
```
如果你的系统非常新，需要安装 python3.11 或 python3.10：
```bash
# Ubuntu 24.04
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11

# Manjaro/Arch
sudo pacman -S yay
yay -S python311 # 不要与 python3.11 包混淆

# 仅适用于 3.11
# 然后在启动脚本中设置环境变量
export python_cmd="python3.11"
# 或者在 webui-user.sh 中
python_cmd="python3.11"
```
2. 导航到你希望安装 webui 的目录并执行以下命令：
```bash
wget -q https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/master/webui.sh
```
或者只需在你想要的位置克隆仓库：
```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
```

3. 运行 `webui.sh`。
4. 检查 `webui-user.sh` 了解选项。
### 在 Apple Silicon 上安装

在[这里](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Installation-on-Apple-Silicon)查找说明。

## 贡献
以下是如何向此仓库添加代码的方法：[贡献](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Contributing)

## 文档

文档已从此 README 移至项目的 [wiki](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki)。

为了让 Google 和其他搜索引擎爬取 wiki，这里有一个（不适合人类阅读的）[可爬取 wiki](https://github-wiki-see.page/m/AUTOMATIC1111/stable-diffusion-webui/wiki) 的链接。

## 致谢
借用代码的许可证可在 `设置 -> 许可证` 界面以及 `html/licenses.html` 文件中找到。

- Stable Diffusion - https://github.com/Stability-AI/stablediffusion, https://github.com/CompVis/taming-transformers, https://github.com/mcmonkey4eva/sd3-ref
- k-diffusion - https://github.com/crowsonkb/k-diffusion.git
- Spandrel - https://github.com/chaiNNer-org/spandrel 实现
  - GFPGAN - https://github.com/TencentARC/GFPGAN.git
  - CodeFormer - https://github.com/sczhou/CodeFormer
  - ESRGAN - https://github.com/xinntao/ESRGAN
  - SwinIR - https://github.com/JingyunLiang/SwinIR
  - Swin2SR - https://github.com/mv-lab/swin2sr
- LDSR - https://github.com/Hafiidz/latent-diffusion
- MiDaS - https://github.com/isl-org/MiDaS
- 优化思路 - https://github.com/basujindal/stable-diffusion
- 交叉注意力层优化 - Doggettx - https://github.com/Doggettx/stable-diffusion, 提示编辑的原始思路
- 交叉注意力层优化 - InvokeAI, lstein - https://github.com/invoke-ai/InvokeAI (原为 http://github.com/lstein/stable-diffusion)
- 次平方交叉注意力层优化 - Alex Birch (https://github.com/Birch-san/diffusers/pull/1), Amin Rezaei (https://github.com/AminRezaei0x443/memory-efficient-attention)
- 文本反转 - Rinon Gal - https://github.com/rinongal/textual_inversion (我们没有使用他的代码，但使用了他的思路)
- SD 放大思路 - https://github.com/jquesnelle/txt2imghd
- 外绘 mk2 的噪声生成 - https://github.com/parlance-zz/g-diffuser-bot
- CLIP 查询器思路和借用部分代码 - https://github.com/pharmapsychotic/clip-interrogator
- 组合式扩散思路 - https://github.com/energy-based-model/Compositional-Visual-Generation-with-Composable-Diffusion-Models-PyTorch
- xformers - https://github.com/facebookresearch/xformers
- DeepDanbooru - 动漫扩散查询器 https://github.com/KichangKim/DeepDanbooru
- 从 float16 UNet 以 float32 精度采样 - marunine 提供思路，Birch-san 提供 Diffusers 实现示例 (https://github.com/Birch-san/diffusers-play/tree/92feee6)
- Instruct pix2pix - Tim Brooks (star), Aleksander Holynski (star), Alexei A. Efros (no star) - https://github.com/timothybrooks/instruct-pix2pix
- 安全建议 - RyotaK
- UniPC 采样器 - Wenliang Zhao - https://github.com/wl-zhao/UniPC
- TAESD - Ollin Boer Bohan - https://github.com/madebyollin/taesd
- LyCORIS - KohakuBlueleaf
- 重启采样 - lambertae - https://github.com/Newbeeer/diffusion_restart_sampling
- Hypertile - tfernd - https://github.com/tfernd/HyperTile
- 初始 Gradio 脚本 - 由 4chan 的一位匿名用户发布。感谢匿名用户。
- (You)
