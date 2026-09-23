# Python 重学微课（Kindle 版）

面向 Kindle Scribe 浏览器的 Python 微课阅读、自测与复习工具。
构建时生成静态 HTML（多页面导航），每课内部用少量原生 JavaScript 实现
分步阅读，localStorage 保存本地学习状态，部署到 GitHub Pages。
网页不运行 Python、不接入 AI、不做账号与云同步。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
```

构建依赖：PyYAML、Jinja2、markdown-it-py（版本锁定见
`requirements-build.txt`）。这些只在开发电脑和 GitHub Actions 中执行，
Kindle 不安装也不执行它们。

## 校验

```bash
.venv/bin/python tools/validate.py
```

校验 `config.yaml`、`content/course.yaml` 与 `content/lessons/*.yaml`：
字段类型与必填项、未知步骤类型、重复 ID（步骤课内/课程目录/题目全站/
选项题内）、缺失引用、正确答案不存在、空解释、非法状态、目录缺课、
前置课不存在或不在前面。报错包含文件路径、步骤 ID 或题目 ID，
不会静默跳过；失败时构建中止。

## 构建

```bash
.venv/bin/python tools/build.py [--base-path /] [--out dist]
```

流程：内容校验（失败即停）→ Markdown 转 HTML（禁用原始 HTML）→
对 `assets/` 算 sha256 取前 8 位得哈希文件名 → Jinja2（自动转义）渲染页面
→ 写 `dist/` → 内链检查 → 体积检查并打印报告。

`--base-path` 覆盖 `config.yaml` 中的 `basePath`，支持 `/` 与 `/仓库名/`
两种部署路径；所有内部链接、资源与 PRL_CONFIG 经同一 URL 生成逻辑处理，
不手写固定根路径。CSS/JS 文件名带构建内容 hash，避免新旧混用。

## 运行测试

```bash
.venv/bin/python -m unittest discover -s tests
```

测试套件（标准库 unittest，无额外依赖）：

| 文件 | 内容 |
|---|---|
| `tests/test_validate.py` | 校验器 20 个负例（非零退出 + 错误含定位标识）与 1 个合法正例；用临时目录构造 YAML，不污染 `content/` |
| `tests/test_build.py` | 真实内容构建：6 页 + 2 哈希资源、内链/锚点、样课静态全文与 `data-correct-option` 一致性、体积预算、`--base-path /myrepo/` 前缀、workflow 语法自检 |
| `tests/test_content.py` | 样课 YAML 蓝图符合性（7 步结构、两题题号/正确项/选项数/解析非空/误解关键词、reveal 标签） |
| `tests/test_examples.py` | `content/fixtures/run-and-bindings/*.py` 真实运行：退出码 0 且 stdout 与同名 `.expected.txt` 逐字节一致 |
| `tests/test_backup.py` | node 真实加载 `assets/reader.js` 的 `validateBackupText`：合法/超限/坏 JSON/原型污染/未知版本/课程不符/非法字段（缺 node 时跳过） |
| `tests/test_reader_static.py` | `node --check`、ES5 启发式扫描零命中、JS≤30 KiB / CSS≤10 KiB、无 `localStorage.clear()` |

## 本地 HTTP 预览

```bash
.venv/bin/python -m http.server --directory dist 8000
```

浏览器打开 `http://localhost:8000`。

**明确禁止用 `file://` 双击页面代替测试**，原因：站内链接与资源引用
是根路径形式（如 `/assets/reader.<hash>.js`、`/lessons/….html`），在
`file://` 下会被解析到文件系统根目录（`file:///assets/…`），导致样式
与脚本加载失败、交互与保存逻辑失真；锚点与历史行为在 `file://` 下也与
HTTP 语义不同。本地验证一律走上面的 HTTP 服务。

## 发布

1. `push` 到 `main` 分支即触发 GitHub Actions（`.github/workflows/pages.yml`）：
   `test` job（校验 → 全量测试 → 冒烟构建）通过后，`build` job 构建并上传
   `dist/`，`deploy` job 发布到 GitHub Pages。
2. `BASE_PATH` 按仓库名自动判断：仓库名为 `<owner>.github.io` 时用 `/`，
   否则用 `/<仓库名>/`。仓库改名后重新 push 即可，无需改代码。
3. 未获发布授权时：只交付工作流与配置说明，不虚构线上地址。

## 目录结构

```text
content/course.yaml          # 目录：模块、课程顺序（唯一依据）
content/lessons/*.yaml       # 一课一文件：步骤、题目、解析
content/fixtures/            # 可运行示例 .py + 同名 .expected.txt
templates/                   # Jinja2 模板（自动转义）
assets/reader.js             # 经典原生 JS（ES5），分步/自测/保存
assets/styles.css            # 样式
tools/validate.py            # 内容校验器
tools/build.py               # 静态站构建器
tests/                       # unittest 测试套件
docs/content-authoring.md    # 写课指南
docs/qa.md                   # 验收记录（桌面已验收 / Kindle 待验收）
requirements-build.txt       # 构建依赖（锁定版本）
.github/workflows/pages.yml  # Pages 发布工作流
dist/                        # 构建产物（不入库手改，只由构建生成）
```

## 体积预算（未压缩，开发规格 §9.3）

每页必要资源总体积不超过 100 KiB：

- HTML：每页 ≤ **60 KiB**
- 共用 JavaScript：≤ **30 KiB**
- CSS：≤ **10 KiB**

构建器每次构建都会检查并打印体积报告，超限则构建失败。
预算不包含用户主动打开的练习文件；同课切步与答题不发网络请求。

## 写新课

见 `docs/content-authoring.md`：YAML 字段表、ID 规则、步骤类型选用、
quiz 写作要求、revision 规则、篇幅目标、fixtures 配对与校验流程。
