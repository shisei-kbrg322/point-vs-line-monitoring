"""simulate.py の結果をグラフにする。"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# 日本語フォント: macOS / Windows / Linux の候補のうち、インストールされているものだけを使う
# （ないフォントを指定すると matplotlib が警告を大量に出すため）
_JP_FONTS = [
    "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo",
    "Noto Sans CJK JP", "IPAexGothic",
]
_installed = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = [f for f in _JP_FONTS if f in _installed] + ["sans-serif"]

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def plot_tradeoff(results, out) -> None:
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    _style(ax)
    x = [r["checks_per_shift"] for r in results]
    y = [r["detection_rate"] * 100 for r in results]
    ax.plot(x, y, color=SERIES[0], linewidth=2, marker="o", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
    ax.axhline(100, color=TEXT_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(x[-1], 101.5, "連続記録（理想）", color=TEXT_2, fontsize=9, ha="right")
    for r, xi, yi in zip(results, x, y):
        ax.annotate(f"{r['strategy']}\n{yi:.0f}%", (xi, yi), textcoords="offset points",
                    xytext=(0, -30 if yi > 60 else 10), ha="center", fontsize=9, color=TEXT)
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x])
    ax.minorticks_off()
    ax.set_ylim(0, 108)
    ax.set_xlabel("1シフトあたりの確認回数（コスト、対数目盛）", color=TEXT_2)
    ax.set_ylabel("途切れの検出率（%）", color=TEXT_2)
    ax.set_title("確認を増やすほど検出率は上がるが、コストも増える",
                 loc="left", color=TEXT, fontsize=13, pad=12)
    fig.tight_layout()
    fig.savefig(out / "tradeoff.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def plot_by_duration(results, bins, by_duration, out) -> None:
    pick = ["引き継ぎ時のみ", "60分ごと", "15分ごと"]
    centers = (bins[:-1] + bins[1:]) / 2
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    _style(ax)
    for color, name in zip(SERIES, pick):
        rates = by_duration[name] * 100
        ax.plot(centers, rates, color=color, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
    ax.axvline(1.0, color=TEXT_2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(1.05, 4, "60分", color=TEXT_2, fontsize=9)
    ax.set_xlim(0, bins[-1] + 0.2)
    ax.set_ylim(0, 105)
    ax.set_xlabel("途切れの長さ（時間）", color=TEXT_2)
    ax.set_ylabel("途切れの検出率（%）", color=TEXT_2)
    ax.set_title("確認間隔より短い途切れは見逃しやすい",
                 loc="left", color=TEXT, fontsize=13, pad=12)
    ax.legend(frameon=False, loc="center", bbox_to_anchor=(0.6, 0.66), labelcolor=TEXT_2)
    fig.tight_layout()
    fig.savefig(out / "by_duration.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def plot_all(results, bins, by_duration, args) -> None:
    plot_tradeoff(results, args.out)
    plot_by_duration(results, bins, by_duration, args.out)
