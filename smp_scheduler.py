#!/usr/bin/env python3
"""
smp_scheduler.py - Symmetric Multi-Processing Interrupt Scheduler

This module simulates the Linux kernel's handling of interrupts across multiple 
CPU cores. It compares different affinity strategies like Pinned (NUMA-aware), 
Balanced (irqbalance-style), and Worst-Case (CPU0-only).

Concepts:
- SMP (Symmetric Multi-Processing): A computing architecture where multiple 
  identical processors connect to a single, shared main memory and have full 
  access to all I/O devices.
- Cache Locality: Keeping an interrupt handler on the core where the 
  related data exists in L1/L2 cache. This minimizes costly memory fetches.
- irqbalance: A Linux daemon that distributes hardware interrupts across 
  processors to improve system performance.
- NUMA (Non-Uniform Memory Access): Systems where memory access time depends 
  on the memory location relative to the processor. Pinning IRQs to local 
  cores is vital for NUMA efficiency.
"""

import copy
import random
from scheduler import PriorityQueue
from scheduler import load_from_proc

class CPUCore:
    """
    Represents an individual CPU core in the SMP system.
    """
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        self.current_interrupt = None
        self.ready_queue = PriorityQueue()
        self.completed = []
        self.busy_until = 0.0
        
        # Statistics
        self.total_interrupts_handled = 0
        self.total_busy_time = 0.0
        self.context_switches = 0

    def is_busy(self, current_time):
        return current_time < self.busy_until

class SMPScheduler:
    """
    Simulates multi-core interrupt scheduling.
    """
    def __init__(self, cpu_count):
        self.cpu_count = cpu_count
        self.cores = [CPUCore(i) for i in range(cpu_count)]
        self.simulation_time = 0.0

    def assign_to_cpu(self, interrupt, cpu_id):
        """
        Assigns an interrupt to a specific CPU's ready queue.
        """
        if 0 <= cpu_id < self.cpu_count:
            self.cores[cpu_id].ready_queue.push(interrupt)
        else:
            # Fallback to CPU0 if invalid ID
            self.cores[0].ready_queue.push(interrupt)

    def assign_balanced(self, interrupt):
        """
        Assigns to the CPU core with the shortest ready queue (Load Balancing).
        """
        best_core = min(self.cores, key=lambda c: len(c.ready_queue._heap))
        best_core.ready_queue.push(interrupt)

    def run_simulation(self, interrupt_list, affinity_dict, mode="pinned"):
        """
        Runs the SMP simulation in one of three modes:
        - pinned: Respects real Linux kernel affinity masks
        - balanced: Distributes load evenly across all cores
        - worst_case: Forces everything to CPU0
        """
        # Reset state
        for core in self.cores:
            core.current_interrupt = None
            core.ready_queue = PriorityQueue()
            core.completed = []
            core.busy_until = 0.0
            core.total_interrupts_handled = 0
            core.total_busy_time = 0.0
            core.context_switches = 0
            
        self.simulation_time = 0.0
        pending = sorted(copy.deepcopy(interrupt_list), key=lambda x: x.arrival_time)
        all_completed = []

        while pending or any(not c.ready_queue.is_empty() for c in self.cores) or any(c.is_busy(self.simulation_time) for c in self.cores):
            # 1. Process all arrivals at the current time
            while pending and pending[0].arrival_time <= self.simulation_time:
                intr = pending.pop(0)
                
                if mode == "worst_case":
                    self.assign_to_cpu(intr, 0)
                elif mode == "balanced":
                    self.assign_balanced(intr)
                elif mode == "pinned":
                    # Find eligible CPUs from affinity_dict
                    irq_str = str(intr.irq_number)
                    if irq_str in affinity_dict:
                        eligible_cpus = affinity_dict[irq_str]['cpus']
                        if eligible_cpus:
                            # Pick the least busy eligible CPU
                            target_cpu = min(eligible_cpus, key=lambda cid: len(self.cores[cid].ready_queue._heap))
                            self.assign_to_cpu(intr, target_cpu)
                        else:
                            self.assign_balanced(intr)
                    else:
                        self.assign_balanced(intr)
                else:
                    self.assign_balanced(intr)

            # 2. Check each core for work
            for core in self.cores:
                if not core.is_busy(self.simulation_time):
                    if not core.ready_queue.is_empty():
                        # Start next interrupt
                        intr = core.ready_queue.pop()
                        core.current_interrupt = intr
                        
                        intr.start_time = self.simulation_time
                        intr.finish_time = intr.start_time + intr.burst_time
                        intr.waiting_time = round(intr.start_time - intr.arrival_time, 2)
                        
                        core.busy_until = intr.finish_time
                        core.total_interrupts_handled += 1
                        core.total_busy_time += intr.burst_time
                        core.context_switches += 1
                        
                        all_completed.append(intr)
                        core.completed.append(intr)

            # 3. Advance clock to next event
            # Significant events: Next arrival or next CPU completion
            next_event = float('inf')
            
            if pending:
                next_event = min(next_event, pending[0].arrival_time)
            
            for core in self.cores:
                if core.is_busy(self.simulation_time):
                    next_event = min(next_event, core.busy_until)
            
            if next_event == float('inf') or next_event <= self.simulation_time:
                # If no future events or weird rounding, small step
                self.simulation_time += 0.1
            else:
                self.simulation_time = next_event

        return all_completed

