#!/usr/bin/env python3
"""
rate_monitor.py - Real-time Interrupt Rate Monitoring for Linux.

This module monitors /proc/interrupts to calculate the delta of interrupt 
counts over time, identifying high-frequency hardware events and system trends.
"""

import time
import collections
from proc_reader import read_interrupts

class InterruptRateMonitor:
    """
    Tracks interrupt counts and calculates per-second rates.
    """
    def __init__(self, poll_interval=1.0, history_size=30):
        self.poll_interval = poll_interval
        self.history_size = history_size
        
        # History storage using deques (O(1) popleft)
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=history_size))
        
        # Snapshots for delta calculation
        self.prev_snapshot = None
        self.curr_snapshot = None
        self.prev_time = None
        self.curr_time = None

    def _read_counts(self):
        """
        Reads /proc/interrupts and aggregates counts across all CPUs.
        
        Why sum all CPU columns? 
        Interrupts in Linux can be balanced across multiple cores. To get the 
        total system-wide rate for a specific IRQ, we must sum the hits recorded 
        by each individual CPU.
        """
        raw_data = read_interrupts()
        counts = {}
        for item in raw_data:
            irq = item['irq']
            # Total count = sum of all per-CPU columns for that IRQ row
            total = sum(item['counts'])
            counts[irq] = {
                "total": total,
                "device": item['device'],
                "type": item['type']
            }
        return counts

    def compute_rates(self):
        """
        Computes the rate (interrupts/sec) based on the delta between snapshots.
        
        What is delta counting?
        /proc/interrupts counts are cumulative since boot. To find the current 
        activity level, we calculate (Current - Previous) / Time Elapsed.
        """
        if self.prev_snapshot is None or self.curr_snapshot is None:
            return {}

        elapsed = self.curr_time - self.prev_time
        if elapsed <= 0:
            return {}

        rates = {}
        for irq, data in self.curr_snapshot.items():
            prev_data = self.prev_snapshot.get(irq)
            if prev_data:
                delta = data['total'] - prev_data['total']
                rate = round(delta / elapsed, 1)
                rates[irq] = {
                    "device": data['device'],
                    "type": data['type'],
                    "rate": rate,
                    "total": data['total']
                }
        return rates

    def start_monitoring(self):
        """
        Generator yielding a rates dict every poll_interval seconds.
        """
        # Initial snapshot
        self.prev_snapshot = self._read_counts()
        self.prev_time = time.time()
        
        try:
            while True:
                time.sleep(self.poll_interval)
                
                self.curr_snapshot = self._read_counts()
                self.curr_time = time.time()
                
                rates = self.compute_rates()
                
                # Update history for sparklines
                for irq, data in rates.items():
                    self.history[irq].append(data['rate'])
                
                yield rates
                
                # Cycle snapshots
                self.prev_snapshot = self.curr_snapshot
                self.prev_time = self.curr_time
        except StopIteration:
            pass

    def get_sparkline(self, irq, length=10):
        """
        Converts the last character trend for the IRQ into block characters.
        ▁▂▃▄▅▆▇█
        """
        history = list(self.history[irq])
        if not history:
            return ""
        
        # Take the tail of the history
        tail = history[-length:]
        
        chars = " ▂▃▄▅▆▇█"
        max_val = max(tail) if max(tail) > 0 else 1
        
        spark = ""
        for val in tail:
            idx = int((val / max_val) * (len(chars) - 1))
            spark += chars[idx]
        return spark

    def get_top_n(self, rates_dict, n=10):
        """
        Returns top N active IRQs sorted by rate.
        
        Why filter zero-rate IRQs?
        Standard PC/Server hardware has hundreds of register IRQ lines, but
        most are idle most of the time. Filtering zeros allows us to focus on 
        active components like the System Timer or Network Interface.
        """
        active = {k: v for k, v in rates_dict.items() if v['rate'] > 0}
        sorted_active = sorted(active.items(), key=lambda x: x[1]['rate'], reverse=True)
        return sorted_active[:n]

def main():
    monitor = InterruptRateMonitor(poll_interval=1.0)
    print(f"--- Monitoring Interrupt Rates (Interval: {monitor.poll_interval}s) ---")
    print(f"{'IRQ':<8} {'RATE (Hz)':<12} {'TOTAL':<15} {'DEVICE'}")
    print("-" * 50)
    
    count = 0
    try:
        for rates in monitor.start_monitoring():
            top_10 = monitor.get_top_n(rates, n=10)
            
            # Print timestamp
            print(f"\n[Snapshot {count+1} - {time.strftime('%H:%M:%S')}]")
            
            # Show highest rate IRQ summary
            if top_10:
                highest_irq, data = top_10[0]
                spark = monitor.get_sparkline(highest_irq)
                print(f"Top Activity: IRQ {highest_irq} ({data['device']}) @ {data['rate']} Hz {spark}")
            
            # Print detailed table for top 5
            for irq, data in top_10[:5]:
                print(f"{irq:<8} {data['rate']:<12.1f} {data['total']:<15} {data['device']}")
            
            count += 1
            if count >= 10:
                break
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
