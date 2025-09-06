<div align="center">

# Albi0
~~[摸鱼的图书馆管理员](https://wiki.biligame.com/seerplan/%E9%98%BF%E5%B0%94%E6%AF%94%E9%9B%B6)~~<br>
🟨插件化的 Unity 游戏资源更新与提取工具🟩

</div>

## 功能特性

- 插件化：通过插件系统以支持多个游戏客户端，并提供了抽象的manifest版本管理器接口，便于支持热更逻辑
- 异步下载：基于 `httpx`、`anyio` 与 `tqdm` 的高速并发下载与实时进度显示

## 已支持的游戏

- [赛尔计划](https://www.biligame.com/detail/?id=107861)
- [赛尔号Unity端](https://seer.61.com/)

## 使用方式

推荐使用 `uvx` 直接运行，无需本地安装依赖，但需要先安装 `uv`，[uv 安装文档](https://docs.astral.sh/uv/getting-started/installation/)

之后使用 `uvx` 运行：

```bash
uvx albi0 --help
```

## 快速开始

1) 列出可用的更新器与提取器：

```bash
uvx albi0 list
```

2) 更新远程资源（示例：下载 NewSeer AB 包）：

```bash
# 可选：切换工作目录（默认当前目录）
uvx albi0 update -n newseer.default -w ./newseer
```

3) 仅查看远程版本号（不下载资源）：

```bash
uvx albi0 update -n newseer.default --version-only
```

4) 提取资源（AB 文件 → 本地目录）：
```bash
# 使用指定提取器提取（按组名/名称）
uvx albi0 extract -n newseer "./path/to/*.ab" -o ./output

# 合并模式（将多个源文件合并为一个环境后再导出）
uvx albi0 extract -n seerproject -m "./assets/**/*.ab" -o ./out

# 原样导出（忽略自定义处理，使用默认提取器）
uvx albi0 extract -e "./raw/*.ab" -o ./raw_out
```

提示：导出路径会自动带上提取器名前缀，例如传入 `-n newseer -o ./output`，实际导出目录为 `./output/newseer/...`。

## CLI 参考

### 顶层命令

```bash
uvx albi0 --help
uvx albi0 list
uvx albi0 update -n <updater_name> [-w WORKING_DIR] [--version-only] [PATTERNS...]
uvx albi0 extract [OPTIONS] [PATTERNS...]
```

### list

- 说明：打印已注册的更新器与提取器（来自已导入的插件）

### update

- 必选参数：`-n, --updater-name` 指定更新器名称或组名（可用名称见 `list` 输出）
- 可选参数：
  - `-w, --working-dir` 切换执行时的工作目录
  - `--version-only` 仅获取远程版本号，不下载资源文件
- 位置参数：`PATTERNS...` 可选的文件名过滤模式（glob语法），用于仅更新匹配的清单项
- 行为：
  - 对比远程与本地资源清单，若需要更新则并发下载资源文件并保存清单
  - 进度条展示每个文件的下载进度与总体任务进度
  - 当传入 `--version-only` 时，仅打印远程版本号并退出，不进行下载
  - 当提供 `PATTERNS...` 时，仅会下载文件名匹配 `PATTERNS...` 的条目

### extract

- 可选参数：
  - `-o, --output-dir` 导出目录（默认当前目录）
  - `-n, --extractor-name` 提取器名称或组名（默认 `default`）
  - `-e, --export-as-is` 原样导出（强制使用默认提取器）
  - `-m, --merge-extract` 合并模式（先合并环境再导出）
- 位置参数：`PATTERNS...` 资源文件的 glob 模式（如 `"./**/*.ab"`）
- 行为：
  - 依次加载匹配到的资源文件，调用插件注册的处理器进行导出
  - 在对象导出前后，可由插件的前/后处理器自定义处理逻辑

## 插件体系概览

- 提取器（Extractor）：在插件模块中通过构造 `Extractor()` 即完成注册
- 更新器（Updater）：在插件模块中通过构造 `Updater()` 即完成注册
- 分组机制：名称支持点号分组，例如 `newseer.default`、`seerproject.ab`；在 CLI 中传入组名可批量执行同组组件

## 典型工作流

```bash
# 1. 查看可用组件
uvx albi0 list

# 2. 下载（或更新）远程资源
uvx albi0 update -n newseer.default -w ./workspace

# 仅下载匹配的资源（使用 glob 过滤）
uvx albi0 update -n newseer.default "*.builtin" "Shader/*"

# 3. 提取资源到本地
uvx albi0 extract -n newseer "./workspace/newseer/assetbundles/**/*.ab" -m -o ./exports
```

## 开发流程

项目使用 `uv` 进行依赖管理与构建：

```bash
# 克隆仓库
git clone https://github.com/SeerAPI/albi0.git

# 安装依赖（包含开发/测试依赖）
uv sync

# 本地运行 CLI
uv run albi0 --help

# 运行测试
uv run --group test pytest

# 构建发行包
uv build
```

## 常见问题（FAQ）

- Q: 为什么没有看到我新写的插件生效？
  - A: 确保插件模块在 `albi0/plugins/__init__.py` 被导入；CLI 入口会导入 `albi0.plugins` 完成注册。
- Q: 下载很慢/失败？
  - A: 默认 `httpx` 客户端带有 UA/Referer 头，且支持并发；可根据网络情况调整并发或使用代理（自行扩展 `Downloader`）。
- Q: 导出结果的格式不符合预期？
  - A: 检查对应插件的对象前处理器与资源后处理器逻辑，或使用 `-e/--export-as-is` 原样导出。

## 目录结构（简要）

```
albi0/
├── cli/                  # CLI命令系统
│   ├── commands/        # 具体命令实现
│   └── __init__.py      # CLI主框架
├── plugins/             # 插件系统
│   ├── seerproject.py   # SeerProject插件
│   └── newseer.py       # NewSeer插件
├── extract/             # 资源提取核心
│   ├── extractor.py     # 提取器实现
│   └── registry.py      # 提取器注册表
├── update/              # 更新功能模块
│   ├── downloader.py    # 下载器实现
│   ├── updater.py       # 更新器实现
│   └── version.py       # 版本管理器实现
├── bytes_reader.py      # 字节流读取工具
├── utils.py             # 通用工具函数
├── typing.py            # 类型定义
├── log.py               # 日志配置
├── container.py         # 插件容器
└── request.py           # httpx客户端封装
```

## 许可证

MIT
