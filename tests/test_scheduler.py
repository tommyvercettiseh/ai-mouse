from collections import Counter

from ai_mouse_lab.aim_scheduler import BalancedTargetScheduler


def test_scheduler_balances_four_size_distance_combinations():
    scheduler = BalancedTargetScheduler(seed=7)
    previous = (500.0, 350.0)
    counts = Counter()
    shapes = Counter()
    for index in range(40):
        target = scheduler.next_target(previous, 1000, 700, shown_at=float(index))
        counts[(target.size_bucket, target.distance_bucket)] += 1
        shapes[target.shape] += 1
        previous = target.center
    assert set(counts) == set(scheduler.COMBINATIONS)
    assert max(counts.values()) - min(counts.values()) <= 1
    assert max(shapes.values()) - min(shapes.values()) <= 1
