"""Write the results paragraph of the README from stats.json, so no result number is ever typed by hand.

The README holds two marker lines; everything between them is replaced. Mock data is refused.
"""

from __future__ import annotations

import json
from pathlib import Path

START = "<!-- results:start -->"
END = "<!-- results:end -->"
PERCENT = 100  # the data files store rates as fractions


class ReportError(Exception):
    pass


def _pct(rate: float, digits: int = 0) -> str:
    return f"{rate * PERCENT:.{digits}f}"


def results_block(stats: dict) -> str:
    """Markdown for the results section, built only from the values in stats.json."""
    if stats.get("mock"):
        raise ReportError("stats.json is mock data: run the real processing first, then write the results")
    lines = [f"- **{stats['landslides']:,}** candidate landslides covering **{stats['area_km2']:,.2f} km²** of forested slopes."]
    if stats.get("roads_blocked_km") is not None and stats.get("communities_cut_off") is not None:
        lines.append(f"- **{stats['roads_blocked_km']:,.1f} km** of road likely blocked and **{stats['communities_cut_off']:,}** "
                     "communities possibly cut off (inferred from landslides next to roads; nobody saw the blockages).")
    else:
        lines.append("- Roads likely blocked and communities possibly cut off: not computed yet.")
    v = stats.get("validation")
    if v:
        by_size = ", ".join(f"{b['size']} {_pct(b['detection_rate'])}% (n = {b['n']})" for b in v["by_size"])
        lines.append(f"- Accuracy on a sealed test half of hand-marked check points that was never used for tuning "
                     f"({v['n_test_landslide']} landslide points, {v['n_test_forest']} forest points): found **{_pct(v['detection_rate'])}%**, "
                     f"false alarms **{_pct(v['false_alarm_rate'])}%**, AUC **{v['auc']:.2f}** (0.5 = guessing, 1.0 = perfect)."
                     + (f" Found by landslide size: {by_size}." if by_size else ""))
    else:
        lines.append("- Accuracy check: not run yet.")
    lines.append(f"- On two passes before the quake the same method flagged {_pct(stats['baseline_no_change_flag_rate'], 1)}% of forested "
                 f"slopes, against {_pct(stats['post_event_flag_rate'], 1)}% after the quake.")
    p = stats["params"]
    lines.append(f"- Settings: drop threshold {p['threshold_db']:g} dB, minimum slope {p['min_slope_deg']:g}°, "
                 f"pixel size {stats['pixel_m']:g} m.")
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
