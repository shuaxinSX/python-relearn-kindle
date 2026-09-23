# 验收记录（QA）

> 里程碑 1（样课 `run-and-bindings` + 静态构建链 + Pages 预览）的验收记录。
> 记录日期：2026-09-23。状态分为"桌面已验收"与"Kindle 待验收"两部分；
> 在实机验证完成前，不写"Kindle 完全兼容"。

## 1. 桌面已验收（2026-09-23，构建机本地）

| # | 项目 | 结果 |
|---|---|---|
| 1 | 内容校验负例 | `tests/test_validate.py` 20 个负例全部通过：每个负例返回码非零，且错误信息含文件路径/步骤 ID/题目 ID（缺必填字段、字段类型错、未知步骤类型、步骤 ID 课内重复、课程 ID 目录重复、题目 ID 全站重复、选项 ID 题内重复、correctOptionId 不存在、题目/选项空解析、选项不足 2 个/超过 4 个、非法 status、目录缺课程文件、前置课不存在/不在前面、一课两个 practice、reveal 缺 revealLabel、siteId 为空、basePath 不合规）；1 个合法正例返回码 0 |
| 2 | 构建 | `python tools/build.py` 返回码 0；生成 6 页（index/course/lessons/run-and-bindings/review/settings/404）+ 2 个哈希资源 |
| 3 | 内链/锚点 | 所有 `href`/`src` 产物链接以 basePath 开头，无硬编码根路径；`#` 锚点在本页均有对应 id；`--base-path /myrepo/` 二次构建下内链/资源/PRL_CONFIG 均带 `/myrepo/` 前缀 |
| 4 | 体积预算 | HTML 最大 16.4 KiB（样课页，预算 60 KiB）；JS 29.9 KiB（预算 30 KiB）；CSS 3.9 KiB（预算 10 KiB）。全部通过（未压缩） |
| 5 | 全量单元测试 | `python -m unittest discover -s tests`：**62 个测试全部通过，0 失败**（validate 21、build 16、内容蓝图 11、fixtures 运行 1、备份校验 8、reader 静态 5） |
| 6 | fixtures 真实运行 | `content/fixtures/run-and-bindings/` 下 5 个脚本（demo/demo_rerun/q1/q2_correct/q2_wrong_order）用 `sys.executable` 实际运行：退出码均为 0，stdout 与同名 `.expected.txt` 逐字节一致 |
| 7 | 样课蓝图符合性 | 7 步、类型仅 read/reveal/quiz、步骤 ID 顺序符合蓝图；两题题号 `run-and-bindings-q1/q2`、正确项 b/a；q1 正确选项含 `2 3`、q2 含 60；每题 3—4 个选项、解析非空；错选项解析覆盖蓝图误解关键词（联动/只执行一次/同时更新；重算/自动/更新）；reveal 步骤有 revealLabel |
| 8 | 本地 HTTP 预览 | `python3 -m http.server --directory dist` 本地服务：`/`、`/course.html`、`/lessons/run-and-bindings.html`（含 `#s-quiz-1` 锚点）、`/review.html`、`/settings.html`、`/404.html` 均返回 200；不存在的路径返回 404；样课页含 2 处 `answer-zone` 答案区 |
| 9 | 备份校验 node 实测 | `node` 真实 `require("…/assets/reader.js")` 取 `validateBackupText`：合法备份 ok 且 preview.read=1、preview.review=1；超 128 KiB→too-large、坏 JSON→invalid-json、`__proto__` 注入→unsafe-keys、schemaVersion=2→unknown-version、courseId 不符→course-mismatch、fontSize 非法/attempts 负数→bad-fields，8 项全部通过 |
| 10 | 无脚本静态可读 | 样课页静态 HTML 含全文与 `answer-zone` 答案区（含"绑定快照""中间结果不会自动重算"等解析与口头检查题）；quiz 块 `data-correct-option` 与 YAML 的 correctOptionId 一一对应；`node --check assets/reader.js` 通过；ES5 启发式扫描（let/const、=>、反引号、class、fetch(、Promise、async/await、行首 import/export）零命中；源码无 `localStorage.clear()` |

备注：里程碑 1 只交付样课 1 节。开发规格 §10.1 A10 的"16 课、32 道题、4 项实践"属于后续里程碑，本次不纳入验收；内容协议本身不硬编码 16 课。

## 2. Kindle 待验收（按开发规格 §10.2）

以下项目必须在用户实际 Kindle Scribe 上验证，当前**全部待验收**。
实测时记录：**型号/代次、固件版本、网络环境、测试日期**，
并打开**实际 GitHub Pages 地址**（待部署后填写真实地址，此处不虚构）。

待测清单：

1. 打开实际 Pages 地址，首页可正常显示"开始学习"。
2. 三档字号（22/26/30）切换有效，排版不错乱。
3. 样课内连续切换步骤（上一部分/下一部分），即时切换且锚点更新。
4. reveal 步骤点击展开答案/结果。
5. 小测选项提交：未选提交有行内提示；提交后锁定并显示解析。
6. 代码块可单独横向滚动，页面无整页横滚。
7. 错题进入复习页；显式重新作答答对后移出复习列表。
8. 睡眠唤醒后页面状态正常。
9. 关闭浏览器后重新打开，继续位置正确（断点继续）。
10. 导出备份 → 清除 → 导入恢复，全流程可用。

**阻断项标准**（出现即列为阻断，不靠加功能回避）：

- 阻断阅读（白屏、正文不可读、步骤无法切换）；
- 无法准确点击（按钮/选项点击区失效或严重错位）；
- 正常环境下无法保存（localStorage 可用时仍丢进度，且非浏览器策略所致）。

桌面缩小窗口、慢速网络、设备模拟只能做预检，不等于 Kindle 实测。
