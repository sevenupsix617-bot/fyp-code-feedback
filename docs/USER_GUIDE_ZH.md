> This Chinese guide describes the author's local setup as checked on 2026-11-11. Absolute paths, database counts and ports are local examples. SQLite snapshots, fictional-class records and API keys are not included in this repository. A fresh clone must create its own database; do not assume it contains the local recordings.

# FYP 网站使用手册：现行功能、指标解释与 Demo 准备

更新及代码核对日期：**2026-11-11（Asia/Macau）**
适用项目：`/Users/a77777/Desktop/fyp-code-feedback`
正式手册位置：`/Users/a77777/Desktop/FYP sem2/网站使用手册_中文版.md`

本手册供日常操作、视频演示和报告查阅使用。功能说明以当前代码为准；评测数字以明确命名的最终结果文件为准。页面上的记录数会随提交改变，不是软件固定参数。本次核对并更新手册与仓库说明，保持既有业务逻辑和数据；同步修正移除语言切换后的旧测试。不改报告或评测标签。

旧手册含多轮历史补充，现已统一为这一份现行说明；更新前原文存放于 `Documents/ChatGPT/FYP/deliverables/manual_update_2026-11-06/网站使用手册_更新前存档.md`，仅供追溯，不作为当前操作依据。

## 0. 本次重新熟悉系统的建议顺序

**先看原网站，再看独立演示环境。**两者运行同一套 Django 代码，差别在数据库中已有的账号和记录。虚构班级没有增加另一套评分算法或另一个产品。

1. **原网站学生流程**：按第 3.1 节用默认库启动 8002，登录 student2。先打开 History，查看 Sum from 1 to 10 已有的三条记录（执行失败 → 输出不匹配 → Solved），逐次 View 对照代码、运行证据和反馈。这一步无需再提交或调用 API。
2. **原网站学习状态**：同一账号打开 Progress，再打开 Current Status。结合第 6、11 节理解：历史雷达＝全部相关尝试的 EMA；当前状态＝最近最多 5 次均值；两个分数都先经过多 Topic 加权分配。不要把它们当作考试成绩或模型准确率。
3. **原网站教师功能**：切换 instructor，依次看 Instructor、Analytics、Students、Experiment、History、Admin。参照第 7–9 节理解每页的用途和每个数字的统计单位；Experiment 先只看表单，不必付费提交。
4. **最后查看虚构班级**：按第 3.2 节启动 8011，用 instructor 查看 30 人目录、分页、班级比例和重复错误。这里的预设数据只展示同一套功能在人数多时怎样工作，不代表真实课堂表现。
5. **再回到视频准备**：8010 是旧记录的独立快照，专门隔离录制操作。它没有自动跟随原库更新；不要因为两个环境里都有 student2，就以为历史相同。等你熟悉系统后，再核对视频文案与操作表。

### 0.1 2026-11-11 核查到的关键变化

- 原库有 **73 条反馈记录、2 个活跃学生账号**。student2 的求和题已经有 3 次尝试，最后一次 Solved；新提交会继续编号，不会重新变成 Attempt 1。
- 8010 快照仍有 **68 条记录**；student2 尚无求和题历史，保留了从 1 开始录制的条件。熟悉系统时优先看原库已有记录，不要提前消耗快照中的首次提交。
- 8011 虚构班级仍有 **30 个账号、39 条预设记录**。不需要重新生成或重置它。
- 当前界面为英文，已移除 EN／中文开关及其脚本。历史截图中的语言按钮不再代表当前页面。
- 仅快照／虚构环境自动显示数据来源横幅；原库默认不显示横幅，可通过 REPORT_DATA_NOTICE 显式设置说明。这不代表原库全部是真实课堂数据。

## 使用索引

- 第 1–3 节：系统用途、数据环境、启动和权限。
- 第 4–6 节：学生提交、结果、历史、Progress 和 Current Status。
- 第 7–9 节：教师 Dashboard、班级分析、学生目录及 Experiment。
- 第 10–11 节：全部状态值、分类、Topic、评分公式与模型处理流程。
- 第 12 节：离线评测、准确率与精确率的分母和适用范围。
- 第 13–14 节：可复制的演示代码、录屏顺序与截图内容。
- 第 15–17 节：维护、常见问题、核查来源和交付检查。
- 附录 A–C：现行 Topic 定义、PECI A-X 清单与 JSON 字段。

## 1. 这个网站解决什么问题

学生代码“能运行”并不等于“符合题意”。网站先运行学生提交的 Python 程序，再把实际输出、异常、预期输出比较结果和教学要求交给模型，生成提示、可能的误区和下一步调试建议。学生可以带着原代码重试同一道题，并查看各次尝试的证据。

教师可以管理题库、查看保存的反馈、按学生人数寻找班级共性问题，并进入个人详情检查证据。Experiment 用于教师手动尝试不同模型和 prompt；批量 Evaluation 结果只保留为离线研究材料，网站已无 Evaluation 页面。

系统包含三个不同层次，演示和报告时应分别解释：

| 层次 | 回答的问题 | 依据 |
| --- | --- | --- |
| 本地执行与输出比较 | 这次程序运行发生了什么？ | stdout、stderr、return code、执行状态和样例输出比较 |
| AI 反馈与诊断 | 这次错误可能是什么，下一步怎么检查？ | 固定分类与 Topic、代码、题意、运行证据；模型仍可能误判 |
| 学习与班级统计 | 哪些 Topic 值得继续练，哪些学生需要跟进？ | 已保存记录上的确定性计算，不是另一轮 AI 自动评价 |

网站是教学反馈原型。Topic 分数是启发式估算，样例通过不等于全部输入正确，分类准确率也不等于反馈质量或学生学习提升。

## 2. 先确认使用的是哪一套数据

### 2.1 当前本地数据环境

以下数量为本次只读核查时的快照，新增提交后会改变。端口只是访问入口，真正决定数据的是启动进程所用的数据库。

| 环境 | 数据库 | 本次核查数量 | 用途 |
| --- | --- | --- | --- |
| 原项目数据库 | `/Users/a77777/Desktop/fyp-code-feedback/db.sqlite3` | 73 条反馈记录；2 个活跃非教师账号 | 日常项目数据，包含演示及已保存测试记录；不能一概称真实课堂数据 |
| 已有记录的独立快照 | `/Users/a77777/Documents/ChatGPT/FYP/ch4_ui_revision/data/record_snapshot.sqlite3` | 68 条记录；2 个学生账号 | 端口 8010 的页面检查和已有结果展示 |
| 独立虚构班级演示库 | `/Users/a77777/Documents/ChatGPT/FYP/ch4_ui_revision/data/fictional_class.sqlite3` | 39 条记录；30 个虚构学生 | 端口 8011 的班级统计、搜索和分页演示 |

**30 人演示库不是研究实验结果。**其中有预置教学历史和脚本反馈；新增脚本样例的运行证据来自本地执行，不表示这些反馈都由真实 API 生成，也不表示进行了 30 人课堂研究。原来的两个学生账号只在独立库中被改为虚构用户名，没有把原项目数据库改造成 30 人班级。

当前自动数据标识仅覆盖 8010 练习快照和 8011 虚构班级。默认原库不自动显示横幅；如配置 REPORT_DATA_NOTICE，则显示该自定义说明。新手动提交与预置记录需区分，不能把原库或快照整体称为真实课堂数据。

### 2.2 四种不能混在一起的数据

| 数据 | 规模与性质 | 应如何称呼 |
| --- | --- | --- |
| 题库及 seed history | 手工设计的教学题、预置尝试 | 教学演示数据 |
| 30 人独立演示库 | 虚构账号、脚本历史 | 用于界面与统计逻辑展示的虚构班级 |
| Refactory 主评测 | 55 个精选错误程序样本；不是已确认的 55 名不同学生 | 真实学生程序样本，非随机抽样 |
| 补充边界测试 | 12 个手工构造样例 | 系统边界测试，与真实学生样本分开报告 |

页面里的“学生数”和评测里的“55 samples”不是同一单位。330 或 110 指样本、模型、prompt 组合产生的评测结果数，不是学生人数。

## 3. 启动、登录与页面入口

### 3.1 启动原项目数据库

在终端执行：

```bash
cd /Users/a77777/Desktop/fyp-code-feedback
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8002 --noreload
```

这条命令在未另设 `DJANGO_DB_PATH` 时使用项目默认数据库；若终端已有该环境变量，应先检查它指向哪套数据。访问地址以启动输出为准。`--noreload` 下修改代码后需手动重启，刷新页面不会重新加载 Python 代码。

