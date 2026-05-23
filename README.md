🖥️ Linux Interrupt Priority Scheduler Simulator
A terminal-based Python application that simulates how the Linux OS handles hardware interrupts using real kernel data from `/proc/interrupts`. Demonstrates core Operating System concepts including interrupt handling, priority scheduling, preemption, context switching, SMP affinity, and live system monitoring — all in your Linux terminal.
---
📸 Demo
```
┌─ Linux Interrupt Priority Scheduler ──────────────────────────────────┐
│  Simulation Time: 42ms        Mode: PREEMPTIVE        IRQs: 12 loaded │
├─ Ready Queue ─────────────────┬─ CPU Execution ───────────────────────┤
│  IRQ 0  timer      P:1 ●●●   │  Running: IRQ 9 eth0                  │
│  IRQ 9  eth0       P:3 ●●    │  Progress: ████████░░░░  4.2ms / 5ms  │
│  IRQ 14 nvme       P:4 ●     │  Latency so far: 1.2ms                │
├─ Context Switch Log ──────────┴───────────────────────────────────────┤
│  \[t=12ms] IRQ 14 (nvme) PREEMPTED → IRQ 0 (timer) \[context saved]    │
│  \[t=13ms] IRQ 0 (timer) ISR completed | latency=0.8ms                │
│  \[t=13ms] IRQ 14 (nvme) RESUMED from context stack                   │# 🖥️ Linux Interrupt Priority Scheduler Simulator

> A terminal-based Python simulator that demonstrates how the Linux kernel handles hardware interrupts using real system interrupt data from `/proc/interrupts`.

This project visualizes core Operating System concepts such as **interrupt handling, priority scheduling, preemption, context switching, SMP affinity, interrupt storms, and live monitoring** — all inside an interactive terminal dashboard.

Ideal for:
- Operating Systems mini-projects
- Linux internals demonstrations
- Academic presentations & viva
- Learning kernel-level scheduling concepts visually

---

# 📸 Demo Preview

```text
┌─ Linux Interrupt Priority Scheduler ──────────────────────────────────┐
│  Simulation Time: 42ms        Mode: PREEMPTIVE        IRQs: 12 loaded │
├─ Ready Queue ─────────────────┬─ CPU Execution ───────────────────────┤
│  IRQ 0  timer      P:1 ●●●   │  Running: IRQ 9 eth0                  │
│  IRQ 9  eth0       P:3 ●●    │  Progress: ████████░░░░  4.2ms / 5ms  │
│  IRQ 14 nvme       P:4 ●     │  Latency so far: 1.2ms                │
├─ Context Switch Log ──────────┴───────────────────────────────────────┤
│  [t=12ms] IRQ 14 PREEMPTED → IRQ 0 (timer)                           │
│  [t=13ms] IRQ 0 completed | latency=0.8ms                            │
│  [t=13ms] IRQ 14 RESUMED from context stack                          │
├─ Metrics ─────────────────────────────────────────────────────────────┤
│  Avg Latency: 2.1ms   Avg Wait: 3.4ms   Throughput: 8 IRQs/100ms     │
└───────────────────────────────────────────────────────────────────────┘
```

---

# 🚀 Features

## ⚡ 1. Priority-Based Interrupt Scheduler
- Reads real interrupt information directly from Linux `/proc/interrupts`
- Simulates:
  - Non-preemptive scheduling
  - Preemptive interrupt scheduling
- Assigns priorities dynamically based on IRQ type
- Uses a min-heap ready queue for scheduling
- Displays:
  - Ready queue
  - CPU execution state
  - Context switch logs
  - Live scheduling metrics
  - Gantt-style execution visualization

---

## 📈 2. Real-Time Interrupt Rate Monitor
- Polls interrupt statistics continuously
- Calculates interrupts/sec for each device
- Displays:
  - Live bar charts
  - Rate spikes
  - Sparkline trends
- Detects abnormal interrupt bursts automatically
- Includes stress-testing mode using real I/O activity

---

## 🧠 3. SMP & CPU Affinity Visualization
- Reads real affinity masks from:

```bash
/proc/irq/<IRQ_NUMBER>/smp_affinity
```

- Visualizes:
  - IRQ-to-CPU mapping
  - Multi-core interrupt distribution
  - Load balancing behavior

### Simulated Modes
- Pinned mode
- Balanced mode (`irqbalance`)
- Worst-case single-core overload

---

## 🚨 4. Interrupt Storm Detection
- Injects synthetic interrupt storms
- Simulates:
  - Queue flooding
  - Latency spikes
  - Kernel throttling behavior
- Logs performance history to CSV
- Generates ASCII trend graphs for analysis

---

# 🎮 Available Modes

| Command | Description |
|---|---|
| `python main.py --mode demo` | Synthetic interrupt simulation |
| `python main.py --mode live` | Live `/proc/interrupts` visualization |
| `python main.py --mode compare` | Preemptive vs Non-preemptive comparison |
| `python main.py --mode report` | Generate simulation report |
| `python main.py --mode monitor` | Real-time interrupt monitor |
| `python main.py --mode stress-demo` | Stress-test interrupt handling |
| `python main.py --mode affinity` | CPU affinity visualization |
| `python main.py --mode affinity-live` | Live SMP affinity monitoring |
| `python main.py --mode storm --irq N --rate R` | Inject interrupt storm |
| `python main.py --mode graph` | Historical metrics visualization |

---

# 🛠️ Installation

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/linux-interrupt-scheduler.git
cd linux-interrupt-scheduler
```

