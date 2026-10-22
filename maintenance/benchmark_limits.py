"""Conservative limits for opt-in, sequential model benchmarks (not an account quota API)."""
from collections import defaultdict, deque


class BenchmarkLimits:
    def __init__(self):
        self.requests = defaultdict(deque)
        self.global_requests = deque()
        self.disabled = set()

    def delay(self, model: str, now: float) -> float:
        if model in self.disabled:
            raise ValueError("model disabled after a quota response")
        windows = [(self.global_requests, 4), (self.requests[model], 4 if 'lite' in model else 2)]
        waits = []
        for queue, limit in windows:
            while queue and now - queue[0] >= 60.1:
                queue.popleft()
            waits.append(max(0.0, queue[0] + 60.1 - now) if len(queue) >= limit else 0.0)
        return max(waits)

    def record(self, model: str, now: float) -> None:
        if self.delay(model, now) > 0:
            raise ValueError("benchmark request would exceed budget")
        self.requests[model].append(now)
        self.global_requests.append(now)