### 3.2 启动已有记录快照或 30 人演示库

分别使用两个终端；下面的环境变量只作用于该条启动命令。

已有记录快照：

```bash
cd /Users/a77777/Desktop/fyp-code-feedback
DJANGO_DB_PATH='/Users/a77777/Documents/ChatGPT/FYP/ch4_ui_revision/data/record_snapshot.sqlite3' .venv/bin/python manage.py runserver 127.0.0.1:8010 --noreload
```

30 人虚构班级：

```bash
cd /Users/a77777/Desktop/fyp-code-feedback
DJANGO_DB_PATH='/Users/a77777/Documents/ChatGPT/FYP/ch4_ui_revision/data/fictional_class.sqlite3' .venv/bin/python manage.py runserver 127.0.0.1:8011 --noreload
```

推荐浏览器分别使用：

- 学生演示／已有记录：`http://127.0.0.1:8010/`。
- 教师虚构班级演示：`http://localhost:8011/`。

Cookie 不按端口隔离。同一浏览器在同一个主机名的不同端口登录不同角色，可能互相影响。上述两个主机名，或两个浏览器／独立隐私窗口，可减少切换账号的干扰。

如端口已占用，先确认是否已有对应服务，不要重复启动：

```bash
lsof -nP -iTCP:8010 -sTCP:LISTEN
lsof -nP -iTCP:8011 -sTCP:LISTEN
```

### 3.3 本地演示账号

| 环境 | 角色 | 用户名 | 密码 |
| --- | --- | --- | --- |
| 默认库／已有记录快照 | 学生 | `student1`、`student2` | `student123` |
| 默认库／已有记录快照 | 教师 | `instructor` | `instructor123` |
| 30 人虚构班级库 | 教师 | `instructor` | `instructor123` |

以上是本地 seed 演示账号，不是生产环境凭证。30 人库中的学生用户名为 `demo_student_01` 至 `demo_student_30`；不能假定 30 个账号都有可用的统一登录密码。展示教师目录不需要逐个登录这些学生。

登录入口：`/accounts/login/`。品牌名称链接会按角色回到教师首页或学生提交页。

### 3.4 路由与权限

| 页面 | 相对地址 | 允许的角色／说明 |
| --- | --- | --- |
| Submit | `/student/` | 学生；教师访问会回教师 Dashboard |
| Progress | `/profile/` | 当前学生本人 |
| Current Status | `/profile/current/` | 当前学生本人 |
| History | `/history/` | 学生只看本人；教师可筛选记录 |
| 保存的结果详情 | `/history/<record_id>/` | 记录本人或教师 |
| Instructor Dashboard | `/instructor/` | 教师 |
| Class Analytics | `/analytics/` | 教师 |
| Student Directory | `/analytics/students/` | 教师；搜索、每页 5 人 |
| 学生历史详情 | `/analytics/students/<user_id>/` | 教师 |
| 学生近期状态 | `/analytics/students/<user_id>/current/` | 教师 |
| Topic 时间证据 | `/analytics/students/<user_id>/skill/<topic_id>/` | 教师或该学生本人 |
| Experiment | `/experiment/` | 教师手动测试 |
| Admin | `/admin/` | 具备对应管理权限的 staff 账号 |

未登录通常先去登录页；登录后越权访问会被拒绝。`/evaluation/` 已移除，应返回 404，不能把它描述成“仅管理员可见的批量评测页”。

### 3.5 当前界面语言

当前使用英文界面，中英切换入口及 ui-i18n.js 已移除，不再提供网站内的语言切换。代码、输入输出和保存的反馈仍按原内容显示。界面显示 Topic，内部历史字段仍叫 `concept_reference`，没有迁移或重写原数据。

## 4. 学生：选题、提交、看结果和重试

### 4.1 选择题目

进入 Submit。题目由教师预先设置题意、教学目标、固定 Topic、样例输入、预期输出、比较模式、默认模型，以及可选 test harness。

学生填写代码，不能在此任意改题目的标准答案或 prompt。学生端使用题目默认 provider 和 `strict_scaffolded` prompt。筛选链接例：`/student/?topic=iteration_range`。

题目状态根据本人在该题的**最新记录**显示：

| 状态 | 条件 | 下拉框提示 |
| --- | --- | --- |
| Not started | 无记录 | `○` |
| In progress | 有记录，最新记录未满足 solved | `↻` 和累计 attempts |
| Solved | 最新记录已解决，或历史兼容判断满足 no_error＋运行成功＋输出匹配 | `✓` |

排序为 In progress → Not started → Solved，各组按题名排序。已解决后再提交错误版本，最新状态可能回到 In progress；不是永久完成锁定。

### 4.2 提交后的真实流程

1. 校验表单，取得该学生在该题最近记录的 trajectory 信息。
2. 沿用已有 trajectory ID 并递增 attempt number；没有可沿用的 ID 时创建新 ID、从 1 开始。
3. 在临时目录中的限时本地 Python 子进程执行，采集运行证据，比较实际／预期输出。
4. 构造 prompt，向配置的 provider 发出请求。
5. 请求成功后解析 JSON，进行 schema 校验及规范化；部分格式问题可本地修正，不额外调用 API。
6. 只有无效 JSON 才最多再发起**一次 JSON-repair request**。不可恢复的 schema 问题不会进入无限修复；API 请求失败也不会自动切换模型。
7. 保存提交、运行证据、反馈或 AI error，再显示结果。trajectory 分配发生在执行前，最终随结果记录一起持久化。

API 不可用、空响应、不可恢复的 JSON/schema 问题都可能使 AI 反馈不可用。提交与已有运行证据仍会保存；此时 `solved=False`。本地运行成功和 AI 请求成功是两件事。

### 4.3 结果页怎样阅读

| 区域 | 该看什么 | 不该误解成什么 |
| --- | --- | --- |
| 顶部题目与 Attempt | 本题第几次已保存尝试 | 不等于模型内部请求次数 |
| Submitted Code | 白底、行号、Python 语法着色的原始提交 | 颜色不是模型确认的错误位置 |
| Runtime Evidence | execution status、output comparison、expected／actual output、stdin、return code、运行毫秒数 | 运行毫秒数不是学生解题耗时 |
| Error Output | 有 stderr 时展开查看真实异常 | 运行症状不自动等于最终错误分类 |
| Tutor Response | Error Classification、Topic、反馈级别、解释 | 模型诊断并不保证正确 |
| Misconception／Suggested Next Step | 可能误区、下一步检查动作 | 不表示系统知道学生真实心理状态 |
| Debug Evidence | 仅教师可展开保存的 JSON、schema 状态、原回复和模型元数据 | confidence 不是校准后的可靠性概率 |

布局是“上方代码与精简证据相邻，下方展开解释”，不是把所有反馈塞进右侧栏。真实 Python traceback 含可定位行号时，已有代码视图可能标示该运行报错行；普通逻辑错误没有自动逐行批注功能。

结果页与 History 中 View 后的详情页复用相同代码／证据／反馈组件，因此保存后的同一条记录应保持同样的内容。详情页不重新请求模型。

### 4.4 Solved 的严格条件

三项必须同时成立：

```text
classification_outcome == no_error
AND execution_status == success
AND output_comparison_status in {exact_match, normalized_match}
```

所以：成功运行但输出错，不是 solved；样例输出匹配但模型仍发现缺陷，也不直接算 solved；没有可比较的预期输出不能仅凭 no_error 算 solved。通过的是当前提供的样例及检查条件，不是对程序所有输入的正确性证明。

### 4.5 重试与换题

- `Retry this question`：回到该题并预填这条记录的代码，学生修改后再提交。
- `Jump to another question`：回到选题页，学生自己选择下一题；系统不会答错后自动跳题。
- `View attempt history`：按这条记录定位其 trajectory 历程。
- 不再操作即可结束练习；“End practice”在活动图中表达学生结束流程，不代表网站另有专门按钮。

当前实现会沿用该学生该题最近的 trajectory，包括 solved 后再次提交的情况；没有“每次解决后自动建立新 trajectory”的规则。

## 5. History：看一串尝试，不覆盖旧代码

每次提交保留独立记录，含代码、时间、运行／输出状态、诊断、反馈、trajectory ID 和 attempt number。History 按“学生＋题目＋trajectory”分组，组内按尝试顺序显示；缺少 trajectory 的旧记录单独保留，不强行伪造链条。