## 2️⃣ Install Dependencies

```bash
pip install rich
```

## 3️⃣ Run the Simulator

```bash
python main.py --mode demo
```

---

# 📂 Project Structure

```text
linux-interrupt-scheduler/
│
├── main.py
├── proc_reader.py
├── interrupt_model.py
├── scheduler.py
├── isr_engine.py
├── metrics.py
├── tui_dashboard.py
│
├── rate_monitor.py
├── rate_visualizer.py
│
├── affinity_reader.py
├── smp_scheduler.py
├── affinity_visualizer.py
│
├── storm_detector.py
├── historical_metrics.py
│
├── metrics_history.csv
├── simulation_report.txt
├── requirements.txt
└── README.md
```

---

# 🧠 Operating System Concepts Demonstrated

| OS Concept | Implementation |
|---|---|
| Interrupt Handling | Real Linux IRQ parsing |
| ISR Execution | Simulated interrupt service routines |
| Priority Scheduling | Heap-based priority queue |
| Preemption | High-priority IRQ interruption |
| Context Switching | ISR save/restore simulation |
| Nested Interrupts | Multi-level interrupt handling |
| Interrupt Latency | Arrival-to-start timing metrics |
| SMP Scheduling | Multi-core IRQ distribution |
| CPU Affinity | Real affinity mask visualization |
| Interrupt Storms | Queue flooding simulation |
| Kernel Virtual Filesystem | `/proc` parsing |
| Linux HZ/Jiffies | Real timer interrupt behavior |

---

# 📊 Performance Results

## Preemptive vs Non-Preemptive Scheduling

| Metric | Non-Preemptive | Preemptive | Improvement |
|---|---|---|---|
| Timer IRQ Latency | ~14.2 ms | ~1.8 ms | ↓ 87% |
| Average IRQ Latency | ~9.4 ms | ~6.1 ms | ↓ 35% |
| Average Wait Time | ~8.6 ms | ~5.3 ms | ↓ 38% |
| Context Switches | 0 | 4–8/run | Tradeoff |

---

## SMP Scheduling Comparison

| Mode | Avg Latency | Load Imbalance |
|---|---|---|
| Worst-case | ~18.4 ms | 0.91 |
| Pinned | ~9.2 ms | 0.44 |
| Balanced | ~7.1 ms | 0.08 |

---

# 🔍 How the System Works

```text
Linux Kernel
     │
     ▼
/proc/interrupts
     │
     ▼
proc_reader.py
     │
     ▼
interrupt_model.py
     │
     ▼
scheduler.py
     │
     ├── Non-Preemptive Scheduler
     └── Preemptive Scheduler
               │
               ▼
        isr_engine.py
               │
               ▼
          metrics.py
               │
               ▼
      tui_dashboard.py
```

