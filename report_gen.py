"""
report_gen.py —— 周日程热力图可视化
读取 current_week.json，生成 7×4 热力图并保存为 weekly_report.png。
"""

import json
import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns

# 解决中文与负号显示
matplotlib.rcParams["axes.unicode_minus"] = False

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = ["AM", "PM", "EVENING", "NIGHT"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_WEEK_PATH = os.path.join(BASE_DIR, "current_week.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "weekly_report.png")


def load_data() -> dict:
    with open(CURRENT_WEEK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_matrix(data: dict) -> np.ndarray:
    """构建 5(行/时段) × 7(列/星期) 的任务数矩阵。"""
    matrix = np.zeros((len(SLOTS), len(DAYS)), dtype=int)
    for col, day in enumerate(DAYS):
        for row, slot in enumerate(SLOTS):
            tasks = data.get(day, {}).get(slot, [])
            matrix[row][col] = len(tasks)
    return matrix


def generate_heatmap(matrix: np.ndarray):
    """生成并保存热力图。"""
    # 自定义颜色映射：绿(0) → 黄(中) → 红(多)
    from matplotlib.colors import LinearSegmentedColormap
    colors = ["#27AE60", "#F1C40F", "#E74C3C"]
    cmap = LinearSegmentedColormap.from_list("schedule", colors, N=256)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap=cmap,
        xticklabels=[d[:3] for d in DAYS],
        yticklabels=SLOTS,
        linewidths=1.2,
        linecolor="#333333",
        cbar_kws={"label": "Task Count"},
        vmin=0,
        ax=ax,
    )
    ax.set_title("Weekly Schedule Heatmap", fontsize=16, fontweight="bold", pad=14)
    ax.set_xlabel("Day of Week", fontsize=12)
    ax.set_ylabel("Time Slot", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)

    plt.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)
    print(f"✅ 热力图已保存至 {OUTPUT_PATH}")


# ───────── 入口 ─────────
if __name__ == "__main__":
    data = load_data()
    matrix = build_matrix(data)
    generate_heatmap(matrix)