结果标题可以是 `Countdown from three · Attempt 3`。这比让学生阅读长 trajectory ID 更容易理解；内部 ID 仍保存在数据中。不要说“页面没显示 ID，所以没有保存 trajectory”。

History 主要操作：

- 展开一组查看历次提交，再点 `View` 打开保存的详情。
- 教师可按学生／题目筛选，也可从 Analytics 的 `View records` 进入带 Topic／类别来源过滤的历史。
- `?attempt=<record_id>` 定位对应尝试历程。
- 当前最多呈现最近 **20 个分组**，不是数据库只保存 20 条，也不是完整历史导出工具。
- 班级证据过滤后的组可能只包含符合过滤条件的记录；清除筛选或进入完整历程再看前后文。

列名已为 **Error Category**。success、exact_match、normalized_match 采用绿色；mismatch／timeout 等用警示色，执行错误用错误色。Runtime 和 Output 的全部取值在页面说明区列出，详见第 10 节。

## 6. Progress 与 Current Status：两个不同问题

### 6.1 Progress／学生个人详情

学生访问 `/profile/`；教师从目录进入 `/analytics/students/<id>/`。

页面显示该学生保存的尝试汇总、八个 Topic 的历史雷达、重复错误及近期记录。点击 Topic 名称或图中点进入 Topic 时间证据，查看作答、分数依据和相关题目。时间线默认最多展示最近 30 条该 Topic 证据，不能说图上已铺开无限完整历史；底层记录另存于 History。

**雷达分数使用所有相关尝试的加权 Topic 分，按时间正序作 EMA，α=0.5。**不是每题最新一次平均，也不是全历史简单平均。每题最新成绩只在 partial-credit 的分配基线中使用，详见第 11 节。

没有练过某 Topic 时，绘图可能用 0 占位，同时通过 N/A／无证据标记区别。它不证明学生掌握度为零。某些轴回到中心、部分线段没有包围面积时，填色只覆盖实际闭合区域，不是整张图应均匀涂色。

个人尝试成功率是 `solved attempts / all saved attempts`；不是已解决题数除以题数，也不是 52.73% 那种离线模型准确率。

个人详情中的重复错误及相关诊断摘要仍按该学生保存的标签／`concept_reference` 汇总；雷达与 Current Status 的 Topic 归属则来自题目固定标签。它们不是同一张统计表，也没有把历史诊断自动换成新分类。

### 6.2 Current Knowledge Status

学生访问 `/profile/current/`；教师看指定学生 `/analytics/students/<id>/current/`。

页面顶部只保留一个清晰的 **Next practice** 行动和理由，下方列出**全部八个 Topic**，不重复逐行堆放同一条 Practice next 提示。未练习的 Topic 也必须保留。

| 页面字段 | 当前算法与含义 |
| --- | --- |
| Recent score | 每个 Topic 最新至多 N 次相关尝试的加权 Topic 分均值，四舍五入；默认 N=5 |
| `3/5 attempts` 等提示 | 实际有 3 次近期证据，上限是 5；不是无记录也硬凑 5 次 |
| Total practice | 该 Topic 所有关联题目的**全部历史尝试次数** |
| Questions | 尝试过的关联题目去重数量 |
| Recent unresolved | 近期窗口内 `solved=False` 的数量／近期实际次数；包含输出错、执行错、AI 失败等未解决状态 |
| No evidence／N/A | 没有该 Topic 已保存尝试；不判为低能力或有困难 |

有证据的 Topic 按近期分数从低到高排列；无证据的放后面。建议候选来自近期分数低于 75 或仍有未解决尝试的 Topic；没有这些候选时才建议从无证据 Topic 收集练习证据。页面只显示候选中的首个行动。

学生点击 Topic／Practise topic，跳转到 `/student/?topic=<id>`；教师看到 View evidence，进入个人 Topic 证据，不替学生提交。

N 可通过 `CURRENT_STATUS_RECENT_ATTEMPTS` 配置，至少为 1，修改后重启相应服务。Current Status 用近期均值，**不是 EMA**；它和 Progress 使用同一套 rubric 与 partial-credit 分配。

页面明确提示“基于近期保存尝试的估算，非标准化测评”。没有专门增加单 Topic 平均解题耗时指标，执行毫秒数也不能替代解题时间。

## 7. 教师 Dashboard 与题库管理

### 7.1 Instructor Dashboard 的分工

教师 Dashboard 是题库和近期记录的工作入口，Class Analytics 才是按学生人数组织的班级分析。两页统计范围不同，不能直接拿总数互相校验。

| Dashboard 区域 | 统计范围 |
| --- | --- |
| Questions／active／inactive | 当前数据库题库条目 |
| Submissions | 所有 CodeFeedbackRecord，含教师实验记录 |
| Students／Demo students | 活跃非 staff 账号 |
| Comparison modes | 题目设置为 strict／normalized 的数量，不是模型准确率 |
| Common PECI Error Categories | 已保存 `peci_error` 记录的出现次数；只列部分高频 A-X，不包含所有补充类别 |
| Provider Defaults | 各题默认 provider 的题目数，不是调用次数或哪个模型效果更好 |
| Output Comparison | 所有已保存记录的输出状态频数 |
| Recent submissions | 最近保存的反馈记录 |

Dashboard 的 PECI 次数榜不等于 Class Analytics 的不同学生数榜，名称相近也不能混讲。

### 7.2 管理题目

使用 Add Question／Manage Questions 进入 Admin 相应管理入口。题目应设置：title、problem_statement、lecture_objective、固定 topic_tags、sample_input、expected_output、comparison_mode、default_llm_provider、is_active，以及需要时的 test_harness。

多次 `input()` 的输入在 sample_input 中按行填写。函数题可以用 test_harness 调用学生函数并打印结果；harness 是教师配置，不是自动生成的隐藏测试全集。禁用题目后学生选题列表不再提供它，旧记录仍应按原证据阅读。

固定 Topic 需要人工选择现有八项，不能把模型随意生成的词直接当作第九个 Topic。题目可带多个 Topic，得分分配按第 11 节处理。

## 8. Class Analytics：先数学生，再看提交频率

### 8.1 顶部四项指标

进入 `/analytics/`。

| 指标 | 当前单位和范围 |
| --- | --- |
| Students | 活跃非教师账号人数，包含尚未练习者 |
| Practising students | 至少有一条关联题目尝试的活跃学生人数 |
| Topic follow-up | 至少一个 Topic 的最新相关尝试仍未解决的不同学生人数；同一学生跨 Topic 不重复计入此总数 |
| Practice submissions | 活跃学生关联题目的保存记录条数，作为次要频率证据 |

这些班级证据排除教师 Experiment、匿名记录、停用学生和未关联题目的记录。

### 8.2 Students Needing Topic Follow-up

每一行用题目固定 Topic 标签找记录，对“学生＋Topic”取时间最新的一次相关尝试：

```text
Topic 比例 = 最新相关尝试未解决的学生数 / 至少练过该 Topic 的学生数
```

例：Iteration 显示 `5 / 6`，意思是六位练过这个 Topic 的学生中，五位的最新相关尝试未解决。不是六次提交中五次错误，也不是全班 30 人中有 25 人不会。

同一学生在这一 Topic 重复十次，分母仍只计一人，分子由其最新相关尝试决定。完全未练过的学生不进入分母，不标成“有困难”。“最新相关”是该 Topic 任一关联题的最新提交，不是每题各取最新再投票；它只能作为跟进线索。

Submissions 列补充全部关联尝试次数和历史未解决次数。多 Topic 题会出现在多个 Topic 中，因此不能把八行提交数直接相加当作独立总提交量。

`View records` 进入固定 Topic 筛选的 History。这是相关证据集合，可能包含该 Topic 的成功及失败历史，不是仅筛出分子中的学生。

### 8.3 Error Categories by Student

此表回答：“哪些学生**曾经**收到过这一保存诊断？”

- Students：同一来源、类别及保存标签下的不同学生数。
- Occurrences：这些记录出现了多少次，重复提交也计次。
- 例：一名学生同类错误十次＝1 student、10 occurrences；两名学生各一次＝2 students、2 occurrences。
- 曾有错误、后来解决的学生仍属于“曾出现”人数；不能把这列当作“目前仍未解决人数”。

Source 保留三个来源：

