#!/usr/bin/env python3
"""
affinity_reader.py - Linux IRQ CPU Affinity Reader

This module provides functionality to read and analyze how interrupts are 
distributed across CPU cores on a Linux system.

Concepts:
- smp_affinity: A hex bitmask where each bit represents a CPU core. 
  If bit N is set, CPU N is allowed to handle that specific IRQ.
- smp_affinity_list: A human-readable range (e.g., "0-3") of CPUs allowed 
   to handle the IRQ.
- IRQ Pinning: Manually restricting an IRQ to specific CPUs. This is critical 
  for performance in NUMA systems (keeping data in local CPU cache) and 
  avoiding "interrupt storms" on CPU0.
- irqbalance: A background daemon that dynamically adjusts these affinities 
  based on system load to prevent any single CPU from being bottlenecked.
"""

import os
from proc_reader import read_interrupts

def get_cpu_count():
    """
    Reads /proc/cpuinfo and counts 'processor' entries to determine 
    the number of logical CPUs.
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            count = 0
            for line in f:
                if line.startswith('processor'):
                    count += 1
            return count
    except FileNotFoundError:
        return 0

def read_affinity_mask(irq):
    """
    Reads /proc/irq/{irq}/smp_affinity as a hex bitmask and converts 
    it to a list of CPU indices.
    
    Example: 
    Mask "0f" (binary 1111) -> [0, 1, 2, 3]
    Mask "01" (binary 0001) -> [0]
    """
    path = f"/proc/irq/{irq}/smp_affinity"
    try:
        if not os.path.exists(path):
            return None
            
        with open(path, 'r') as f:
            mask_str = f.read().strip().replace(',', '')
            mask_val = int(mask_str, 16)
            
            cpus = []
            cpu_idx = 0
            while mask_val > 0:
                if mask_val & 1:
                    cpus.append(cpu_idx)
                mask_val >>= 1
                cpu_idx += 1
            return cpus
    except (IOError, PermissionError, ValueError):
        return None

def read_affinity_list(irq):
    """
    Reads /proc/irq/{irq}/smp_affinity_list for a human-readable representation.
    Returns strings like "0-3" or "0,2".
    """
    path = f"/proc/irq/{irq}/smp_affinity_list"
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return f.read().strip()
    except (IOError, PermissionError):
        return None

def get_all_affinities(irq_list):
    """
    Takes a list of IRQ numbers (as strings or ints) and returns a detailed 
    dictionary of their CPU assignment state.
    """
    total_cpus = get_cpu_count()
    affinities = {}
    
    for irq in irq_list:
        cpus = read_affinity_mask(irq)
        if cpus is None:
            continue
            
        affinity_str = read_affinity_list(irq)
        
        # is_pinned = True if assigned to fewer CPUs than the total count
        is_pinned = len(cpus) < total_cpus if total_cpus > 0 else False
        
        # Get path for the mask string again to store it
        try:
            with open(f"/proc/irq/{irq}/smp_affinity", 'r') as f:
                mask_hex = f.read().strip()
        except:
            mask_hex = "unknown"

        affinities[irq] = {
            "mask": mask_hex,
            "cpus": cpus,
            "affinity_str": affinity_str,
            "is_pinned": is_pinned
        }
    return affinities

def get_per_cpu_irq_load(affinities, rates):
    """
    Computes per-CPU interrupt load.
    
    Formula: If an IRQ has rate R and is assigned to N CPUs, 
    each assigned CPU handles R/N interrupts/sec.
    """
    load = {}
    cpu_count = get_cpu_count()
    for i in range(cpu_count):
        load[i] = 0.0
        
    for irq, rate_info in rates.items():
        if str(irq) in affinities:
            aff = affinities[str(irq)]
            assigned_cpus = aff['cpus']
            if assigned_cpus:
                rate_per_cpu = rate_info['rate'] / len(assigned_cpus)
                for cpu in assigned_cpus:
                    if cpu in load:
                        load[cpu] += rate_per_cpu
        elif irq in affinities: # Handle cases where irq might be int
            aff = affinities[irq]
            assigned_cpus = aff['cpus']
            if assigned_cpus:
                rate_per_cpu = rate_info['rate'] / len(assigned_cpus)
                for cpu in assigned_cpus:
                    if cpu in load:
                        load[cpu] += rate_per_cpu
                        
    return load

def main():
    """
    Simulator Entry Point: Reads system status and displays affinity diagnostics.
    """
    print("\n--- Linux IRQ Affinity Diagnostics ---")
    
    # 1. Get total CPU count
    cpus = get_cpu_count()
    print(f"System logical CPUs: {cpus}")
    
    # 2. Get active IRQs from proc_reader
    irq_data = read_interrupts()
    active_irqs = [item['irq'] for item in irq_data if item['irq'].isdigit()]
    
    # 3. Get affinities for all numeric IRQs
    affinities = get_all_affinities(active_irqs)
    
    # 4. Print Table
    header = f"{'IRQ':<6} | {'Device':<25} | {'Mask':<12} | {'CPUs':<15} | {'Pinned?'}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Map IRQ to device for display
    irq_to_device = {item['irq']: item['device'] for item in irq_data}
    
    for irq in active_irqs:
        if irq in affinities:
            aff = affinities[irq]
            device = irq_to_device.get(irq, "Unknown")[:25]
            mask = aff['mask']
            cpus_assigned = str(aff['cpus'])
            is_pinned = "Yes" if aff['is_pinned'] else "No"
            print(f"{irq:<6} | {device:<25} | {mask:<12} | {cpus_assigned:<15} | {is_pinned}")

    # 5. Load Summary (Using a mock rate if monitoring isn't active)
    # Here we'll just sum the total interrupts from proc_reader as a 'load' proxy 
    # to demonstrate the math if no real rate monitor is running.
    mock_rates = {}
    for item in irq_data:
        if item['irq'].isdigit():
            # Using current total / 1000 as a dummy 'rate' for visualization
            mock_rates[item['irq']] = {'rate': sum(item['counts']) / 1000.0}
            
    cpu_load = get_per_cpu_irq_load(affinities, mock_rates)
    
    print("\n--- Estimated Per-CPU IRQ Load Summary (Relative) ---")
    for cpu, load in cpu_load.items():
        bar = "█" * int(min(load * 2, 40))
        print(f"CPU {cpu:<2}: [{bar:<40}] {load:>8.2f} pts")

    print("\nNotes on IRQ Affinity:")
    print("- smp_affinity masks determine which cores 'service' a hardware interrupt vector.")
    print("- NUMA Awareness: Pinning Nic/Disk IRQs to the CPU closest to the hardware PCI-e lane ")
    print("  drastically reduces latency by keeping data in local L1/L2 caches.")
    print("- Production systems use 'irqbalance' to spread load, but high-performance servers ")
    print("  often disable it and manually pin IRQs for deterministic behavior.")

if __name__ == "__main__":
    main()
