"""Controlled real Python threads for the built-in counter fixture only."""
from threading import Barrier, Lock, Thread


def counter_trial(fixed=False):
    counter = [0]
    barrier = Barrier(2, timeout=2)
    lock = Lock()
    errors = []
    def worker():
        try:
            if fixed:
                with lock:
                    counter[0] = counter[0] + 1
            else:
                local = counter[0]
                # Both workers must finish reading before either can write.
                barrier.wait()
                counter[0] = local + 1
        except Exception as exc:
            errors.append(type(exc).__name__)
    threads = [Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    if errors or any(t.is_alive() for t in threads):
        raise RuntimeError('Controlled thread experiment did not complete')
    return {'fixture': 'two-worker-counter', 'fixed': fixed, 'expected': 2,
            'actual': counter[0], 'violation': counter[0] != 2,
            'scope': 'Instrumented counter fixture with forced read interleaving; not arbitrary source code.'}
