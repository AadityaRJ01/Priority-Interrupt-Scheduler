#!/usr/bin/env python3
"""
rate_visualizer.py - High-fidelity Dashboard for Linux Interrupt Rates.

Uses the 'rich' library to build a live visualization of the data provided 
by rate_monitor.py, featuring bar charts, sparklines, and event logging.
"""

import os
import time
import sys
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console, Group
from rich.text import Text
from rich.align import Align
from rich import box

from rate_monitor import InterruptRateMonitor

# System Info
KERNEL_VERSION = os.uname().release
CPU_COUNT = os.cpu_count() or "Unknown"

# Color mappings
TYPE_COLORS = {
    "TIMER": "bold red",
    "KEYBOARD": "yellow",
    "NETWORK": "cyan",
    "DISK": "green",
    "OTHER": "white"
}

class RateVisualizer:
    def __init__(self, poll_interval=1.0):
        self.monitor = InterruptRateMonitor(poll_interval=poll_interval)
        self.start_wall_time = time.time()
        self.peak_rate = {"irq": "None", "value": 0.0}
        self.total_counts = {} # irq -> total
        self.prev_rates = {} # irq -> rate
        self.event_log = []
        self.max_rate_seen = 1.0 # For bar chart scaling
        self.known_irqs = set()

    def update_stats(self, rates_dict):
        current_time_str = datetime.now().strftime("%H:%M:%S")
        
        for irq, data in rates_dict.items():
            rate = data['rate']
            
            # 1. New IRQ Detection
            if irq not in self.known_irqs:
                if self.known_irqs: # Don't log everything on first run
                    self.log_event(f"[{current_time_str}] New IRQ detected: {irq} ({data['device']})")
                self.known_irqs.add(irq)

            # 2. Spike Detection (>3x previous)
            prev_rate = self.prev_rates.get(irq, 0.0)
            if prev_rate > 5 and rate > (prev_rate * 3):
                self.log_event(f"[{current_time_str}] IRQ {irq} spike: {prev_rate:.0f} → {rate:.0f}/s ({data['device']})")

            # 3. Peak Rate tracking
            if rate > self.peak_rate["value"]:
                self.peak_rate = {"irq": irq, "value": rate}
            
            # 4. Max rate for scaling bars
            if rate > self.max_rate_seen:
                self.max_rate_seen = rate

            # 5. Total counts tracking
            self.total_counts[irq] = data['total']
            self.prev_rates[irq] = rate

    def log_event(self, msg):
        self.event_log.append(msg)
        if len(self.event_log) > 5:
            self.event_log.pop(0)

    def make_header(self, total_rate) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        grid.add_row(
            Text(f"Linux Interrupt Rate Monitor", style="bold white on blue"),
            Text(f"TOTAL: {total_rate:.1f}/s", style="bold green"),
            Text(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        )
        grid.add_row(
            Text(f"Kernel: {KERNEL_VERSION}", style="dim cyan"),
            Text(f"CPUs: {CPU_COUNT}", style="dim cyan"),
            Text("")
        )
        return Panel(grid, box=box.HORIZONTALS)

    def make_bar_chart(self, top_n) -> Panel:
        table = Table(box=box.SIMPLE, expand=True, show_header=False)
        table.add_column("IRQ", width=6)
        table.add_column("Device", width=12)
        table.add_column("Bar", ratio=1)
        table.add_column("Rate", width=10, justify="right")
        table.add_column("Sparkline", width=12)

        for irq, data in top_n:
            rate = data['rate']
            itype = data['type']
            color = TYPE_COLORS.get(itype, "white")
            
            # Bar implementation
            bar_width = 30
            filled_len = int((rate / self.max_rate_seen) * bar_width) if self.max_rate_seen > 0 else 0
            bar = "█" * filled_len + "░" * (bar_width - filled_len)
            
            spark = self.monitor.get_sparkline(irq, length=10)
            
            table.add_row(
                Text(str(irq), style=color),
                Text(data['device'][:12], style=color),
                Text(bar, style=color),
                f"{rate:>.1f}/s",
                spark
            )
        return Panel(table, title="[bold]Live Rate Activity (Top 10)[/bold]", border_style="cyan")

    def make_sidebar(self, rates_dict) -> Panel:
        uptime = int(time.time() - self.start_wall_time)
        quiet_count = len([k for k, v in rates_dict.items() if v['rate'] == 0])
        
        most_active_irq = "None"
        if self.total_counts:
            most_active_irq = max(self.total_counts, key=self.total_counts.get)

        lines = [
            f"[bold yellow]Peak session:[/bold yellow]",
            f"  IRQ {self.peak_rate['irq']} ({self.peak_rate['value']:.1f}/s)",
            "",
            f"[bold green]Most active (Total):[/bold green]",
            f"  IRQ {most_active_irq}",
            "",
            f"[bold cyan]Quiet IRQs:[/bold cyan] {quiet_count}",
            f"[bold white]Uptime:[/bold white] {uptime}s"
        ]
        return Panel("\n".join(lines), title="[bold]Session Stats[/bold]", border_style="magenta")

    def make_logs(self) -> Panel:
        log_content = "\n".join(self.event_log) if self.event_log else "Waiting for events..."
        return Panel(log_content, title="[bold]Event Log[/bold]", border_style="white")

    def run(self):
        layout = Layout()
        layout.split(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=7)
        )
        layout["main"].split_row(
            Layout(name="chart", ratio=3),
            Layout(name="sidebar", ratio=1)
        )
        
        with Live(layout, refresh_per_second=2, screen=True):
            for rates in self.monitor.start_monitoring():
                # 1. Update internal tracking
                self.update_stats(rates)
                
                # 2. Prepare data for panels
                total_rate = sum(d['rate'] for d in rates.values())
                top_10 = self.monitor.get_top_n(rates, n=10)
                
                # 3. Update Panels
                layout["header"].update(self.make_header(total_rate))
                layout["chart"].update(self.make_bar_chart(top_10))
                layout["sidebar"].update(self.make_sidebar(rates))
                layout["footer"].update(self.make_logs())

if __name__ == "__main__":
    try:
        viz = RateVisualizer(poll_interval=1.0)
        viz.run()
    except KeyboardInterrupt:
        pass
