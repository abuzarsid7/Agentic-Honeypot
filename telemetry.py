"""
Production Telemetry & Metrics System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose: Real-time monitoring and performance tracking for honeypot system
Features:
  • API request metrics (latency, throughput, errors)
  • Scam detection statistics
  • Intelligence extraction tracking
  • Normalization performance benchmarks
  • Session analytics

Run benchmarks: python telemetry.py
Import for production: from telemetry import track_request, get_metrics
"""

import time
from datetime import datetime
from collections import defaultdict
from typing import Dict, Optional
from contextlib import contextmanager
from normalizer import normalize_input

# ═══════════════════════════════════════════════════════════════
# PRODUCTION METRICS STORAGE
# ═══════════════════════════════════════════════════════════════

class MetricsCollector:
    """Thread-safe metrics collector for production use"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics"""
        self.start_time = datetime.now()
        
        # API Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0.0
        
        # Detection Metrics
        self.scams_detected = 0
        self.scams_missed = 0
        self.total_messages_analyzed = 0
        
        # Intelligence Metrics
        self.urls_extracted = 0
        self.phones_extracted = 0
        self.upis_extracted = 0
        self.accounts_extracted = 0
        
        # Normalization Metrics
        self.normalizations_applied = 0
        self.obfuscations_defeated = 0
        
        # Session Metrics
        self.active_sessions = defaultdict(dict)
        self.completed_sessions = 0
        
        # Error Tracking
        self.errors_by_type = defaultdict(int)
        self.last_error = None
    
    def track_request(self, latency_ms: float, success: bool = True):
        """Track API request"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_latency_ms += latency_ms
    
    def track_detection(self, detected: bool):
        """Track scam detection result"""
        self.total_messages_analyzed += 1
        if detected:
            self.scams_detected += 1
        else:
            self.scams_missed += 1
    
    def track_intelligence(self, intel_type: str, count: int = 1):
        """Track intelligence extraction"""
        if intel_type == "url":
            self.urls_extracted += count
        elif intel_type == "phone":
            self.phones_extracted += count
        elif intel_type == "upi":
            self.upis_extracted += count
        elif intel_type == "account":
            self.accounts_extracted += count
    
    def track_normalization(self, obfuscation_found: bool):
        """Track normalization application"""
        self.normalizations_applied += 1
        if obfuscation_found:
            self.obfuscations_defeated += 1
    
    def track_error(self, error_type: str, error_msg: str):
        """Track error occurrence"""
        self.errors_by_type[error_type] += 1
        self.last_error = {
            "type": error_type,
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_metrics(self) -> Dict:
        """Get current metrics snapshot"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        avg_latency = (self.total_latency_ms / self.total_requests) if self.total_requests > 0 else 0
        
        return {
            "system": {
                "uptime_seconds": round(uptime, 2),
                "started_at": self.start_time.isoformat()
            },
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": round((self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0, 2),
                "avg_latency_ms": round(avg_latency, 4),
                "requests_per_second": round(self.total_requests / uptime if uptime > 0 else 0, 2)
            },
            "detection": {
                "messages_analyzed": self.total_messages_analyzed,
                "scams_detected": self.scams_detected,
                "scams_missed": self.scams_missed,
                "detection_rate": round((self.scams_detected / self.total_messages_analyzed * 100) if self.total_messages_analyzed > 0 else 0, 2)
            },
            "intelligence": {
                "urls_extracted": self.urls_extracted,
                "phones_extracted": self.phones_extracted,
                "upis_extracted": self.upis_extracted,
                "accounts_extracted": self.accounts_extracted,
                "total_intel": self.urls_extracted + self.phones_extracted + self.upis_extracted + self.accounts_extracted
            },
            "normalization": {
                "total_normalizations": self.normalizations_applied,
                "obfuscations_defeated": self.obfuscations_defeated,
                "obfuscation_rate": round((self.obfuscations_defeated / self.normalizations_applied * 100) if self.normalizations_applied > 0 else 0, 2)
            },
            "sessions": {
                "active": len(self.active_sessions),
                "completed": self.completed_sessions
            },
            "errors": {
                "total": sum(self.errors_by_type.values()),
                "by_type": dict(self.errors_by_type),
                "last_error": self.last_error
            }
        }
    
    def print_summary(self):
        """Print metrics summary to console"""
        metrics = self.get_metrics()
        
        print("\n" + "═" * 80)
        print("📊 HONEYPOT TELEMETRY SUMMARY")
        print("═" * 80)
        
        print(f"\n⏱️  SYSTEM")
        print(f"  • Uptime: {metrics['system']['uptime_seconds']:.2f} seconds")
        print(f"  • Started: {metrics['system']['started_at']}")
        
        print(f"\n📡 API REQUESTS")
        print(f"  • Total: {metrics['requests']['total']}")
        print(f"  • Successful: {metrics['requests']['successful']}")
        print(f"  • Failed: {metrics['requests']['failed']}")
        print(f"  • Success Rate: {metrics['requests']['success_rate']}%")
        print(f"  • Avg Latency: {metrics['requests']['avg_latency_ms']:.4f} ms")
        print(f"  • Throughput: {metrics['requests']['requests_per_second']:.2f} req/sec")
        
        print(f"\n🔍 SCAM DETECTION")
        print(f"  • Messages Analyzed: {metrics['detection']['messages_analyzed']}")
        print(f"  • Scams Detected: {metrics['detection']['scams_detected']}")
        print(f"  • Detection Rate: {metrics['detection']['detection_rate']}%")
        
        print(f"\n🎯 INTELLIGENCE EXTRACTION")
        print(f"  • URLs: {metrics['intelligence']['urls_extracted']}")
        print(f"  • Phone Numbers: {metrics['intelligence']['phones_extracted']}")
        print(f"  • UPI IDs: {metrics['intelligence']['upis_extracted']}")
        print(f"  • Accounts: {metrics['intelligence']['accounts_extracted']}")
        print(f"  • Total Intel: {metrics['intelligence']['total_intel']}")
        
        print(f"\n🔧 NORMALIZATION")
        print(f"  • Total Normalizations: {metrics['normalization']['total_normalizations']}")
        print(f"  • Obfuscations Defeated: {metrics['normalization']['obfuscations_defeated']}")
        print(f"  • Obfuscation Rate: {metrics['normalization']['obfuscation_rate']}%")
        
        print(f"\n💬 SESSIONS")
        print(f"  • Active: {metrics['sessions']['active']}")
        print(f"  • Completed: {metrics['sessions']['completed']}")
        
        if metrics['errors']['total'] > 0:
            print(f"\n❌ ERRORS")
            print(f"  • Total: {metrics['errors']['total']}")
            for error_type, count in metrics['errors']['by_type'].items():
                print(f"  • {error_type}: {count}")
        
        print("\n" + "═" * 80)