| Source | 含义 |
| --- | --- |
| PECI A-X (stored) | 保存时为 `peci_error` 且有合法 A-X 码 |
| Project supplement (stored) | 保存时属于四个项目补充 outcome |
| Legacy annotation (unchanged) | 保存的旧版类别；没有自动重新归入现行分类 |

旧记录不会因为今天出现 NameError 就自动改为新的 Runtime error。`no_error` 不列入错误榜；unknown／outside 若没有可识别的历史诊断也不应假装属于这些错误行。点 View records 查看该来源及类别的原始保存记录。

### 8.4 Instructional Suggestions

建议来自上面按学生人数得到的 Topic／错误证据，提供跟进方向和记录入口。它是确定性统计生成的文案，不是额外付费调用模型生成的课堂结论。教师应查看代码和上下文，再决定讲解或练习安排。

### 8.5 Question Difficulty Overview

此表按学生练习历程统计。教师 Experiment 不纳入；当前函数筛选非 staff 学生的关联题目记录，**没有再限定 active**，与顶部活跃班级统计的范围不完全相同。停用学生的旧练习可能仍在这里。

| 字段 | 当前含义 |
| --- | --- |
| Attempts | 该题全部学生提交次数 |
| Students | 做过该题的不同学生数 |
| Avg to solve | 每个已解决历程中，从开始到第一次 solved 的尝试次数，再对这些已解决历程求平均 |
| Unresolved | 历史未解决的 attempts 数；副行另列 unsolved runs |
| Solve rate | solved runs / all runs；不是 solved attempts / attempts |
| Mismatch | 执行成功但输出不匹配的提交数 |
| Runtime errors | name/type/value/index/key/eof/module/import/runtime 等异常提交数 |
| Other failures | syntax、indentation、timeout、system 等其他执行失败，另作补充 |

run 优先按学生＋题目＋trajectory 分组；无 trajectory 的旧记录按同一学生同一题归为兼容分组。没有已解决 run 时 Avg to solve 为 N/A，不写 0。

例：甲第三次解决，乙第五次解决，丙仍未解决：Avg to solve＝(3+5)/2＝4；Solve rate＝2/3。丙保留在解决率分母，但不被虚构成“用了多少次才解决”。一个历程可以包含两次未解决尝试和一次成功，因此历史 unresolved attempts 不会因最后解决而消失。

排序：平均解决次数从高到低，没有可计算平均的放后，再参考尝试量与题名。标签是项目启发式规则：

- **Unattempted**：零尝试。
- **Difficult**：平均至少 3 次且总尝试至少 3；或总尝试至少 5 且解决率不超过 50%。
- **Popular, easier**：总尝试至少 5、至少 2 名学生、解决率至少 75%、平均不超过 2 次。
- **Limited evidence**：已尝试但不满足以上条件。

高尝试量可能只是热门；高解决率也可能伴随很多次才解决。标签用于教学筛查，不是标准化难度测量。

### 8.6 长表滚动与不同统计范围

Error Categories by Student 和 Question Difficulty Overview 使用最高约 **440px** 的内部滚动区，表头固定；宽表可横向滚动。鼠标放在表内上下滚动即可看余下条目，不必让整页无限变长。所有数据仍在表里；打印时滚动区展开。

页下方 Output Comparison Status 按**所有已保存记录**计次数，包含教师实验。因此其数字可大于顶部 Practice submissions，不代表人数统计错误。

## 9. Student Directory 与 Experiment

### 9.1 从 30 人里找到一个学生

在 Class Analytics 点 Student Directory，或直接访问 `/analytics/students/`。

- 搜索用户名或姓名，大小写不敏感，输入会去掉首尾空白。
- 每页 **5 人**；30 人且未筛选时共 6 页。
- Previous／Next 翻页保留搜索条件；Clear 清除搜索。
- 只列活跃非 staff 账号，按用户名及 ID 稳定排序。
- 列为 Student、Attempts、Questions、Solved attempts、Last activity、View Profile。
- 无练习者显示无证据，不能只凭目录认定其能力低。

目录的 Attempts 是该用户全部保存反馈条数；Questions 是关联题去重数；Solved attempts 是成功尝试次数，均不是标准能力评分。教师点击 View Profile 看八个 Topic、历史和重复错误，再点 Current Status 看近期估算。

页面 ID 取自该数据库。不要假定默认库的 `/students/4/` 与虚构库同编号一定是同一人；应由目录链接进入。

### 9.2 Experiment 的正确用途

入口 `/experiment/`，教师手动填题目、目标、学生代码、stdin、expected output、比较模式，选择 DeepSeek／Kimi 和三种 prompt。

| 条件 | 输入与约束的变化 |
| --- | --- |
| Baseline | 题目、support code、学生代码、固定 Topic；不提供 runtime evidence |
| Context-aware | 在 Baseline 上加入 teaching objective、样例／测试信息、执行结果和预期输出比较 |
| Strict-scaffolded | 保留 Context-aware，再强化受支持错误类别、简短可执行提示、避免完整修正代码、可能 misconception 等要求 |

同一评测版本的条件共享固定类别与结构化 JSON 字段。三种条件不只是“有没有运行输出”这一处不同，因此不能声称比较单独证明了 runtime evidence 的因果作用。

推荐用相同题目、代码、输入与 expected output，只改变 provider／prompt，逐条检查：是否准确引用 45 与 55、是否定位边界、类别是否符合定义、建议能否操作、是否泄露完整代码。单个样例的文字长短不能证明哪个模型总体更好。

Experiment 当前是手动单条测试，不是自动并排对照实验台，也不展示批量准确率。保存记录没有学生选题练习的相同题目关联，不能混入班级 Topic 人数。真实提交会调用 API；价格未配置时 Estimated cost 显示 not configured，不表示免费或费用为零。

## 10. 状态字段、分类体系与 Topic

### 10.1 execution_status：15 个可能值

| 值 | 含义 |
| --- | --- |
| success | 程序进程返回成功；不保证输出正确 |
| syntax_error | Python SyntaxError |
| indentation_error | IndentationError／TabError |
| name_error | NameError／UnboundLocalError |
| type_error | TypeError |
| value_error | ValueError |
| index_error | IndexError |
| key_error | KeyError |
| eof_error | EOFError，常见于输入不足 |
| module_not_found | ModuleNotFoundError |
| import_error | ImportError |
| runtime_error | 未落入上述细类的非零返回异常 |
| timeout | 超过执行时间上限 |
| empty_code | 执行函数收到空代码；正常提交表单通常先拒绝空代码 |
| system_error | 执行环境／子进程调用等系统侧错误 |

旧数据可能为空，并不表示出现了第 16 个标准状态。`execution_status=runtime_error` 与 AI 的 `classification_outcome=runtime_error` 是两个不同字段。

### 10.2 output_comparison_status：6 个可能值

| 值 | 含义 |
| --- | --- |
| exact_match | actual 与 expected 原始字符串完全相同，包括换行等 |
| normalized_match | 原文不同，规范化后相同，且比较模式允许 normalized |
| mismatch | 有 expected output，执行无失败信号，但输出未满足所选比较模式 |
| execution_error | 有 expected output，程序执行失败，无法作为正常输出比较 |
| timeout | 有 expected output，执行超时 |
| not_applicable | 未提供非空 expected output，未进行输出判对错 |

比较函数先检查 expected output 是否为空；没有预期输出时，即使执行失败，Output 也可能是 not_applicable，要同时阅读 Runtime 列。

Strict：只认原始字符串相等。Normalized：先试完全相等；不相等时统一换行、去首尾空白和空行、合并行内空格／tab，并默认忽略大小写后比较。它**不会把多行输出变成一行**，也不会宽松比较不同数字。

因此 `4 8 12 16 20` 一行与五行分别打印五个数仍可是 mismatch。使用 strict 的题，末尾空格或换行也可能影响匹配。

### 10.3 现行错误分类：24＋4

PECI A-X 24 类的名称来自 Cooke、Hawwash 和 Smith（2019）的 PECI Table 1；代码中的操作性定义为项目实现使用的解释，不应把每段英文定义冒充文献逐字原文。Topic 是基于 PECI concepts 整理的八个教学组，不等于 24 个错误类别。

四个补充类别由项目定义，与 A-X 并列，不分配伪造的 PECI 字母：

