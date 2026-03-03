"""
hud_display.py —— 极简桌面悬浮窗（tkinter）
显示当前时段任务 + 下一时段预告，30 秒自动刷新。
"""

import tkinter as tk
import json
import os
import sys
import subprocess
import webbrowser
import signal
from datetime import datetime

# ───────── 常量 ─────────
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = ["AM", "PM", "EVENING", "NIGHT"]
SLOT_HOURS = {
    "AM":      (6, 12),
    "PM":      (12, 18),
    "EVENING": (18, 22),
    "NIGHT":   (22, 24),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_WEEK_PATH = os.path.join(BASE_DIR, "current_week.json")

BG_COLOR = "#2C2C2C"
FG_COLOR = "#FFFFFF"
FG_DIM   = "#888888"
FONT     = ("Consolas", 13, "bold")
REFRESH_MS = 30_000  # 30 秒
DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_SCRIPT = os.path.join(BASE_DIR, "phantom_dashboard.py")


# ───────── 工具函数 ─────────
def current_day() -> str:
    return DAYS[datetime.now().weekday()]


def current_slot() -> str:
    h = datetime.now().hour
    for slot, (start, end) in SLOT_HOURS.items():
        if start <= h < end:
            return slot
    return "NIGHT"


def next_slot(day: str, slot: str):
    idx = SLOTS.index(slot)
    if idx < len(SLOTS) - 1:
        return day, SLOTS[idx + 1]
    day_idx = DAYS.index(day)
    return DAYS[(day_idx + 1) % 7], SLOTS[0]


def load_data() -> dict:
    if os.path.exists(CURRENT_WEEK_PATH):
        with open(CURRENT_WEEK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def format_tasks(tasks: list) -> str:
    if not tasks:
        return "（空）"
    return " | ".join(tasks)


# ───────── HUD 窗口 ─────────
class HUD(tk.Tk):
    def __init__(self):
        super().__init__()
        self._dashboard_proc = None  # Streamlit 子进程

        # 窗口属性
        self.overrideredirect(True)      # 无边框
        self.attributes("-topmost", True) # 置顶
        self.configure(bg=BG_COLOR)
        self.attributes("-alpha", 0.75)  # 半透明（0.0 全透明 ~ 1.0 不透明）

        # 初始位置：右上角偏移
        screen_w = self.winfo_screenwidth()
        self.geometry(f"+{screen_w - 620}+30")

        # 标签
        self.now_label = tk.Label(
            self, text="NOW: ...", font=FONT,
            fg=FG_COLOR, bg=BG_COLOR, anchor="w",
            padx=12, pady=4,
        )
        self.now_label.pack(fill="x")

        self.next_label = tk.Label(
            self, text="NEXT: ...", font=FONT,
            fg=FG_DIM, bg=BG_COLOR, anchor="w",
            padx=12, pady=4,
        )
        self.next_label.pack(fill="x")

        # ── 按钮栏 ──
        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(fill="x", padx=8, pady=(0, 6))

        self.open_btn = tk.Button(
            btn_frame, text="📋 打开看板", font=("Microsoft YaHei", 9),
            fg=FG_COLOR, bg="#3A7CA5", activebackground="#5AACD5",
            bd=0, padx=8, pady=2,
            command=self._open_dashboard,
        )
        self.open_btn.pack(side="left", padx=(0, 6))

        self.close_btn = tk.Button(
            btn_frame, text="✕ 关闭全部", font=("Microsoft YaHei", 9),
            fg=FG_COLOR, bg="#C0392B", activebackground="#E74C3C",
            bd=0, padx=8, pady=2,
            command=self._shutdown_all,
        )
        self.close_btn.pack(side="left")

        # 拖动支持（绑在标签上，避免与按钮冲突）
        self._drag_data = {"x": 0, "y": 0}
        for widget in (self.now_label, self.next_label):
            widget.bind("<Button-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_drag)

        # 双击标签也可打开看板
        self.now_label.bind("<Double-Button-1>", lambda e: self._open_dashboard())
        self.next_label.bind("<Double-Button-1>", lambda e: self._open_dashboard())

        # 首次刷新
        self.refresh()

    # ── 拖动 ──
    def _on_press(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    # ── Dashboard 管理 ──
    def _start_streamlit(self):
        """后台启动 Streamlit 服务（如果尚未运行）。"""
        if self._dashboard_proc and self._dashboard_proc.poll() is None:
            return  # 已在运行
        self._dashboard_proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", DASHBOARD_SCRIPT,
             "--server.headless", "true"],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    def _open_dashboard(self):
        """启动 Streamlit（若未启动）并在浏览器中打开看板。"""
        self._start_streamlit()
        # 给 Streamlit 一点启动时间后打开浏览器
        self.after(1500, lambda: webbrowser.open(DASHBOARD_URL))

    def _shutdown_all(self):
        """关闭 Streamlit 子进程并退出 HUD。"""
        if self._dashboard_proc and self._dashboard_proc.poll() is None:
            self._dashboard_proc.terminate()
            try:
                self._dashboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._dashboard_proc.kill()
        self.destroy()

    # ── 数据刷新 ──
    def refresh(self):
        try:
            data = load_data()
            day = current_day()
            slot = current_slot()
            nd, ns = next_slot(day, slot)

            now_tasks  = data.get(day, {}).get(slot, [])
            next_tasks = data.get(nd, {}).get(ns, [])

            self.now_label.config(text=f"NOW  [{slot}]:  {format_tasks(now_tasks)}")
            self.next_label.config(text=f"NEXT [{ns}]:  {format_tasks(next_tasks)}")
        except Exception as exc:
            self.now_label.config(text=f"NOW: 读取失败")
            self.next_label.config(text=str(exc)[:60])

        self.after(REFRESH_MS, self.refresh)


# ───────── 入口 ─────────
if __name__ == "__main__":
    app = HUD()
    app.mainloop()
