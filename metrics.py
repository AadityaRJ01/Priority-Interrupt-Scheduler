#!/usr/bin/env python3
"""
metrics.py - Performance Metrics Calculator for OS Interrupt Scheduling.

This module computes and visualizes key performance indicators (KPIs) for 
interrupt scheduling algorithms, helping evaluate system responsiveness 
and efficiency.
"""

import copy
from scheduler import Scheduler, PreemptiveScheduler
from isr_engine import generate_synthetic_stream

class MetricsReport:
    """
    Calculates, aggregates, and displays performance metrics for a scheduled 
    set of interrupt objects.
    """
    def __init__(self, name, results):
        self.name = name
        self.results = results
        
        # Simulation boundary analysis
        if not results:
            self.start_time = 0
            self.end_time = 0
        else:
            self.start_time = min(i.arrival_time for i in results)
            self.end_time = max(i.finish_time for i in results)
        
        self.total_sim_time = self.end_time - self.start_time

    def calculate_aggregates(self):
        """Computes system-wide averages and efficiency ratios."""
        if not self.results:
            return {}

        n = len(self.results)
        
        # Per-interrupt metrics are already calculated in the scheduler, 
        # but we use those fields to compute averages here.
        avg_wait = sum(i.waiting_time for i in self.results) / n
        avg_turnaround = sum(i.turnaround_time for i in self.results) / n
        
        # Interrupt Latency is defined here as time from arrival to first start
        avg_latency = sum(i.start_time - i.arrival_time for i in self.results) / n
        
        # CPU Utilization: (Work / Total Time)
        total_burst = sum(i.burst_time for i in self.results)
        utilization = (total_burst / self.total_sim_time * 100) if self.total_sim_time > 0 else 0
        
        # Throughput: Interrupts per 100ms
        throughput = (n / self.total_sim_time * 100) if self.total_sim_time > 0 else 0

        return {
            "avg_wait": avg_wait,
            "avg_turnaround": avg_turnaround,
            "avg_latency": avg_latency,
            "utilization": utilization,
            "throughput": throughput
        }

    def display_gantt(self, width=80):
        """Prints an ASCII Gantt chart showing the execution timeline."""
        if not self.results or self.total_sim_time <= 0:
            print("[Gantt Chart unavailable: No data]")
            return

        print(f"\n--- EXECUTION TIMELINE (Gantt Chart): {self.name} ---")
        
        # Sort by IRQ for vertical stability
        sorted_results = sorted(self.results, key=lambda x: x.irq_number)
        
        for intr in sorted_results:
            row = [" "] * width
            
            def to_scale(t):
                # Normalize time to the [0, width] range
                offset = t - self.start_time
                idx = int((offset / self.total_sim_time) * (width - 1))
                return max(0, min(width - 1, idx))

            # Mark waiting period (Arrival to First Start)
            wait_start = to_scale(intr.arrival_time)
            wait_end = to_scale(intr.start_time)
            for i in range(wait_start, wait_end):
                row[i] = "."

            # Mark running intervals (for preemption support)
            for start, end in intr.run_intervals:
                s_idx = to_scale(start)
                e_idx = to_scale(end if end is not None else self.end_time)
                for i in range(s_idx, e_idx + 1):
                    row[i] = "#"

            # Print the row
            print(f"IRQ {intr.irq_number:4} |{''.join(row)}|")
        
        print(" " * 9 + f"{self.start_time:.1f}ms" + " " * (width - 10) + f"{self.end_time:.1f}ms")
        print("Legend: # = Running (ISR), . = Waiting in Queue")

    def display(self):
        """Prints the full tabular report and summary stats."""
        print(f"\n{'='*90}")
        print(f" REPORT: {self.name}")
        print(f"{'='*90}")
        
        # Per-interrupt details
        header = f"{'IRQ':<6} {'TYPE':<10} {'PRIO':<6} {'ARR':<8} {'START':<8} {'FINISH':<8} {'WAIT':<8} {'TURN':<8} {'LATENCY':<8}"
        print(header)
        print("-" * len(header))
        
        for i in sorted(self.results, key=lambda x: x.arrival_time):
            latency = i.start_time - i.arrival_time
            # Response time is same as waiting for non-preemptive, but latency is tracked separately
            print(f"{i.irq_number:<6} {i.irq_type:<10} {i.priority:<6} {i.arrival_time:<8.1f} {i.start_time:<8.1f} "
                  f"{i.finish_time:<8.1f} {i.waiting_time:<8.1f} {i.turnaround_time:<8.1f} {latency:<8.1f}")
        
        # Summary Aggregates
        print("-" * len(header))
        metrics = self.calculate_aggregates()
        print(f"Average Waiting Time    : {metrics['avg_wait']:.2f} ms")
        print(f"Average Turnaround Time : {metrics['avg_turnaround']:.2f} ms")
        print(f"Average Interrupt Latency: {metrics['avg_latency']:.2f} ms")
        print(f"CPU Utilization         : {metrics['utilization']:.1f} %")
        print(f"System Throughput       : {metrics['throughput']:.2f} interrupts / 100ms")
        
        # Significance Comments
        print("\n--- Why these metrics matter for OS tuning ---")
        print("1. LATENCY: Critical for real-time responsiveness. High latency drops network packets or misses timer ticks.")
        print("2. TURNAROUND: Total time an interrupt occupies resources; affects how fast background tasks can resume.")
        print("3. UTILIZATION: If > 80%, the system enters 'Interrupt Storm' territory, starving user processes (CPU Lag).")
        
        self.display_gantt()

