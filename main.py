#!/usr/bin/env python3
"""
main.py - Entry point for the Linux Interrupt Priority Scheduler Simulator.

This module provides a CLI to launch simulations, TUI dashboards, 
and real-time interrupt monitoring with stress testing capabilities.
"""

import argparse
import time
import sys
import threading
import subprocess
import os

# Guarded imports for modularity and safety
try:
    from tui_dashboard import startup_screen, run_simulation
except ImportError:
    startup_screen = None
    run_simulation = None

try:
    from rate_visualizer import RateVisualizer
    from rate_monitor import InterruptRateMonitor
except ImportError:
    RateVisualizer = None
    InterruptRateMonitor = None

try:
    from affinity_visualizer import AffinityVisualizer
    from affinity_reader import get_cpu_count
except ImportError:
    AffinityVisualizer = None
    get_cpu_count = None

def run_monitor_mode():
    """
    Launches the real-time interrupt rate monitor with a session summary on exit.
    """
    if not RateVisualizer:
        print("[Error] rate_visualizer.py not found. Monitor mode unavailable.")
        return

    print("\nStarting real-time interrupt rate monitor...")
    print("Reading from /proc/interrupts every 1 second")
    print("Press Ctrl+C to stop")
    
    for i in range(3, 0, -1):
        print(f"Starting in {i}...", end="\r")
        time.sleep(1)
    
    viz = RateVisualizer(poll_interval=1.0)
    start_time = time.time()
    
    try:
        viz.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Session Summary
        duration = time.time() - start_time
        print("\n" + "="*50)
        print(" SESSION SUMMARY")
        print("="*50)
        print(f"Total Runtime       : {duration:.1f} seconds")
        print(f"Peak IRQ Observed   : {viz.peak_rate['irq']} ({viz.peak_rate['value']:.1f} Hz)")
        
        total_observed = sum(viz.total_counts.values())
        print(f"Total Interrupts    : {total_observed}")
        
        most_consistent = "None"
        if viz.prev_rates:
           most_consistent = max(viz.prev_rates, key=viz.prev_rates.get)
        print(f"Most Active IRQ     : {most_consistent}")
        print("="*50 + "\n")

