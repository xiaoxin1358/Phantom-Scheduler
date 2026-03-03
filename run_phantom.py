"""
run_phantom.py —— 一键启动 Phantom Scheduler 系统
  - HUD 悬浮窗（pythonw 后台静默运行）
  - Streamlit 可视化看板
"""

import subprocess
import sys
import os
import time
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HUD_SCRIPT = os.path.join(BASE_DIR, "hud_display.py")
DASHBOARD_SCRIPT = os.path.join(BASE_DIR, "phantom_dashboard.py")
SCHEDULER_CORE = os.path.join(BASE_DIR, "phantom_scheduler.py")
CURRENT_WEEK = os.path.join(BASE_DIR, "current_week.json")
TEMPLATE = os.path.join(BASE_DIR, "template.json")


# ───────── 环境检查 ─────────
def preflight():
    """检查必要文件并在需要时初始化 current_week.json。"""
    ok = True

    if not os.path.exists(SCHEDULER_CORE):
        print(f"[✗] 未找到核心模块: {SCHEDULER_CORE}")
        ok = False

    if not os.path.exists(HUD_SCRIPT):
        print(f"[✗] 未找到 HUD 脚本: {HUD_SCRIPT}")
        ok = False

    if not os.path.exists(DASHBOARD_SCRIPT):
        print(f"[✗] 未找到 Dashboard 脚本: {DASHBOARD_SCRIPT}")
        ok = False

    if not ok:
        print("\n缺少关键文件，无法启动。请确认项目完整性。")
        sys.exit(1)

    # 若 current_week.json 不存在，调用核心模块初始化
    if not os.path.exists(CURRENT_WEEK):
        print("[i] current_week.json 不存在，正在初始化...")
        # 导入核心模块触发自动生成
        sys.path.insert(0, BASE_DIR)
        from phantom_scheduler import PhantomScheduler
        PhantomScheduler()  # __init__ 会自动加载模板并保存
        print("[✓] current_week.json 已生成\n")
    else:
        print("[✓] current_week.json 已就绪\n")


# ───────── 查找 pythonw ─────────
def find_pythonw() -> str:
    """尝试找到 pythonw 可执行文件（Windows 静默运行）。"""
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if os.path.exists(pythonw):
        return pythonw
    # 回退到普通 python
    return sys.executable


# ───────── 启动子进程 ─────────
def main():
    print("=" * 50)
    print("  👻  Phantom Scheduler  —  System Launcher")
    print("=" * 50)
    print()

    preflight()

    # ── 启动 HUD 悬浮窗 ──
    print("正在觉醒怪盗感官 (HUD)...")
    pythonw = find_pythonw()
    hud_proc = subprocess.Popen(
        [pythonw, HUD_SCRIPT],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    print(f"  → HUD 已启动 (PID: {hud_proc.pid})")
    print()
    print("  悬浮窗操作提示：")
    print("    📋 点击「打开看板」 → 启动 Streamlit 并在浏览器打开")
    print("    ✕  点击「关闭全部」 → 关闭看板 + HUD")
    print("    🖱  拖动标签文字    → 移动悬浮窗位置")
    print("    🖱  双击标签文字    → 快速打开看板")
    print()
    print("Goodbye 👋")


if __name__ == "__main__":
    main()
