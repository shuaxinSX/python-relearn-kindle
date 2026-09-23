# V1 可读性复查清单

以下为自动定位，不能代替 Kindle 阅读体验。代码行宽按中文约两列估算；40 列及正文 100–250 汉字是目标。超过 12 行的模块/异常处理有上下文必要性，是否进一步拆分保留为编辑取舍。

| 课 | 位置 | 代码行数 | 最长显示列 |
|---|---|---:|---:|
| loops | s-mechanism/bodyMd/0 | 4 | 43 |
| lists-tuples | s-mechanism/bodyMd/0 | 8 | 48 |
| dicts | s-mechanism/bodyMd/0 | 6 | 53 |
| sets | s-mechanism/bodyMd/0 | 5 | 42 |
| sets | s-quiz-2/options/d/textMd/0 | 8 | 44 |
| sets | s-practice/solutionMd/0 | 11 | 46 |
| functions | s-mechanism/bodyMd/0 | 9 | 43 |
| functions | s-quiz-2/promptMd/0 | 9 | 43 |
| functions | s-quiz-2/options/a/textMd/0 | 5 | 43 |
| functions | s-quiz-2/options/b/textMd/0 | 5 | 43 |
| functions | s-quiz-2/options/c/textMd/0 | 5 | 43 |
| alias-copy | s-mechanism/bodyMd/0 | 5 | 42 |
| alias-copy | s-predict/bodyMd/0 | 5 | 42 |
| alias-copy | s-misconception/bodyMd/0 | 5 | 42 |
| comprehensions-sort | s-mechanism/bodyMd/0 | 9 | 42 |
| comprehensions-sort | s-predict/bodyMd/0 | 8 | 41 |
| comprehensions-sort | s-quiz-1/options/a/textMd/0 | 4 | 41 |
| comprehensions-sort | s-quiz-1/options/b/textMd/0 | 4 | 41 |
| comprehensions-sort | s-practice/solutionMd/0 | 10 | 45 |
| comprehensions-sort | s-practice/solutionMd/3 | 8 | 42 |
| paths-text | s-join/bodyMd/0 | 3 | 42 |
| paths-text | s-predict/bodyMd/0 | 12 | 42 |
| paths-text | s-misconception/bodyMd/0 | 10 | 61 |
| paths-text | s-quiz-2/options/a/textMd/0 | 6 | 57 |
| paths-text | s-quiz-2/options/b/textMd/0 | 3 | 57 |
| modules-venv | s-mechanism/bodyMd/0 | 2 | 47 |
| modules-venv | s-predict/bodyMd/0 | 14 | 46 |
| modules-venv | s-misconception/bodyMd/0 | 10 | 46 |
| modules-venv | s-quiz-1/promptMd/0 | 13 | 46 |
| tests-boundaries | s-mechanism/bodyMd/0 | 6 | 41 |
| tests-boundaries | s-predict/bodyMd/0 | 10 | 46 |
| tests-boundaries | s-quiz-1/options/a/textMd/0 | 1 | 61 |
| tests-boundaries | s-quiz-1/options/b/textMd/0 | 1 | 58 |
| tests-boundaries | s-quiz-1/options/d/textMd/0 | 1 | 53 |
| tests-boundaries | s-quiz-2/options/a/textMd/0 | 1 | 52 |
| tests-boundaries | s-quiz-2/options/c/textMd/0 | 1 | 50 |
| tests-boundaries | s-quiz-2/options/d/textMd/0 | 2 | 47 |
| tests-boundaries | s-practice/solutionMd/0 | 5 | 46 |
| tests-boundaries | s-practice/solutionMd/2 | 10 | 65 |
| tests-boundaries | s-practice/solutionMd/3 | 16 | 62 |
| tests-boundaries | s-practice/solutionMd/4 | 11 | 65 |
| tests-boundaries | s-practice/solutionMd/5 | 6 | 54 |

P4 的 `s-practice/taskMd` 去除代码围栏后约 585 个汉字，超过 350 字建议值。
是否拆分这份文件连接任务说明保留为编辑取舍，不影响其输入/输出契约测试。
