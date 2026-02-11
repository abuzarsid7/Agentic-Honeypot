"""
Performance Benchmarks for Normalization Module
Run with: python benchmark_normalizer.py
"""

import time
from normalizer import normalize_input

# Test cases representing real-world scam messages
TEST_CASES = [
    "Fr33 Bitcoin!!! Click hxxps://paypal[.]com",
    "Urgent @ction n33d3d",
    "Your account will be blocked today. Send OTP to +91-9876543210",
    "C0ngr@tul@ti0ns! Y0u w0n 10 l@kh. Visit bit[.]ly/scam",
    "Your bank account blocked. Verify at hxxps://bank[.]com/verify",
    "Send m0n3y t0 scammer@paytm immediately",
    "Urgent KYC update needed call now",
    "Call +91 (987) 654-3210 n0w",
    "Win 1 cr0re! Click: tinyurl[.]com/fake",
    "Transfer Rs.5000 to winner@upi today"
]


def benchmark_single_message(text: str, iterations: int = 1000) -> float:
    """Benchmark normalization of a single message"""
    start = time.perf_counter()
    for _ in range(iterations):
        normalize_input(text)
    end = time.perf_counter()
    return (end - start) / iterations * 1000  # Convert to milliseconds


def benchmark_batch(test_cases: list, iterations: int = 100) -> dict:
    """Benchmark batch processing"""
    results = {}
    
    for i, text in enumerate(test_cases, 1):
        avg_time = benchmark_single_message(text, iterations)
        results[f"test_{i}"] = {
            "input_length": len(text),
            "avg_time_ms": round(avg_time, 4),
            "throughput_per_sec": int(1000 / avg_time) if avg_time > 0 else float('inf')
        }
    
    return results


if __name__ == "__main__":
    print("═" * 80)
    print("NORMALIZATION MODULE - PERFORMANCE BENCHMARKS")
    print("═" * 80)
    print()
    
    # Warmup
    print("Warming up...")
    for text in TEST_CASES[:3]:
        normalize_input(text)
    print("Warmup complete.\n")
    
    # Run benchmarks
    print("Running benchmarks (100 iterations per test)...")
    results = benchmark_batch(TEST_CASES, iterations=100)
    
    print("\n" + "─" * 80)
    print(f"{'Test':<10} {'Input Len':<12} {'Avg Time (ms)':<18} {'Throughput/sec':<15}")
    print("─" * 80)
    
    total_time = 0
    for test_name, metrics in results.items():
        print(f"{test_name:<10} "
              f"{metrics['input_length']:<12} "
              f"{metrics['avg_time_ms']:<18.4f} "
              f"{metrics['throughput_per_sec']:<15,}")
        total_time += metrics['avg_time_ms']
    
    print("─" * 80)
    avg_time = total_time / len(results)
    avg_throughput = int(1000 / avg_time) if avg_time > 0 else float('inf')
    
    print(f"\n{'AVERAGE':<10} {'-':<12} {avg_time:<18.4f} {avg_throughput:<15,}")
    print()
    print("═" * 80)
    print("SUMMARY")
    print("═" * 80)
    print(f"✓ Average processing time: {avg_time:.4f} ms per message")
    print(f"✓ Average throughput: {avg_throughput:,} messages/second")
    print(f"✓ Total test cases: {len(results)}")
    print("═" * 80)
    
    # Production estimate
    print("\n📊 PRODUCTION ESTIMATES")
    print("─" * 80)
    daily_volume = 1_000_000
    processing_time_sec = (daily_volume * avg_time) / 1000
    print(f"For {daily_volume:,} messages/day:")
    print(f"  • Total processing time: {processing_time_sec:.2f} seconds")
    print(f"  • That's only {processing_time_sec/60:.2f} minutes of CPU time!")
    print(f"  • Load: {processing_time_sec/86400*100:.4f}% of a single core")
    print("═" * 80)
