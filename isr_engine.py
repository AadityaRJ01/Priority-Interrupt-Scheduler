#!/usr/bin/env python3
"""
isr_engine.py - ISR Execution Simulator.

This module simulates the physical execution of Interrupt Service Routines,
demonstrating the "top-half" of Linux interrupt handling with live logging
and context-switch visualization.
"""

import time
import random
from scheduler import Scheduler, PreemptiveScheduler, load_from_proc
from interrupt_model import Interrupt

class ISREngine:
    """
    Simulates the real-time execution environment for interrupts.
    Scaling factor allows ms simulation times to be visible to humans (e.g., 0.05s per 1ms).
    """
    def __init__(self, scale=0.02):
        self.scale = scale # 1ms in simulation = 'scale' seconds in real time

    def run_simulation(self, scheduler_instance):
        """
        Drives the simulation based on the scheduler's computed trace.
        """
        print(f"\n--- Starting ISR Live Simulation (Scale: {self.scale}s real-time per 1ms sim-time) ---")
        print("Note: In Linux, ISRs (Top Halves) must be short to keep the system responsive.\n")

        if isinstance(scheduler_instance, PreemptiveScheduler):
            # Preemptive Replay using the trace recorded during simulation
            trace = scheduler_instance.trace
            last_sim_time = 0.0
            
            for event in trace:
                sim_time, etype, current_intr = event[0], event[1], event[2]
                
                # Wait for the next event to occur in simulation time
                delay = (sim_time - last_sim_time) * self.scale
                if delay > 0:
                    time.sleep(delay)
                last_sim_time = sim_time
                
                if etype == "START":
                    print(f"[t={sim_time:5.1f}ms] IRQ {current_intr.irq_number:4} ({current_intr.irq_type:8}) — ISR started   | priority={current_intr.priority} device={current_intr.device_name[:20]}")
                elif etype == "PREEMPT":
                    preemptor = event[3]
                    print(f"[t={sim_time:5.1f}ms] PREEMPTED IRQ {current_intr.irq_number:4} → switching to IRQ {preemptor.irq_number:4} (context saved to stack)")
                elif etype == "RESUME":
                    print(f"[t={sim_time:5.1f}ms] IRQ {current_intr.irq_number:4} — ISR resumed   | remaining={current_intr.remaining_time:.1f}ms")
                elif etype == "FINISH":
                    print(f"[t={sim_time:5.1f}ms] IRQ {current_intr.irq_number:4} — ISR completed | turnaround={current_intr.turnaround_time:5.1f}ms")
        else:
            # Non-Preemptive Replay
            results = scheduler_instance.run()
            last_sim_time = 0.0
            for intr in results:
                # Wait until start
                time.sleep((intr.start_time - last_sim_time) * self.scale)
                print(f"[t={intr.start_time:5.1f}ms] IRQ {intr.irq_number:4} ({intr.irq_type:8}) — ISR started   | priority={intr.priority}")
                
                # Wait for burst completion
                time.sleep(intr.burst_time * self.scale)
                print(f"[t={intr.finish_time:5.1f}ms] IRQ {intr.irq_number:4} — ISR completed | turnaround={intr.turnaround_time:5.1f}ms")
                last_sim_time = intr.finish_time

def generate_synthetic_stream(n=10):
    """
    Generates a stream of random interrupts for testing preemption density.
    """
    interrupts = []
    # Standard Linux classification types and their priorities
    TYPES = {
        "TIMER":    {"prio": 1, "burst": 1},
        "KEYBOARD": {"prio": 2, "burst": 2},
        "NETWORK":  {"prio": 3, "burst": 5},
        "DISK":     {"prio": 4, "burst": 8},
        "OTHER":    {"prio": 5, "burst": 3}
    }
    type_names = list(TYPES.keys())
    
    for i in range(n):
        t_name = random.choice(type_names)
        t_data = TYPES[t_name]
        intr = Interrupt(
            irq_number=str(200 + i), 
            device_name=f"synthetic_dev_{i}",
            irq_type=t_name,
            priority=t_data['prio'],
            arrival_time=round(random.uniform(0, 30), 2), # Compete in a narrow 30ms window
            burst_time=t_data['burst']
        )
        interrupts.append(intr)
    return interrupts

def main():
    engine = ISREngine(scale=0.02) # Fast enough for a demo

    # 1. Synthetic Stream Demo (High Preemption Chance)
    print("="*80)
    print("DEMO 1: Synthetic Interrupt Stream (High Preemption density)")
    print("="*80)
    synthetic_stream = generate_synthetic_stream(n=8)
    ps = PreemptiveScheduler()
    ps.load_interrupts(synthetic_stream)
    ps.simulate() # Record the trace
    engine.run_simulation(ps)

    # 2. Real /proc/interrupts Demo
    print("\n" + "="*80)
    print("DEMO 2: Real /proc/interrupts Stream (Current System State)")
    print("="*80)
    real_stream = load_from_proc()
    # Use real data but sorted for a cleaner simulation
    ps_real = PreemptiveScheduler()
    ps_real.load_interrupts(real_stream[:15]) # Limit to first 15 for demo
    ps_real.simulate()
    engine.run_simulation(ps_real)

    print("\n" + "="*80)
    print("--- Linux Interrupt Internals ---")
    print("Top-Half: The hardware-facing part of the ISR. It MUST be fast, as it")
    print("          runs with interrupts potentially disabled. It only does ")
    print("          critical work (e.g., acknowledging hardware, copying data).")
    print("Bottom-Half: Deferred work (tasklets, workqueues) handled after the ")
    print("             time-critical ISR finishes, allowing other interrupts to run.")
    print("Scaling: In real systems, 1ms is huge. ISRs typically finish in microseconds.")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