| outcome | label | 操作性范围 |
| --- | --- | --- |
| condition_error | Condition Error | 可执行程序中的比较／布尔条件运算符或边界错，选错分支 |
| loop_boundary_error | Loop Boundary Error | 循环起止或次数 off-by-one，造成数量或结果错 |
| logical_error | Logical error | 算法、条件或状态更新违背题意；没有更具体类别时才用 |
| runtime_error | Runtime error | 因异常终止，且没有 A-X 类别能准确描述主要错误 |

Condition Error 和 Loop Boundary Error 沿用早期项目名称，因为它们比硬套某个 A-X 码更贴合相应错误。确切英文定义见附录 A。

`classification_outcome` 共八值：`peci_error`、`no_error`、`outside_peci_scope`、`condition_error`、`loop_boundary_error`、`logical_error`、`runtime_error`、`unknown`。仅 `peci_error` 携带 A-X 字母码；其他情况该码为空。

outside_peci_scope 仍用于真实无法由现行类别覆盖的问题；unknown 用于证据不足。它们没有从 schema 删除，但本轮 55 个确认标签里 outside 为零。不能为追求零 outside 强迫未来所有未知错误进入 Logical error。

运行时症状和根因可能不同：拼错变量造成 NameError，根因可能是 N，而不是一律 Runtime error。`q5-011` 确认标签保留 Logical error，实际证据为 TypeError，两个模型都判 Runtime error；这个歧义原样保留，没有为了提高准确率修改标签。

### 10.4 JSON 与反馈解释

现行版本为 `feedback_schema_v4_revised_taxonomy`。模型输出经过解析、校验及规范化后，页面使用保存的结构化字段展示。反馈 Level 1／2／3 表示一般提示、针对性提示、明确调试步骤，不是学生成绩等级；三个 prompt 也不等于三个 Level。

`uses_runtime_evidence`、`does_reveal_solution` 和 confidence 含模型自报信息；额外泄露检测也只是程序规则。不能说“标 false 就证明完全没有泄露”或“high 就是准确率高”。字段表见附录 C。

## 11. 评分与知识估算：报告可引用的实现口径

### 11.1 单次尝试原始 rubric

按下表从上往下匹配，先命中的分支返回分数及英文 reason，不叠加：

| 优先级 | 条件 | 分数 |
| --- | --- | ---: |
| 1 | `solved=True` | 100 |
| 2 | execution_status 非空且不是 success | 20 |
| 3 | output_comparison_status 为 mismatch | 45 |
| 4 | exact_match，但尚未 solved | 75 |
| 5 | normalized_match，但尚未 solved | 65 |
| 6 | error_category 非空，且此前没有决定性条件 | 35 |
| 7 | 其余 | 0 |

这是项目为反馈证据设置的启发式分数，不是人工评分的考试分。AI 失败也不会必然记 0：如果已有 mismatch 等运行证据，仍可能按对应分支记分，进而影响知识估算。

### 11.2 多 Topic partial credit

先按**当前每道题最新一次原始分**，为各 Topic 算平均基线 L。再对每条历史尝试分 S 和该题 n 个 Topic，分配：

```text
credit(Ti) = (S × n) × Li / ΣLj
```

补充实现规则：任一关联 Topic 的基线为 0 时，该题改用相等权重，每个 Topic 得 S；Topic 信用分上限 100，超出部分继续按权重分配给尚未封顶的 Topic。

例：S=50，A/B/C 基线为 100/100/20，总池 150：A≈68.18、B≈68.18、C≈13.64，可写约 68／68／14。这里的“总池”是 n 个 Topic 信用分的总和，不是把原题的 50 分直接分成三份。

重要实现特点：所有历史尝试使用这一轮当前基线重新分配。新成绩改变基线时，早期 Topic 信用分也可能改变。**不能写成“每次提交时只按此前知识状态更新并永久固定”。**这套分配反映估计权重，不能证明低分 Topic 就是这次错误的真正原因。

### 11.3 Progress 雷达：EMA

把某 Topic 所有相关尝试的加权信用分按 `(created_at, id)` 从早到晚排列：

```text
EMA1 = credit1
EMAt = 0.5 × creditt + 0.5 × EMA(t−1)
display_score = round(final_EMA)
```

例如信用分 20 → 45 → 100，EMA 为 20 → 32.5 → 66.25，最终显示约 66。后期表现权重更高，早期错误逐渐衰减；新成绩也会通过 partial-credit 基线影响历史信用分。

### 11.4 Current Status：近期均值

复用上述加权信用分，但只取该 Topic 最新至多 N 次求均值。默认 N=5，少于 5 次就按实际次数，不补 0。练习总数仍统计全历史。

报告应分开写：**历史雷达＝所有尝试 EMA；当前状态＝近期窗口均值；多 Topic 分配＝当前每题最新成绩基线。**它们不是互相替换的同一个“平均分”。

## 12. 离线评测：版本、百分比和结果文件

### 12.1 哪一份是当前结果

目录：`/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/`。

现行最终汇总：

- `peci_ax_evaluation_revised_final_summary.md`
- `peci_ax_evaluation_revised_final_summary.json`

`peci_ax_evaluation_summary_revised.md`、`peci_ax_evaluation_summary_revised_v2.md` 等是中间阶段文件；不能因为文件名带 revised 就选为最终结果。正式数字以下面的 final 为准，旧结果保留追溯。

### 12.2 三个标签版本分别回答什么

| 版本／数据 | 设计 | 指标 | 正确解释 |
| --- | --- | --- | --- |
| Day 12 旧项目分类 | 55 Refactory × 2 providers × 3 prompts＝330 | Baseline 61/110＝55.45%；Context-aware 100/110＝90.91%；Strict-scaffolded 96/110＝87.27%；合计 257/330＝77.88% | 与旧项目标签的一致率；不是现行 24＋4 分类准确率 |
| 冻结 A-X 历史版 | 同一 55 样本 × 2 providers × strict＝110 | 总计 55/110＝50.00%；域内 40/52＝76.92%；原 outside 15/58＝25.86% | 26 条域内／29 条原 outside 标签下的历史结果 |
| 修订 24＋4 最终版 | 同一 55 样本 × 2 providers × strict＝110 | 58/110＝52.73% | 修订人工确认分类下的现行评测 |

不能把 52.73% 与 50.00% 写成“准确率提高 2.73 个百分点”：标签空间已改变。也不能把旧 Context-aware 的 90.91% 当成当前网站新分类准确率。

### 12.3 29 条原 outside 怎样处理

经代码、失败测试、运行证据与分类定义核对，研究者确认修订：

| 归类 | 数量 | 样例 ID 简写 |
| --- | ---: | --- |
| 保留／重归 A-X | 4 | q4-009→L；q4-010→E；q5-005→W；q5-010→W |
| Condition Error | 1 | q1-001 |
| Loop Boundary Error | 1 | q5-001 |
| Logical error | 13 | 包含 q5-011 |
| Runtime error | 10 | 越界、未绑定变量等具体代码问题 |

其余 26 条原 A-X 保留。因此最终 **30 条 A-X＋25 条补充类别＝55 条**。确认 CSV：`peci_ax_ground_truth_confirmed.csv`；原版备份 `peci_ax_ground_truth_confirmed_original_v1.csv`，修订版另存 `peci_ax_ground_truth_confirmed_revised_v1.csv`。不要在录屏或手册操作时再次随意改标签。

### 12.4 当前结果与可用率

| 项目 | 数量 | 百分比 |
| --- | ---: | ---: |
| DeepSeek 正确 | 27/55 | 49.09% |
| Kimi 正确 | 31/55 | 56.36% |
| 全部正确 | 58/110 | 52.73% |
| 最终结构化可用 | 107/110 | 97.27% |
| 最终无效响应 | 3/110，均为 Kimi | 2.73% |

三个无效结果是 q2-009 空响应、q2-010 JSON 截断、q5-007 空响应。最终集合没有 provider/API 传输失败，但保留三条不可用输出；不能据此声称最初 110 次请求一次全部成功。

最终集合保留源运行中 104 条可用结果，包括错误预测，仅用技术补跑替换 6 条失败结果；不是按准确率挑较好答案。110 是最终计划样本－模型配对数，不是包含修复、限流及补跑在内的总 HTTP 请求数。

### 12.5 准确率、召回率、精确率怎么计算

```text
整体准确率 = 正确 sample-provider 结果数 / 全部计划结果数
类别召回率 Recall = 该类预测正确数 TP / 该类真实标签总数 (TP+FN)
类别精确率 Precision = 该类预测正确数 TP / 所有被预测为该类的结果数 (TP+FP)
F1 = 2 × Precision × Recall / (Precision+Recall)
```

