"""
PhantomScheduler —— 日程管理系统核心逻辑
"""

import json
import os
from datetime import datetime
from typing import List, Optional

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = ["AM", "PM", "EVENING", "NIGHT"]

# 时段对应的小时区间（左闭右开）
SLOT_HOURS = {
    "AM":      (6, 12),
    "PM":      (12, 18),
    "EVENING": (18, 22),
    "NIGHT":   (22, 24),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.json")
CURRENT_WEEK_PATH = os.path.join(BASE_DIR, "current_week.json")


class PhantomScheduler:
    """周日程管理器：加载、查询、完成、平移、添加任务。"""

    def __init__(self):
        self.data: dict = {}
        self.load_template()

    # -------------------------------------------------------- IO
    def load_template(self):
        """读取 template.json；若 current_week.json 不存在则基于模板初始化。"""
        if os.path.exists(CURRENT_WEEK_PATH):
            with open(CURRENT_WEEK_PATH, "r", encoding="utf-8") as f:
                self.data = self._ensure_week_data(json.load(f))
            self._save()
        elif os.path.exists(TEMPLATE_PATH):
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                self.data = self._ensure_week_data(json.load(f))
            self._save()
        else:
            # 既无模板也无周文件 → 生成空白数据
            self.data = self._empty_week()
            self._save()

    def _save(self):
        """将当前数据写回 current_week.json。"""
        with open(CURRENT_WEEK_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------- 辅助
    @staticmethod
    def _empty_week() -> dict:
        return {day: {slot: [] for slot in SLOTS} for day in DAYS}

    @staticmethod
    def _ensure_week_data(raw_data: dict) -> dict:
        """规范数据结构为固定 7 天 × 4 时段。"""
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

    @staticmethod
    def current_day() -> str:
        """返回今天是星期几（英文）。"""
        return DAYS[datetime.now().weekday()]

    @staticmethod
    def current_slot() -> str:
        """根据当前小时返回时段名。"""
        h = datetime.now().hour
        for slot, (start, end) in SLOT_HOURS.items():
            if start <= h < end:
                return slot
        # 0-6 点视为 NIGHT（跨日）
        return "NIGHT"

    @staticmethod
    def next_slot(day: str, slot: str):
        """返回 (next_day, next_slot)。NIGHT 之后跳到下一天 AM。"""
        idx = SLOTS.index(slot)
        if idx < len(SLOTS) - 1:
            return day, SLOTS[idx + 1]
        # NIGHT → 下一天 AM
        day_idx = DAYS.index(day)
        next_day = DAYS[(day_idx + 1) % 7]
        return next_day, SLOTS[0]

    # -------------------------------------------------------- 核心方法
    def get_tasks(self, day: str, slot: str) -> List[str]:
        """返回指定时段的任务列表。"""
        return self.data.get(day, {}).get(slot, [])

    def mark_done(self, day: str, slot: str, task_index: int) -> Optional[str]:
        """根据索引删除（完成）任务，返回被删除的任务名。"""
        tasks = self.get_tasks(day, slot)
        if 0 <= task_index < len(tasks):
            removed = tasks.pop(task_index)
            self._save()
            return removed
        return None

    def shift_task(self, day: str, slot: str, task_index: int) -> Optional[str]:
        """
        将任务从当前时段移除并追加到下一个时段。
        NIGHT → 下一天 AM。
        返回被平移的任务名。
        """
        tasks = self.get_tasks(day, slot)
        if 0 <= task_index < len(tasks):
            task = tasks.pop(task_index)
            next_day, next_slot = self.next_slot(day, slot)
            self.data[next_day][next_slot].append(task)
            self._save()
            return task
        return None

    def add_task(self, day: str, slot: str, task_name: str):
        """手动添加任务。"""
        if day not in self.data:
            self.data[day] = {s: [] for s in SLOTS}
        if slot not in self.data[day]:
            self.data[day][slot] = []
        self.data[day][slot].append(task_name)
        self._save()
