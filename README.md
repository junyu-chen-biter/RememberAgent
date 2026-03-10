## 写在最前
本项目使用SQLite数据库存储所有数据，python运行所有推荐功能，所以理论上在遇到大量的数据时，数据库的读写操作和查找推荐题目会成为性能瓶颈。未来可以用更好的算法优化推荐速度，欢迎大家提出宝贵建议，同时因为是本地项目，可以在dp.py文件中更改每日复习的题目数量和推荐算法的权重。
目前该项目仅在提取文档和题目挖空上使用了ai，逻辑比较简单，当下最流行的langchain，langgraph等框架在本项目中没有使用，所以未来有意向做agent的朋友可以一起讨论提出宝贵建议。


# RememberAgent（知识复习 Agent）

一个基于 Streamlit 的本地知识复习工具：支持导入 PDF / Markdown 教材和笔记，调用大模型自动提炼知识点并生成“挖空题”，再结合考试 DDL、学分、难度、遗忘程度与掌握度进行每日复习推荐。

## 功能概览

- **学科管理**：为每门课设置难度系数、学分、考试日期（DDL）。
- **知识导入**：上传 PDF / Markdown，自动抽取知识点并生成填空题（挖空题），保存到本地 SQLite。
- **开始复习**：按优先级推荐今日应复习的卡片；支持自评“烂熟 / 继续考 / 完全没记起来 / 不用掌握”。
- **仪表盘**：展示知识点总数、今日复习、总体掌握度、学科进度与今日待办推荐。

## 目录结构

项目非常精简，主要文件如下：

