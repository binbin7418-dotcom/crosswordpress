# CrosswordPress — 验收记录（ACCEPTANCE）

验收（`test/acceptance_test.py`，真实运行结果见 `test/acceptance_results.txt`）：**8/8 PASS**

## 验收设计

- 词表：随附 24 词水果主题 `sample_words.csv`（word,clue）
- 生成：seed=7、每题提供 14 词、共 6 题成书
- 断言：
  - 每题实际放置 ≥10 词（实测 13–14/14，共 81 词）
  - 每题过独立复检：从裁剪后网格重新扫描，全部横/竖 run 集合 == 已放置词集合；逐词字母与网格一致；编号无缺口；线索表恰好覆盖每词一次
  - PDF 结构：14 页（1 标题＋6 题＋1 解答标题＋6 解答），页面 612×792pt（8.5×11in）经 pypdf 重开实测
  - 确定性：同 seed 两次布局逐词坐标全等

## 诚实边界

放不下的词如实报告（placed vs offered），绝不破坏交叉硬塞——这是与「生成器把词表原样印出来」类竞品的差异点。
