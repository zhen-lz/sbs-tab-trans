## 快速开始
### 环境准备
1. 克隆/下载项目到本地
2. 安装依赖（推荐使用虚拟环境）
```bash
python -m venv venv
# 激活虚拟环境（Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate）
# 安装依赖
pip install -r requirements.txt
```

### 依赖说明
- `pyav`：默认视频处理引擎
- `numpy`：视频帧处理基础库
- `scikit-image`：非标准分割线检测（结构相似度计算）

### 系统要求
- Python 3.9+

## 使用指南
### 基本用法
```bash
python main.py 输入视频
```

### 常用参数
| 参数 | 说明 | 示例 |
|------|------|------|
| `-o/--output` | 指定输出文件路径 | `-o ./output/result.mp4` |
| `-m/--mode` | 手动指定转换模式（sbs2tab/tab2sbs） | `-m sbs2tab` |
| `-a/--autodetect-nonstandard` | 启用非标准分割线检测 | `--autodetect-nonstandard` |
| `-v/--verbose` | 显示实时转换进度 | `--verbose` |

## 注意事项
1. 非标准分割检测功能会增加少量计算耗时，标准格式视频可不用启用

## 命令行帮助
```
usage: main.py [-h] [-o OUTPUT] [-m {sbs2tab,tab2sbs}] [-a] [-v] input

3D视频格式转换器：支持SBS与TAB互相转换

positional arguments:
  input                 输入视频文件路径

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        输出视频文件路径
  -m {sbs2tab,tab2sbs}, --mode {sbs2tab,tab2sbs}
                        转换模式：sbs2tab(SBS转TAB) 或 tab2sbs(TAB转SBS)
  -a, --autodetect-nonstandard
                        启用非标准分割线检测（适用于非对称分割的视频）
  -v, --verbose         显示详细转换进度
```