对 A-X，只有 outcome 与 A-X 字母码同时匹配才算正确；补充类别按 outcome 匹配。无效输出留在整体准确率及真实类别的分母里。

例：Runtime error 有 10 个真实样本，两个 provider 共 20 个真实结果，其中 16 个判对，因此 Recall＝16/20＝80%。模型一共预测了 32 次 Runtime error，只有 16 次正确，因此 Precision＝16/32＝50%。意思是“能找回多数真实运行错误，但也把别的错误误判成它”。

| 类别 | 真实程序样本数 | 召回率（合并两个模型） | 精确率（合并两个模型） |
| --- | ---: | ---: | ---: |
| N Misspelled names or keywords | 9 | 66.67% | 75.00% |
| V Call without parentheses | 3 | 83.33% | 100.00% |
| Runtime error | 10 | 80.00% | 50.00% |
| Logical error | 13 | 46.15% | 52.17% |
| Condition Error | 1 | 100.00% | 20.00% |
| Loop Boundary Error | 1 | 100.00% | 20.00% |

两个边界类各仅 1 个真实样本，即每类共 2 个 provider 结果，却各被预测 10 次，只有 2 次正确；100% Recall 不能解读成可靠分类。Logical error 的 26 个真实结果中，7 次被判 Condition、5 次被判 Loop Boundary。A 和 N 各有 6 次被判 Runtime，反映根因与运行症状容易混淆。

完整类别矩阵／逐模型指标见 final summary；55 条只覆盖 12 个有样本类别，16 个无样本 A-X 类别不能声称已验证。按类“accuracy”在这类汇总中通常就是该类 recall，不能直接称为 precision。

### 12.6 报告和视频的解释边界

- 同一批 55 条用于分类修订和再评测，不是独立留出测试集。
- 样本刻意选择，不代表所有初学者程序的类别分布。
- 分类一致率不等于提示有用率，更不等于真实学习提升。
- 20 条反馈质量 spot-check 是 AI 辅助、研究者核验，不是独立大规模人工实验。
- 12 条手工边界样例与 Refactory 分开。Day 14 的 60/72＝83.33% 是其历史补充测试结果，不并入本轮 58/110。
- token 用量和延迟可作为记录阅读；未配置单价不能报告 API 费用总额。
- 不需要为了录视频重新批量调用 API。现场 API 的一次回答也不能覆盖冻结评测结果。

## 13. 可直接使用的演示代码

这些是教学例子，不是新的评测样本。下列 stdout 与执行状态可由本地程序核验；**分类和反馈由真实模型产生，不能保证每次完全一样**。若要保证视频连续，应先试录并保留真实记录，失败就如实展示，不编辑数据库伪造成功。

### 13.1 三次尝试后成功：Countdown from three

选题 `Countdown from three`。题目使用 strict 比较，expected output 为四行：

```text
3
2
1
Go!
```

第一次：少打印 1。

```python
n = 3
while n > 1:
    print(n)
    n -= 1
print("Go!")
```

实际输出 `3\n2\nGo!\n`，运行 success，输出 mismatch，应保持 In progress。点 Retry this question。

第二次：又多打印 0。

```python
n = 3
while n >= 0:
    print(n)
    n -= 1
print("Go!")
```

实际输出 `3\n2\n1\n0\nGo!\n`，运行 success，输出 mismatch，仍 In progress。再次 Retry。

第三次：边界正确。

```python
n = 3
while n > 0:
    print(n)
    n -= 1
print("Go!")
```

运行 success、输出 exact_match；当模型同时给出 no_error 时进入 Solved。展示代码、四行输出和反馈，再点 View attempt history 看三次版本。

**编号提醒：**若 student1 已在该题有记录，这三次新尝试不会自动成为 Attempt 1／2／3。需要从 1 录制时，可在独立演示库用 Admin 新建无历史的非 staff 演示账号；不要为拍视频删除原始研究／学生历史。此处是“三次新提交后成功”的脚本，不保证既有账号的绝对编号。

### 13.2 能运行但结果错：Sum from 1 to 10

```python
total = 0
for i in range(1, 10):
    total += i
print(total)
```

expected `55\n`；actual `45\n`；success＋mismatch。现行分类定义可用 Loop Boundary Error 描述，不能沿用旧手册“此例正式分类一定为 Outside PECI Scope”的说法。模型具体预测以保存结果为准。

改成 `range(1, 11)` 得到 55；是否 Solved 仍需满足三项条件。

### 13.3 输入与输出格式：Greeting with input

```python
name = input()
print("Hello" + name)
```

题目 sample_input `Ada\n`；expected `Hello Ada\n`；actual `HelloAda\n`，success＋mismatch。修正为 `print("Hello " + name)`。用来展示 stdin 注入和输出间隔，不要求观众在运行页面手动交互输入。

### 13.4 SyntaxError 与 NameError

同样选择 Sum from 1 to 10。缺冒号：

```python
total = 0
for i in range(1, 11)
    total += i
print(total)
```

Runtime 为 syntax_error，Output 为 execution_error；可对照 S 缺标点定义。

变量拼错：

```python
total = 0
for i in range(1, 11):
    total += i
print(totla)
```

Runtime 为 name_error，Output 为 execution_error；可对照 N 拼写错误。不要因为 Runtime 栏写 name_error 就强制宣称 AI 分类必须 Runtime error。

### 13.5 可选：Five multiples 的行格式

```python
n = int(input())
for i in range(1, 6):
    print(n * i)
```

stdin `4\n`，数值是 4、8、12、16、20，但输出为五行，题目要求一行 `4 8 12 16 20\n`，strict 下 mismatch。修正例：

```python
n = int(input())
print(" ".join(str(n * i) for i in range(1, 6)))
```

此例可以解释“数算对了，格式仍可能不符合要求”。

## 14. 为视频和报告组织演示

### 14.1 视频要求与建议路线要分开

已找到的《FYP Instruction Handbook 2025_26》§2.5.2（印刷第 9 页／PDF 第 10 页）要求：demo video 最长 **6 分钟**，约 2 分钟 Problem Formulation、约 4 分钟 Outcome Demonstration；用于口头展示时需现场讲解。

该手册是 2025/26 版本，目前材料中未找到另一个明确改写视频时长的 2026/27 通知。因此以此准备，并以课程最新通知为准。当前 final presentation 的 5–10 分钟口头报告＋5 分钟问答，不是视频时长要求。未找到明确的视频分辨率、文件大小或提交截止时间规定，不应自行写成学校硬性要求。

详细来源和录制准备见：`/Users/a77777/Documents/ChatGPT/FYP/deliverables/FYP_demo视频要求核查与录制准备_2026-11-06.md`。

视频另有单独维护的文案与录制操作表。当前主线为：三次尝试 → trajectory → Progress／Current Status → 教师跟进 → 简短评测 → 学习目标。熟悉网站时按本手册第 0 节进行，剪辑前再核对最新视频文件，不套用旧版时间表。

当前视频仍为待核对文案；其中的流程时间不是系统使用步骤的强制顺序。视频的具体操作以 `/Users/a77777/Documents/ChatGPT/FYP/deliverables/Demo视频录制操作对照表.md` 为准：8010 的 student2 录制求和题三次新尝试，8011 的 instructor 展示独立虚构班级。原库的 student1 和 student2 在求和题都已有历史；只有 8010 快照中的 student2 当前仍可从 Attempt 1 起步。结尾落在学习支持和独立解决问题的目标，评测仅简短补充。

### 14.2 报告截图应展示什么

以下对应本轮 Chapter 4 的图号规划；若最终报告另有重新编号，以正文实际题注为准。

| 图 | 应截的真实页面 | 保留的信息／建议英文图题 |
| --- | --- | --- |
| Figure 4.1 | 学生结果页，或 History View 的同一保存结果 | 代码、Runtime／Output、expected／actual、针对性反馈；`Student submission, execution evidence and targeted feedback.` |
| Figure 4.4 | Current Status | 顶部一个行动＋全部八个 Topic，含 No evidence；`Current knowledge status based on recent topic attempts.` |
| Figure 4.5 | Class Analytics 的 Topic／类别／建议区域 | 不同学生数、分母、次要 occurrences、来源及 View records；`Class-level follow-up evidence based on distinct students.` |
| Figure 4.6 | Student Directory，再配一张选中学生 Profile | 搜索、每页 5 人、分页、View Profile；个人八 Topic 另图或子图；`Searchable student directory and individual learning evidence.` |

