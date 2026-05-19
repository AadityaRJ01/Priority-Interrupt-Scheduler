#!/usr/bin/env python3
"""
interrupt_model.py - High-level interrupt modeling and prioritization.

This module consumes the raw /proc/interrupts data and classifies interrupts
into functional categories with associated priorities and simulated execution times.
"""

import random
from proc_reader import read_interrupts

class Interrupt:
    """
    Represents a modeled system interrupt with simulation parameters.
    """
    def __init__(self, irq_number, device_name, irq_type, priority, arrival_time, burst_time):
        self.irq_number = irq_number
        self.device_name = device_name
        self.irq_type = irq_type       # e.g., TIMER, KEYBOARD, NETWORK, DISK, OTHER
        self.priority = priority      # 1 (High) to 5 (Low)
        self.arrival_time = arrival_time # Simulated arrival in ms (0-100)
        self.burst_time = burst_time     # Simulated ISR execution time in ms
        self.remaining_time = burst_time # Time left to process (for preemption)
        self.preemption_count = 0        # Number of times this interrupt was paused
        self.run_intervals = []          # List of (start, end) time segments
        self.state = "WAITING"         # WAITING, RUNNING, COMPLETED

    def __repr__(self):
        return f"<Interrupt IRQ={self.irq_number} Type={self.irq_type} Prio={self.priority}>"

def classify_and_prioritize(raw_list):
    """
    Maps real device names to categories and assigns priorities.
    
    Priority & Burst Mappings:
    - TIMER      : Prio 1, Burst 1ms
    - KEYBOARD   : Prio 2, Burst 2ms
    - NETWORK    : Prio 3, Burst 5ms
    - DISK       : Prio 4, Burst 8ms
    - OTHER      : Prio 5, Burst 3ms
    """
    interrupts = []
    
    # Configuration for classification and simulation
    CONFIG = {
        "TIMER":    {"prio": 1, "burst": 1},
        "KEYBOARD": {"prio": 2, "burst": 2},
        "NETWORK":  {"prio": 3, "burst": 5},
        "DISK":     {"prio": 4, "burst": 8},
        "OTHER":    {"prio": 5, "burst": 3}
    }

    for raw in raw_list:
        # Use device description if available, otherwise fallback to chip type
        desc = raw['device'].lower() if raw['device'] else raw['type'].lower()
        irq_id = raw['irq']
        
        # Classification Logic
        # - IRQ 0 and LOC are always timers
        # - i8042 covers standard keyboards/mice
        # - eth/enp/iwlwifi cover network interfaces found on Linux
        # - ahci/nvme/sd/sata cover disk controllers
        
        if 'timer' in desc or irq_id == '0' or irq_id == 'LOC':
            itype = "TIMER"
        elif 'i8042' in desc or 'keyboard' in desc:
            itype = "KEYBOARD"
        elif any(x in desc for x in ['eth', 'enp', 'iwlwifi', 'wlan', 'ath10k', 'rtw']):
            itype = "NETWORK"
        elif any(x in desc for x in ['ahci', 'nvme', 'sd', 'disk', 'sata', 'scsi']):
            itype = "DISK"
        else:
            itype = "OTHER"
            
        params = CONFIG[itype]
        
        # Create Interrupt object with simulated arrival time
        obj = Interrupt(
            irq_number=irq_id,
            device_name=raw['device'] if raw['device'] else raw['type'],
            irq_type=itype,
            priority=params['prio'],
            arrival_time=round(random.uniform(0, 100), 2),
            burst_time=params['burst']
        )
        interrupts.append(obj)
        
    # Sort primarily by Priority (lower number = higher importance)
    # Secondarily by Arrival Time (FIFO within same priority)
    interrupts.sort(key=lambda x: (x.priority, x.arrival_time))
    
    return interrupts

def main():
    """
    Demonstrates classification and prioritization logic.
    """
    print("Fetching raw interrupt data...")
    raw_data = read_interrupts()
    
    if not raw_data:
        print("Error: Could not read /proc/interrupts. Ensure you are running on Linux.")
        return

    classified = classify_and_prioritize(raw_data)
    
    print("\n" + "="*110)
    print(f"{'IRQ':<8} {'TYPE':<12} {'PRIO':<8} {'ARRIVAL(ms)':<15} {'BURST(ms)':<15} {'STATE':<12} {'DEVICE DESCRIPTION'}")
    print("="*110)
    
    for intr in classified:
        print(f"{intr.irq_number:<8} {intr.irq_type:<12} {intr.priority:<8} {intr.arrival_time:<15} {intr.burst_time:<15} {intr.state:<12} {intr.device_name}")
    
    print("-" * 110)
    print("\n--- Why are Timer Interrupts (Prio 1) the highest priority? ---")
    print("1. Scheduling Ticks: Linux uses timer interrupts (jiffies) to trigger the scheduler.")
    print("2. Preemption: They allow the OS to pause long-running processes to let others run.")
    print("3. Timekeeping: Systems rely on these for accurate wall-clock time and interval timers.")
    print("In Linux, missing a timer tick can lead to system drift and sluggish UI responsiveness.\n")

if __name__ == "__main__":
    main()