def run_comparison(stream_size=8):
    """Generates data and compares non-preemptive vs preemptive schedulers."""
    print(f"Generating synthetic stream of {stream_size} interrupts...")
    stream = generate_synthetic_stream(stream_size)
    
    # 1. Non-Preemptive Simulation
    s_np = Scheduler()
    s_np.load_interrupts(copy.deepcopy(stream))
    results_np = list(s_np.run())
    report_np = MetricsReport("NON-PREEMPTIVE (FIFO within Priority)", results_np)
    
    # 2. Preemptive Simulation
    s_p = PreemptiveScheduler()
    s_p.load_interrupts(copy.deepcopy(stream))
    results_p = list(s_p.simulate())
    report_p = MetricsReport("PREEMPTIVE (Nested Interrupts)", results_p)
    
    # Display results
    report_np.display()
    print("\n" + "*"*90 + "\n")
    report_p.display()

    # Final Side-by-Side Aggregate Comparison
    print("\n" + "="*90)
    print(" FINAL PERFORMANCE COMPARISON (Aggregates)")
    print("="*90)
    m_np = report_np.calculate_aggregates()
    m_p = report_p.calculate_aggregates()
    
    comp_fmt = "{:<30} {:<20} {:<20} {:<15}"
    print(comp_fmt.format("Metric", "Non-Preemptive", "Preemptive", "Improvement"))
    print("-" * 90)
    
    metrics_to_comp = [
        ("Avg Waiting Time (ms)", "avg_wait", True),     # True = lower is better
        ("Avg Turnaround Time (ms)", "avg_turnaround", True),
        ("Avg Latency (ms)", "avg_latency", True),
        ("Throughput (per 100ms)", "throughput", False)  # False = higher is better
    ]
    
    for label, key, lower_better in metrics_to_comp:
        val_np = m_np[key]
        val_p = m_p[key]
        
        diff = val_np - val_p if lower_better else val_p - val_np
        improve_pct = (diff / val_np * 100) if val_np != 0 else 0
        
        print(comp_fmt.format(label, f"{val_np:.2f}", f"{val_p:.2f}", f"{improve_pct:+.1f}%"))
    
    print("-" * 90)
    print("Note: Preemption significantly reduces latency for high-priority interrupts by")
    print("allowing them to 'cut the line', even if another ISR is already running.")

if __name__ == "__main__":
    run_comparison(8)