4.5 展示“老师从班级层面发现问题”；4.6 展示“老师在约 30 人中找到某一人并查证”。两张不是重复截图。

长页不要整页缩成一条：用正常桌面宽度截相关模块，按 A4 印刷后可读为准。若八 Topic 和建议放不下，分两张连续子图，不能裁掉未练 Topic。滚动表可以只截当前可读区域，并说明可内部滚动；若正文声称展示全量条目，则补后续分图。截图必须来自运行的真实界面，不画假页面。

图注说明环境与数据来源，例如：`Interface demonstration using fictional student accounts and scripted practice records; not classroom-study results.` 原记录快照里的旧 schema 反馈应注明为保存历史，不声称它来自本轮新分类 API。

### 14.3 写报告时可查的实现表述

| 主题 | 准确写法要点 | 对应来源 |
| --- | --- | --- |
| 系统流程 | 限时本地执行→比较输出→构造 prompt→调用模型→验证／最多一次无效 JSON 修复→保存→学生选择重试 | `views.py`、`json_repair.py` |
| 知识估算 | 当前基线加权分配；历史雷达全尝试 EMA α=0.5；Current Status 最近 N 次均值 | `analytics.py` |
| 班级分析 | Topic 用最新相关尝试的学生比例；错误用曾出现诊断的不同学生数；提交次数为辅助 | `build_class_evidence` |
| 分类来源 | PECI 文献 24 个名称＋项目操作性定义＋四个补充类别；历史记录不重标 | `taxonomy.py`、保存记录 |
| 研究结果 | final summary 58/110；不可与旧标签 50% 当同一指标比较 | final summary MD／JSON |
| 限制 | 非独立测试集、类别不均衡、根因／症状歧义、原型执行隔离边界 | 方法、结果及代码证据 |

手册提供实现依据，不代替学校模板、正式引用或最终报告审核。不要直接把操作命令、账号和内部路径整段放进正文。

## 15. 维护、初始化和验证

### 15.1 Fresh clone

数据库通常不随仓库分发。依 README 安装依赖、配置环境、执行 migrate，再按需要初始化教学演示。模型请求需要有效 API key；不要把 `.env`、真实密钥或数据库中的个人信息提交到公开仓库。

