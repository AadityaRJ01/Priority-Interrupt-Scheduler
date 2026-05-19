#!/usr/bin/env python3
"""
proc_reader.py - Linux /proc/interrupts parser

This module provides functions to read and parse the /proc/interrupts virtual filesystem file,
which tracks how many interrupts have been delivered to each CPU on the system.

Interrupts are signals from hardware or software to the CPU indicating an event needs attention.
- Hardware Interrupts: External devices like timers, NICs, keyboards.
- Software Interrupts: Internal signals like NMIs, IPIs, or localized CPU timers.
"""

import os

def get_cpu_count():
    """
    Reads the header of /proc/interrupts to determine the number of active CPUs.
    The first line lists CPU names (e.g., CPU0, CPU1, ...).
    """
    try:
        with open('/proc/interrupts', 'r') as f:
            header = f.readline()
            # Split whitespace to count 'CPU0', 'CPU1', etc.
            return len(header.split())
    except FileNotFoundError:
        # /proc/interrupts only exists on Linux
        return 0

def read_interrupts():
    """
    Parses /proc/interrupts and returns a list of dictionaries.
    
    Each dictionary represents one interrupt line with the following keys:
    - 'irq': The IRQ vector number or symbolic name (e.g., '0', 'NMI', 'LOC').
    - 'counts': A list of integers representing interrupt counts for each CPU.
    - 'type': The interrupt controller/chip name (e.g., 'IO-APIC-edge').
    - 'device': The device name or description registered for this interrupt.
    
    Parsing Logic:
    1. Skip the header line (CPU columns).
    2. Split each line by whitespace.
    3. The first part is the IRQ (strip the trailing colon).
    4. The next N parts are counts for the N CPUs detected.
    5. Remaining parts are the chip name and device description.
    """
    cpu_count = get_cpu_count()
    if cpu_count == 0:
        return []

    interrupt_list = []
    
    try:
        with open('/proc/interrupts', 'r') as f:
            # Skip the CPU header line
            f.readline()
            
            for line in f:
                if not line.strip():
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                # IRQ name/number is the first field, usually followed by a colon
                irq_id = parts[0].rstrip(':')
                
                # Next N fields are the per-CPU counts
                # We use the detected cpu_count to know how many integers to read
                counts = []
                for i in range(1, cpu_count + 1):
                    try:
                        counts.append(int(parts[i]))
                    except (ValueError, IndexError):
                        # Should not happen in standard /proc/interrupts but handle gracefully
                        counts.append(0)
                
                # Remaining fields describe the technology and device
                # Example for numeric IRQ: 14: count... IR-IO-APIC 14-fasteoi INTC1055:00
                # Example for symbolic IRQ: NMI: count... Non-maskable interrupts
                extra = parts[cpu_count + 1:]
                
                if irq_id.isdigit():
                    # Hardware IRQs usually have a chip name and then the device
                    if len(extra) >= 2:
                        chip_type = extra[0]
                        description = " ".join(extra[1:])
                    elif len(extra) == 1:
                        chip_type = extra[0]
                        description = ""
                    else:
                        chip_type = ""
                        description = ""
                else:
                    # Symbolic IRQs (NMI, LOC, etc.) often just have a description
                    chip_type = ""
                    description = " ".join(extra)
                
                interrupt_list.append({
                    'irq': irq_id,
                    'counts': counts,
                    'type': chip_type,
                    'device': description
                })
    except FileNotFoundError:
        pass
        
    return interrupt_list

def main():
    """
    Pretty-prints the interrupts table for demonstration.
    """
    try:
        data = read_interrupts()
        cpus = get_cpu_count()
        
        if not data:
            print("No interrupt data found (ensure you are on Linux).")
            return

        # Build header dynamically based on the number of CPUs
        header_fmt = "{:<6}" + "{:>12}" * cpus + "  {:<20} {}"
        cpu_labels = [f"CPU{i}" for i in range(cpus)]
        
        print("\n--- Linux System Interrupts (/proc/interrupts) ---\n")
        print(header_fmt.format("IRQ", *cpu_labels, "CHIP/TYPE", "DESCRIPTION"))
        print("-" * 110)
        
        for item in data:
            # Format row data
            row = [item['irq']] + item['counts'] + [item['type'], item['device']]
            print(header_fmt.format(*row))
            
        print("\nNote: Numeric IRQs are hardware vectors. Symbolic names (NMI, LOC) are specialized interrupts.")
        print("CPU Affinity (which CPU handles which IRQ) can be configured via /proc/irq/N/smp_affinity.")

    except Exception as e:
        print(f"Error printing data: {e}")

if __name__ == "__main__":
    main()
