"""Read-only HTTP load test; reports observed results, never invents capacity."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import time
import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000/health/ready')
    parser.add_argument('--requests', type=int, default=100)
    parser.add_argument('--concurrency', type=int, default=8)
    parser.add_argument('--output', default='reports/load-test.json')
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 100 or not 1 <= args.requests <= 10000:
        parser.error('并发需为 1..100，请求数需为 1..10000')
    def probe(_):
        started = time.perf_counter()
        try:
            response = requests.get(args.url, timeout=30)
            return {'status': response.status_code, 'seconds': time.perf_counter() - started}
        except requests.RequestException:
            return {'status': 0, 'seconds': time.perf_counter() - started}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(probe, range(args.requests)))
    elapsed = time.perf_counter() - started
    durations = sorted(row['seconds'] for row in results)
    report = {'url': args.url, 'requests': args.requests, 'concurrency': args.concurrency,
              'elapsed_seconds': elapsed, 'requests_per_second': args.requests / elapsed,
              'mean_seconds': statistics.mean(durations), 'p95_seconds': durations[int(.95 * (len(durations)-1))],
              'failures': sum(row['status'] != 200 for row in results), 'samples': results,
              'scope': '只读指定端点的本机观测；不代表 AI 调用或公网容量'}
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('requests', 'concurrency', 'failures', 'p95_seconds')}))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
