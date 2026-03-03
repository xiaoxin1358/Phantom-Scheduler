"""
plan_tool.py —— 基于终端的交互式日程管理脚本（使用 rich 库）
"""

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from phantom_scheduler import PhantomScheduler, DAYS, SLOTS

console = Console()
scheduler = PhantomScheduler()


# ───────────────────────── 表格渲染 ─────────────────────────
def render_week_table():
    """用 rich 表格展示整周日程：列 = 周一~周日，行 = 4 个时段。"""
    table = Table(
        title="📅 Weekly Schedule",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("Time Slot", style="bold yellow", width=10)
    for day in DAYS:
        is_today = day == scheduler.current_day()
        style = "bold green" if is_today else "white"
        table.add_column(day[:3], style=style, width=16)

    for slot in SLOTS:
        row = [slot]
        for day in DAYS:
            tasks = scheduler.get_tasks(day, slot)
            cell = "\n".join(f"• {t}" for t in tasks) if tasks else "[dim]—[/dim]"
            row.append(cell)
        table.add_row(*row)

    console.print(table)


def render_today_table():
    """只显示今日日程。"""
    day = scheduler.current_day()
    cur_slot = scheduler.current_slot()
    table = Table(title=f"📌 Today: {day}", box=box.SIMPLE_HEAVY, show_lines=True)
    table.add_column("Slot", style="bold yellow", width=10)
    table.add_column("Tasks", width=50)

    for slot in SLOTS:
        tasks = scheduler.get_tasks(day, slot)
        marker = " ◀ NOW" if slot == cur_slot else ""
        cell = "\n".join(f"[{i}] {t}" for i, t in enumerate(tasks)) if tasks else "[dim]—[/dim]"
        table.add_row(f"{slot}{marker}", cell)

    console.print(table)


# ───────────────────────── 初始化规划 ─────────────────────────
def init_planning():
    """扫描 current_week.json 中所有空时段，逐个询问用户是否填入任务。"""
    empty_slots = []
    for day in DAYS:
        for slot in SLOTS:
            if not scheduler.get_tasks(day, slot):
                empty_slots.append((day, slot))

    if not empty_slots:
        console.print("[green]所有时段均已有任务，无需初始化规划。[/green]\n")
        return

    console.print(f"[yellow]检测到 {len(empty_slots)} 个空时段，开始初始规划（直接回车跳过）：[/yellow]\n")
    for day, slot in empty_slots:
        task = Prompt.ask(f"  [{day}][{slot}] 请填入要做的一件事", default="")
        if task.strip():
            scheduler.add_task(day, slot, task.strip())

    console.print("[green]初始化规划完成！[/green]\n")


# ───────────────────────── 选择任务辅助 ─────────────────────────
def choose_task(action_label: str):
    """让用户选择日期、时段和任务编号，返回 (day, slot, index) 或 None。"""
    day = scheduler.current_day()
    slot = scheduler.current_slot()

    tasks = scheduler.get_tasks(day, slot)
    if not tasks:
        console.print(f"[red]当前时段 [{day}][{slot}] 没有任务。[/red]")
        # 允许用户手动指定
        day = Prompt.ask("请输入星期", choices=DAYS, default=day)
        slot = Prompt.ask("请输入时段", choices=SLOTS, default=slot)
        tasks = scheduler.get_tasks(day, slot)
        if not tasks:
            console.print("[red]该时段没有任务。[/red]")
            return None

    console.print(f"\n[cyan]{day} / {slot} 的任务列表：[/cyan]")
    for i, t in enumerate(tasks):
        console.print(f"  [bold][{i}][/bold] {t}")

    idx = IntPrompt.ask(f"请选择要{action_label}的任务编号")
    if 0 <= idx < len(tasks):
        return day, slot, idx
    console.print("[red]编号无效。[/red]")
    return None


# ───────────────────────── 主菜单 ─────────────────────────
def main_menu():
    while True:
        console.print("\n[bold magenta]═══ Phantom Scheduler ═══[/bold magenta]")
        console.print("[1] 查看今日日程")
        console.print("[2] 完成任务 (Done)")
        console.print("[3] 平移任务 (Shift)")
        console.print("[4] 手动插入任务")
        console.print("[5] 查看整周总览")
        console.print("[0] 退出\n")

        choice = Prompt.ask("请选择", choices=["0", "1", "2", "3", "4", "5"], default="1")

        if choice == "0":
            console.print("[dim]Goodbye 👋[/dim]")
            break

        elif choice == "1":
            render_today_table()

        elif choice == "2":
            result = choose_task("完成")
            if result:
                day, slot, idx = result
                removed = scheduler.mark_done(day, slot, idx)
                if removed:
                    console.print(f"[green]✅ 已完成：{removed}[/green]")

        elif choice == "3":
            result = choose_task("平移")
            if result:
                day, slot, idx = result
                shifted = scheduler.shift_task(day, slot, idx)
                if shifted:
                    nd, ns = scheduler.next_slot(day, slot)
                    console.print(f"[yellow]➡️  已将「{shifted}」平移到 {nd}/{ns}[/yellow]")

        elif choice == "4":
            day = Prompt.ask("星期", choices=DAYS, default=scheduler.current_day())
            slot = Prompt.ask("时段", choices=SLOTS, default=scheduler.current_slot())
            task_name = Prompt.ask("任务名称")
            if task_name.strip():
                scheduler.add_task(day, slot, task_name.strip())
                console.print(f"[green]✅ 已添加到 {day}/{slot}[/green]")

        elif choice == "5":
            render_week_table()


# ───────────────────────── 入口 ─────────────────────────
if __name__ == "__main__":
    console.print("[bold cyan]Phantom Scheduler v1.0[/bold cyan] — 日程管理终端工具\n")
    render_week_table()
    init_planning()
    main_menu()
