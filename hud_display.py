"""
hud_display.py —— Persona 5 风格桌面悬浮窗
锐利斜边 · 红黑高对比 · 爆发标签 · 周历 · 时段行 · 高能量切割感
"""

import tkinter as tk
import json
import os
import sys
import subprocess
import webbrowser
import math
import random
from datetime import datetime, timedelta

# ───────── 常量 ─────────
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBR = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
SLOTS = ["AM", "PM", "Evening", "Night"]
SLOT_HOURS = {
    "AM":      (6, 12),
    "PM":      (12, 18),
    "Evening": (18, 22),
    "Night":   (22, 24),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_WEEK_PATH = os.path.join(BASE_DIR, "current_week.json")
TEMP_TODOS_PATH = os.path.join(BASE_DIR, "temp_todos.json")
REFRESH_MS = 30_000
DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_SCRIPT = os.path.join(BASE_DIR, "phantom_dashboard.py")

# ── P5 配色 ──
C_BG      = "#111111"
C_DGRAY   = "#1A1A1A"
C_MGRAY   = "#2A2A2A"
C_LGRAY   = "#888888"
C_RED     = "#E8001C"
C_DRED    = "#B80018"
C_BLUE    = "#2E7BBF"
C_DBLUE   = "#1A5A8A"
C_WHITE   = "#FFFFFF"
C_CREAM   = "#F0EBE0"

# ── 画布尺寸 ──
W, H = 500, 560

# ── 时段配色 & 图标 ──
SLOT_CFG = {
    "AM":      {"color": "#CC2222", "icon": "📝"},
    "PM":      {"color": "#BB2020", "icon": "📋"},
    "Evening": {"color": C_BLUE,    "icon": "🕐"},
    "Night":   {"color": C_DGRAY,   "icon": "🌙"},
}


# ───────── 工具函数 ─────────
def current_day() -> str:
    return DAYS[datetime.now().weekday()]

def current_slot() -> str:
    h = datetime.now().hour
    for slot, (start, end) in SLOT_HOURS.items():
        if start <= h < end:
            return slot
    return "Night"

def next_slot(day: str, slot: str):
    idx = SLOTS.index(slot)
    if idx < len(SLOTS) - 1:
        return day, SLOTS[idx + 1]
    day_idx = DAYS.index(day)
    return DAYS[(day_idx + 1) % 7], SLOTS[0]

def ensure_week_data(raw_data: dict) -> dict:
    normalized = {day: {slot: [] for slot in SLOTS} for day in DAYS}
    if not isinstance(raw_data, dict):
        return normalized
    for day in DAYS:
        day_data = raw_data.get(day, {})
        if not isinstance(day_data, dict):
            continue
        for slot in SLOTS:
            tasks = day_data.get(slot, [])
            normalized[day][slot] = list(tasks) if isinstance(tasks, list) else []
    return normalized

def load_data() -> dict:
    if os.path.exists(CURRENT_WEEK_PATH):
        with open(CURRENT_WEEK_PATH, "r", encoding="utf-8") as f:
            return ensure_week_data(json.load(f))
    return ensure_week_data({})

def normalize_temp_todos(raw) -> list:
    def as_item(text: str, done: bool = False, item_id: str = None, created_at: str = None):
        now_iso = datetime.now().isoformat(timespec="seconds")
        return {
            "id": item_id or f"todo-{int(datetime.now().timestamp() * 1000)}-{random.randint(100, 999)}",
            "text": text,
            "done": bool(done),
            "created_at": created_at or now_iso,
        }

    if isinstance(raw, dict):
        raw = raw.get("items", [])
    if isinstance(raw, str):
        raw = raw.splitlines()
    if not isinstance(raw, list):
        return []

    normalized = []
    for idx, item in enumerate(raw):
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            normalized.append(
                as_item(
                    text=text,
                    done=item.get("done", False),
                    item_id=str(item.get("id") or f"todo-migrated-{idx}"),
                    created_at=item.get("created_at"),
                )
            )
            continue
        if item is None:
            continue
        text = str(item).strip()
        if text:
            normalized.append(as_item(text=text))
    return normalized

def load_temp_todos() -> list:
    if not os.path.exists(TEMP_TODOS_PATH):
        return []
    try:
        with open(TEMP_TODOS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return normalize_temp_todos(raw)

def save_temp_todos(items: list):
    payload = {
        "items": normalize_temp_todos(items),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(TEMP_TODOS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def create_temp_item(text: str, done: bool = False) -> dict:
    return {
        "id": f"todo-{int(datetime.now().timestamp() * 1000)}-{random.randint(100, 999)}",
        "text": text,
        "done": bool(done),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

def format_tasks(tasks: list) -> str:
    if not tasks:
        return "—"
    return " | ".join(tasks)

def get_week_dates():
    """返回本周 Mon-Sun 的日期数字列表。"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i)).day for i in range(7)]


# ───────── 绘制辅助 ─────────
def draw_pixel_star(canvas, cx, cy, size, color):
    s = size
    pts = []
    for i in range(5):
        ao = math.radians(-90 + i * 72)
        ai = math.radians(-90 + i * 72 + 36)
        pts.extend([cx + s * math.cos(ao), cy + s * math.sin(ao)])
        pts.extend([cx + s * 0.4 * math.cos(ai), cy + s * 0.4 * math.sin(ai)])
    canvas.create_polygon(pts, fill=color, outline="")


def make_burst_pts(x, y, w, h, spike=7, seed=0):
    """生成矩形周围锯齿/爆发边缘的多边形点列表。"""
    random.seed(seed)
    pts = []
    # 上边
    for i in range(28):
        t = i / 27
        px = x + t * w
        dy = (-spike if i % 2 == 0 else spike * 0.3) * random.uniform(0.5, 1.0)
        pts.extend([px, y + dy])
    # 右边
    for i in range(1, 9):
        t = i / 8
        py = y + t * h
        dx = (spike if i % 2 == 0 else -spike * 0.3) * random.uniform(0.5, 1.0)
        pts.extend([x + w + dx, py])
    # 下边
    for i in range(28):
        t = i / 27
        px = x + w - t * w
        dy = (spike if i % 2 == 0 else -spike * 0.3) * random.uniform(0.5, 1.0)
        pts.extend([px, y + h + dy])
    # 左边
    for i in range(1, 8):
        t = i / 8
        py = y + h - t * h
        dx = (-spike if i % 2 == 0 else spike * 0.3) * random.uniform(0.5, 1.0)
        pts.extend([x + dx, py])
    return pts


def draw_cityscape(canvas, x, y, w, h):
    """在指定区域绘制简化城市剪影。"""
    buildings = [
        (0.00, 0.30), (0.04, 0.65), (0.10, 0.45), (0.16, 0.80),
        (0.22, 0.55), (0.30, 0.90), (0.38, 0.50), (0.46, 0.72),
        (0.54, 0.60), (0.62, 0.85), (0.70, 0.48), (0.78, 0.70),
        (0.86, 0.55), (0.93, 0.40), (1.00, 0.30),
    ]
    pts = [x, y + h]
    for bx, bh in buildings:
        pts.extend([x + w * bx, y + h * (1 - bh)])
    pts.extend([x + w, y + h])
    canvas.create_polygon(pts, fill="#0A1828", outline="")


def draw_moon(canvas, cx, cy, r):
    """绘制新月。"""
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#DDCC77", outline="")
    canvas.create_oval(cx - r + 5, cy - r - 3, cx + r + 5, cy + r - 3,
                       fill=SLOT_CFG["Night"]["color"], outline="")


def draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill, outline, width=1):
    r = max(2, min(r, int((x2 - x1) / 2), int((y2 - y1) / 2)))
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=outline, width=width)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=outline, width=width)
    canvas.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=fill, outline=outline, width=width)
    canvas.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=fill, outline=outline, width=width)
    canvas.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=fill, outline=outline, width=width)
    canvas.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=fill, outline=outline, width=width)


class RemindersWindow(tk.Toplevel):
    def __init__(self, parent, on_change, on_close=None):
        super().__init__(parent)
        self._on_change = on_change
        self._on_close = on_close
        self.items = load_temp_todos()

        self.title("提醒事项")
        self.geometry("440x560+120+120")
        self.configure(bg="#F2F2F7")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._pending_var = tk.StringVar(value="待办 0")
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        header = tk.Frame(self, bg="#F2F2F7")
        header.pack(fill="x", padx=14, pady=(12, 8))

        tk.Label(
            header,
            text="提醒事项",
            font=("Microsoft YaHei", 14, "bold"),
            fg="#1C1C1E",
            bg="#F2F2F7",
        ).pack(side="left")

        tk.Label(
            header,
            textvariable=self._pending_var,
            font=("Microsoft YaHei", 10),
            fg="#636366",
            bg="#F2F2F7",
        ).pack(side="right")

        list_card = tk.Frame(self, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E5E5EA")
        list_card.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._listbox = tk.Listbox(
            list_card,
            font=("Microsoft YaHei", 11),
            bg="#FFFFFF",
            fg="#1C1C1E",
            selectbackground="#E5F1FF",
            selectforeground="#1C1C1E",
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
        )
        self._listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        scrollbar = tk.Scrollbar(list_card, command=self._listbox.yview)
        scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 8))
        self._listbox.configure(yscrollcommand=scrollbar.set)

        actions = tk.Frame(self, bg="#F2F2F7")
        actions.pack(fill="x", padx=14, pady=(0, 8))

        tk.Button(
            actions,
            text="切换完成",
            command=self._toggle_done,
            bg="#FFFFFF",
            fg="#0A84FF",
            activebackground="#EAF3FF",
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions,
            text="删除选中",
            command=self._delete_selected,
            bg="#FFFFFF",
            fg="#FF3B30",
            activebackground="#FFF0EF",
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side="left")

        add_card = tk.Frame(self, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E5E5EA")
        add_card.pack(fill="x", padx=14, pady=(0, 14))

        tk.Label(
            add_card,
            text="快速添加（每行一项）",
            font=("Microsoft YaHei", 9),
            fg="#636366",
            bg="#FFFFFF",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self._input = tk.Text(
            add_card,
            height=5,
            font=("Microsoft YaHei", 10),
            bg="#FFFFFF",
            fg="#1C1C1E",
            insertbackground="#1C1C1E",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#D1D1D6",
            highlightcolor="#0A84FF",
        )
        self._input.pack(fill="x", padx=8, pady=(0, 8))

        foot = tk.Frame(add_card, bg="#FFFFFF")
        foot.pack(fill="x", padx=8, pady=(0, 8))

        tk.Button(
            foot,
            text="添加多行",
            command=self._add_lines,
            bg="#0A84FF",
            fg="#FFFFFF",
            activebackground="#006BE0",
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side="right")

        tk.Button(
            foot,
            text="关闭",
            command=self._close,
            bg="#FFFFFF",
            fg="#1C1C1E",
            activebackground="#EFEFF4",
            relief="flat",
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side="right", padx=(0, 8))

    def _refresh_list(self):
        self._listbox.delete(0, tk.END)
        for item in self.items:
            mark = "✓" if item.get("done", False) else "○"
            self._listbox.insert(tk.END, f"{mark}  {item.get('text', '')}")
        pending = sum(1 for item in self.items if not item.get("done", False))
        self._pending_var.set(f"待办 {pending}")

    def _persist(self):
        save_temp_todos(self.items)
        if callable(self._on_change):
            self._on_change(self.items)

    def _selected_index(self):
        selected = self._listbox.curselection()
        if not selected:
            return None
        return selected[0]

    def _toggle_done(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.items[idx]["done"] = not bool(self.items[idx].get("done", False))
        self._persist()
        self._refresh_list()
        self._listbox.selection_set(idx)

    def _delete_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.items.pop(idx)
        self._persist()
        self._refresh_list()

    def _add_lines(self):
        raw = self._input.get("1.0", "end-1c")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return
        for line in lines:
            self.items.append(create_temp_item(line, done=False))
        self._input.delete("1.0", "end")
        self._persist()
        self._refresh_list()

    def _close(self):
        if callable(self._on_close):
            self._on_close()
        self.destroy()


# ───────── HUD 窗口 ─────────
class HUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self._dashboard_proc = None
        self._temp_todos = load_temp_todos()
        self._reminders_window = None

        # 窗口属性
        self.overrideredirect(True)
        self.attributes("-topmost", False)
        self.attributes("-alpha", 0.95)
        self.configure(bg="#000000")
        self._trans = "#010101"
        self.wm_attributes("-transparentcolor", self._trans)

        sw = self.winfo_screenwidth()
        self.geometry(f"{W}x{H}+{sw - W - 30}+20")

        self.canvas = tk.Canvas(self, width=W, height=H,
                                bg=self._trans, highlightthickness=0)
        self.canvas.pack()

        self._drag = {"x": 0, "y": 0}
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Double-Button-1>", lambda e: self._open_dashboard())

        # 按钮热区 (后续在 _draw 中设定)
        self._btn_open = (0, 0, 0, 0)
        self._btn_reminders = (0, 0, 0, 0)
        self._btn_close = (0, 0, 0, 0)

        self.refresh()

    # ═══════════════════ 绘制主流程 ═══════════════════
    def _draw(self):
        c = self.canvas
        c.delete("all")

        data = load_data()
        day = current_day()
        slot = current_slot()
        nd, ns = next_slot(day, slot)
        now_tasks  = data.get(day, {}).get(slot, [])
        next_tasks = data.get(nd, {}).get(ns, [])
        now_text  = format_tasks(now_tasks)
        next_text = format_tasks(next_tasks)

        # ── 1. 背景 ──
        self._draw_bg(c)

        # ── 2. NOW 爆发标签 ──
        self._draw_burst_banner(c, 15, 12, W - 30, 60, C_RED,
                                f"NOW:  {now_text}", seed=101)

        # ── 3. NEXT 爆发标签 ──
        self._draw_burst_banner(c, 25, 82, W - 50, 50, C_BLUE,
                                f"NEXT:  {next_text}", seed=202)

        # ── 4. 周历条 ──
        self._draw_calendar(c, day)

        # ── 5. 时段行 ──
        self._draw_slots(c, day, slot, data)

        # ── 6. 按钮 ──
        self._draw_buttons(c)

        # ── 7. 装饰星星 ──
        self._draw_stars(c)

    # ─────────── 背景 ───────────
    def _draw_bg(self, c):
        # 主面板多边形
        c.create_polygon(
            8, 4,  W - 4, 6,  W - 2, H - 6,  6, H - 2,
            fill=C_BG, outline="#333333", width=2,
        )
        # 散布几何碎片装饰
        random.seed(77)
        for _ in range(18):
            gx = random.randint(10, W - 10)
            gy = random.randint(10, H - 10)
            gs = random.randint(12, 35)
            sides = random.choice([3, 4])
            a0 = random.uniform(0, math.pi)
            pts = []
            for v in range(sides):
                a = a0 + v * 2 * math.pi / sides
                pts.extend([gx + gs * math.cos(a), gy + gs * math.sin(a)])
            c.create_polygon(pts, fill=random.choice([C_DGRAY, C_MGRAY, "#1A0005"]),
                             outline="")
        # 边角红色三角装饰
        c.create_polygon(10, H - 5, 10, H - 50, 55, H - 5, fill=C_DRED, outline="")
        c.create_polygon(W - 10, 6, W - 10, 50, W - 55, 6, fill=C_DRED, outline="")

    # ─────────── 爆发标签 ───────────
    def _draw_burst_banner(self, c, x, y, w, h, fill_color, text, seed=0):
        # 白色锯齿外边
        burst_pts = make_burst_pts(x - 4, y - 4, w + 8, h + 8, spike=8, seed=seed)
        c.create_polygon(burst_pts, fill=C_WHITE, outline="")

        # 内部彩色斜切填充
        sk = 10
        c.create_polygon(
            x + sk,     y + 3,
            x + w - 2,  y + 1,
            x + w - sk,  y + h - 3,
            x + 2,      y + h - 1,
            fill=fill_color, outline="",
        )

        # 半色调网点纹理（用小线条模拟）
        for i in range(x + sk + 5, x + w - sk, 14):
            c.create_line(i, y + 5, i, y + h - 5, fill="#333333", width=1)

        # 文字（截断防溢出）
        display = text if len(text) <= 32 else text[:30] + "…"
        c.create_text(x + w // 2, y + h // 2,
                      text=display,
                      font=("Impact", 15, "bold"),
                      fill=C_WHITE, anchor="center")

    # ─────────── 周历 ───────────
    def _draw_calendar(self, c, today_name):
        y0 = 142
        today_idx = DAYS.index(today_name)
        dates = get_week_dates()
        col_w = (W - 50) // 7
        x0 = 25

        # 底色条
        c.create_polygon(
            x0 - 5, y0 - 4,  x0 + 7 * col_w + 8, y0 - 6,
            x0 + 7 * col_w + 5, y0 + 62,  x0 - 8, y0 + 60,
            fill=C_DGRAY, outline="#333333", width=1,
        )

        for i in range(7):
            cx = x0 + i * col_w + col_w // 2
            is_today = (i == today_idx)
            is_sun = (i == 6)

            # ── 星期名 ──
            if is_today:
                # 红色高亮背景
                c.create_rectangle(cx - col_w // 2 + 3, y0,
                                   cx + col_w // 2 - 3, y0 + 22,
                                   fill=C_RED, outline="")
            c.create_text(cx, y0 + 11, text=DAY_ABBR[i],
                          font=("Impact", 10, "bold"),
                          fill=C_WHITE if is_today else "#777777")

            # ── 日期方块 ──
            bx1 = cx - col_w // 2 + 4
            bx2 = cx + col_w // 2 - 4
            by1 = y0 + 26
            by2 = y0 + 56

            c.create_rectangle(bx1, by1, bx2, by2,
                               fill=C_RED if is_today else "#111111",
                               outline="#444444", width=1)

            # 日期文字
            if is_today:
                txt_color = C_WHITE
            elif is_sun:
                txt_color = C_RED
            else:
                txt_color = C_WHITE

            c.create_text(cx, (by1 + by2) // 2, text=str(dates[i]),
                          font=("Impact", 15, "bold"), fill=txt_color)

    # ─────────── 时段行 ───────────
    def _draw_slots(self, c, today, cur_slot, data):
        y0 = 215
        slot_h = 48
        gap = 4
        label_w = 120

        for idx, slot_name in enumerate(SLOTS):
            y = y0 + idx * (slot_h + gap)
            tasks = data.get(today, {}).get(slot_name, [])
            task_text = format_tasks(tasks)
            is_cur = (slot_name == cur_slot)
            cfg = SLOT_CFG[slot_name]
            color = cfg["color"]
            icon = cfg["icon"]
            sk = 8

            # ── 左侧图标+名称区 ──
            c.create_polygon(
                18, y,  18 + label_w + sk, y,
                18 + label_w, y + slot_h,  18, y + slot_h,
                fill="#111111", outline="#333333", width=1,
            )
            # 图标
            c.create_text(42, y + slot_h // 2,
                          text=icon, font=("Segoe UI Emoji", 15))
            # 时段名
            c.create_text(72, y + slot_h // 2,
                          text=slot_name.upper(),
                          font=("Impact", 11, "bold"),
                          fill=C_CREAM, anchor="w")

            # ── 右侧任务条 ──
            rx = 18 + label_w + 4
            rw = W - rx - 18
            c.create_polygon(
                rx + sk, y - 1,
                rx + rw, y + 1,
                rx + rw - sk, y + slot_h + 1,
                rx, y + slot_h - 1,
                fill=color, outline="",
            )

            # Evening 特殊：城市剪影
            if slot_name == "Evening":
                draw_cityscape(c, rx + sk, y + 2, rw - sk * 2, slot_h - 4)

            # Night 特殊：月亮
            if slot_name == "Night":
                draw_moon(c, rx + rw - 30, y + slot_h // 2, 10)

            # 当前时段指示箭头
            if is_cur:
                ax = 12
                ay = y + slot_h // 2
                c.create_polygon(ax, ay - 7, ax + 9, ay, ax, ay + 7,
                                 fill=C_RED, outline="")

            # 任务文字
            display = task_text if len(task_text) <= 25 else task_text[:23] + "…"
            c.create_text(rx + sk + 12, y + slot_h // 2,
                          text=display,
                          font=("Impact", 13, "bold"),
                          fill=C_WHITE, anchor="w")

    # ─────────── 按钮 ───────────
    def _draw_buttons(self, c):
        by = H - 92
        bh = 36

        # ── 左：打开看板（蓝色）──
        lx1, lx2 = 25, 230
        c.create_polygon(
            lx1, by,  lx2, by - 4,  lx2 + 5, by + bh + 2,  lx1 + 5, by + bh,
            fill=C_DBLUE, outline=C_BLUE, width=2,
        )
        c.create_polygon(
            lx1 + 2, by + 2,  lx2 - 2, by - 2,  lx2 - 1, by + bh // 2,
            lx1 + 3, by + bh // 2,
            fill=C_BLUE, outline="",
        )
        c.create_text((lx1 + lx2) // 2 - 5, by + bh // 2,
                      text="📁  打开看板",
                      font=("Microsoft YaHei", 11, "bold"), fill=C_WHITE)
        self._btn_open = (lx1, by - 4, lx2 + 5, by + bh + 2)

        # ── 右：关闭全部（红色）──
        rx1, rx2 = 260, W - 25
        c.create_polygon(
            rx1, by - 4,  rx2, by,  rx2 - 5, by + bh,  rx1 - 5, by + bh + 2,
            fill=C_DRED, outline=C_RED, width=2,
        )
        c.create_polygon(
            rx1 + 2, by - 2,  rx2 - 2, by + 2,  rx2 - 3, by + bh // 2,
            rx1 + 1, by + bh // 2,
            fill=C_RED, outline="",
        )
        c.create_text((rx1 + rx2) // 2, by + bh // 2,
                      text="✕  关闭全部",
                      font=("Microsoft YaHei", 11, "bold"), fill=C_WHITE)
        self._btn_close = (rx1 - 5, by - 4, rx2, by + bh + 2)

        # ── 下：打开提醒事项（苹果风格）──
        ty = H - 46
        tx1, tx2 = 25, W - 25
        draw_rounded_rect(c, tx1, ty, tx2, ty + 30, 12,
                  fill="#F2F2F7", outline="#D1D1D6", width=1)
        c.create_text((tx1 + tx2) // 2, ty + 15,
                  text="📝  打开提醒事项",
                  font=("Microsoft YaHei", 10, "bold"), fill="#0A84FF")
        self._btn_reminders = (tx1, ty, tx2, ty + 30)

    # ─────────── 临时代办 ───────────
    def _ensure_temp_editor(self):
        if self._temp_editor is None:
            self._temp_editor = tk.Text(
                self,
                font=("Microsoft YaHei", 10),
                bg="#FFFFFF",
                fg="#1C1C1E",
                insertbackground="#1C1C1E",
                relief="flat",
                bd=1,
                highlightthickness=1,
                highlightbackground="#D1D1D6",
                highlightcolor="#0A84FF",
                padx=8,
                pady=6,
                undo=True,
            )
            if self._temp_editor_cache:
                self._temp_editor.insert("1.0", self._temp_editor_cache)

    def _hide_temp_editor(self):
        if self._temp_editor is not None:
            self._temp_editor.place_forget()

    def _draw_temp_todos(self, c):
        px1, py1, px2, py2 = 18, H - 184, W - 18, H - 18
        self._temp_panel_rect = (px1, py1, px2, py2)
        self._todo_check_hits = {}
        self._todo_delete_hits = {}

        draw_rounded_rect(c, px1, py1, px2, py2, 14,
                          fill="#F2F2F7", outline="#D1D1D6", width=1)

        c.create_text(px1 + 14, py1 + 19,
                      text="提醒事项",
                      font=("SF Pro Display", 12, "bold"),
                      fill="#1C1C1E", anchor="w")

        pending = sum(1 for item in self._temp_todos if not item.get("done", False))
        c.create_text(px2 - 100, py1 + 19,
                      text=f"待办 {pending}",
                      font=("Microsoft YaHei", 9),
                      fill="#636366", anchor="w")

        # 展开/收起按钮
        tx1, tx2 = px2 - 92, px2 - 12
        ty1, ty2 = py1 + 8, py1 + 30
        draw_rounded_rect(c, tx1, ty1, tx2, ty2, 10,
                          fill="#FFFFFF", outline="#D1D1D6", width=1)
        c.create_text((tx1 + tx2) // 2, (ty1 + ty2) // 2,
                      text="展开" if not self._temp_expanded else "收起",
                      font=("Microsoft YaHei", 9, "bold"), fill="#0A84FF")
        self._btn_temp_toggle = (tx1, ty1, tx2, ty2)

        list_x1, list_y1 = px1 + 10, py1 + 36
        list_x2, list_y2 = px2 - 10, py2 - 86
        draw_rounded_rect(c, list_x1, list_y1, list_x2, list_y2, 12,
                          fill="#FFFFFF", outline="#E5E5EA", width=1)

        row_h = 30
        visible = max(1, (list_y2 - list_y1 - 8) // row_h)
        shown_items = self._temp_todos[:visible]

        if not shown_items:
            c.create_text((list_x1 + list_x2) // 2, (list_y1 + list_y2) // 2,
                          text="暂无提醒，展开后可批量新增",
                          font=("Microsoft YaHei", 10), fill="#8E8E93")
        else:
            for idx, item in enumerate(shown_items):
                iy = list_y1 + 6 + idx * row_h
                cy = iy + row_h // 2

                cx = list_x1 + 16
                c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8,
                              fill="#0A84FF" if item.get("done", False) else "#FFFFFF",
                              outline="#0A84FF" if item.get("done", False) else "#C7C7CC",
                              width=1)
                if item.get("done", False):
                    c.create_text(cx, cy, text="✓", font=("Microsoft YaHei", 9, "bold"), fill="#FFFFFF")
                self._todo_check_hits[item["id"]] = (cx - 10, cy - 10, cx + 10, cy + 10)

                text = str(item.get("text", "")).strip()
                display = text if len(text) <= 26 else text[:24] + "…"
                t_color = "#8E8E93" if item.get("done", False) else "#1C1C1E"
                c.create_text(list_x1 + 34, cy, text=display,
                              font=("Microsoft YaHei", 10), fill=t_color, anchor="w")
                if item.get("done", False):
                    c.create_line(list_x1 + 34, cy, list_x1 + 34 + min(280, len(display) * 9), cy,
                                  fill="#C7C7CC", width=1)

                dx = list_x2 - 16
                c.create_oval(dx - 9, cy - 9, dx + 9, cy + 9,
                              fill="#FFF1F0", outline="#FFCCC7", width=1)
                c.create_text(dx, cy, text="×", font=("Microsoft YaHei", 9, "bold"), fill="#FF3B30")
                self._todo_delete_hits[item["id"]] = (dx - 10, cy - 10, dx + 10, cy + 10)

                if idx < len(shown_items) - 1:
                    c.create_line(list_x1 + 32, iy + row_h, list_x2 - 12, iy + row_h,
                                  fill="#EFEFF4", width=1)

            hidden = len(self._temp_todos) - len(shown_items)
            if hidden > 0:
                c.create_text(list_x2 - 12, list_y2 - 12,
                              text=f"+{hidden} 条未显示",
                              font=("Microsoft YaHei", 9), fill="#8E8E93", anchor="e")

        if self._temp_expanded:
            self._ensure_temp_editor()
            ex1, ey1 = px1 + 12, py2 - 76
            ew, eh = (px2 - px1) - 24, 40
            self._temp_editor.place(x=ex1, y=ey1, width=ew, height=eh)

            c.create_text(px1 + 14, py2 - 84,
                          text="快速添加（每行一项）",
                          font=("Microsoft YaHei", 9), fill="#636366", anchor="w")

            sx1, sx2 = px2 - 178, px2 - 92
            cx1, cx2 = px2 - 86, px2 - 12
            by1, by2 = py2 - 30, py2 - 8

            draw_rounded_rect(c, sx1, by1, sx2, by2, 10,
                              fill="#0A84FF", outline="#0A84FF", width=1)
            c.create_text((sx1 + sx2) // 2, (by1 + by2) // 2,
                          text="保存", font=("Microsoft YaHei", 9, "bold"), fill=C_WHITE)
            self._btn_temp_save = (sx1, by1, sx2, by2)

            draw_rounded_rect(c, cx1, by1, cx2, by2, 10,
                              fill="#FFFFFF", outline="#D1D1D6", width=1)
            c.create_text((cx1 + cx2) // 2, (by1 + by2) // 2,
                          text="取消", font=("Microsoft YaHei", 9, "bold"), fill="#1C1C1E")
            self._btn_temp_cancel = (cx1, by1, cx2, by2)
        else:
            self._hide_temp_editor()
            self._btn_temp_save = (0, 0, 0, 0)
            self._btn_temp_cancel = (0, 0, 0, 0)
            c.create_text(px1 + 12, py2 - 18,
                          text="提示：展开后可勾选、删除，并支持每行新增",
                          font=("Microsoft YaHei", 9),
                          fill="#8E8E93", anchor="w")

    # ─────────── 装饰星星 ───────────
    def _draw_stars(self, c):
        random.seed(42)
        positions = [
            (30, 8), (W - 40, 10), (55, 3), (W - 65, 5),
            (W // 2 - 55, 7), (W // 2 + 50, 4),
            (20, H - 58), (W - 30, H - 55),
            (15, 140), (W - 20, 138),
        ]
        for i, (sx, sy) in enumerate(positions):
            clr = C_RED if i % 2 == 0 else C_WHITE
            draw_pixel_star(c, sx, sy, 4 + (i % 3), clr)

    # ═══════════════════ 交互 ═══════════════════
    def _on_click(self, event):
        x, y = event.x, event.y
        # 按钮检测
        bx1, by1, bx2, by2 = self._btn_open
        if bx1 <= x <= bx2 and by1 <= y <= by2:
            self._open_dashboard()
            return
        bx1, by1, bx2, by2 = self._btn_reminders
        if bx1 <= x <= bx2 and by1 <= y <= by2:
            self._open_reminders_window()
            return
        bx1, by1, bx2, by2 = self._btn_close
        if bx1 <= x <= bx2 and by1 <= y <= by2:
            self._shutdown_all()
            return

        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag["x"]
        dy = event.y - self._drag["y"]
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

    # ── Dashboard ──
    def _start_streamlit(self):
        if self._dashboard_proc and self._dashboard_proc.poll() is None:
            return
        self._dashboard_proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", DASHBOARD_SCRIPT,
             "--server.headless", "true"],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    def _open_dashboard(self):
        self._start_streamlit()
        self.after(1500, lambda: webbrowser.open(DASHBOARD_URL))

    def _on_reminders_changed(self, items):
        self._temp_todos = normalize_temp_todos(items)

    def _on_reminders_closed(self):
        self._reminders_window = None

    def _open_reminders_window(self):
        if self._reminders_window is not None:
            try:
                if self._reminders_window.winfo_exists():
                    self._reminders_window.focus_force()
                    self._reminders_window.lift()
                    return
            except tk.TclError:
                self._reminders_window = None
        self._reminders_window = RemindersWindow(
            self,
            self._on_reminders_changed,
            on_close=self._on_reminders_closed,
        )

    def _shutdown_all(self):
        if self._dashboard_proc and self._dashboard_proc.poll() is None:
            self._dashboard_proc.terminate()
            try:
                self._dashboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._dashboard_proc.kill()
        if self._reminders_window and self._reminders_window.winfo_exists():
            self._reminders_window.destroy()
            self._reminders_window = None
        self.destroy()

    # ── 刷新 ──
    def refresh(self):
        self._draw()
        self.after(REFRESH_MS, self.refresh)


# ───────── 入口 ─────────
if __name__ == "__main__":
    app = HUD()
    app.mainloop()
