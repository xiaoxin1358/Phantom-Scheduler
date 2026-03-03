"""
phantom_dashboard.py —— Streamlit 可视化日程规划看板
启动方式: streamlit run phantom_dashboard.py
"""

import json
import os
import streamlit as st

# ───────── 常量 ─────────
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_CN = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
           "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
SLOTS = ["AM", "PM", "Evening", "Night"]
SLOT_EMOJI = {"AM": "☀️", "PM": "🌤️", "Evening": "🌇", "Night": "🌙"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.json")
CURRENT_WEEK_PATH = os.path.join(BASE_DIR, "current_week.json")

SEPARATOR = " | "  # 多任务显示/编辑分隔符，认为是堆积时段


# ───────── IO 工具 ─────────
def empty_week() -> dict:
    return {day: {slot: [] for slot in SLOTS} for day in DAYS}


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return empty_week()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: str = CURRENT_WEEK_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def tasks_to_str(tasks: list) -> str:
    """列表 → 输入框显示字符串"""
    return SEPARATOR.join(tasks) if tasks else ""


def str_to_tasks(text: str) -> list:
    """输入框字符串 → 列表（兼容逗号和竖线分隔）"""
    if not text.strip():
        return []
    # 同时支持 " | " 和 "，" 和 "," 分隔
    import re
    parts = re.split(r"\s*[|,，]\s*", text.strip())
    return [p for p in parts if p]


# ───────── 页面配置 ─────────
st.set_page_config(
    page_title="Phantom Scheduler Dashboard",
    page_icon="👻",
    layout="wide",
)

st.markdown("""
<style>
    /* 紧凑排版 */
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stTextInput"] label { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ───────── Session State 初始化 ─────────
if "schedule" not in st.session_state:
    st.session_state.schedule = load_json(CURRENT_WEEK_PATH)


def refresh_from_file():
    st.session_state.schedule = load_json(CURRENT_WEEK_PATH)


def refresh_from_template():
    st.session_state.schedule = load_json(TEMPLATE_PATH)


def clear_all():
    st.session_state.schedule = empty_week()


# ───────── 顶部工具栏 ─────────
st.title("👻 Phantom Scheduler")

toolbar = st.columns([1.5, 1.5, 1.5, 5])
with toolbar[0]:
    save_clicked = st.button("💾 Save Schedule", use_container_width=True)
with toolbar[1]:
    load_tpl_clicked = st.button("📄 Load Template", use_container_width=True)
with toolbar[2]:
    clear_clicked = st.button("🗑️ Clear All", use_container_width=True)

if load_tpl_clicked:
    refresh_from_template()
    st.toast("已从模板重新加载！", icon="📄")
    st.rerun()

if clear_clicked:
    clear_all()
    st.toast("已清空所有任务！", icon="🗑️")
    st.rerun()


# ───────── 7 × 4 网格 ─────────
data = st.session_state.schedule
cols = st.columns(7)

# 用于收集用户编辑后的值
edited: dict = {day: {} for day in DAYS}

for col_idx, day in enumerate(DAYS):
    with cols[col_idx]:
        st.subheader(f"{DAY_CN[day]}")
        for slot in SLOTS:
            tasks = data.get(day, {}).get(slot, [])
            key = f"{day}__{slot}"
            value = st.text_input(
                label=f"{SLOT_EMOJI.get(slot, '')} {slot}",
                value=tasks_to_str(tasks),
                key=key,
                label_visibility="visible",
            )
            edited[day][slot] = str_to_tasks(value)


# ───────── 保存逻辑 ─────────
if save_clicked:
    save_json(edited)
    st.session_state.schedule = edited
    st.toast("日程已保存！ ✅", icon="💾")
    st.rerun()


# ───────── 底部统计 ─────────
st.divider()
total = sum(len(edited[d][s]) for d in DAYS for s in SLOTS)
busy = sum(1 for d in DAYS for s in SLOTS if len(edited[d][s]) > 1)
empty = sum(1 for d in DAYS for s in SLOTS if len(edited[d][s]) == 0)

stat_cols = st.columns(3)
stat_cols[0].metric("📋 总任务数", total)
stat_cols[1].metric("🔥 堆积时段 (>1)", busy)
stat_cols[2].metric("🟢 空闲时段", empty)
