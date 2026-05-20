#!/usr/bin/env python3
"""
scheduler.py - Core Interrupt Scheduler Simulation.

This module simulates the Linux kernel's handling of interrupts using
a priority-based non-preemptive scheduling algorithm.
"""

import heapq
import itertools
from proc_reader import read_interrupts
from interrupt_model import classify_and_prioritize, Interrupt

class PriorityQueue:
    """
    A priority queue backed by heapq (a min-heap).
    Standard priority scheduling uses a min-heap because we always want to extract
     the element with the 'smallest' priority value (where 1 is highest priority).
    """
    def __init__(self):
        self._heap = []
        # Counter ensures stable sorting (FIFO) for items with same priority/arrival
        self._counter = itertools.count()

    def push(self, item: Interrupt):
        # We sort by (priority, arrival_time)
        entry = (item.priority, item.arrival_time, next(self._counter), item)
        heapq.heappush(self._heap, entry)

    def pop(self) -> Interrupt:
        if not self.is_empty():
            return heapq.heappop(self._heap)[-1]
        return None

    def is_empty(self):
        return len(self._heap) == 0

class Scheduler:
    """
    Simulates a non-preemptive priority scheduler.
    In a non-preemptive system, once an ISR starts, it runs to completion even if
    a higher-priority interrupt arrives during its execution.
    """
    def __init__(self):
        self.ready_queue = PriorityQueue()
        self.all_interrupts = []
        self.execution_log = []

    def load_interrupts(self, interrupts):
        # Sort by arrival time to simulate the sequence of events
        self.all_interrupts = sorted(interrupts, key=lambda x: x.arrival_time)

    def run(self):
        """
        Simulates the scheduling process over a timeline as a generator.
        Yields snapshots of the system state at each significant event.
        """
        current_time = 0.0
        pending = self.all_interrupts[:]
        
        while pending or not self.ready_queue.is_empty():
            # 1. Add all interrupts that have arrived by the current time to the ready queue
            while pending and pending[0].arrival_time <= current_time:
                self.ready_queue.push(pending.pop(0))
            
            # 2. If the CPU is idle but more interrupts are expected, advance time
            if self.ready_queue.is_empty() and pending:
                current_time = pending[0].arrival_time
                continue
            
            # 3. Pick the highest priority interrupt from the ready queue
            intr = self.ready_queue.pop()
            if not intr:
                break
                
            # Simulate execution (Non-preemptive)
            intr.state = "RUNNING"
            intr.start_time = current_time
            intr.finish_time = intr.start_time + intr.burst_time
            intr.waiting_time = round(intr.start_time - intr.arrival_time, 2)
            intr.turnaround_time = round(intr.finish_time - intr.arrival_time, 2)
            intr.run_intervals = [(intr.start_time, intr.finish_time)]
            
            # Yield state before completion for live tracking
            yield {
                "time": current_time,
                "active_interrupt": intr,
                "event": f"START: IRQ {intr.irq_number}",
                "ready_queue": [e[-1] for e in self.ready_queue._heap]
            }

            intr.state = "COMPLETED"
            self.execution_log.append(intr)
            current_time = intr.finish_time
            
            yield {
                "time": current_time,
                "active_interrupt": None,
                "event": f"FINISH: IRQ {intr.irq_number}",
                "ready_queue": [e[-1] for e in self.ready_queue._heap]
            }
            
        return self.execution_log

