#!/usr/bin/env python3
"""
tui_dashboard.py - Live Terminal UI for Linux Interrupt Scheduler.

Uses the 'rich' library to create a dynamic, multi-panel dashboard showing
the scheduler's real-time state, queue status, and performance metrics.
"""

import time
import sys
import random
import copy
from datetime import datetime

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console, Group
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich.align import Align
from rich import box

from scheduler import Scheduler, PreemptiveScheduler, load_from_proc
from interrupt_model import Interrupt
from isr_engine import generate_synthetic_stream
from metrics import MetricsReport

console = Console()

# Color mapping for categories
PRIO_COLORS = {
    "TIMER": "bold red",
    "KEYBOARD": "bold yellow",
    "NETWORK": "bold blue",
    "DISK": "bold green",
    "OTHER": "white"
}

class Dashboard:
    def __init__(self, scheduler, mode_name):
        self.scheduler = scheduler
        self.mode_name = mode_name
        self.start_time = time.time()
        self.logs = []
        self.completed_interrupts = []
        self.current_state = {
            "time": 0.0,
            "active_interrupt": None,
            "event": "Initializing...",
            "ready_queue": [],
            "stack": []
        }
        self.gantt_rows = {} # IRQ -> Gantt string

    def update_logs(self, event):
        if event:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.logs.append(f"[{timestamp}] {event}")
            if len(self.logs) > 10:
                self.logs.pop(0)

    def make_header(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            Text("Linux Interrupt Priority Scheduler Simulator", style="bold cyan"),
            Text(f"Mode: {self.mode_name} | Sim Time: {self.current_state['time']:.2f}ms", style="bold magenta"),
        )
        return Panel(grid, style="white on blue")

    def make_ready_queue(self) -> Panel:
        table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("IRQ", style="cyan")
        table.add_column("Device")
        table.add_column("Type")
        table.add_column("Prio", justify="center")
        table.add_column("Arrival")
        table.add_column("Status")

        for intr in self.current_state["ready_queue"]:
            color = PRIO_COLORS.get(intr.irq_type, "white")
            table.add_row(
                intr.irq_number,
                intr.device_name[:15],
                Text(intr.irq_type, style=color),
                str(intr.priority),
                f"{intr.arrival_time:.1f}",
                "WAITING"
            )
        return Panel(table, title="[bold]Ready Queue[/bold]", border_style="blue")

    def make_stack(self) -> Panel:
        # For preemptive mode, show the nested interrupt stack
        if not hasattr(self.scheduler, 'context_stack'):
            return Panel(Text("N/A in Non-Preemptive"), title="Interrupt Stack")
            
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Depth")
        table.add_column("IRQ")
        table.add_column("Remaining")

        for i, intr in enumerate(reversed(self.current_state.get("stack", []))):
            table.add_row(str(i+1), intr.irq_number, f"{intr.remaining_time:.1f}ms")
            
        return Panel(table, title="[bold]Nested Context Stack (LIFO)[/bold]", border_style="yellow")

    def make_cpu_status(self) -> Panel:
        intr = self.current_state["active_interrupt"]
        if not intr or intr.state != "RUNNING":
            return Panel(Align.center(Text("\n[italic]CPU IDLE[/italic]", style="dim")), title="CPU Status")

        color = PRIO_COLORS.get(intr.irq_type, "white")
        progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        
        # Calculate percentage based on burst_time and remaining_time
        # Since the scheduler is discrete, we simulate the visual countdown
        percent = ((intr.burst_time - intr.remaining_time) / intr.burst_time) * 100
        progress.add_task(f"IRQ {intr.irq_number}", total=100, completed=percent)

        details = Group(
            Text(f"Executing: {intr.irq_type} (IRQ {intr.irq_number})", style=f"bold {color}"),
            Text(f"Priority: {intr.priority} | Burst: {intr.burst_time}ms"),
            progress
        )
        return Panel(details, title="[bold]CPU Execution[/bold]", border_style="red")

    def make_metrics(self) -> Panel:
        if not self.completed_interrupts:
            return Panel(Text("No data yet..."), title="Metrics")

        # Use MetricsReport to compute current averages
        report = MetricsReport("Live", self.completed_interrupts)
        aggs = report.calculate_aggregates()
        
        table = Table.grid(padding=(0, 1))
        table.add_row("Avg Waiting:", f"[bold green]{aggs.get('avg_wait', 0):.2f}ms[/bold green]")
        table.add_row("Avg Latency:", f"[bold yellow]{aggs.get('avg_latency', 0):.2f}ms[/bold yellow]")
        table.add_row("Throughput :", f"[bold cyan]{aggs.get('throughput', 0):.2f}/100ms[/bold cyan]")
        
        return Panel(table, title="[bold]Real-time Metrics[/bold]", border_style="magenta")

    def make_logs(self) -> Panel:
        log_text = Text("\n".join(self.logs))
        return Panel(log_text, title="[bold]Context Switch Log[/bold]", border_style="white")

    def make_gantt(self) -> Panel:
        # Build ASCII Gantt lines
        width = 60
        # Update gantt rows for completed interrupts
        for intr in self.completed_interrupts:
            if intr.irq_number not in self.gantt_rows:
                # Basic representation for the dashboard
                self.gantt_rows[intr.irq_number] = f"IRQ {intr.irq_number:4} | {'#' * 10} | Done"
        
        lines = [v for k, v in sorted(self.gantt_rows.items())]
        return Panel("\n".join(lines[-5:]), title="[bold]Recent Completions (Gantt)[/bold]", border_style="green")

    def __rich__(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=10)
        )
        layout["main"].split_row(
            Layout(name="queue", ratio=2),
            Layout(name="side", ratio=1)
        )
        layout["side"].split_column(
            Layout(name="cpu", size=7),
            Layout(name="stack", ratio=1),
            Layout(name="metrics", size=6)
        )
        layout["footer"].split_row(
            Layout(name="logs", ratio=1),
            Layout(name="gantt", ratio=1)
        )

        layout["header"].update(self.make_header())
        layout["queue"].update(self.make_ready_queue())
        layout["cpu"].update(self.make_cpu_status())
        layout["stack"].update(self.make_stack())
        layout["metrics"].update(self.make_metrics())
        layout["logs"].update(self.make_logs())
        layout["gantt"].update(self.make_gantt())

        return layout

