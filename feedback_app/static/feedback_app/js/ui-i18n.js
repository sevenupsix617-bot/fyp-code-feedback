(function () {
    "use strict";

    // Fixed UI copy only. Student code, runtime data, and generated feedback stay verbatim.
    const zh = {
        "AI Programming Feedback": "AI 编程反馈",
        "Instructor": "教师", "Analytics": "学习分析", "Experiment": "实验",
        "History": "历史记录", "Admin": "管理后台", "Submit": "提交",
        "Progress": "学习进展", "Current Status": "当前状态", "Logout": "退出登录",
        "Sign out": "退出登录", "Primary navigation": "主导航",
        "Interface language": "界面语言", "English interface": "英文界面",
        "Chinese interface": "中文界面", "Secure Access": "安全登录",
        "Code Feedback Login": "编程反馈登录", "Username": "用户名",
        "Password": "密码", "Log in": "登录", "Login": "登录",

        "Instructor Workspace": "教师工作区", "Instructor Dashboard": "教师仪表盘",
        "Question bank management, evaluator workflow, and recent feedback evidence.": "管理题库、评估流程和近期反馈记录。",
        "Add Question": "新增题目", "Manage Questions": "管理题目",
        "Experiment Interface": "实验界面", "Questions": "题目",
        "Submissions": "提交记录", "Demo Students": "演示学生",
        "Comparison Modes": "输出比较方式", "Student and evaluator records": "学生和教师的记录",
        "Non-staff active accounts": "活跃学生账号",
        "Literature-derived Taxonomy": "文献分类体系",
        "Common PECI Error Categories": "常见 PECI 错误类别",
        "Question Defaults": "题目默认设置", "Provider Defaults": "模型默认设置",
        "Runtime Evidence": "运行证据", "Output Comparison": "输出比较",
        "Question Bank": "题库", "Admin-Managed Teaching Tasks": "教学题目",
        "Evidence Log": "证据记录", "Recent Feedback Records": "近期反馈记录",
        "Difficulty not set": "未设置难度", "No tags": "无主题标签",
        "No questions yet.": "暂无题目。", "No records yet.": "暂无记录。",

        "Learning Analytics": "学习分析", "Class Analytics": "班级分析",
        "Class-level evidence, student progress profiles, and stored next-step suggestions.": "查看班级证据、学生进展和已保存的下一步建议。",
        "All saved attempts": "全部已保存的尝试",
        "Records with a stored classification outcome": "有分类结果的记录",
        "All saved attempts not marked solved": "所有尚未解决的尝试",
        "24 categories named directly from PECI Table 1": "直接来自 PECI 表 1 的 24 个类别",
        "Deterministic Statistics": "确定性统计", "Concept Evidence": "概念掌握证据",
        "Weak Concepts": "薄弱概念", "Teaching Actions": "教学建议",
        "Instructional Suggestions": "教学建议", "Student Profiles": "学生档案",
        "Skill Mastery Overview": "技能掌握概览", "Student Activity": "学生学习情况",
        "Question Evidence": "题目证据", "Question Difficulty Overview": "题目难度概览",
        "Output Comparison Status": "输出比较状态",
        "Across all saved records, including instructor manual experiments.": "统计所有已保存记录，包括教师手动实验。",
        "Stored AI Next Steps": "已保存的下一步建议",
        "Recent Feedback Suggestions": "近期反馈建议",
        "Previous student": "上一位学生", "Next student": "下一位学生",
        "Attempts": "尝试次数", "Solved": "已解决", "Unresolved": "未解决",
        "Students": "学生", "Total Attempts": "总尝试次数",
        "Average Attempts to Solve": "平均解决所需尝试次数",
        "Resolution Rate": "解决率", "Mismatch": "输出不匹配",
        "Runtime Error": "运行错误", "No Attempts": "无人尝试",
        "Hard Question": "难题", "Popular Easy Question": "热门简单题",

        "Student Portal": "学生页面", "Submit Python Code": "提交 Python 代码",
        "Choose a preset question and submit your Python code for feedback.": "选择一道题，提交 Python 代码以获取反馈。",
        "Question and Submission": "题目与提交", "Selected Question": "当前题目",
        "Question": "题目", "Sample Input": "示例输入", "Expected Output": "预期输出",
        "Your Python Code": "你的 Python 代码", "Student Python Code": "学生 Python 代码",
        "Paste your Python code here.": "在此粘贴你的 Python 代码。",
        "Paste the student Python code.": "在此粘贴学生的 Python 代码。",
        "Submit Code": "提交代码", "Submit for Feedback": "提交并获取反馈",
        "View History": "查看历史记录", "View attempt history": "查看本题尝试历程",
        "Try Again": "再次尝试", "Retry This Question": "重做此题",
        "Back to Questions": "返回题目", "Topic": "主题", "Topic Focus": "主题筛选",
        "Problem Statement": "题目描述", "Lecture Objective": "教学目标",
        "Enter the programming question.": "输入编程题目。",
        "Example: practise for loops and range boundaries.": "例如：练习 for 循环与 range 边界。",

        "Evaluator-only": "仅供教师使用",
        "Manual prompt, provider, runtime, and output comparison tests.": "手动测试提示词、模型、运行和输出比较。",
        "Manual Test Case": "手动测试用例",
        "Prompt and Runtime Evaluation": "提示词与运行评估",
        "AI Tutor": "AI 导师", "Prompt Version": "提示词版本",
        "Baseline": "基础提示词", "Context-aware": "情境增强提示词",
        "Strict scaffolded": "严格引导提示词",
        "Strict exact output": "严格匹配输出",
        "Normalized beginner-friendly output": "适合初学者的标准化输出比较",
        "Programming Question": "编程题目", "Output Comparison Mode": "输出比较方式",
        "Optional stdin. Use new lines for multiple input() calls.": "可选的标准输入。多次 input() 调用请分行填写。",
        "Optional expected output for comparison.": "可选的预期输出，用于比较。",
        "Run Experiment": "运行实验", "Run Another Experiment": "再做一次实验",

        "Feedback Result": "反馈结果", "Instructor experiment submission": "教师实验提交",
        "Submitted Code": "提交的代码", "Original Student Code": "学生原始代码",
        "Feedback Summary": "反馈概要", "Error Classification": "错误分类",
        "Error Category": "错误类别", "Concept": "概念", "Feedback Level": "反馈级别",
        "AI Self-Reported Confidence": "AI 自报信心",
        "Not a calibrated reliability score": "不是经过校准的可靠性分数",
        "Exact PECI literature category name or explicit system outcome": "PECI 文献中的类别名称或明确的系统结果",
        "Misconception": "概念误区", "Suggested Next Step": "建议的下一步",
        "Runtime Result": "运行结果", "Execution Status": "执行状态",
        "Execution status": "执行状态", "Return Code": "返回码",
        "Return code": "返回码", "Execution Time": "执行耗时",
        "Execution time": "执行耗时", "Output comparison": "输出比较",
        "Sample Input:": "示例输入：", "· Python traceback": "· Python 报错回溯",
        "Expected and Actual Output": "预期与实际输出", "Actual Output": "实际输出",
        "Error Output": "错误输出", "Debug Evidence": "调试证据",
        "Stored Metadata and Raw Response": "已保存的元数据与原始回复",
        "Raw AI response": "AI 原始回复", "Schema notes": "结构说明",
        "Token Usage": "Token 用量", "Estimated Cost": "估算费用",

        "Submission Archive": "提交档案", "Submission History": "提交历史",
        "Submission Detail": "提交详情", "Back to History": "返回历史记录",
        "Filter": "筛选", "Clear Filters": "清除筛选",
        "Student": "学生", "Date": "日期", "Runtime": "运行", "Output": "输出",
        "Status reference": "状态说明", "Runtime status values": "运行状态取值",
        "Output comparison status values": "输出比较状态取值",
        "No submissions found.": "没有找到提交记录。",
        "Feedback unavailable": "反馈暂不可用", "Level not recorded": "未记录级别",

        "My Learning Progress": "我的学习进展", "Student Profile": "学生档案",
        "Topic-level skill mastery, repeated mistakes, and traceable attempt evidence.": "查看各主题的掌握度、重复错误和可追溯的尝试记录。",
        "Saved submissions": "已保存的提交", "Distinct tasks attempted": "尝试过的不同题目",
        "Topic-Level Progress": "主题进展", "Skill Mastery Radar": "技能掌握雷达图",
        "Current Topic Scores": "当前主题得分",
        "Select a Topic label or point to inspect its time-based attempt evidence.": "选择主题标签或图上的点，查看按时间排列的尝试证据。",
        "Mistake Pattern": "错误模式", "Repeated Error Pattern": "重复错误模式",
        "Weak Knowledge": "薄弱知识点", "Mastery Evidence": "掌握证据",
        "Mastered Concepts": "已掌握的概念", "Attempt Evidence": "尝试证据",
        "Recent Attempt Sequence": "近期尝试顺序", "Saved Feedback": "已保存的反馈",
        "Next-Step Suggestions": "下一步建议", "Topic Skill Evidence": "主题技能证据",
        "Time-Based Evidence": "时间证据", "Attempt Timeline": "尝试时间线",
        "Traceable Records": "可追溯记录",
        "Weighted latest attempt per tagged question, averaged": "按题目标签加权后的最近一次尝试均分",
        "Questions carrying this fixed Topic tag": "带有此主题标签的题目",
        "All stored attempts for this Topic": "该主题的全部已保存尝试",
        "Hover or focus a point to see its question, date, error classification, solved state, comparison result, and scoring reason.": "将鼠标移到点上或聚焦，查看题目、日期、错误分类、解决状态、比较结果和评分原因。",

        "Current Knowledge Status": "当前知识状态",
        "Recent topic-level attempt evidence": "各主题的近期尝试证据",
        "Next Practice": "下一步练习", "Suggested Topics": "建议练习的主题",
        "Current Estimate": "当前估计", "Topics": "主题", "Recent score": "近期得分",
        "Practice": "练习", "Practice this topic": "练习此主题",
        "View historical progress": "查看历史进展",
        "View current status": "查看当前状态",
        "Historical Progress": "历史进展",
        "Practise": "去练习", "Practise topic": "练习此主题",
        "Practice next": "优先练习", "View evidence": "查看证据",
        "No evidence": "暂无证据",
        "No clear weak topic appears in the recent attempts. Keep practising across the question bank.": "近期尝试中没有明显薄弱的主题。请继续练习不同题目。",
        "Multi-topic marks are apportioned using baseline topic scores from each question's latest attempt; a zero baseline uses equal shares.": "多主题题目的得分按各主题的基线分数分配；基线为零时平均分配。",
        "Earlier Topic credits can change when baseline scores change; this weighting suggests where to practise, but does not prove which topic caused an error.": "基线分数变化时，之前分配的主题分数也可能变化；加权结果提示练习方向，但不能证明错误由哪个主题造成。",
        "A topic without attempts has insufficient evidence, not a score of zero. AI feedback failures may also affect the estimate.": "没有尝试记录的主题是证据不足，不代表得零分。AI 反馈失败也可能影响估计。",
        "Open Question Admin": "打开题目管理",
        "Open Full History": "查看完整历史",
        "Mode": "方式", "Provider": "模型", "Status": "状态",
        "Updated": "更新时间", "Manage": "管理", "User": "用户",
        "Error": "错误", "Comparison": "比较", "Detail": "详情",
        "View": "查看", "Edit": "编辑", "Active": "启用", "Inactive": "停用",
        "No questions have been created.": "尚未创建题目。",
        "No submissions yet.": "暂无提交记录。",
        "Tutor Response": "导师反馈", "DeepSeek Tutor Response": "DeepSeek 导师反馈",
        "Kimi Tutor Response": "Kimi 导师反馈",
        "Error classification": "错误分类", "Feedback level": "反馈级别",
        "AI self-reported confidence": "AI 自报信心",
        "Solution leakage": "答案泄漏", "JSON compliance": "JSON 合规性",
        "Schema status": "结构状态", "Schema version": "结构版本",
        "Runtime evidence": "运行证据", "Token usage": "Token 用量",
        "Estimated cost": "估算费用",
        "No structured AI feedback was generated for this submission.": "此次提交没有生成结构化 AI 反馈。",
        "This submission does not contain structured AI feedback.": "此次提交没有结构化 AI 反馈。",
        "No Error": "无错误", "not classified": "未分类",
        "not specified": "未指定", "not recorded": "未记录",
        "not configured": "未配置", "not run": "未运行",
        "flagged": "已标记", "not flagged": "未标记",
        "Submission Detail": "提交详情",
        "Program Structure and Statements": "程序结构与语句",
        "Variables and Assignment": "变量与赋值",
        "Expressions and Operators": "表达式与运算符",
        "Conditionals and Boolean Logic": "条件与布尔逻辑",
        "Iteration and Range": "循环与 range",
        "Functions and Return Values": "函数与返回值",
        "Strings, Input, and Output": "字符串、输入与输出",
        "Collections and Indexing": "集合与索引",
        "Dashboard": "仪表盘", "Classified": "已分类", "Taxonomy": "分类体系",
        "No topic tags": "无主题标签", "Manual test": "手动测试",
        "Anonymous": "匿名", "No stdin input.": "无标准输入。",
        "No expected output.": "无预期输出。", "No actual output.": "无实际输出。",
        "Back to Analytics": "返回班级分析", "Student History": "学生历史记录",
        "My History": "我的历史记录", "Back to Student Profile": "返回学生档案",
        "Back to Progress": "返回学习进展", "Solved Attempts": "已解决的尝试",
        "Attempt Success Rate": "尝试成功率", "No attempted tagged question": "没有尝试过带此标签的题目",
        "How mastery is calculated:": "掌握度计算方式：",
        "No Error = 100; output mismatch = 45; sample output matched but unresolved feedback remains = 40; unresolved classified attempt without decisive output evidence = 35; execution error = 20; no reliable evidence = 0. First, the latest raw question marks are averaged per Topic to establish baseline levels. Multi-Topic marks are then distributed in proportion to those baselines, with equal shares when a baseline is zero and a 100-point cap. The radar averages each Topic's attributed latest question marks. A Topic with no attempted tagged question is shown as": "无错误得 100 分；输出不匹配得 45 分；示例输出匹配但反馈仍指出未解决问题得 40 分；没有决定性输出证据的已分类未解决尝试得 35 分；执行错误得 20 分；没有可靠证据得 0 分。先取每题最近一次原始分数，按主题求均值得到基线；多主题题目的分数再按基线比例分配，基线为零则平均分配，分数上限为 100。雷达图展示各主题归因分数的均值。没有尝试过的主题显示为",
        ", not as a measured failure. This is a transparent prototype heuristic, not a standardised educational measurement.": "，而不是测得失败。这是一种透明的原型估算方法，不是标准化教育测量。",
        "No repeated unresolved error has been detected.": "尚未发现重复出现的未解决错误。",
        "No weak concept has enough evidence yet.": "目前没有足够证据判定薄弱概念。",
        "No mastered concept has been recorded yet.": "尚未记录已掌握的概念。",
        "No attempts have been saved.": "尚未保存尝试记录。",
        "No unresolved next-step suggestions are currently saved.": "目前没有已保存的未解决问题建议。",
        "Score": "分数", "Category": "类别", "Attempt": "尝试",
        "Current Mastery": "当前掌握度", "Questions Attempted": "已尝试题目",
        "Saved Attempts": "已保存的尝试", "Question Attempt": "题目尝试次数",
        "Question Mark": "题目得分", "Topic Credit": "主题归因分数",
        "Timeline": "时间线",
        "How this Topic score is calculated:": "该主题得分计算方式：",
        "No Error = 100; output mismatch = 45; sample output matched but an unresolved issue remains = 40; unresolved classified attempt without decisive output evidence = 35; execution error = 20; no reliable evidence = 0. The current mastery value averages the latest attributed mark for each attempted question carrying this Topic tag. Attribution uses the unweighted baseline Topic levels; a zero baseline gives equal shares. The line above shows the original question marks over time. The table also shows the baseline-weighted Topic credit for each attempt, recalculated from current baselines. This is a prototype heuristic, not a standardised educational measurement.": "无错误得 100 分；输出不匹配得 45 分；示例输出匹配但问题仍未解决得 40 分；没有决定性输出证据的已分类未解决尝试得 35 分；执行错误得 20 分；没有可靠证据得 0 分。当前掌握度取该主题相关题目最近一次归因分数的均值。归因使用未加权的主题基线，基线为零则平均分配。上方折线展示原始题目得分的时间变化；下方表格展示按当前基线重新计算的各次主题归因分数。这是原型估算方法，不是标准化教育测量。",
        "No attempt has been saved for a question tagged with this Topic.": "尚未保存带有此主题标签的题目尝试。",
        "No evidence is available for this Topic.": "该主题暂无证据。",
        "Review records across students, questions, runtime evidence, and feedback categories.": "查看不同学生和题目的运行证据及反馈类别。",
        "Review your previous attempts and tutor feedback.": "查看之前的尝试和导师反馈。",
        "Submit Attempt": "提交一次尝试", "All students": "所有学生",
        "All questions": "所有题目", "Apply": "应用筛选",
        "In progress": "进行中", "Submitted At": "提交时间",
        "Code Preview": "代码预览", "Action": "操作",
        "Runtime:": "运行状态：", "Output:": "输出比较：",
        "Runtime success means the code ran; it does not mean the answer is correct. Output match compares the configured sample, not every possible input.": "运行成功只代表代码可以执行，不代表答案正确。输出匹配只比较已设置的样例，不代表覆盖所有可能输入。",
        "Student Submission": "学生提交", "Runtime Feedback Request": "运行反馈请求",
        "Generate Feedback": "生成反馈", "View all questions": "查看全部题目",
        "Your previous code is preserved below. Edit it and submit another attempt for the same question.": "上次提交的代码已保留在下方。修改后可再次提交同一道题。",
        "No active question is available for this topic.": "这个主题目前没有可用题目。",
        "AI error:": "AI 错误：",
        "Retry this question": "重做这道题", "Jump to another question": "换一道题",
        "— you can move on to the next question.": "— 可以继续做下一道题。",
        "Program": "程序", "Structure": "结构", "Variables &": "变量与",
        "Assignment": "赋值", "Expressions &": "表达式与", "Operators": "运算符",
        "Conditionals &": "条件与", "Boolean Logic": "布尔逻辑",
        "Iteration &": "循环与", "Range": "range",
        "Functions &": "函数与", "Returns": "返回值",
        "Strings &": "字符串与", "Input/Output": "输入/输出",
        "Collections &": "集合与", "Indexing": "索引",
        "Each Topic uses an EMA (alpha=0.5) of all baseline-weighted attempt credits.": "每个主题对全部尝试的基线加权分数计算指数移动平均（EMA，alpha=0.5）。",
        "Fixed Topic Mastery": "固定主题掌握度",
        "View Profile": "查看档案", "Student profiles": "学生档案列表",
        "The page shows the exact literature category names. A-X source codes are stored internally only for traceability. Runtime status and legacy labels are excluded.": "这里显示文献中的原始类别名称。A-X 编码仅用于内部追溯；运行状态和旧版标签未计入。",
        "This table uses student question attempts only; the class totals above include other saved records. Average attempts to solve counts submissions up to the first solved attempt in each student practice run, then averages solved runs only. More attempts to solve can signal difficulty; total attempts alone can reflect popularity. Unsolved runs stay in the solve-rate denominator.": "此表仅统计学生答题尝试；上方班级总数还包括其他已保存记录。平均解决所需次数统计每轮练习到首次解决为止的提交，仅对已解决轮次求平均。解决所需次数越多可能表示题目越难；总尝试次数也可能只是反映题目受欢迎程度。未解决轮次仍计入解决率分母。",
        "Popular, easier: at least 5 attempts by 2 students, at least 75% of runs solved, and an average of at most 2 attempts to solve. Difficult: at least 3 attempts to solve on average, or at least 5 attempts with a solve rate of 50% or lower. Other attempted questions have limited evidence. A mismatch ran successfully but printed the wrong output; runtime errors are exceptions, while other failures include syntax errors and timeouts.": "热门较易题：至少两位学生共尝试 5 次、解决率不低于 75%，且平均最多 2 次解决。难题：平均至少 3 次才解决，或至少 5 次尝试而解决率不高于 50%。其余已尝试题目证据有限。输出不匹配表示程序运行成功但输出错误；运行错误是执行时异常；其他失败包括语法错误与超时。",
        "Avg to solve": "平均解决次数", "Solve rate": "解决率",
        "Runtime errors": "运行错误", "Difficult": "难题",
        "Unattempted": "无人尝试", "Popular, easier": "热门较易题",
        "Limited evidence": "证据有限"
    };
    const zhCaseFolded = new Map(
        Object.entries(zh).map(([english, chinese]) => [english.toLowerCase(), chinese])
    );

    const dynamicCopy = [
        [/^(\d+) active, (\d+) inactive$/, (_match, active, inactive) => `${active} 道启用，${inactive} 道停用`],
        [/^(\d+) normalized, (\d+) strict$/, (_match, normalized, strict) => `${normalized} 道标准化比较，${strict} 道严格比较`],
        [/^Latest (\d+) attempts per topic$/, (_match, count) => `每个主题最近 ${count} 次尝试`],
        [/^Estimated from up to the latest (\d+) saved attempts for each topic, not a standardised assessment\. Multi-topic marks are apportioned using baseline topic scores from each question's latest attempt; a zero baseline uses equal shares\. Earlier Topic credits can change when baseline scores change; this weighting suggests where to practise, but does not prove which topic caused an error\. A topic without attempts has insufficient evidence, not a score of zero\. AI feedback failures may also affect the estimate\.$/, (_match, count) => `根据每个主题最多最近 ${count} 次已保存尝试估算，并非标准化测评。多主题题目的得分按各主题的基线分数分配；基线为零时平均分配。基线分数变化时，之前分配的主题分数也可能变化；加权结果提示练习方向，但不能证明错误由哪个主题造成。没有尝试记录的主题是证据不足，不代表得零分。AI 反馈失败也可能影响估计。`],
        [/^(.*) · Recent topic-level attempt evidence$/, (_match, username) => `${username} · 各主题的近期尝试证据`],
        [/^(\d+) of the latest (\d+) attempts were unresolved\.$/, (_match, unresolved, total) => `最近 ${total} 次尝试中，有 ${unresolved} 次未解决。`],
        [/^(\d+) unresolved saved attempts$/, (_match, count) => `${count} 次尚未解决的尝试`],
        [/^(\d+) solved \/ (\d+) attempts$/, (_match, solved, total) => `${solved} 次已解决，共 ${total} 次尝试`],
        [/^(\d+)\/8 topics with evidence$/, (_match, count) => `8 个主题中有 ${count} 个有证据`],
        [/^(\d+) weighted latest question scores? averaged · (\d+) attempts$/, (_match, questions, attempts) => `${questions} 道题的最新加权分数均值 · ${attempts} 次尝试`],
        [/^Latest submission (.+)$/, (_match, date) => `最近提交于 ${date}`],
        [/^(.*) \| Latest submission (.+)$/, (_match, username, date) => `${username} | 最近提交于 ${date}`],
        [/^(\d+) attempts?$/, (_match, count) => `${count} 次尝试`],
        [/^(\d+) questions?$/, (_match, count) => `${count} 道题目`],
        [/^(\d+) students?$/, (_match, count) => `${count} 位学生`],
        [/^(\d+) solved runs?$/, (_match, count) => `${count} 轮已解决`],
        [/^(\d+) unsolved runs?$/, (_match, count) => `${count} 轮未解决`],
        [/^(\d+) students? solved$/, (_match, count) => `${count} 位学生解决`],
        [/^(\d+) other failures?$/, (_match, count) => `${count} 次其他失败`],
        [/^(\d+)\/(\d+) runs$/, (_match, solved, total) => `${solved}/${total} 轮练习`],
        [/^(\d+) of (\d+)$/, (_match, current, total) => `第 ${current} 位，共 ${total} 位`],
        [/^Prioritise (.+)$/, (_match, category) => `优先复习：${category}`],
        [/^Review (.+)$/, (_match, concept) => `复习：${zh[concept] || concept}`],
        [/^(\d+) unresolved attempts are currently grouped here\. Use this category for the next mini-review or worked debugging example\.$/, (_match, count) => `当前有 ${count} 次未解决尝试归在此类。下次可用它做简短复习或调试示例。`],
        [/^This concept appears in (\d+) unresolved attempts\. The evidence comes from saved feedback records, not a free-form model summary\.$/, (_match, count) => `这个概念出现在 ${count} 次未解决尝试中。依据来自已保存的反馈记录，不是模型自由生成的总结。`],
        [/^Retry (.+)$/, (_match, title) => `重做：${title}`],
        [/^Practising (.+)\.$/, (_match, topic) => `正在练习：${zh[topic] || topic}。`],
        [/^(.+) Attempt Timeline$/, (_match, topic) => `${zh[topic] || topic} 尝试时间线`],
        [/^(.*) · Attempt (\d+)$/, (_match, title, number) => `${title} · 第 ${number} 次尝试`],
        [/^Attempt (\d+)$/, (_match, number) => `第 ${number} 次尝试`],
        [/^Prompt: (.*)$/, (_match, value) => `提示词：${value}`],
        [/^Model: (.*)$/, (_match, value) => `模型：${value}`],
        [/^Leakage flag: (.*)$/, (_match, value) => `泄漏标记：${zh[value] || value}`],
        [/^Outcome: (.*)$/, (_match, value) => `分类结果：${value}`],
        [/^Line (\d+)$/, (_match, number) => `第 ${number} 行`],
        [/^Return code: (.*)$/, (_match, value) => `返回码：${value}`],
        [/^Execution time: (.*)$/, (_match, value) => `执行耗时：${value}`]
    ];

    const excluded = "pre, code, textarea, input, select[name=question] option, script, style, [contenteditable], [data-no-translate], .feedback-box, .question-description";
    const originalText = new WeakMap();
    const originalAttributes = new WeakMap();
    const attributeNames = ["placeholder", "title", "aria-label"];

    function translateText(node, language) {
        const parent = node.parentElement;
        if (!parent || parent.closest(excluded)) return;
        if (!originalText.has(node)) originalText.set(node, node.nodeValue);
        const original = originalText.get(node);
        const label = original.trim();
        const lookup = label.replace(/\s+/g, " ");
        const fixed = zh[lookup] || zhCaseFolded.get(lookup.toLowerCase());
        const dynamic = dynamicCopy.find(([pattern]) => pattern.test(lookup));
        if (!fixed && !dynamic) return;
        const start = original.indexOf(label);
        const translated = language === "zh"
            ? (fixed || lookup.replace(dynamic[0], dynamic[1]))
            : label;
        const value = original.slice(0, start) + translated + original.slice(start + label.length);
        if (node.nodeValue !== value) node.nodeValue = value;
    }

    function translateAttributes(element, language) {
        if (element.closest("[data-no-translate], pre, code, .feedback-box")) return;
        let originals = originalAttributes.get(element);
        if (!originals) {
            originals = {};
            for (const name of attributeNames) {
                if (element.hasAttribute(name)) originals[name] = element.getAttribute(name);
            }
            originalAttributes.set(element, originals);
        }
        for (const [name, value] of Object.entries(originals)) {
            const translated = language === "zh"
                ? (zh[value] || zhCaseFolded.get(value.toLowerCase()) || value)
                : value;
            if (element.getAttribute(name) !== translated) element.setAttribute(name, translated);
        }
    }

    function applyLanguage(language) {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
        document.title = language === "zh"
            ? originalTitle.split(" | ").map((part) => zh[part] || part).join(" | ")
            : originalTitle;
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) translateText(walker.currentNode, language);
        document.querySelectorAll("*").forEach((element) => translateAttributes(element, language));
        document.querySelectorAll("[data-ui-language]").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.uiLanguage === language));
        });
    }

    const originalTitle = document.title;
    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("pre, code, textarea, .feedback-box").forEach((element) => {
            element.setAttribute("translate", "no");
        });
        let language = "en";
        try {
            language = localStorage.getItem("feedback-ui-language") === "zh" ? "zh" : "en";
        } catch (_error) {
            // Storage can be disabled; the switch still works for this page.
        }
        applyLanguage(language);
        document.querySelectorAll("[data-ui-language]").forEach((button) => {
            button.addEventListener("click", () => {
                language = button.dataset.uiLanguage;
                try { localStorage.setItem("feedback-ui-language", language); } catch (_error) { /* optional */ }
                applyLanguage(language);
            });
        });
    });
})();
