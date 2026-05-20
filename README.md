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
│  \[t=13ms] IRQ 14 (nvme) RESUMED from context stack                   │
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