def compare_modes(interrupt_list, affinity_dict):
    """
    Runs and compares Pinned vs Balanced vs Worst-Case strategies.
    """
    from affinity_reader import get_cpu_count
    cpu_count = get_cpu_count()
    if cpu_count == 0: cpu_count = 1 # Fallback
    
    scheduler = SMPScheduler(cpu_count)
    modes = ["pinned", "balanced", "worst_case"]
    results = {}

    for mode in modes:
        completed_intrs = scheduler.run_simulation(interrupt_list, affinity_dict, mode)
        
        # Calculate Metrics
        total_latency = sum(i.waiting_time for i in completed_intrs)
        avg_latency = total_latency / len(completed_intrs) if completed_intrs else 0
        max_latency = max(i.waiting_time for i in completed_intrs) if completed_intrs else 0
        
        total_switches = sum(c.context_switches for c in scheduler.cores)
        
        # CPU Utilizations
        max_time = max((c.busy_until for c in scheduler.cores), default=1.0)
        if max_time == 0: max_time = 1.0
        
        utils = [(c.total_busy_time / max_time) * 100 for c in scheduler.cores]
        avg_util = sum(utils) / len(utils)
        
        # Load Imbalance Score
        max_util = max(utils)
        min_util = min(utils)
        imbalance = (max_util - min_util) / avg_util if avg_util > 0 else 0
        
        results[mode] = {
            "avg_latency": round(avg_latency, 2),
            "max_latency": round(max_latency, 2),
            "total_switches": total_switches,
            "avg_utilization": round(avg_util, 2),
            "imbalance_score": round(imbalance, 3),
            "per_cpu_utils": utils
        }
        
    return results

def main():
    """
    Main entry point for SMP simulation.
    """
    from affinity_reader import get_all_affinities
    from proc_reader import read_interrupts
    from interrupt_model import classify_and_prioritize

    print("\n--- Linux SMP Interrupt Scheduler Simulation ---")
    
    # 1. Load Real System Data
    raw = read_interrupts()
    interrupts = classify_and_prioritize(raw)
    
    irq_list = [i.irq_number for i in interrupts if i.irq_number.isdigit()]
    affinities = get_all_affinities(irq_list)
    
    print(f"Simulation Workspace: {len(interrupts)} interrupts across {len(set(irq_list))} vectors.")
    
    # 2. Run Modes
    results = compare_modes(interrupts, affinities)
    
    # 3. Print Comparison Table
    print("\n" + "="*80)
    print(f"{'Affinity Mode':<15} | {'Avg Latency':<12} | {'Max Latency':<12} | {'Avg Util%':<10} | {'Imbalance'}")
    print("-" * 80)
    
    for mode, data in results.items():
        print(f"{mode.capitalize():<15} | {data['avg_latency']:<12.2f} | {data['max_latency']:<12.2f} | {data['avg_utilization']:<10.1f} | {data['imbalance_score']}")
    
    print("="*80)
    
    print("\nKey Insights:")
    print("- Pinned Mode: Reflects YOUR current system config. It uses real IRQ masks.")
    print("- Balanced Mode: The 'Ideal' scenario for a non-real-time system, similar to irqbalance.")
    print("- Worst Case: Simulates 'Interrupt Storm' on CPU0. Notice the spike in Latency.")
    
    print("\nWhy it matters:")
    print("1. Cache Locality: If IRQs are spread too thin (jitter), L1/L2 cache misses increase.")
    print("2. Determinism: High-prio real-time tasks often PIN interrupts to keep specific ")
    print("   cores 'quiet' for critical tasks.")
    print("3. NUMA: In large servers, accessing RAM across CPU sockets is slow. Affinity ")
    print("   ensures the NIC and the CPU handling its traffic are on the same silicon die.")

if __name__ == "__main__":
    main()
