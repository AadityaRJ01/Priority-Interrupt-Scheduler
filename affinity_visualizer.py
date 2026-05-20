#!/usr/bin/env python3
"""
affinity_visualizer.py - Rich-based CPU Affinity & SMP Dashboard

This module provides a terminal user interface to visualize the relationship 
between hardware interrupts, CPU cores, and scheduling efficiency.
"""

import os
import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

from proc_reader import read_interrupts
from affinity_reader import get_all_affinities, get_cpu_count, get_per_cpu_irq_load
from rate_monitor import InterruptRateMonitor
from smp_scheduler import compare_modes
from scheduler import load_from_proc

class AffinityVisualizer:
    def __init__(self):
        self.console = Console()
        self.cpu_count = get_cpu_count()
        self.rate_monitor = InterruptRateMonitor(poll_interval=0.5)

    def get_system_info(self):
        """Fetches basic kernel and hardware info."""
        try:
            kernel = os.uname().release
        except:
            kernel = "Unknown"
        
        raw_intrs = read_interrupts()
        irq_count = len([i for i in raw_intrs if i['irq'].isdigit()])
        
        return {
            "kernel": kernel,
            "cpus": self.cpu_count,
            "irqs": irq_count
        }

    def fetch_data(self):
        """Gathers data from all modules for the dashboard."""
        # 1. Get rates (short poll to get baseline)
        rates_gen = self.rate_monitor.start_monitoring()
        rates = next(rates_gen) 
        
        # 2. Get affinities
        irq_ids = [k for k in rates.keys() if k.isdigit()]
        affinities = get_all_affinities(irq_ids)
        
        # 3. Get load
        per_cpu_load = get_per_cpu_irq_load(affinities, rates)
        
        # 4. Run SMP comparison
        interrupts = load_from_proc()
        comparison = compare_modes(interrupts, affinities)
        
        return {
            "rates": rates,
            "affinities": affinities,
            "load": per_cpu_load,
            "comparison": comparison
        }

    def create_header(self, info):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        grid.add_row(
            Text(f"CPU Affinity & SMP Interrupt Distribution", style="bold cyan"),
            Text(f"Kernel: {info['kernel']} | CPUs: {info['cpus']} | IRQs: {info['irqs']}", style="dim")
        )
        return Panel(grid, style="white")

    def create_affinity_grid(self, rates, affinities):
        table = Table(title="Top 15 Active IRQ Affinities", box=None, padding=(0, 1))
        table.add_column("IRQ & Device", style="cyan", width=35)
        for i in range(self.cpu_count):
            table.add_column(f"CPU{i}", justify="center")
        
        # Sort by rate and take top 15
        sorted_rates = sorted(rates.items(), key=lambda x: x[1]['rate'], reverse=True)
        top_15 = sorted_rates[:15]
        
        for irq_id, rdata in top_15:
            if irq_id not in affinities: continue
            
            aff = affinities[irq_id]
            is_pinned = aff['is_pinned']
            row_style = "yellow" if is_pinned else "white"
            
            label = f"IRQ {irq_id:<3} {rdata['device'][:18]:<18} {rdata['rate']:>6.1f}/s"
            
            row_values = []
            for cpu_idx in range(self.cpu_count):
                if cpu_idx in aff['cpus']:
                    row_values.append(Text("██", style="cyan"))
                else:
                    row_values.append(Text("░░", style="dim"))
            
            table.add_row(label, *row_values, style=row_style)
            
        return Panel(table, title="[bold]Affinity Grid[/bold]")

    def create_load_chart(self, load):
        max_load = max(load.values()) if load else 1
        if max_load == 0: max_load = 1
        
        chart_table = Table(box=None, show_header=False)
        for cpu_idx, rate in load.items():
            percentage = (rate / max_load) * 100
            bar_width = int(percentage / 3.33) # 30 char wide max
            
            if percentage > 70: color = "red"
            elif percentage > 40: color = "yellow"
            else: color = "green"
            
            bar = "█" * bar_width + "░" * (30 - bar_width)
            chart_table.add_row(
                f"CPU{cpu_idx:<2}",
                Text(bar, style=color),
                f"{rate:>8.1f} /s"
            )
            
        return Panel(chart_table, title="[bold]Per-CPU Interrupt Load[/bold]")

    def create_comparison_table(self, comparison):
        table = Table(box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Pinned", justify="right")
        table.add_column("Balanced", justify="right")
        table.add_column("Worst Case", justify="right")
        
        metrics = [
            ("Avg Latency (ms)", "avg_latency", "lower"),
            ("Max Latency (ms)", "max_latency", "lower"),
            ("Avg Util %", "avg_utilization", "lower"),
            ("Imbalance Score", "imbalance_score", "lower"),
            ("Context Switches", "total_switches", "lower")
        ]
        
        for label, key, goal in metrics:
            p_val = comparison['pinned'][key]
            b_val = comparison['balanced'][key]
            w_val = comparison['worst_case'][key]
            
            vals = [p_val, b_val, w_val]
            best = min(vals) if goal == "lower" else max(vals)
            
            row = [label]
            for v in vals:
                style = "bold green" if v == best else ""
                row.append(Text(str(v), style=style))
                
            table.add_row(*row)
            
        return Panel(table, title="[bold]SMP Mode Comparison[/bold]")

    def create_recommendations(self, rates, affinities, load):
        recs = []
        
        # 1. Check for specific high-rate pinned IRQs
        sorted_rates = sorted(rates.items(), key=lambda x: x[1]['rate'], reverse=True)
        for irq_id, rdata in sorted_rates[:3]:
            if irq_id in affinities and affinities[irq_id]['is_pinned']:
                cpus = affinities[irq_id]['affinity_str'] or str(affinities[irq_id]['cpus'])
                recs.append(f"• [yellow]IRQ {irq_id} ({rdata['device'][:10]}) is pinned to CPU {cpus}[/]. Consider spreading if throughput is a bottleneck.")
        
        # 2. Check for CPU load imbalance
        max_cpu_idx = max(load, key=load.get)
        total_load = sum(load.values())
        if total_load > 0:
            max_share = (load[max_cpu_idx] / total_load) * 100
            if max_share > 50:
                recs.append(f"• [red]CPU {max_cpu_idx} is handling {max_share:.1f}% of all interrupts[/]. irqbalance may need tuning.")
        
        # 3. Count pinned IRQs
        pinned_count = len([a for a in affinities.values() if a['is_pinned']])
        if pinned_count > 5:
            recs.append(f"• {pinned_count} IRQs are fully pinned to single cores - check for latency spikes under heavy system load.")
            
        if not recs:
            recs.append("• System looks optimally balanced.")
            
        return Panel("\n".join(recs), title="[bold]Insights & Recommendations[/bold]")

    def run(self):
        with self.console.status("[bold green]Analyzing system affinity..."):
            info = self.get_system_info()
            data = self.fetch_data()

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5)
        )
        layout["main"].split_row(
            Layout(name="grid", ratio=2),
            Layout(name="stats", ratio=1)
        )
        layout["stats"].split_column(
            Layout(name="load"),
            Layout(name="comp")
        )

        layout["header"].update(self.create_header(info))
        layout["grid"].update(self.create_affinity_grid(data['rates'], data['affinities']))
        layout["load"].update(self.create_load_chart(data['load']))
        layout["comp"].update(self.create_comparison_table(data['comparison']))
        layout["footer"].update(self.create_recommendations(data['rates'], data['affinities'], data['load']))

        self.console.clear()
        self.console.print(layout)

if __name__ == "__main__":
    visualizer = AffinityVisualizer()
    visualizer.run()
