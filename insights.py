"""Plain-language interpretations for RestEdge historical analysis."""

from dataclasses import asdict, dataclass

import pandas as pd

from analytics import REST_CATEGORY_ORDER


@dataclass(frozen=True)
class RestInsight:
    category: str
    signal: str
    tone: str
    games: int
    hit_rate: float | None
    difference_points: float | None
    explanation: str
    sample_note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _sample_note(games: int) -> str:
    if games < 10:
        return "Small sample. One result can materially change this rate."
    if games < 25:
        return "Developing sample. Use as context, not a standalone forecast."
    return "Larger historical sample, but still descriptive rather than predictive."


def build_rest_insight(
    summary: pd.DataFrame,
    overall: dict,
    category: str,
    market_name: str,
    line: float,
) -> RestInsight:
    """Describe one rest split as historical performance context."""
    if category not in REST_CATEGORY_ORDER:
        raise ValueError(f"Unknown rest category: {category}")

    matching = summary[summary["REST_CATEGORY"].astype(str) == category]
    if matching.empty:
        raise ValueError(f"Summary does not include rest category: {category}")

    row = matching.iloc[0]
    games = int(row["GAMES"])
    hit_rate = None if pd.isna(row["HIT_RATE"]) else float(row["HIT_RATE"])
    overall_rate = overall.get("hit_rate")
    overall_rate = None if pd.isna(overall_rate) else float(overall_rate)
    difference = None
    if hit_rate is not None and overall_rate is not None:
        difference = (hit_rate - overall_rate) * 100

    if games == 0 or hit_rate is None:
        signal = "NO SAMPLE"
        tone = "neutral"
        explanation = (
            f"No eligible {market_name.lower()} games are available for {category.lower()} "
            f"at a {line:.1f} line."
        )
    elif games < 10:
        signal = "INSUFFICIENT SAMPLE"
        tone = "caution"
        explanation = (
            f"Results finished {int(row['HITS'])} above and {games - int(row['HITS'])} below the threshold in this split "
            f"({hit_rate:.1%}), but {games} games are not enough for a stable rest signal."
        )
    elif difference is not None and difference >= 8:
        signal = "HIGHER HISTORICAL RATE"
        tone = "positive"
        explanation = (
            f"The above-threshold rate was {hit_rate:.1%}, {abs(difference):.1f} percentage points above "
            f"the player's overall {overall_rate:.1%} rate at {line:.1f}."
        )
    elif difference is not None and difference <= -8:
        signal = "LOWER HISTORICAL RATE"
        tone = "negative"
        explanation = (
            f"The above-threshold rate was {hit_rate:.1%}, {abs(difference):.1f} percentage points below "
            f"the player's overall {overall_rate:.1%} rate at {line:.1f}."
        )
    else:
        signal = "NO CLEAR REST DIFFERENCE"
        tone = "neutral"
        difference_text = "close to the overall rate"
        if difference is not None:
            difference_text = f"within {abs(difference):.1f} percentage points of the overall rate"
        explanation = (
            f"The observed {hit_rate:.1%} above-threshold rate was {difference_text}; rest alone did not "
            "separate this split meaningfully."
        )

    sample_note = _sample_note(games)

    return RestInsight(
        category=category,
        signal=signal,
        tone=tone,
        games=games,
        hit_rate=hit_rate,
        difference_points=difference,
        explanation=explanation,
        sample_note=sample_note,
    )


def build_all_rest_insights(
    summary: pd.DataFrame,
    overall: dict,
    market_name: str,
    line: float,
) -> list[RestInsight]:
    """Build interpretations in the dashboard's fixed rest-category order."""
    return [
        build_rest_insight(summary, overall, category, market_name, line)
        for category in REST_CATEGORY_ORDER
    ]