---

# ⚙️ Requirements

- Linux (Ubuntu recommended)
- Python 3.8+
- `rich` Python library

> ⚠️ This project works only on Linux because it depends on `/proc/interrupts`.

---

# 📚 Learning Resources

- Linux `/proc/interrupts` documentation
- Linux Kernel IRQ documentation
- Red Hat SMP Affinity docs
- *Operating System Concepts* — Silberschatz
- kernel.org interrupt handling references

---

# 🎯 Educational Value

This project demonstrates:
- Real-world OS scheduling behavior
- Linux kernel interaction without kernel modules
- Visualization of low-level system concepts
- Performance analysis using real interrupt data
- Multi-core interrupt balancing

It combines:
- Systems Programming
- Linux Internals
- Scheduling Algorithms
- Performance Monitoring
- Terminal UI Development

---

# 📄 License

MIT License — free to use for educational and learning purposes.

---

# 👨‍💻 Author

Built with Python on Linux using real kernel interrupt data.

If you found this project useful, consider giving it a ⭐ on GitHub.
├─ Metrics ─────────────────────────────────────────────────────────────┤
│  Avg Latency: 2.1ms   Avg Wait: 3.4ms   Throughput: 8 IRQs/100ms    │
└───────────────────────────────────────────────────────────────────────┘
```
---
🚀 Quick Start
```bash
# 1. Clone the project
git clone https://github.com/yourusername/linux-interrupt-scheduler
cd linux-interrupt-scheduler

# 2. Install the only dependency
pip install rich