- [app.py](file:///d:/RememberAgent/RememberAgent/app.py)：Streamlit UI（主页 / 开始复习 / 学科设置 / 导入知识）
- [db.py](file:///d:/RememberAgent/RememberAgent/db.py)：SQLite 表结构与推荐/统计逻辑
- [extractor.py](file:///d:/RememberAgent/RememberAgent/extractor.py)：读取 PDF/Markdown + 大模型两步法抽取挖空题
- [llm_client.py](file:///d:/RememberAgent/RememberAgent/llm_client.py)：OpenAI SDK 兼容调用（默认适配火山方舟/豆包）
- [requirements.txt](file:///d:/RememberAgent/RememberAgent/requirements.txt)：依赖列表
- [run_agent.bat](file:///d:/RememberAgent/RememberAgent/run_agent.bat)：Windows 一键启动脚本（基于 conda）

## 环境准备（重点）

### 1) Python/Conda

推荐在 Windows 上使用 **Miniconda / Anaconda** 创建独立环境运行（因为项目自带的 bat 脚本默认用 conda）。

- 建议 Python 版本：3.10 或 3.11（Streamlit / openai / pandas 更稳）
- 确保 `conda` 命令可用：
  - 推荐做法：用 **Anaconda Prompt** 打开项目目录运行脚本
  - 或者：把 conda 加到系统 PATH（不推荐新手手动折腾，容易污染全局环境）

### 2) 创建并安装依赖

项目默认 conda 环境名是 `langchain-env`（可改，见下文 bat 设置）。

在 Anaconda Prompt / PowerShell 执行：

```bash
cd /d d:\RememberAgent\RememberAgent
conda create -n langchain-env python=3.10 -y
conda activate langchain-env
pip install -r requirements.txt
```

依赖说明（来自 [requirements.txt](file:///d:/RememberAgent/RememberAgent/requirements.txt)）：

- `streamlit`：Web UI
- `openai`：大模型 SDK（OpenAI 风格接口）
- `python-dotenv`：从 `.env` 读取密钥配置
- `pypdf`：PDF 文本抽取（扫描版图片 PDF 无法直接抽取）
- `pandas`：表格展示与统计

### 3) 配置大模型环境变量（必须）

大模型相关配置由 [llm_client.py](file:///d:/RememberAgent/RememberAgent/llm_client.py#L16-L58) 读取：

- `ARK_API_KEY`（或 `OPENAI_API_KEY`）：API Key（二者有其一即可）
- `ARK_MODEL`：模型/推理接入点 ID（例如火山方舟常见是 `ep-xxxx`）
- `ARK_BASE_URL`：可选；不设置时默认 `https://ark.cn-beijing.volces.com/api/v3`

推荐用 `.env` 文件（放在项目根目录，即与 `app.py` 同级）。因为 bat 启动时会 `cd` 到脚本所在目录，`.env` 会被自动读取。

#### A. 使用火山方舟 / 豆包（默认场景）

在 `d:\RememberAgent\RememberAgent\.env` 写入：

```env
ARK_API_KEY=你的_api_key
ARK_MODEL=ep-xxxxxxxxxxxxxxxx
# ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

#### B. 使用 OpenAI（可选）

同样写入 `.env`：

```env
OPENAI_API_KEY=你的_api_key
ARK_BASE_URL=https://api.openai.com/v1
ARK_MODEL=gpt-4o-mini
```

说明：
- 这里仍然使用 `ARK_` 前缀变量名是因为项目把“模型名”统一叫 `ARK_MODEL`；如果你接入 OpenAI，只要把 `ARK_BASE_URL` 指向 OpenAI，并把 `ARK_MODEL` 换成 OpenAI 模型名即可。

## 运行方式

### 方式 1：双击 run_agent.bat（推荐）

直接双击 [run_agent.bat](file:///d:/RememberAgent/RememberAgent/run_agent.bat) 启动。

脚本做了这些事：

- 自动切换到脚本所在目录（保证能找到 `app.py` 与 `.env`）
- 检查系统 PATH 中是否能找到 `conda`
- 使用 `conda run -n <环境名> python -m streamlit run app.py` 启动 Streamlit

启动后浏览器通常会自动打开，默认地址是：

- http://localhost:8501

### 方式 2：手动命令启动（更可控）

在项目目录下执行：

```bash
conda activate langchain-env
python -m streamlit run app.py
```

如果你不想 `activate`，也可以与 bat 一样：

```bash
conda run -n langchain-env python -m streamlit run app.py
```

## bat 脚本设置（重点）

### 1) 修改 conda 环境名

[run_agent.bat](file:///d:/RememberAgent/RememberAgent/run_agent.bat#L8-L25) 第 8 行：

```bat
set "CONDA_ENV_NAME=langchain-env"
```

把 `langchain-env` 改成你实际创建的环境名即可，例如：

```bat
set "CONDA_ENV_NAME=remember-agent"
```

然后用同名环境安装依赖：

```bash
conda create -n remember-agent python=3.10 -y
conda activate remember-agent
pip install -r requirements.txt
```

### 2) conda 找不到（脚本报 ERROR: conda command not found）

脚本用 `where conda` 检测 conda 是否在 PATH 内（见 [run_agent.bat](file:///d:/RememberAgent/RememberAgent/run_agent.bat#L10-L21)）。

解决办法优先级建议如下：

1. **用 Anaconda Prompt** 打开后再运行/双击脚本（最省心）
2. 在系统环境变量里把 conda 加入 PATH（不建议新手，容易影响其他 Python 环境）
3. 不用 bat，改为“手动命令启动”（上文方式 2）

### 3) 调整端口/地址（可选）

如果 8501 被占用，可以把 [run_agent.bat](file:///d:/RememberAgent/RememberAgent/run_agent.bat#L23-L25) 启动命令改成：

```bat
conda run -n %CONDA_ENV_NAME% python -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1
```

## 使用说明（UI 流程）

### 1) 学科设置

进入“学科设置”页面，添加学科：

- 学科名称
- 难度系数（difficulty）
- 学分（credits）
- 考试日期 DDL（影响紧急度）

### 2) 导入知识

进入“导入知识”页面：

1. 先选择学科
2. 上传 PDF 或 Markdown（`.md/.markdown`）
3. 点击“开始分析”

处理过程（见 [extractor.py](file:///d:/RememberAgent/RememberAgent/extractor.py#L47-L145)）：

- 第一步：把原始长文本整理成“知识点条目列表”
- 第二步：基于条目生成挖空题：`{'q': '... ____ ...', 'a': '被挖掉的关键内容'}` 列表

### 3) 开始复习

进入“开始复习”页面：

- 系统会根据优先级推荐今日要复习的卡片，并展示推荐理由
- 先在心里回忆答案，再点按钮显示答案
- 自评选项会更新掌握度与后续推荐频率：
  - 已经烂熟于心：掌握度直接到 5
  - 继续考：掌握度 +1（最多 5）
  - 完全没记起来：掌握度会被拉低（增加复习频率）
  - 不用掌握：标记为 ignored，之后不再出现

每日推荐上限默认 100（见 [db.py](file:///d:/RememberAgent/RememberAgent/db.py#L5-L11) 的 `DAILY_RECOMMENDATION_LIMIT`）。

## 数据与存储

- 数据库文件：运行后会在项目目录生成 `knowledge_agent.db`（SQLite）
- 如果你想“清空所有数据”，最简单的方式是关闭程序后删除该 db 文件（下次启动会自动重建表）

## 常见问题

### 1) 提示未找到 ARK_API_KEY / OPENAI_API_KEY

说明 `.env` 或系统环境变量未配置正确。检查：

- `.env` 是否放在 `app.py` 同级目录
- Key 的变量名是否写对：`ARK_API_KEY` 或 `OPENAI_API_KEY`

### 2) 提示未配置 ARK_MODEL

需要在 `.env` / 系统环境变量设置 `ARK_MODEL`：

- 火山方舟：通常是推理接入点 ID（`ep-xxxx`）
- OpenAI：是模型名（如 `gpt-4o-mini`）

### 3) PDF 导入后提取内容很少/为空

`pypdf` 只能抽取“文本层”，对于扫描件（图片）PDF 通常抽不到字，需要先 OCR 成可选中文本版 PDF，再导入。