class PreemptiveScheduler(Scheduler):
    """
    Simulates a preemptive priority scheduler where high-priority interrupts
    can interrupt lower-priority ones.
    """
    def __init__(self):
        super().__init__()
        self.context_stack = []  # Stack for LIFO nested interrupts
        self.context_switches = 0
        self.preemption_log = []
        self.trace = [] # List of (time, event_type, interrupt)

    def simulate(self):
        """
        Real-time discrete event simulation for nested interrupts.
        Yields state snapshots at each event (Arrival, Preemption, Completion).
        """
        current_time = 0.0
        pending = sorted(self.all_interrupts, key=lambda x: x.arrival_time)
        active_intr = None
        
        while pending or not self.ready_queue.is_empty() or active_intr or self.context_stack:
            # 1. Process all arrivals up to current time
            while pending and pending[0].arrival_time <= current_time:
                arrived = pending.pop(0)
                
                # Check for preemption if an interrupt is running
                if active_intr and arrived.priority < active_intr.priority:
                    # PREEMPT!
                    active_intr.state = "WAITING"
                    active_intr.preemption_count += 1
                    active_intr.run_intervals[-1] = (active_intr.run_intervals[-1][0], current_time)
                    
                    self.context_switches += 1
                    self.context_stack.append(active_intr)
                    msg = f"PREEMPT: IRQ {arrived.irq_number} preempts {active_intr.irq_number}"
                    self.preemption_log.append(f"[{current_time}ms] {msg}")
                    self.trace.append((current_time, "PREEMPT", active_intr, arrived))
                    
                    yield {
                        "time": current_time,
                        "active_interrupt": active_intr,
                        "event": msg,
                        "ready_queue": [e[-1] for e in self.ready_queue._heap],
                        "stack": self.context_stack[:]
                    }

                    # Start the new interrupt
                    active_intr = arrived
                    active_intr.start_time = current_time
                    active_intr.state = "RUNNING"
                    active_intr.run_intervals.append((current_time, None))
                    self.trace.append((current_time, "START", active_intr))
                    
                    yield {
                        "time": current_time,
                        "active_interrupt": active_intr,
                        "event": f"START: IRQ {active_intr.irq_number}",
                        "ready_queue": [e[-1] for e in self.ready_queue._heap],
                        "stack": self.context_stack[:]
                    }
                else:
                    # Just add to ready queue
                    self.ready_queue.push(arrived)
                    yield {
                        "time": current_time,
                        "active_interrupt": active_intr,
                        "event": f"ARRIVAL: IRQ {arrived.irq_number}",
                        "ready_queue": [e[-1] for e in self.ready_queue._heap],
                        "stack": self.context_stack[:]
                    }
            
            # 2. If no active interrupt, pick from ready queue OR context stack
            if not active_intr:
                if not self.ready_queue.is_empty():
                    active_intr = self.ready_queue.pop()
                    if active_intr.remaining_time == active_intr.burst_time:
                        active_intr.start_time = current_time
                        etype = "START"
                    else:
                        etype = "RESUME"
                    self.trace.append((current_time, etype, active_intr))
                    active_intr.state = "RUNNING"
                    active_intr.run_intervals.append((current_time, None))
                    
                    yield {
                        "time": current_time,
                        "active_interrupt": active_intr,
                        "event": f"{etype}: IRQ {active_intr.irq_number}",
                        "ready_queue": [e[-1] for e in self.ready_queue._heap],
                        "stack": self.context_stack[:]
                    }
                elif self.context_stack:
                    active_intr = self.context_stack.pop()
                    self.trace.append((current_time, "RESUME", active_intr))
                    active_intr.state = "RUNNING"
                    active_intr.run_intervals.append((current_time, None))
                    
                    yield {
                        "time": current_time,
                        "active_interrupt": active_intr,
                        "event": f"RESUME: IRQ {active_intr.irq_number}",
                        "ready_queue": [e[-1] for e in self.ready_queue._heap],
                        "stack": self.context_stack[:]
                    }
                elif pending:
                    # Advance time to next arrival
                    current_time = pending[0].arrival_time
                    continue
                else:
                    break
            
            # 3. Step forward to the next "event"
            time_to_next_arrival = (pending[0].arrival_time - current_time) if pending else float('inf')
            time_to_completion = active_intr.remaining_time
            
            step = min(time_to_next_arrival, time_to_completion)
            
            # For the TUI, we might want to yield *intermediate* progress steps
            # but the scheduler simulation is discrete. We'll handle progress interpolation in the TUI.
            
            active_intr.remaining_time -= step
            current_time += step
            
            # 4. Handle completion
            if active_intr.remaining_time <= 0:
                active_intr.state = "COMPLETED"
                active_intr.finish_time = current_time
                active_intr.run_intervals[-1] = (active_intr.run_intervals[-1][0], current_time)
                active_intr.waiting_time = round(active_intr.start_time - active_intr.arrival_time, 2)
                active_intr.turnaround_time = round(active_intr.finish_time - active_intr.arrival_time, 2)
                self.trace.append((current_time, "FINISH", active_intr))
                self.execution_log.append(active_intr)
                
                yield {
                    "time": current_time,
                    "active_interrupt": active_intr,
                    "event": f"FINISH: IRQ {active_intr.irq_number}",
                    "ready_queue": [e[-1] for e in self.ready_queue._heap],
                    "stack": self.context_stack[:]
                }
                active_intr = None
                
        return self.execution_log

