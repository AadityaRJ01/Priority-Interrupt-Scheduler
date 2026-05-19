#!/usr/bin/env python3
"""
metrics.py - Performance Metrics Calculator for Interrupt Scheduling.

This module analyzes simulation results to compute efficiency metrics
like waiting time, CPU utilization, and generates Gantt charts for comparison.
"""

import copy
from scheduler import Scheduler, PreemptiveScheduler
from isr_engine import generate_synthetic_stream

class MetricsReport:
    """
    Analyzes and displays performance metrics for interrupt scheduling.
    """
    def __init__(self, name, results):
        self.name = name
        self.results = results
        # Determine total time span for utilization/throughput
        if not results:
            self.total_time = 0
            self.start_time = 0
            self.end_time = 0
        else:
            self.start_time = min(i.arrival_time for i in results)
            self.end_time = max(i.finish_time for i in results)
            self.total_time = self.end_time - self.start_time

    def calculate_aggregates(self):
        if not self.results:
            return None
        
        count = len(self.results)
        avg_wait = sum(i.waiting_time for i in self.results) / count
        avg_turnaround = sum(i.turnaround_time for i in self.results) / count
        # In this simulation, latency = time from arrival to FIRST start
        avg_latency = sum(i.start_time - i.arrival_time for i in self.results) / count
        
        total_burst = sum(i.burst_time for i in self.results)
        cpu_util = (total_burst / self.total_time) * 100 if self.total_time > 0 else 0
        throughput = (count / self.total_time) * 100 if self.total_time > 0 else 0
        
        return {
            "Avg Wait": f"{avg_wait:.2f}ms",
            "Avg Turnaround": f"{avg_turnaround:.2f}ms",
            "Avg Latency": f"{avg_latency:.2f}ms",
            "CPU Util": f"{cpu_util:.1f}%",
            "Throughput": f"{throughput:.2f} /100ms"
        }

    def display_gantt(self):
        """
        Prints a simple ASCII Gantt chart of the code execution.
        """
        if not self.results:
            return
            
        print(f"\nGantt Chart: {self.name}")
        width = 60
        
        # Sort results by IRQ number for consistent vertical order
        display_list = sorted(self.results, key=lambda x: x.irq_number)
        
        for intr in display_list:
            line = [" "] * width
            
            # Map simulation time [0, end_time] to Gantt width [0, width]
            def to_gantt(t):
                if self.end_time == 0: return 0
                idx = int((t / self.end_time) * (width - 1))
                return max(0, min(width - 1, idx))

            # Mark Arrival
            arr_idx = to_gantt(intr.arrival_time)
            line[arr_idx] = "|"
            
            # Mark Lifecycle (Wait + Run)
            end_idx = to_gantt(intr.finish_time)
            for i in range(arr_idx + 1, end_idx):
                line[i] = "."

            # Mark Running Intervals (overwrites waiting)
            for start, end in intr.run_intervals:
                if end is None: end = self.end_time # Should not happen with completed results
                s_idx = to_gantt(start)
                e_idx = to_gantt(end)
                for i in range(s_idx, e_idx + 1):
                    line[i] = "#"
            
            print(f"IRQ {intr.irq_number:4} |{''.join(line)}|")
        
        print(" " * 9 + "0ms" + " " * (width - 6) + f"{self.end_time:.1f}ms")
        print("Legend: | Arrival, # Running, . Waiting")

    def display(self):
        print(f"\n>>> REPORT: {self.name} <<<")
        print("-" * 75)
        fmt = "{:<8} {:<12} {:<10} {:<10} {:<10} {:<10}"
        print(fmt.format("IRQ", "TYPE", "WAIT", "TURN", "LATENCY", "PREEMPTS"))
        print("-" * 75)
        
        for i in sorted(self.results, key=lambda x: x.arrival_time):
            latency = round(i.start_time - i.arrival_time, 2)
            print(fmt.format(i.irq_number, i.irq_type, i.waiting_time, i.turnaround_time, latency, i.preemption_count))
            
        print("-" * 75)
        aggs = self.calculate_aggregates()
        for k, v in aggs.items():
            print(f"{k:<20}: {v}")

def compare_schedulers(stream):
    """
    Executes both scheduling algorithms on the same data and prints comparisons.
    """
    print("\n" + "#" * 80)
    print("### PERFORMANCE COMPARISON: NON-PREEMPTIVE VS PREEMPTIVE ###")
    print("#" * 80)
    
    # 1. Non-Preemptive
    s_np = Scheduler()
    s_np.load_interrupts(copy.deepcopy(stream))
    # We must ensure run() returns the execution_log correctly
    results_np = s_np.run()
    report_np = MetricsReport("Non-Preemptive (Standard Priority)", results_np)
    
    # 2. Preemptive
    s_p = PreemptiveScheduler()
    s_p.load_interrupts(copy.deepcopy(stream))
    results_p = s_p.simulate()
    report_p = MetricsReport("Preemptive (Nested Interrupts)", results_p)
    
    # Display side-by-side
    report_np.display()
    report_np.display_gantt()
    print("\n" + "*" * 60)
    report_p.display()
    report_p.display_gantt()

def main():
    # Generate 8 synthetic interrupts for a clear visual comparison
    print("Benchmarking Scheduler performance with 8 synthetic interrupts...")
    synthetic_stream = generate_synthetic_stream(8)
    compare_schedulers(synthetic_stream)
    
    print("\n--- Why These Metrics Matter for OS Performance ---")
    print("1. Latency: Response time for hardware events. Preemption drastically ")
    print("   reduces latency for high-priority tasks (e.g., Timers).")
    print("2. Throughput: System efficiency. While preemption improves latency, it ")
    print("   adds small overhead due to context switches (register saving/restoring).")
    print("3. CPU Utilization: The fraction of time spent in ISRs. Sustained high ")
    print("   utilization (>90%) can starve user-mode processes, leading to lag.")

if __name__ == "__main__":
    main()