# Global metrics collector instance
_metrics = MetricsCollector()


# ═══════════════════════════════════════════════════════════════
# PUBLIC API FOR PRODUCTION USE
# ═══════════════════════════════════════════════════════════════

@contextmanager
def track_request():
    """Context manager for tracking API requests with automatic timing"""
    start = time.perf_counter()
    success = True
    try:
        yield
    except Exception as e:
        success = False
        _metrics.track_error(type(e).__name__, str(e))
        raise
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        _metrics.track_request(latency_ms, success)


def track_detection(detected: bool):
    """Track scam detection result"""
    _metrics.track_detection(detected)


def track_intelligence(intel_type: str, count: int = 1):
    """Track intelligence extraction"""
    _metrics.track_intelligence(intel_type, count)


def track_normalization(obfuscation_found: bool):
    """Track normalization application"""
    _metrics.track_normalization(obfuscation_found)


def get_metrics() -> Dict:
    """Get current metrics"""
    return _metrics.get_metrics()


def reset_metrics():
    """Reset all metrics"""
    _metrics.reset()


def print_metrics():
    """Print metrics summary"""
    _metrics.print_summary()


# ═══════════════════════════════════════════════════════════════
# BENCHMARK FUNCTIONS (For Development/Testing)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# BENCHMARK FUNCTIONS (For Development/Testing)
# ═══════════════════════════════════════════════════════════════

# Test cases representing real-world scam messages
BENCHMARK_TEST_CASES = [
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
    print("🔧 HONEYPOT TELEMETRY - NORMALIZATION BENCHMARKS")
    print("═" * 80)
    print()
    
    # Warmup
    print("Warming up...")
    for text in BENCHMARK_TEST_CASES[:3]:
        normalize_input(text)
    print("Warmup complete.\n")
    
    # Run benchmarks
    print("Running benchmarks (100 iterations per test)...")
    results = benchmark_batch(BENCHMARK_TEST_CASES, iterations=100)
    
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
    
    print("\n" + "═" * 80)
    print("💡 PRODUCTION INTEGRATION")
    print("═" * 80)
    print("""
To use telemetry in production, add to main.py:

    from telemetry import track_request, track_detection, track_intelligence, get_metrics
    
    @app.post("/honeypot")
    def honeypot(payload: dict, x_api_key: str = Header(None)):
        with track_request():  # Auto-track latency
            scam_detected = detect_scam(message["text"], history)
            track_detection(scam_detected)  # Track detection result
            
            # Track intelligence extraction
            if urls_found:
                track_intelligence("url", count=len(urls_found))
            if phones_found:
                track_intelligence("phone", count=len(phones_found))
            ...
    
    @app.get("/metrics")
    def metrics():
        return get_metrics()  # Expose metrics endpoint
""")
    print("═" * 80)
