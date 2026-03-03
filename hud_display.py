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
W, H = 500, 518

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


# ───────── HUD 窗口 ─────────
class HUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self._dashboard_proc = None

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
        by = H - 50
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

    def _shutdown_all(self):
        if self._dashboard_proc and self._dashboard_proc.poll() is None:
            self._dashboard_proc.terminate()
            try:
                self._dashboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._dashboard_proc.kill()
        self.destroy()

    # ── 刷新 ──
    def refresh(self):
        self._draw()
        self.after(REFRESH_MS, self.refresh)


# ───────── 入口 ─────────
if __name__ == "__main__":
    app = HUD()
    app.mainloop()