# 3. Run the demo
python main.py --mode demo
```
> \*\*Requires Linux.\*\* `/proc/interrupts` is a Linux kernel virtual file — this project will not work on Windows or macOS.
---
✨ Features
Feature 1 — Core Priority Scheduler Simulator
Reads real interrupts from `/proc/interrupts`, classifies them by type, assigns priorities, and runs both non-preemptive and preemptive scheduling algorithms. Displays a live TUI dashboard with ready queue, CPU execution panel, context switch log, metrics, and Gantt chart.
Feature 2 — Real-Time Interrupt Rate Monitor
Polls `/proc/interrupts` every second and computes live interrupts/sec per device. Shows a color-coded bar chart with sparkline trends. Automatically detects and logs rate spikes (3× normal). Includes a stress-demo mode that triggers real I/O and shows interrupt rates change live.
Feature 3 — CPU Affinity Visualizer (SMP)
Reads real affinity bitmasks from `/proc/irq/N/smp\_affinity` and renders a CPU × IRQ grid showing which cores handle which interrupts. Simulates three modes — pinned, balanced, worst-case — and compares latency and load imbalance scores across all three.
Feature 4 — Interrupt Storm Detection + Historical Metrics
Injects a synthetic interrupt storm, demonstrates latency spikes on high-priority IRQs, and simulates kernel throttling. Logs metrics from every run to CSV and renders ASCII trend graphs for data-driven comparison across runs.
---
🎮 All Demo Modes
Command	Description
`python main.py --mode demo`	Synthetic 10-interrupt demo with live TUI
`python main.py --mode live`	Real `/proc/interrupts` data with TUI
`python main.py --mode compare`	Non-preemptive vs preemptive side-by-side
`python main.py --mode report`	Generate `simulation\_report.txt`
`python main.py --mode monitor`	Live interrupt rate bar chart dashboard
`python main.py --mode stress-demo`	Automated I/O stress + rate visualization
`python main.py --mode affinity`	CPU affinity grid + SMP comparison
`python main.py --mode affinity-live`	Auto-refreshing affinity view
`python main.py --mode storm --irq N --rate R`	Inject storm on IRQ N at R/sec
`python main.py --mode graph`	Historical metrics trend graphs
---
📁 Project Structure
```
linux-interrupt-scheduler/
│
├── main.py                  # Entry point — CLI modes
├── proc\_reader.py           # Parses /proc/interrupts
├── interrupt\_model.py       # Classifies IRQs, assigns priorities
├── scheduler.py             # Non-preemptive + preemptive schedulers
├── isr\_engine.py            # ISR execution simulator
├── metrics.py               # Latency, waiting time, turnaround time
├── tui\_dashboard.py         # Rich live terminal dashboard
│
├── rate\_monitor.py          # Delta-rate polling engine
├── rate\_visualizer.py       # Live rate bar chart TUI
│
├── affinity\_reader.py       # Reads smp\_affinity bitmasks
├── smp\_scheduler.py         # Multi-core scheduling simulation
├── affinity\_visualizer.py   # Affinity grid + SMP comparison panel
│
├── storm\_detector.py        # Storm injection + throttling simulation
├── historical\_metrics.py    # CSV logging + ASCII trend graphs
│
├── metrics\_history.csv      # Auto-generated run history
├── simulation\_report.txt    # Auto-generated report
├── requirements.txt
└── README.md
```
---
🧠 OS Concepts Demonstrated
Concept	How It's Shown
Interrupt Handling	Real IRQ data parsed live from `/proc/interrupts`
ISR (Interrupt Service Routine)	Simulated top-half execution with burst times
Priority Scheduling	Min-heap queue — timer=1, keyboard=2, network=3, disk=4
Preemption	Higher-priority IRQ interrupts a running ISR mid-execution
Context Switching	LIFO interrupt stack — paused ISR resumes after higher-priority one finishes
Nested Interrupts	Multi-level preemption tracked via context stack depth
Interrupt Latency	Measured per IRQ: `start\_time − arrival\_time`
SMP / CPU Affinity	Real `/proc/irq/N/smp\_affinity` bitmasks visualized
irqbalance	Simulated balanced mode vs real pinned affinity
Interrupt Storm	Injected storm floods queue, spikes latency, triggers throttle
Virtual Filesystem	`/proc` as kernel data interface — read without disk I/O
Linux HZ / Jiffies	Timer IRQ rate matches kernel HZ (250 or 1000/sec)
---
📊 Key Results
Preemptive vs Non-Preemptive Scheduling:
Metric	Non-Preemptive	Preemptive	Change
TIMER avg latency	~14.2 ms	~1.8 ms	↓ 87%
All IRQs avg latency	~9.4 ms	~6.1 ms	↓ 35%
Avg waiting time	~8.6 ms	~5.3 ms	↓ 38%
Context switches	0	4–8 per run	cost of preemption
SMP Distribution Modes:
Mode	Avg Latency	Load Imbalance Score
Worst-case (all on CPU0)	~18.4 ms	0.91 (severe)
Pinned (real affinity)	~9.2 ms	0.44 (moderate)
Balanced (irqbalance)	~7.1 ms	0.08 (near-balanced)
---
⚙️ Requirements
Linux (Ubuntu 20.04+ recommended)
Python 3.8+
`pip install rich`
No root access required. Standard user read permissions are sufficient for `/proc/interrupts` and `/proc/irq/`.
---
🔍 How It Works
```
Linux Kernel
     │
     ▼
/proc/interrupts  ←──────────────────── polled every 1 second (Feature 2)
     │
     ▼
proc\_reader.py  ──→  interrupt\_model.py  ──→  scheduler.py
(parse)               (classify + priority)    (min-heap queue)
                                                    │
                           ┌────────────────────────┤
                           ▼                        ▼
                    Non-Preemptive           Preemptive
                    Scheduler                Scheduler
                           │                        │
                           └───────────┬────────────┘
                                       ▼
                                 isr\_engine.py
                                 (simulate ISR execution)
                                       │
                                       ▼
                                  metrics.py
                                  (latency, wait, turnaround)
                                       │
                                       ▼
                               tui\_dashboard.py
                               (Rich live terminal UI)
```
---
📖 Learning Resources
Linux `/proc/interrupts` documentation
IRQ affinity — Red Hat docs
Linux Interrupt Handling — kernel.org
Operating System Concepts — Silberschatz (textbook)
---
📄 License
MIT License — free to use for educational purposes.
---
<p align="center">Built on Linux · Powered by Python · Data from the kernel itself</p>
