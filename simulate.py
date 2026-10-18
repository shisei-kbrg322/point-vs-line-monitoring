"""点の確認と線の確認 — 確認間隔と途切れ検出率のシミュレーション

交代制の監視業務を単純化したモデルで、
「引き継ぎ時だけ確認する運用」と「一定間隔で自動確認する運用」の
途切れ検出率と確認コストを比べる。

モデル
- 1シフト = SHIFT_HOURS 時間。シフトの開始時と終了時に引き継ぎ確認がある
- 各シフトで監視対象が1回だけ途切れる
  - 途切れの開始時刻: シフト内で一様ランダム
  - 途切れの長さ: MIN_OUTAGE〜MAX_OUTAGE 時間で一様ランダム
  - 途切れがシフト終了をまたぐ場合は、引き継ぎ確認でも検出できる
- 確認時刻に途切れが続いていれば「検出」とする
- 「連続記録」は途切れをすべて記録できる理想形（基準線）

使い方
    python simulate.py                  # 既定値で実行
    python simulate.py --trials 50000   # 試行回数を変える
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Strategy:
    name: str             # 表示名
    interval_min: float | None  # 定期確認の間隔（分）。None = 引き継ぎ時のみ / 連続記録


def build_strategies() -> list[Strategy]:
    return [
        Strategy("引き継ぎ時のみ", None),
        Strategy("120分ごと", 120),
        Strategy("60分ごと", 60),
        Strategy("30分ごと", 30),
        Strategy("15分ごと", 15),
        Strategy("5分ごと", 5),
    ]


def check_times(strategy: Strategy, shift_hours: float) -> np.ndarray:
    """1シフト内の確認時刻（時間単位）。引き継ぎ確認（0h と終了時）は常に含む。"""
    times = {0.0, shift_hours}
    if strategy.interval_min is not None:
        step = strategy.interval_min / 60
        times.update(np.arange(0.0, shift_hours + 1e-9, step).round(6).tolist())
    return np.array(sorted(times))


def simulate_outages(trials: int, shift_hours: float, min_h: float, max_h: float,
                     rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    start = rng.uniform(0.0, shift_hours, trials)
    duration = rng.uniform(min_h, max_h, trials)
    return start, start + duration


def evaluate(strategy: Strategy, starts: np.ndarray, ends: np.ndarray,
             shift_hours: float) -> dict:
    t = check_times(strategy, shift_hours)
    # 途切れ区間 [start, end) に入る最初の確認時刻を探す
    idx = np.searchsorted(t, starts, side="left")
    first = np.where(idx < len(t), t[np.minimum(idx, len(t) - 1)], np.inf)
    detected = first < ends
    delay_h = np.where(detected, first - starts, np.nan)
    return {
        "strategy": strategy.name,
        "interval_min": strategy.interval_min if strategy.interval_min else "",
        "checks_per_shift": len(t),
        "detection_rate": float(detected.mean()),
        "median_delay_min": float(np.nanmedian(delay_h) * 60) if detected.any() else float("nan"),
        "detected": detected,
    }


def detection_by_duration(result: dict, starts: np.ndarray, ends: np.ndarray,
                          bins: np.ndarray) -> np.ndarray:
    duration = ends - starts
    which = np.digitize(duration, bins) - 1
    rates = np.full(len(bins) - 1, np.nan)
    for i in range(len(bins) - 1):
        mask = which == i
        if mask.any():
            rates[i] = result["detected"][mask].mean()
    return rates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, default=20000, help="シミュレーションするシフト数")
    parser.add_argument("--shift-hours", type=float, default=12.0, help="1シフトの長さ（時間）")
    parser.add_argument("--min-outage", type=float, default=0.25, help="途切れの最短時間（時間）")
    parser.add_argument("--max-outage", type=float, default=6.0, help="途切れの最長時間（時間）")
    parser.add_argument("--seed", type=int, default=42, help="乱数シード（再現用）")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="出力フォルダ")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    starts, ends = simulate_outages(args.trials, args.shift_hours,
                                    args.min_outage, args.max_outage, rng)

    results = [evaluate(s, starts, ends, args.shift_hours) for s in build_strategies()]

    bins = np.arange(args.min_outage, args.max_outage + 0.25, 0.25)
    by_duration = {r["strategy"]: detection_by_duration(r, starts, ends, bins) for r in results}

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "interval_min", "checks_per_shift",
                         "detection_rate", "median_delay_min"])
        for r in results:
            writer.writerow([r["strategy"], r["interval_min"], r["checks_per_shift"],
                             f"{r['detection_rate']:.4f}", f"{r['median_delay_min']:.1f}"])
        writer.writerow(["連続記録（基準）", "", "", "1.0000", "0.0"])

    print(f"試行回数: {args.trials:,} シフト / 1シフト {args.shift_hours:g} 時間 / "
          f"途切れ {args.min_outage:g}〜{args.max_outage:g} 時間\n")
    print(f"{'確認方法':<10} {'確認回数':>6} {'検出率':>8} {'検出までの中央値':>12}")
    for r in results:
        delay = "-" if np.isnan(r["median_delay_min"]) else f"{r['median_delay_min']:.0f} 分"
        print(f"{r['strategy']:<10} {r['checks_per_shift']:>6} "
              f"{r['detection_rate']:>8.1%} {delay:>12}")
    print(f"{'連続記録（基準）':<10} {'-':>6} {1:>8.1%} {'0 分':>12}")

    from plot import plot_all  # matplotlib は描画時だけ読み込む
    plot_all(results, bins, by_duration, args)
    print(f"\n出力: {args.out}/results.csv, {args.out}/tradeoff.png, {args.out}/by_duration.png")


if __name__ == "__main__":
    main()
