# Linux Interrupt Priority Scheduler Simulator

A modular Python-based system to monitor, model, and simulate Linux kernel interrupt handling.

## Features
- **Real-time Parsing**: Extracts live data from `/proc/interrupts`.
- **Priority Modeling**: Classifies interrupts (Timer, Disk, Network, etc.) with kernel-standard priorities.
- **Scheduling Simulation**: Covers both **Non-Preemptive** and **Preemptive (Nested)** scheduling algorithms.
- **Performance Metrics**: Calculates Latency, Waiting Time, Turnaround Time, CPU Utilization, and Throughput.
- **Visual Dashboards**: High-fidelity terminal UIs built with the `rich` library.

## Getting Started

### Installation
Ensure you have Python 3.x and the `rich` library installed:
```bash
pip install rich
```

### Usage

#### 1. Interactive Dashboard
Explore the scheduler logic with real system data or synthetic scenarios.
```bash
python3 main.py --mode demo
```

#### 2. Real-time Rate Monitor
Watch live interrupt counts and frequencies across your system CPUs.
```bash
python3 main.py --mode monitor
```
**Example Output:**
```text
Top Activity: IRQ LOC (Local timer interrupts) @ 4211.6 Hz █▇▇▇▆
LOC      4211.6       4007544         Local timer interrupts
IWI      365.3        258655          IRQ work interrupts
```

#### 3. Stress Demo
See how real hardware activity (Disk I/O, Network traffic) affects interrupt rates.
```bash
python3 main.py --mode stress-demo
```
This mode triggers `dd` and `ping` commands while visualizing the resulting spikes in the dashboard.

#### 4. Performance Metrics
Compare the efficiency of Preemptive vs Non-Preemptive scheduling.
```bash
python3 metrics.py
```

## Module Overview
- `proc_reader.py`: Low-level parser for virtual filesystem data.
- `interrupt_model.py`: High-level classification and priority mapping.
- `scheduler.py`: The core scheduling engine (Generators for live updates).
- `metrics.py`: Aggregate statistics and performance comparison.
- `tui_dashboard.py`: Live execution visualization.
- `rate_monitor.py`: Delta-based rate calculation.
- `rate_visualizer.py`: Full-screen monitoring dashboard.

## Why it matters
Missing a **Timer Interrupt (Prio 1)** in Linux can lead to system drift, UI lag, and broken scheduling ticks. This project demonstrates why priorities and preemption are critical for modern kernel design.