def run_stress_demo():
    """
    Simulates real hardware activity while monitoring interrupt rates.
    """
    if not RateVisualizer:
        print("[Error] rate_visualizer.py not found. Stress demo unavailable.")
        return

    print("\n>>> STARTING INTERRUPT STRESS DEMO <<<")
    print("The Dashboard will launch in the background.")
    print("Watch the 'Event Log' and 'Bars' for spikes!\n")
    time.sleep(2)

    viz = RateVisualizer(poll_interval=1.0)
    
    # Run visualizer in a separate thread to allow stress actions in main thread
    viz_thread = threading.Thread(target=viz.run, daemon=True)
    viz_thread.start()

    try:
        # Step 1: Baseline
        time.sleep(3)
        
        # Step 2: Disk I/O
        print(">>> Generating disk I/O interrupts...")
        subprocess.run(["dd", "if=/dev/urandom", "of=/tmp/stress_test", "bs=4k", "count=10000"], 
                       stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        # Step 3: Network
        print(">>> Generating network interrupts...")
        # Rapid localhost pings (simulating high network traffic)
        # Note: In Linux, ping -f (flood) is great but needs root. We use -i 0.1 for rapid.
        subprocess.run(["ping", "127.0.0.1", "-c", "50", "-i", "0.1"], 
                       stdout=subprocess.DEVNULL)
        time.sleep(3)
        
        # Step 4: Back to baseline
        print(">>> Back to baseline...")
        time.sleep(5)
        
    finally:
        if os.path.exists("/tmp/stress_test"):
            os.remove("/tmp/stress_test")
        print("\nStress Demo Completed.")

def run_affinity_mode(live=False):
    """
    Launches the CPU Affinity Visualizer dashboard.
    """
    if not AffinityVisualizer:
        print("[Error] affinity_visualizer.py not found. Affinity mode unavailable.")
        return

    cpus = get_cpu_count()
    print(f"Reading CPU affinity masks from /proc/irq/*/smp_affinity...")
    print(f"Analyzing interrupt distribution across {cpus} CPU cores...")
    time.sleep(1)

    viz = AffinityVisualizer()
    
    if live:
        run_affinity_live_mode(viz)
    else:
        while True:
            viz.run()
            print("\n" + "-"*50)
            choice = input("Press [R] to refresh | [L] for live mode | [Q] to quit: ").upper()
            if choice == 'R':
                continue
            elif choice == 'L':
                run_affinity_live_mode(viz)
                break
            elif choice == 'Q':
                break

def run_affinity_live_mode(viz):
    """
    Auto-refreshing dashboard with change logging.
    """
    print("Entering Live Affinity Mode (refresh every 5s). Press Ctrl+C to exit.")
    time.sleep(1)
    
    prev_data = None
    changes_log = []
    
    try:
        while True:
            curr_data = viz.fetch_data()
            
            # Simple change detection
            if prev_data:
                # CPU Load changes
                for cpu_idx, load in curr_data['load'].items():
                    prev_load = prev_data['load'].get(cpu_idx, 0)
                    if abs(load - prev_load) > 10: # Threshold for 'significant'
                        diff = load - prev_load
                        trend = "+" if diff > 0 else ""
                        msg = f"CPU{cpu_idx} load changed from {prev_load:.1f} to {load:.1f} ({trend}{diff:.1f}/s)"
                        changes_log.append(msg)
                
                # IRQ Rate changes
                top_irq = max(curr_data['rates'], key=lambda k: curr_data['rates'][k]['rate'])
                prev_rate = prev_data['rates'].get(top_irq, {}).get('rate', 0)
                if abs(curr_data['rates'][top_irq]['rate'] - prev_rate) > 50:
                    msg = f"IRQ {top_irq} ({curr_data['rates'][top_irq]['device'][:10]}) rate changed from {prev_rate:.1f}/s to {curr_data['rates'][top_irq]['rate']:.1f}/s"
                    changes_log.append(msg)

            # Update dashboard (Note: Standard AffinityVisualizer.run() doesn't show logs, 
            # so we'll print them after the TUI refresh for simplicity in this implementation)
            viz.run()
            
            if changes_log:
                print("\n[Latest Activity Logs]")
                for log in changes_log[-3:]: # Show last 3
                    print(f"  {log}")
            
            # Countdown
            for i in range(5, 0, -1):
                print(f"Next refresh in {i}s...", end="\r")
                time.sleep(1)
                
            prev_data = curr_data
            
    except KeyboardInterrupt:
        print("\n\n>>> LIVE AFFINITY SESSION SUMMARY <<<")
        if changes_log:
            print(f"Significant events detected: {len(changes_log)}")
            print(f"Most recent: {changes_log[-1]}")
        else:
            print("No significant changes detected during session.")
        print("-" * 40)

def main():
    parser = argparse.ArgumentParser(description="Linux Interrupt Scheduler Simulator")
    parser.add_argument("--mode", choices=["demo", "monitor", "stress-demo", "affinity", "affinity-live"], default="demo",
                        help="Operating mode for the simulator")
    
    args = parser.parse_args()

    if args.mode == "monitor":
        run_monitor_mode()
    elif args.mode == "stress-demo":
        run_stress_demo()
    elif args.mode == "affinity":
        run_affinity_mode(live=False)
    elif args.mode == "affinity-live":
        run_affinity_mode(live=True)
    else:
        # Default interactive menu
        if not startup_screen:
            print("[Error] tui_dashboard.py not found. Interactive demo unavailable.")
            return

        while True:
            choice, real_data = startup_screen()
            if choice == 'Q':
                break
            elif choice == '4':
                run_monitor_mode()
                continue
            elif choice == '5':
                run_affinity_mode()
                continue
            
            try:
                run_simulation(choice, real_data)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(3)

if __name__ == "__main__":
    main()
