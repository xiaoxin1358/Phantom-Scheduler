# Phantom Scheduler

一个本地运行的周计划系统，包含三套交互方式：

- 终端交互工具（Rich）
- 桌面悬浮窗 HUD（Tkinter）
- 可视化编辑看板（Streamlit）

此外提供周任务热力图导出脚本。

---

## 目录结构

- `phantom_scheduler.py`：核心日程数据结构与操作（加载、完成、平移、添加）
- `plan_tool.py`：终端交互工具（Rich UI）
- `hud_display.py`：桌面悬浮窗（显示 NOW/NEXT、可打开看板）
- `phantom_dashboard.py`：Streamlit 可视化看板（7×4 编辑）
- `run_phantom.py`：一键启动器（会检查并初始化 `current_week.json`）
- `report_gen.py`：生成 `weekly_report.png` 热力图
- `template.json`：模板周计划
- `current_week.json`：当前周计划（运行后自动维护）
- `start_phantom.bat` / `start_phantom_hidden.vbs`：Windows 快捷启动脚本

---

## 运行环境

- Python 3.9+（Windows）
- 建议使用虚拟环境

安装依赖：

```bash
pip install rich streamlit numpy matplotlib seaborn
```

> `tkinter` 通常随 Windows Python 自带。

---

## 快速开始

在项目根目录执行：

### 1) 一键启动（推荐）

```bash
python run_phantom.py
```

行为说明：

- 检查核心脚本是否存在
- 若 `current_week.json` 不存在，会自动初始化并创建
- 启动 HUD 悬浮窗

### 2) 启动终端交互工具

```bash
python plan_tool.py
```

可在终端执行：查看、完成、平移、添加任务。

### 3) 启动可视化看板

```bash
streamlit run phantom_dashboard.py
```

浏览器默认打开：`http://localhost:8501`

### 4) 生成周报热力图

```bash
python report_gen.py
```

输出文件：`weekly_report.png`

---

## 数据文件说明

### `current_week.json` 自动创建规则

- 会在以下场景自动创建：
  - 运行 `run_phantom.py` 且文件不存在
  - 或任何代码实际实例化 `PhantomScheduler()` 时
- 不会自动创建 `template.json`
- 当 `template.json` 不存在时，会用空白周结构初始化 `current_week.json`

### 数据结构

按「星期 -> 时段 -> 任务数组」组织，例如：

```json
{
  "Monday": {
    "AM": ["任务1"],
    "PM": [],
    "Evening": ["任务2"],
    "Night": []
  }
}
```

---

## Windows 启动脚本

- `start_phantom.bat`：直接用指定解释器启动 `hud_display.py`
- `start_phantom_hidden.vbs`：隐藏窗口方式调用 bat

如果你本机 Python 路径不同，请修改 `start_phantom.bat` 中解释器路径。

---

## 已知注意点

1. **时段命名存在两套写法**
   - 一部分脚本使用：`EVENING` / `NIGHT`
   - 另一部分脚本使用：`Evening` / `Night`
   - 若混用不同入口，可能导致同一时段数据显示不一致。

2. **`.gitignore` 当前忽略了所有 `*.json`**
   - 包括 `template.json` 与 `current_week.json`
   - 若希望提交模板文件，请调整 `.gitignore` 规则。

---

## 常见问题

### Q: 首次运行哪个文件会生成 JSON？

推荐运行：

```bash
python run_phantom.py
```

它会在缺失时自动创建 `current_week.json`。

### Q: 直接运行 `phantom_scheduler.py` 会生成吗？

默认不会。因为该文件没有独立执行入口；只有在其他脚本中实例化 `PhantomScheduler()` 时才会触发创建。

---

## 建议工作流

1. 用 `streamlit run phantom_dashboard.py` 进行整周编辑
2. 日常用 `run_phantom.py` 启动 HUD 跟踪 NOW/NEXT
3. 周末运行 `python report_gen.py` 导出热力图复盘