def load_from_proc():
    """
    Chains the proc_reader and interrupt_model to get real-world data.
    """
    raw = read_interrupts()
    modeled = classify_and_prioritize(raw)
    return modeled

def demo_preemption():
    """
    Demos a real preemption scenario:
    - DISK (Prio 4) starts at t=0, Duration=8ms
    - TIMER (Prio 1) arrives at t=4ms, Duration=1ms
    """
    print("\n--- Preemption Demo Scenario (DISK vs TIMER) ---")
    
    # We create manual Interrupt objects for the demo
    disk = Interrupt("121", "nvme0", "DISK", 4, 0.0, 8.0)
    timer = Interrupt("0", "timer", "TIMER", 1, 4.0, 1.0)
    
    ps = PreemptiveScheduler()
    ps.load_interrupts([disk, timer])
    ps.simulate()
    
    for log in ps.preemption_log:
        print(log)
    
    print("\nFinal State:")
    for i in ps.execution_log:
        print(f"IRQ {i.irq_number:3} ({i.irq_type:8}): Finish={i.finish_time}ms, Preemptions={i.preemption_count}")

def main():
    print("--- Interrupt Scheduler Simulation ---")
    
    # 1. Non-Preemptive Run (Real Data)
    print("\n[Stage 1: Non-Preemptive Simulation (Real /proc/interrupts)]")
    interrupts = load_from_proc()
    scheduler = Scheduler()
    scheduler.load_interrupts(interrupts)
    results = list(scheduler.run())
    
    fmt = "{:<8} {:<10} {:<6} {:<12} {:<10} {:<10} {:<10} {:<10} {:<20}"
    print(fmt.format("IRQ", "TYPE", "PRIO", "ARRIVAL", "START", "BURST", "FINISH", "WAIT", "DEVICE"))
    for i in results[:10]: # Just show top 10 for brevity
        print(fmt.format(i.irq_number, i.irq_type, i.priority, i.arrival_time, round(i.start_time, 2), i.burst_time, round(i.finish_time, 2), i.waiting_time, i.device_name[:30]))
    print("... (truncated)")

    # 2. Preemptive Demo
    print("\n[Stage 2: Preemptive Nested Interrupts Simulation]")
    demo_preemption()
    
    print("\n" + "="*120)
    print("--- Linux Interrupt Theory ---")
    print("Nesting Rules: Linux supports nested interrupts. Priorities: NMI > Hardware IRQ > softirq > tasklet.")
    print("IRET: The 'Interrupt Return' instruction pops the saved program counter and flags to resume a preempted context.")
    print("cli/sti: Critical sections use 'cli' (Clear Interrupt Flag) to disable preemption and 'sti' to re-enable it.")
    print("Context Switch: In interrupts, this is extremely fast as it only saves registers to the kernel stack.")
    print("="*120 + "\n")

if __name__ == "__main__":
    main()