初始化命令（只在选定的演示库中主动执行）：

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py seed_demo --with-history
```

`seed_demo` 会创建／更新演示账号、重设这些演示账号的密码并更新同名教学题。`--with-history` 还会写入确定性预置历史并清理过期 seed 记录，不是“调用模型生成真实研究结果”。这些命令**不是只读检查**；已有重要数据时不要为刷新页面随手重复执行。

尤其 `--reset-demo-history --with-history` 会删除演示学生已有提交，再重建预置轨迹。本手册不建议在原数据库为了录视频使用它；先用独立库或无历史账号。

当前设置支持 `DJANGO_DB_PATH` 指向独立库。新库需要先迁移；只复制模板、改 URL 端口不会自动生成 30 名学生，也不能假设 seed_demo 自动构造了本次独立 30 人班级。

### 15.2 本地执行的安全范围

`code_runner.py` 使用临时目录、`python3 -I -B`、捕获 stdout／stderr 和 timeout；网页当前默认运行上限 3 秒，离线评测可以使用不同 timeout。它是原型级子进程隔离，不是容器、独立用户或完整文件／网络／内存隔离环境。

因此报告中可以写 time-limited local execution，不能宣称已实现生产级安全沙箱。录制使用受控教学代码，不以此公开服务执行任意陌生代码。

### 15.3 最近已有测试证据

| 检查 | 已保存结果 | 证据位置 |
| --- | --- | --- |
| 当前完整测试（2026-11-11） | 发现 135 项：129 通过、6 条条件跳过；0 失败／错误 | `deliverables/manual_github_review_2026-11-11/django_tests.txt` |
| 每页 5 人后的目录／界面专项 | 6 项通过，0 失败 | `ch4_ui_revision/directory_five_per_page_tests.txt` |

路径均在 `/Users/a77777/Documents/ChatGPT/FYP/` 下。本次为 GitHub 上传运行了完整 `python manage.py test`；135 项中 129 通过，6 项条件跳过，不将跳过当作通过。跳过涉及尚未解压的条件性 Refactory 源文件检查。之前目录专项日志作为历史补充保留。

需要在新代码提交后重新验证时，可运行：

```bash
python manage.py test
```

## 16. 常见问题

**页面里没有 30 个学生？** 先确认服务使用 fictional_class.sqlite3，而不是默认库或 8010 快照。目录只列活跃非 staff；搜索条件也会缩小结果。

**从学生结果详情进入后，为什么没有模型选择？** 学生题由教师配置 provider；手动 provider／prompt 选择在教师 Experiment。

**结果页没有变／仍显示旧术语？** 先检查浏览器主机、端口、运行进程对应代码；`--noreload` 需重启。History 会保留旧诊断，不代表现在重新调用了旧模型。

**为什么 Runtime 是 success，而题目仍 In progress？** success 只说明执行完成；输出可能 mismatch，或者模型不是 no_error。

**为什么输出匹配但只有 75／65？** 原始 rubric 对尚未 solved 的 exact／normalized match 分别记 75／65；一旦 solved 记 100。多 Topic 分配及汇总后图中分数还会变化。

**为什么以前的 Topic 分数也变了？** partial-credit 使用当前最新题目分基线重分配历史信用，不是逐次固定；见第 11 节。

**为什么 Current Status 和雷达不同？** 前者近期窗口均值，后者所有尝试 EMA；两者窗口和汇总法不同。

**为什么班级错误人数不等于未解决人数？** 错误表统计“曾出现”，Topic 跟进看“最新相关尝试未解决”；问题不同。

**为什么 Analytics 和 Dashboard 的输出次数不同于练习次数？** Dashboard／Output Comparison 可含教师实验；活跃班级人数统计排除这些记录。

**为什么平均三次才解决，但 Solve rate 是 100%？** 所有 run 最终都解决，不代表每次提交都成功。Avg to solve 和最终 run 解决率是不同指标。

**为什么调用失败仍有 History 记录？** 系统保留代码和已获得的运行证据，记录 AI error；不会伪造反馈或自动切到另一个 provider。

**能不能用同一段代码保证第三次一定 Solved？** 本地 stdout 可确定；真实模型回答有波动，第三次还须 no_error。不能为配合视频而假写数据库结果。

**为什么没有 EN／中文按钮？** 当前版本已移除网站内语言切换。旧截图／旧说明里出现该按钮，不代表当前功能；代码和保存的反馈内容没有因此改写。

**Evaluation 页面不见了，评测是否被删？** 只是网站路由与入口移除，离线 runner、CSV、summary 和原始结果仍在。

## 17. 查证来源与录制前检查

### 17.1 当前代码定位

| 内容 | 文件／函数 |
| --- | --- |
| 路由 | `feedback_project/urls.py` |
| 独立库、近期窗口配置 | `feedback_project/settings.py` |
| 提交、trajectory、solved、权限、目录分页、历史过滤 | `feedback_app/views.py` |
| runtime、比较模式 | `feedback_app/code_runner.py`、`output_comparison.py` |
| rubric／partial credit／EMA／Current Status | `feedback_app/analytics.py` 中 `_attempt_score_details`、`_allocate_partial_credit`、`_attributed_attempt_scores`、`build_skill_mastery`、`build_current_status` |
| 班级人数与难度 | `build_class_evidence`、`stored_error_identity`、`build_question_difficulty` |
| 分类／Topic／schema | `taxonomy.py`、`feedback_schema.py` |
| prompt／JSON 修复 | `prompt_builder.py`、`json_repair.py`、`ai_response.py` |
| 结果和详情共用布局 | `_review_top.html`、`_review_feedback.html`、`_review_debug.html` |
| 班级、状态、目录模板 | `analytics.html`、`current_status.html`、`student_directory.html` |
| 界面语言 | 当前英文界面；base.html 已无语言切换入口，旧 ui-i18n.js 已移除 |
| 演示账号、题目及预置历史 | `management/commands/seed_demo.py` |
| 主评测数据来源 | `evaluation_dataset_sources.md`、`evaluation_samples.json` |

相对代码路径均基于 `/Users/a77777/Desktop/fyp-code-feedback/`。下列附录从本次源文件抽取，不是新的类别建议。

### 17.2 录制／截图检查清单

- [ ] 确认端口、数据库、角色，以及是真实 API 结果还是预置／脚本反馈。
- [ ] 确认题目 active、stdin／expected output／比较模式与样例匹配。
- [ ] 若需要 Attempt 1 起步，使用独立无历史演示账号，不清空原始数据。
- [ ] 展示代码、实际／预期输出、反馈和下一步，不只展示分类卡片。
- [ ] 保留八 Topic 和 No evidence；不把未练学生当作困难学生。
- [ ] 教师页讲清人数与次数；搜索目录每页 5 人，点击进入个人证据。
- [ ] 需完整长表时录内部滚动，不把其余条目说成被删除。
- [ ] 解释 52.73% 时带 58/110 和修订标签范围，不与旧版本直接比升幅。
- [ ] 隐去密码、密钥、个人信息；截图图注说明演示来源。
- [ ] 按最终 A4／视频分辨率检查字体，不把整张长网页缩到不可读。

<!-- GENERATED_REFERENCE_APPENDICES -->

## 附录 A：八个 Topic 与项目补充类别的现行英文定义

以下从 `feedback_app/taxonomy.py` 原样抽取 label 和操作性定义，供核对代码与报告。

| Topic ID | 页面名称 | 操作性定义 | 对应 PECI concept 线索 |
| --- | --- | --- | --- |
| program_structure | Program Structure and Statements | Program execution order, Python statements, block structure, and how separate statements form a complete program. | C1 The Program; C4 Statements |
| variables_assignment | Variables and Assignment | Creating names, storing values, updating state, and tracing how assignment changes a variable during execution. | C2 Variables |
| expressions_operators | Expressions and Operators | Arithmetic, comparison, division, modulo, precedence, and the evaluation of expressions. | C3 Expressions |
| conditionals_boolean | Conditionals and Boolean Logic | Boolean conditions and if/elif/else branches used to select which statements execute. | C6 Conditionals |
| iteration_range | Iteration and Range | for/while loops, range boundaries, repeated state updates, accumulator patterns, and loop termination. | C9 Iteration |
| functions_returns | Functions and Return Values | Function definitions and calls, parameters, local scope, and returning a value to the caller. | C5 Functions; C8 Fruitful functions |
| strings_io | Strings, Input, and Output | String values and quotation, reading user input, conversion at the input boundary, and producing the required printed format. | C10 Strings; C4 Statements |
| collections_indexing | Collections and Indexing | Lists, dictionaries, and tuples, including element access, indices, traversal, and collection operations. | C11 Lists; C12 Dictionaries; C13 Tuples |

| 项目 outcome | label | 操作性定义原文 |
| --- | --- | --- |
| condition_error | Condition Error | A comparison or Boolean condition uses an incorrect operator or boundary (for example, < instead of <=), causing an executable program to select the wrong branch. |
| loop_boundary_error | Loop Boundary Error | A loop starts, stops, or repeats an off-by-one number of times, causing an incorrect count or result. |
| logical_error | Logical error | The program executes but its algorithm, condition, or state update produces a result inconsistent with the task. Use only when no more specific category applies. |
| runtime_error | Runtime error | The program terminates with a runtime exception, such as IndexError, UnboundLocalError, TypeError, or ValueError, for which no PECI A-X category describes the primary error. |

## 附录 B：PECI A-X 24 类参考清单

名称取自项目所采用的 PECI 类别；Definition 列是代码中的项目操作性定义，不是声称逐字摘录文献。

| 码 | 类别名称 | 当前操作性定义 |
| --- | --- | --- |
| A | Invalid names | An identifier is invalid for the role in which it is used, excluding the more specific misspelling and reserved-keyword cases N and O. |
| B | Left-to-right assignments | The student treats assignment as if the value flows from the left side to the right side, reversing Python's target = value relationship. |
| C | Assignments in expressions | An assignment is placed where an expression or Boolean test is required, or assignment and expression evaluation are confused. |
| D | Expressions as parameters | An expression is supplied or structured incorrectly as a function argument or parameter, so the call does not represent the intended value or contract. |
| E | Literal values instead of variables | A fixed literal is used where the task requires a variable or computed value, causing the program to work only for a particular case. |
| F | Extra or missing spaces | Spaces are added or omitted where they change required program or output form, including exact-format output tasks. |
| G | Invalid else-statements | An else or elif branch is attached, ordered, or structured incorrectly relative to its if statement. |
| H | Missing or extra quotation marks | A string uses missing, extra, or mismatched quotation marks, changing or invalidating the intended string literal. |
| I | Division and modulo | Division or modulo is selected, interpreted, or applied incorrectly for the required calculation or divisibility test. |
| J | Invalid use of the and-operator | The Boolean and operator combines conditions incorrectly or is used where separate complete comparisons are required. |
| K | Wrong or extra keyword | A Python keyword is incorrect, unnecessary, or placed where the language does not permit it. |
| L | Incorrect structure | The program's statement, block, branch, loop, or function structure is arranged incorrectly and no more specific PECI category describes the primary cause. |
| M | Unbalanced parentheses and brackets | Opening and closing parentheses, square brackets, or braces are missing, extra, or mismatched. |
| N | Misspelled names or keywords | A variable, function, method, or keyword is spelled inconsistently with its definition or Python's required spelling. |
| O | Using keywords as names | A reserved Python keyword is used as a variable, function, parameter, or other identifier. |
| P | Using assignment instead of comparison | Assignment syntax is used where equality or another comparison is intended. |
| Q | Misspelled operators | An operator is written in an invalid or unintended form, such as mistyping a comparison or arithmetic operator. |
| R | Unterminated string literal | A string begins with a quotation mark but is not closed correctly before the line or file ends. |
| S | Missing colon, comma or operator | Required punctuation or an operator is omitted, such as a missing colon after a compound statement or a missing comma between arguments. |
| T | Invalid indentation | Indentation is missing, unexpected, or inconsistent, so Python block membership is invalid or differs from the intended control flow. |
| U | Code after a break statement | Statements are placed after break in the same loop block and are therefore unreachable on that path. |
| V | Call without parentheses | A function or method is referenced without the parentheses needed to call it when execution of that callable is intended. |
| W | Useless computations | A computation is performed but its result is neither stored, returned, printed, nor otherwise used to affect the program. |
| X | Useless comparison | A comparison is evaluated but its Boolean result is ignored and therefore does not influence control flow or output. |

## 附录 C：结构化反馈字段

版本：`feedback_schema_v4_revised_taxonomy`。下列是 schema 的 required 字段；数据库另保存 runtime、prompt、AI error 等证据，不能把两者混为一个表。

| 字段 | 类型 | schema 中的含义／约束 |
| --- | --- | --- |
| classification_outcome | string | Whether the result is one PECI error, no error, a genuine issue outside the PECI A-X inventory, one of the project-defined error categories, or unknown. Allowed: 'peci_error', 'no_error', 'outside_peci_scope', 'condition_error', 'loop_boundary_error', 'logical_error', 'runtime_error', 'unknown'. |
| peci_error_code | string | Exactly one literature-derived PECI code A-X when classification_outcome is peci_error; otherwise an empty string. Allowed: '', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X'. |
| feedback_level | string | Level 1 general hint, Level 2 targeted hint, Level 3 explicit debugging step. Allowed: 'Level 1', 'Level 2', 'Level 3'. |
| concept_reference | string | The most relevant fixed topic label supplied in the question context, or Unknown when no topic can be supported. Allowed: 'Program Structure and Statements', 'Variables and Assignment', 'Expressions and Operators', 'Conditionals and Boolean Logic', 'Iteration and Range', 'Functions and Return Values', 'Strings, Input, and Output', 'Collections and Indexing', 'Unknown'. |
| misconception | string | One short sentence describing the student's most likely misunderstanding, grounded in the code and runtime evidence. Return an empty string when classification_outcome is no_error or unknown. |
| feedback | string | Short scaffolded feedback without full corrected code. |
| does_reveal_solution | boolean | True only if the response gives away the full answer or corrected program. |
| uses_runtime_evidence | boolean | True if the feedback uses stdout, stderr, timeout, or comparison evidence. |
| suggested_next_step | string | One concrete next debugging action for the student. |
| confidence | string |  Allowed: 'low', 'medium', 'high'. |

`concept_reference` 是保留的内部键，界面称 Topic；不是新增另一套 Concept。`error_category`、`peci_error_label` 等页面展示字段可在校验／规范化后派生，不能声称都要求模型作为独立 required 字段返回。