def startup_screen():
    console.clear()
    console.print(Align.center(Text("\nLinux Interrupt Priority Scheduler Dashboard", style="bold cyan underline")), style="bold")
    
    # Check /proc/interrupts
    real_data = load_from_proc()
    console.print(Align.center(f"\n[bold green]System Check:[/bold green] Loaded {len(real_data)} real interrupts from /proc/interrupts"))
    
    table = Table(title="Select Simulation Mode", box=box.DOUBLE, show_header=False)
    table.add_row("[1]", "Run with REAL System Interrupts")
    table.add_row("[2]", "Run SYNTHETIC Demo (High Preemption Chance)")
    table.add_row("[3]", "Performance COMPARISON Mode (Standard vs Preemptive)")
    table.add_row("[4]", "Real-time INTERRUPT RATE Monitor")
    table.add_row("[Q]", "Quit")
    console.print(Align.center(table))
    
    choice = console.input("[bold yellow]Enter choice: [/bold yellow]").strip().upper()
    return choice, real_data

def run_simulation(mode_choice, real_data):
    if mode_choice == '1':
        stream = real_data[:20]
        scheduler = PreemptiveScheduler()
        name = "Real System Data (Preemptive)"
    elif mode_choice == '2':
        stream = generate_synthetic_stream(12)
        scheduler = PreemptiveScheduler()
        name = "Synthetic Preemptive Demo"
    elif mode_choice == '3':
        console.print("[bold red]Comparison mode is best viewed via metrics.py for static reports.[/bold red]")
        console.print("Redirecting to Comprehensive Metrics Report...")
        time.sleep(2)
        from metrics import run_comparison
        run_comparison(8)
        return
    else:
        return

    scheduler.load_interrupts(stream)
    dashboard = Dashboard(scheduler, name)

    with Live(dashboard, refresh_per_second=10, screen=True) as live:
        # Iterate through the scheduler generator
        for state in scheduler.simulate():
            dashboard.current_state = state
            if state["event"]:
                dashboard.update_logs(state["event"])
            
            # If an interrupt finished, add it to metrics
            if "FINISH" in state["event"]:
                dashboard.completed_interrupts.append(state["active_interrupt"])
            
            # Slow down simulation to make it visible
            time.sleep(0.5) 
            
        time.sleep(2) # Show final state
    
    console.print(f"\n[bold green]Simulation Complete.[/bold green] Processed {len(dashboard.completed_interrupts)} interrupts.")
    input("Press Enter to return to menu...")

def main():
    while True:
        choice, real_data = startup_screen()
        if choice == 'Q':
            break
        try:
            run_simulation(choice, real_data)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
