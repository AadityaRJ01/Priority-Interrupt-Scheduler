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

    viz_thread = threading.Thread(target=viz.run, daemon=True)
    viz_thread.start()

    try:
        # Step 1: Baseline
        time.sleep(3)

        # Step 2: Disk I/O
        print(">>> Generating disk I/O interrupts...")
        subprocess.run(
            ["dd", "if=/dev/urandom", "of=/tmp/stress_test", "bs=4k", "count=10000"],
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)

        # Step 3: Network
        print(">>> Generating network interrupts...")
        subprocess.run(
            ["ping", "127.0.0.1", "-c", "50", "-i", "0.1"],
            stdout=subprocess.DEVNULL
        )
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
    Auto-refreshing affinity dashboard with change logging.
    """
    print("Entering Live Affinity Mode (refresh every 5s). Press Ctrl+C to exit.")
    time.sleep(1)

    prev_data = None
    changes_log = []

    try:
        while True:
            curr_data = viz.fetch_data()

            if prev_data:
                for cpu_idx, load in curr_data['load'].items():
                    prev_load = prev_data['load'].get(cpu_idx, 0)
                    if abs(load - prev_load) > 10:
                        diff = load - prev_load
                        trend = "+" if diff > 0 else ""
                        msg = f"CPU{cpu_idx} load changed from {prev_load:.1f} to {load:.1f} ({trend}{diff:.1f}/s)"
                        changes_log.append(msg)

                top_irq = max(curr_data['rates'], key=lambda k: curr_data['rates'][k]['rate'])
                prev_rate = prev_data['rates'].get(top_irq, {}).get('rate', 0)
                if abs(curr_data['rates'][top_irq]['rate'] - prev_rate) > 50:
                    msg = (
                        f"IRQ {top_irq} ({curr_data['rates'][top_irq]['device'][:10]}) "
                        f"rate changed from {prev_rate:.1f}/s to "
                        f"{curr_data['rates'][top_irq]['rate']:.1f}/s"
                    )
                    changes_log.append(msg)

            viz.run()

            if changes_log:
                print("\n[Latest Activity Logs]")
                for log in changes_log[-3:]:
                    print(f"  {log}")

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


def run_compare_mode():
    """
    Runs both schedulers and prints a side-by-side comparison of metrics.
    """
    try:
        from proc_reader import read_interrupts
        from interrupt_model import classify_and_prioritize
        from scheduler import Scheduler, PreemptiveScheduler
    except ImportError as e:
        print(f"[Error] Missing module: {e}")
        return

    print("\n" + "="*60)
    print("      SCHEDULING ALGORITHM COMPARISON")
    print("="*60)

    # --- Non-Preemptive ---
    print("\n[1/2] Running Non-Preemptive Scheduler...")
    raw1 = read_interrupts()
    interrupts1 = classify_and_prioritize(raw1)
    s1 = Scheduler()
    s1.load_interrupts(interrupts1)
    _ = list(s1.run())
    completed_np = s1.execution_log

    # --- Preemptive ---
    print("[2/2] Running Preemptive Scheduler...")
    raw2 = read_interrupts()
    interrupts2 = classify_and_prioritize(raw2)
    s2 = PreemptiveScheduler()
    s2.load_interrupts(interrupts2)
    _ = list(s2.simulate())
    completed_p = s2.execution_log

    # --- Metrics ---
    np_waits = [i.waiting_time    for i in completed_np if hasattr(i, 'waiting_time')]
    p_waits  = [i.waiting_time    for i in completed_p  if hasattr(i, 'waiting_time')]
    np_lat   = [i.latency         for i in completed_np if hasattr(i, 'latency')]
    p_lat    = [i.latency         for i in completed_p  if hasattr(i, 'latency')]
    np_tat   = [i.turnaround_time for i in completed_np if hasattr(i, 'turnaround_time')]
    p_tat    = [i.turnaround_time for i in completed_p  if hasattr(i, 'turnaround_time')]
    np_cs    = getattr(s1, 'context_switch_count', 0)
    p_cs     = getattr(s2, 'context_switch_count', 0)

    print("\n" + "="*60)
    print(f"{'METRIC':<25} {'NON-PREEMPTIVE':>15} {'PREEMPTIVE':>15}")
    print("="*60)

    if np_waits and p_waits:
        print(f"{'Avg Waiting Time':<25} "
              f"{sum(np_waits)/len(np_waits):>14.2f}ms "
              f"{sum(p_waits)/len(p_waits):>14.2f}ms")
    if np_lat and p_lat:
        print(f"{'Avg Latency':<25} "
              f"{sum(np_lat)/len(np_lat):>14.2f}ms "
              f"{sum(p_lat)/len(p_lat):>14.2f}ms")
    if np_tat and p_tat:
        print(f"{'Avg Turnaround Time':<25} "
              f"{sum(np_tat)/len(np_tat):>14.2f}ms "
              f"{sum(p_tat)/len(p_tat):>14.2f}ms")

    print(f"{'Context Switches':<25} {np_cs:>15} {p_cs:>15}")
    print("="*60)
    print("\nDone.")


def run_live_mode():
    """
    Runs the TUI dashboard with real /proc/interrupts data.
    """
    if not run_simulation:
        print("[Error] tui_dashboard.py not found. Live mode unavailable.")
        return
    print("Starting live mode with real /proc/interrupts data...")
    try:
        run_simulation('live', real_data=True)
    except Exception as e:
        print(f"[Error] Live mode failed: {e}")


def run_report_mode():
    """
    Generates a simulation_report.txt file.
    """
    try:
        from proc_reader import read_interrupts
        from interrupt_model import classify_and_prioritize
        import platform
    except ImportError as e:
        print(f"[Error] Missing module: {e}")
        return

    print("Generating simulation report...")

    raw = read_interrupts()
    interrupts = classify_and_prioritize(raw)

    with open('simulation_report.txt', 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("LINUX INTERRUPT PRIORITY SCHEDULER - SIMULATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Hostname    : {platform.node()}\n")
        f.write(f"Kernel      : {platform.release()}\n")
        f.write(f"CPU Count   : {os.cpu_count()}\n")
        f.write(f"IRQs Loaded : {len(interrupts)}\n\n")
        f.write("Interrupt Classification:\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'IRQ':<8} {'TYPE':<12} {'PRIORITY':<10} {'BURST':<10} DEVICE\n")
        f.write("-" * 60 + "\n")
        for irq in interrupts:
            f.write(
                f"{str(irq.irq_number):<8} "
                f"{irq.irq_type:<12} "
                f"{irq.priority:<10} "
                f"{irq.burst_time:<10} "
                f"{irq.device_name}\n"
            )
        f.write("\nSee --mode compare for full scheduler metrics.\n")

    print("Report saved to simulation_report.txt")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Linux Interrupt Scheduler Simulator")
    parser.add_argument(
        "--mode",
        choices=[
            'demo', 'monitor', 'stress-demo',
            'affinity', 'affinity-live',
            'compare', 'live', 'report'
        ],
        default="demo",
        help="Operating mode for the simulator"
    )

    args = parser.parse_args()

    if args.mode == 'monitor':
        run_monitor_mode()

    elif args.mode == 'stress-demo':
        run_stress_demo()

    elif args.mode == 'affinity':
        run_affinity_mode(live=False)

    elif args.mode == 'affinity-live':
        run_affinity_mode(live=True)

    elif args.mode == 'compare':
        run_compare_mode()

    elif args.mode == 'live':
        run_live_mode()

    elif args.mode == 'report':
        run_report_mode()

    elif args.mode == 'demo':
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