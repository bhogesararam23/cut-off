"""Write the results paragraph of the README from stats.json, so no result number is ever typed by hand.

The README holds two marker lines; everything between them is replaced. Mock data is refused.
"""

from __future__ import annotations

import json
from pathlib import Path

START = "<!-- results:start -->"
END = "<!-- results:end -->"
PERCENT = 100  # the data files store rates as fractions
MIN_N_TO_SCORE = 5  # with fewer test points than this, a rate would be meaningless


class ReportError(Exception):
    pass


def _pct(rate: float, digits: int = 0) -> str:
    return f"{rate * PERCENT:.{digits}f}"


SPLIT_NOTE = ("This is a random split of points within one study area, labelled from optical imagery and checked by eye. "
              "It is not independent geographic validation and not field validation; nearby points may share conditions.")
TWICE_NOTE = ("The held-out half was scored twice: first on the original method, then after the method was revised using the "
              "tuning half only. Both results are shown.")


def _score_line(v: dict, label: str) -> str:
    by_size = ", ".join(f"{b['size']} {_pct(b['detection_rate'])}% (n = {b['n']})" if b["n"] >= MIN_N_TO_SCORE
                        else f"{b['size']}: n = {b['n']}, too few to score" for b in v["by_size"])
    return (f"- {label} ({v['n_test_landslide']} landslide points, {v['n_test_forest']} forest points): found "
            f"**{_pct(v['detection_rate'])}%**, false alarms **{_pct(v['false_alarm_rate'])}%**, AUC **{v['auc']:.2f}** "
            f"(0.5 = guessing, 1.0 = perfect)." + (f" Found by landslide size: {by_size}." if by_size else ""))


def results_block(stats: dict) -> str:
    """Markdown for the results section, built only from the values in stats.json."""
    if stats.get("mock"):
        raise ReportError("stats.json is mock data: run the real processing first, then write the results")
    lines = []
    base, post = stats["baseline_no_change_flag_rate"], stats["post_event_flag_rate"]
    if base >= post:
        lines.append("- **The detector flags as much change without an earthquake as with one at this setting, so single "
                     "detections are weak evidence.**")
    lines.append(f"- **{stats['landslides']:,}** candidate landslides (connected patches of flagged radar pixels) covering "
                 f"**{stats['area_km2']:,.2f} km²** of forested slopes. A candidate is a lead, not a confirmed landslide.")
    if stats.get("roads_blocked_km") is not None and stats.get("communities_cut_off") is not None:
        lines.append(f"- **{stats['roads_blocked_km']:,.1f} km** of road likely blocked and **{stats['communities_cut_off']:,}** "
                     "communities possibly cut off (inferred from candidate landslides next to roads; nobody saw the blockages).")
    else:
        lines.append("- Roads likely blocked and communities possibly cut off: not computed yet.")
    v, v0 = stats.get("validation"), stats.get("validation_original")
    if v:
        lines.append(_score_line(v, "Held-out point split, " + ("second scoring, revised method" if v0 else "scoring")))
        if v0:
            lines.append(_score_line(v0, "Held-out point split, first scoring, original method"))
            lines.append("- " + TWICE_NOTE)
        lines.append("- " + SPLIT_NOTE)
    else:
        lines.append("- Accuracy check: not run yet.")
    lines.append(f"- Pre-event baseline (ordinary change between two passes before the quake, 20 Sep to 2 Oct 2026; rain, soil "
                 f"moisture, farming and vegetation can change over 12 days): the same method flagged {_pct(base, 1)}% of forested "
                 f"slopes, against {_pct(post, 1)}% in a pair spanning the quake from the same track.")
    if base >= post:
        lines.append("- **Caution:** the pre-event baseline flagged as much as the post-quake pair. Natural change between two "
                     "passes is as large as the landslide signal at this setting, so single detections are weak evidence.")
    p = stats["params"]
    window = (f", local-mean window {p['highpass_px']} pixels ({p['highpass_px'] * stats['pixel_m']:g} m)" if p.get("highpass_px", 0) > 1 else "")
    lines.append(f"- Settings: drop threshold {p['threshold_db']:g} dB below the local mean{window}, minimum slope {p['min_slope_deg']:g}°, "
                 f"minimum patch {p['min_pixels']} pixels, pixel size {stats['pixel_m']:g} m.")
    lines.append("")
    lines.append("All results come from radar processed in advance. This is a research demo, not an official warning.")
    return "\n".join(lines)


def update_readme(readme: Path, stats_path: Path) -> str:
    """Replace the text between the markers with the current results. Returns the new block."""
    readme, stats_path = Path(readme), Path(stats_path)
    if not stats_path.is_file():
        raise ReportError(f"stats file not found: {stats_path}")
    block = results_block(json.loads(stats_path.read_text(encoding="utf-8")))
    text = readme.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ReportError(f"{readme.name} needs exactly one '{START}' line followed by one '{END}' line")
    head, rest = text.split(START)
    _, tail = rest.split(END)
    readme.write_text(f"{head}{START}\n{block}\n{END}{tail}", encoding="utf-8", newline="\n")
    return block
