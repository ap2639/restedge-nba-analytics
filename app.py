import os
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    MARKETS,
    build_player_catalog,
    load_processed_data,
    overall_performance,
    summarize_by_rest,
)
from insights import build_all_rest_insights
from modeling import chronological_player_backtest
from news import fetch_live_player_news, load_player_news, merge_news_items
from scenario import build_scenario_projection


BASE_DIR = Path(__file__).resolve().parent
LEGACY_DATA_PATH = BASE_DIR / "data" / "processed_player_games.csv"
VERSIONED_DATA_DIR = BASE_DIR / "data" / "season_store" / "processed"
METADATA_DIR = BASE_DIR / "data" / "season_store" / "metadata"
NEWS_PATH = BASE_DIR / "data" / "news" / "latest_news.json"

COLORS = {
    "page": "#080808",
    "shell": "#f3f4f0",
    "card": "#ffffff",
    "soft": "#e5e7e2",
    "line": "#d5d8d2",
    "ink": "#0c0d10",
    "muted": "#747a78",
    "lime": "#b8f52f",
    "lime_dark": "#91c51c",
    "purple": "#8b48e8",
    "black": "#070707",
}

REST_SHORT_NAMES = {
    "Back-to-back": "B2B",
    "1 day off": "1 DAY",
    "2+ days off": "2+ DAYS",
}

PAGES = {
    "home": "Home",
    "slate": "Slate",
    "markets": "Splits",
    "players": "Players",
    "scenario-lab": "Scenario Lab",
    "news": "News",
    "model-lab": "Model Lab",
    "methodology": "Methodology",
}


st.set_page_config(page_title="RestEdge Basketball Analytics", layout="wide")


def apply_styles() -> None:
    st.html(
        f"""
        <style>
        .stApp {{ background:{COLORS['page']}; color:{COLORS['ink']}; font-family:Arial,Helvetica,sans-serif; }}
        header[data-testid="stHeader"] {{ height:0; background:transparent; }}
        [data-testid="stToolbar"],[data-testid="stDecoration"],section[data-testid="stSidebar"] {{ display:none!important; }}
        .block-container {{ background:{COLORS['shell']}; border:1px solid #303030; border-radius:18px; margin:1.2rem auto 3rem; max-width:1420px; padding:1rem 1.15rem 1.4rem 5.7rem; }}
        h1,h2,h3,p,label,button,input,[data-testid="stMetricLabel"],[data-testid="stMetricValue"] {{ font-family:Arial,Helvetica,sans-serif!important; }}
        p,label {{ color:{COLORS['ink']}!important; }}
        [data-testid="stSelectbox"],[data-testid="stNumberInput"] {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:9px; padding:.45rem .65rem .25rem; }}
        div[data-baseweb="select"]>div,div[data-baseweb="input"]>div {{ background:{COLORS['card']}!important; border:0!important; color:{COLORS['ink']}!important; }}
        div[data-baseweb="select"] *,div[data-baseweb="input"] * {{ color:{COLORS['ink']}!important; }}
        div[data-baseweb="popover"] {{ color-scheme:light!important; }}
        div[data-baseweb="popover"] [role="listbox"] {{ background:{COLORS['card']}!important; border:1px solid {COLORS['line']}!important; color:{COLORS['ink']}!important; }}
        div[data-baseweb="popover"] [role="option"] {{ background:{COLORS['card']}!important; color:{COLORS['ink']}!important; }}
        div[data-baseweb="popover"] [role="option"]:hover {{ background:{COLORS['soft']}!important; }}
        div[data-baseweb="popover"] [role="option"][aria-selected="true"] {{ background:{COLORS['lime']}!important; color:{COLORS['ink']}!important; }}
        [data-testid="stNumberInput"] button {{ background:{COLORS['card']}!important; border-color:{COLORS['line']}!important; color:{COLORS['ink']}!important; }}
        [data-testid="stSelectbox"] label,[data-testid="stNumberInput"] label {{ color:{COLORS['muted']}!important; font-size:.68rem!important; font-weight:800!important; letter-spacing:.06em; text-transform:uppercase; }}
        [data-testid="stDataFrame"],[data-testid="stPlotlyChart"] {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; overflow:hidden; }}
        [data-testid="stAlert"] {{ border-radius:8px; }}
        .side-rail {{ align-items:center; background:{COLORS['card']}; border-right:1px solid {COLORS['line']}; border-radius:17px 0 0 17px; display:flex; flex-direction:column; gap:.38rem; left:max(calc((100vw - 1420px)/2 + 1px),1px); max-height:calc(100vh - 2.5rem); overflow-y:auto; padding:.8rem .65rem; position:fixed; top:1.25rem; width:70px; z-index:20; }}
        .rail-brand {{ align-items:center; background:{COLORS['ink']}; border-radius:50%; color:{COLORS['lime']}; display:flex; font-size:.72rem; font-weight:900; height:42px; justify-content:center; margin-bottom:.55rem; width:42px; }}
        .rail-item {{ align-items:center; background:#f5f5f2; border:1px solid transparent; border-radius:8px; color:{COLORS['ink']}; display:flex; font-size:.62rem; font-weight:900; height:42px; justify-content:center; width:42px; }}
        .rail-item.active {{ background:{COLORS['lime']}; border-color:{COLORS['lime_dark']}; }}
        .rail-spacer {{ flex:1; min-height:12px; }}
        .basketball-icon {{ background:#fff; border:2px solid {COLORS['ink']}; border-radius:50%; height:19px; position:relative; width:19px; }}
        .basketball-icon::before {{ border-left:1.5px solid {COLORS['ink']}; content:""; height:17px; left:7px; position:absolute; transform:rotate(35deg); top:-1px; }}
        .basketball-icon::after {{ border-top:1.5px solid {COLORS['ink']}; content:""; left:0; position:absolute; top:8px; transform:rotate(-18deg); width:17px; }}
        .top-nav {{ align-items:center; display:grid; gap:.7rem; grid-template-columns:auto 1fr auto; padding:.2rem .35rem .9rem; }}
        .brand {{ color:{COLORS['ink']}; font-size:1.45rem; font-style:italic; font-weight:950; letter-spacing:-.05em; }}
        .nav-links {{ display:flex; gap:.12rem; justify-content:center; min-width:0; overflow-x:auto; scrollbar-width:none; }}
        .nav-link {{ border-radius:7px; color:{COLORS['ink']}; cursor:pointer; flex:0 0 auto; font-size:.65rem; font-weight:750; padding:.52rem .48rem .38rem; text-decoration:none!important; transition:background-color .15s ease; white-space:nowrap; }}
        .nav-link:hover {{ background:{COLORS['soft']}; color:{COLORS['ink']}; }}
        .nav-link.active::after {{ background:{COLORS['ink']}; content:""; display:block; height:3px; margin:5px auto 0; width:4px; }}
        .season-chip {{ background:{COLORS['ink']}; border-radius:8px; color:#fff; font-size:.67rem; font-weight:800; letter-spacing:.05em; padding:.65rem .85rem; text-transform:uppercase; }}
        .control-title {{ color:{COLORS['ink']}; font-size:.72rem; font-style:italic; font-weight:900; letter-spacing:.04em; margin:.15rem 0 .4rem; text-transform:uppercase; }}
        .rest-strip {{ background:{COLORS['black']}; border-radius:12px; margin-top:.85rem; padding:.8rem; }}
        .strip-header {{ align-items:center; color:#fff; display:flex; font-size:.75rem; font-style:italic; font-weight:900; justify-content:space-between; margin:0 .15rem .55rem; text-transform:uppercase; }}
        .strip-note {{ color:#999; font-size:.6rem; font-style:normal; letter-spacing:.05em; }}
        .split-cards {{ display:grid; gap:.55rem; grid-template-columns:repeat(3,1fr); }}
        .split-card {{ background:{COLORS['card']}; border-radius:9px; display:grid; gap:.45rem; grid-template-columns:52px 1fr auto; min-height:82px; padding:.65rem; }}
        .split-badge {{ align-items:center; background:{COLORS['soft']}; border-radius:7px; color:{COLORS['ink']}; display:flex; font-size:.62rem; font-weight:950; justify-content:center; text-align:center; }}
        .split-name {{ color:{COLORS['muted']}; font-size:.58rem; font-weight:800; letter-spacing:.05em; text-transform:uppercase; }}
        .split-rate {{ color:{COLORS['ink']}; font-size:1.15rem; font-weight:950; margin-top:.12rem; }}
        .split-record {{ color:{COLORS['muted']}; font-size:.62rem; margin-top:.15rem; }}
        .split-price {{ align-self:center; color:{COLORS['ink']}; font-size:1rem; font-weight:950; }}
        .panel-title {{ align-items:center; color:{COLORS['ink']}; display:flex; font-size:.8rem; font-style:italic; font-weight:950; justify-content:space-between; letter-spacing:.02em; margin:.9rem .25rem .35rem; text-transform:uppercase; }}
        .panel-kicker {{ color:{COLORS['muted']}; font-size:.58rem; font-style:normal; letter-spacing:.05em; }}
        .player-card {{ background:{COLORS['soft']}; border-radius:11px; min-height:360px; overflow:hidden; position:relative; }}
        .player-card-top {{ padding:1rem 1rem 0; position:relative; z-index:2; }}
        .player-team {{ color:{COLORS['muted']}; font-size:.62rem; font-weight:850; letter-spacing:.06em; text-transform:uppercase; }}
        .player-name {{ color:{COLORS['ink']}; font-size:1.35rem; font-weight:950; letter-spacing:-.035em; line-height:1; margin-top:.25rem; max-width:180px; }}
        .player-headshot {{ bottom:80px; height:245px; object-fit:contain; position:absolute; right:-12px; width:245px; z-index:1; }}
        .team-watermark {{ color:#d5d7d1; font-size:5rem; font-weight:950; left:12px; line-height:1; position:absolute; top:92px; }}
        .profile-stats {{ background:{COLORS['card']}; bottom:0; display:grid; gap:1px; grid-template-columns:repeat(3,1fr); left:0; padding:.55rem; position:absolute; right:0; z-index:3; }}
        .profile-stat {{ border-right:1px solid {COLORS['line']}; padding:.45rem .35rem; text-align:center; }}
        .profile-stat:last-child {{ border-right:0; }}
        .profile-value {{ color:{COLORS['ink']}; font-size:1rem; font-weight:950; }}
        .profile-label {{ color:{COLORS['muted']}; font-size:.55rem; font-weight:800; margin-top:.12rem; text-transform:uppercase; }}
        .odds-summary {{ background:{COLORS['card']}; border-radius:10px; display:grid; gap:1px; grid-template-columns:repeat(4,1fr); margin-top:.55rem; padding:.55rem; }}
        .odds-cell {{ border-right:1px solid {COLORS['line']}; padding:.4rem .3rem; text-align:center; }}
        .odds-cell:last-child {{ border-right:0; }}
        .odds-value {{ color:{COLORS['ink']}; font-size:.88rem; font-weight:950; }}
        .odds-label {{ color:{COLORS['muted']}; font-size:.5rem; font-weight:800; margin-top:.12rem; text-transform:uppercase; }}
        .recent-list {{ background:{COLORS['card']}; border-radius:10px; padding:.5rem .7rem; }}
        .recent-row {{ align-items:center; border-bottom:1px solid {COLORS['line']}; display:grid; gap:.5rem; grid-template-columns:52px 1fr 58px 50px; padding:.62rem .15rem; }}
        .recent-row:last-child {{ border-bottom:0; }}
        .result-pill {{ align-items:center; border-radius:6px; display:flex; font-size:.6rem; font-weight:950; height:32px; justify-content:center; }}
        .result-pill.over {{ background:{COLORS['lime']}; color:{COLORS['ink']}; }}
        .result-pill.under {{ background:{COLORS['soft']}; color:{COLORS['muted']}; }}
        .recent-matchup {{ color:{COLORS['ink']}; font-size:.72rem; font-weight:850; }}
        .recent-date {{ color:{COLORS['muted']}; font-size:.56rem; margin-top:.12rem; }}
        .recent-stat {{ color:{COLORS['ink']}; font-size:.85rem; font-weight:950; text-align:right; }}
        .recent-rest {{ color:{COLORS['muted']}; font-size:.58rem; text-align:right; }}
        .rest-table {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; overflow:hidden; }}
        .rest-table-row {{ align-items:center; border-bottom:1px solid {COLORS['line']}; color:{COLORS['ink']}; display:grid; gap:.4rem; grid-template-columns:1.35fr repeat(4,.72fr); min-height:46px; padding:.35rem .7rem; }}
        .rest-table-row:last-child {{ border-bottom:0; }}
        .rest-table-row.header {{ background:{COLORS['soft']}; color:{COLORS['muted']}; font-size:.52rem; font-weight:900; letter-spacing:.055em; min-height:36px; text-transform:uppercase; }}
        .rest-table-cell {{ color:inherit; font-size:.65rem; text-align:right; }}
        .rest-table-cell:first-child {{ font-weight:850; text-align:left; }}
        .rest-table-row:not(.header) .rest-table-cell:nth-child(5),.rest-table-row:not(.header) .rest-table-cell:nth-child(6) {{ font-weight:900; }}
        .insight-grid {{ display:grid; gap:.65rem; grid-template-columns:repeat(3,1fr); }}
        .insight-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; min-height:155px; padding:.85rem; }}
        .insight-card.positive {{ border-top:4px solid {COLORS['lime_dark']}; }}
        .insight-card.negative {{ border-top:4px solid {COLORS['purple']}; }}
        .insight-card.caution {{ border-top:4px solid #d6a225; }}
        .insight-card.neutral {{ border-top:4px solid {COLORS['muted']}; }}
        .insight-category {{ color:{COLORS['muted']}; font-size:.55rem; font-weight:900; letter-spacing:.06em; text-transform:uppercase; }}
        .insight-signal {{ color:{COLORS['ink']}; font-size:.72rem; font-weight:950; margin:.32rem 0 .45rem; }}
        .insight-copy {{ color:{COLORS['ink']}; font-size:.64rem; line-height:1.45; }}
        .insight-note {{ color:{COLORS['muted']}; font-size:.56rem; line-height:1.4; margin-top:.5rem; }}
        .method-note {{ color:{COLORS['muted']}; font-size:.66rem; line-height:1.5; margin-top:.8rem; }}
        .page-heading {{ align-items:end; display:flex; justify-content:space-between; margin:.35rem .2rem .8rem; }}
        .page-eyebrow {{ color:{COLORS['muted']}; font-size:.58rem; font-weight:850; letter-spacing:.09em; text-transform:uppercase; }}
        .page-title {{ color:{COLORS['ink']}; font-size:1.55rem; font-style:italic; font-weight:950; letter-spacing:-.035em; margin-top:.2rem; }}
        .page-copy {{ color:{COLORS['muted']}; font-size:.68rem; line-height:1.45; max-width:430px; text-align:right; }}
        .method-grid {{ display:grid; gap:.7rem; grid-template-columns:repeat(2,1fr); margin-top:.8rem; }}
        .method-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:1rem; }}
        .method-card h3 {{ color:{COLORS['ink']}; font-size:.78rem; font-style:italic; margin:0 0 .45rem; text-transform:uppercase; }}
        .method-card p {{ color:{COLORS['muted']}!important; font-size:.67rem; line-height:1.55; margin:0; }}
        .visual-guide {{ background:#eef0eb; border-left:4px solid {COLORS['lime_dark']}; border-radius:7px; color:{COLORS['ink']}; font-size:.64rem; line-height:1.48; margin:.25rem 0 .55rem; padding:.65rem .75rem; }}
        .visual-guide strong {{ font-weight:950; }}
        .metric-grid {{ display:grid; gap:.6rem; grid-template-columns:repeat(4,1fr); margin:.45rem 0; }}
        .metric-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:.8rem; }}
        .metric-card.dark {{ background:{COLORS['ink']}; border-color:{COLORS['ink']}; }}
        .metric-card.dark .metric-label,.metric-card.dark .metric-sub {{ color:#aeb3af; }}
        .metric-card.dark .metric-value {{ color:#fff; }}
        .metric-label {{ color:{COLORS['muted']}; font-size:.52rem; font-weight:900; letter-spacing:.06em; text-transform:uppercase; }}
        .metric-value {{ color:{COLORS['ink']}; font-size:1.2rem; font-weight:950; margin-top:.25rem; }}
        .metric-sub {{ color:{COLORS['muted']}; font-size:.55rem; line-height:1.35; margin-top:.18rem; }}
        .slate-grid {{ display:grid; gap:.65rem; grid-template-columns:repeat(3,1fr); }}
        .slate-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:.8rem; }}
        .slate-matchup {{ color:{COLORS['ink']}; font-size:.9rem; font-weight:950; }}
        .slate-meta {{ color:{COLORS['muted']}; font-size:.58rem; margin-top:.25rem; }}
        .slate-leader {{ border-top:1px solid {COLORS['line']}; color:{COLORS['ink']}; font-size:.64rem; margin-top:.55rem; padding-top:.5rem; }}
        .status-panel {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:1rem; }}
        .status-title {{ color:{COLORS['ink']}; font-size:.9rem; font-weight:950; }}
        .status-copy {{ color:{COLORS['muted']}; font-size:.68rem; line-height:1.55; margin-top:.4rem; }}
        .status-badge {{ background:{COLORS['soft']}; border-radius:999px; color:{COLORS['ink']}; display:inline-block; font-size:.52rem; font-weight:900; letter-spacing:.05em; margin-top:.55rem; padding:.35rem .55rem; text-transform:uppercase; }}
        .news-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; margin-bottom:.6rem; padding:.9rem 1rem; }}
        .news-card.official {{ border-left:5px solid {COLORS['lime_dark']}; }}
        .news-card.injury {{ border-left:5px solid #d6a225; }}
        .news-card.reporting {{ border-left:5px solid {COLORS['purple']}; }}
        .news-title a {{ color:{COLORS['ink']}; font-size:.82rem; font-weight:950; line-height:1.35; text-decoration:none; }}
        .news-title a:hover {{ text-decoration:underline; }}
        .news-meta {{ color:{COLORS['muted']}; font-size:.59rem; line-height:1.45; margin-top:.35rem; }}
        .news-tag {{ background:{COLORS['soft']}; border-radius:999px; color:{COLORS['ink']}; display:inline-block; font-size:.5rem; font-weight:900; letter-spacing:.05em; margin-right:.35rem; padding:.28rem .48rem; text-transform:uppercase; }}
        div[data-testid="stButton"] button {{ background:{COLORS['ink']}; border:0; border-radius:8px; color:#fff; font-size:.65rem; font-weight:900; min-height:2.4rem; padding:.45rem .8rem; }}
        div[data-testid="stButton"] button p {{ color:#fff!important; font-size:.65rem; font-weight:900; }}
        div[data-testid="stButton"] button:hover {{ background:#292b2f; color:#fff; }}
        .data-table {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; overflow-x:auto; }}
        .data-table table {{ border-collapse:collapse; color:{COLORS['ink']}; font-size:.63rem; width:100%; }}
        .data-table th {{ background:{COLORS['soft']}; color:{COLORS['muted']}; font-size:.52rem; letter-spacing:.05em; padding:.65rem; text-align:right; text-transform:uppercase; white-space:nowrap; }}
        .data-table th:first-child,.data-table td:first-child {{ text-align:left; }}
        .data-table td {{ border-top:1px solid {COLORS['line']}; padding:.7rem .65rem; text-align:right; }}
        .data-table td:first-child {{ font-weight:900; }}
        hr {{ border-color:{COLORS['line']}!important; }}
        @media(max-width:1050px) {{ .side-rail{{display:none}} .block-container{{border-radius:0;margin:0;max-width:none;padding:1rem}} .top-nav{{grid-template-columns:1fr auto}} .nav-links{{grid-column:1/-1;grid-row:2;justify-content:flex-start}} .nav-link{{font-size:.65rem;padding:.5rem}} .split-cards,.insight-grid,.slate-grid{{grid-template-columns:1fr}} .metric-grid{{grid-template-columns:repeat(2,1fr)}} .page-heading{{align-items:start;flex-direction:column;gap:.45rem}} .page-copy{{text-align:left}} }}
        </style>
        """
    )


def current_page() -> str:
    page = st.query_params.get("page", "home")
    if isinstance(page, list):
        page = page[0] if page else "home"
    return page if page in PAGES else "home"


def render_navigation(page: str, season_label: str) -> None:
    links = "".join(
        f'<a class="nav-link{" active" if slug == page else ""}" href="?page={slug}" target="_self">{label}</a>'
        for slug, label in PAGES.items()
    )
    rail_links = "".join(
        f'<a class="rail-item{" active" if slug == page else ""}" href="?page={slug}" target="_self" '
        f'title="{label}" style="text-decoration:none">{short}</a>'
        for slug, label, short in [
            ("home", "Home", "HM"),
            ("slate", "Slate", "SLT"),
            ("markets", "Splits", "SPL"),
            ("players", "Players", "PLY"),
            ("scenario-lab", "Scenario Lab", "SCN"),
            ("news", "News", "NWS"),
            ("model-lab", "Model Lab", "MDL"),
        ]
    )
    st.html(
        f"""
        <div class="side-rail">
            <div class="rail-brand">RE</div>{rail_links}
            <div class="rail-spacer"></div><a class="rail-item" href="?page=methodology" target="_self" title="Methodology" style="text-decoration:none">?</a>
        </div>
        <div class="top-nav"><div class="brand">RestEdge</div>
            <div class="nav-links">{links}</div>
            <div class="season-chip">NBA {escape(season_label)}</div></div>
        """
    )


def render_page_heading(eyebrow: str, title: str, copy: str) -> None:
    st.html(
        f'<div class="page-heading"><div><div class="page-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="page-title">{escape(title)}</div></div><div class="page-copy">{escape(copy)}</div></div>'
    )


def render_visual_guide(title: str, explanation: str) -> None:
    st.html(
        f'<div class="visual-guide"><strong>{escape(title)}:</strong> {escape(explanation)}</div>'
    )


def render_metric_cards(cards: list[tuple[str, str, str]], dark: bool = False) -> None:
    card_class = "metric-card dark" if dark else "metric-card"
    body = "".join(
        f'<div class="{card_class}"><div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{escape(value)}</div><div class="metric-sub">{escape(detail)}</div></div>'
        for label, value, detail in cards
    )
    st.html(f'<div class="metric-grid">{body}</div>')


def render_html_table(frame: pd.DataFrame) -> None:
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in frame.columns)
    rows = []
    for _, row in frame.iterrows():
        cells = "".join(f"<td>{escape(str(value))}</td>" for value in row.tolist())
        rows.append(f"<tr>{cells}</tr>")
    st.html(
        '<div class="data-table"><table><thead><tr>'
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


@st.cache_data(show_spinner=False)
def load_data(file_path: str) -> pd.DataFrame:
    return load_processed_data(file_path)


@st.cache_data(ttl=3600, show_spinner=False)
def load_live_player_news(player_id: int, player_name: str):
    return fetch_live_player_news(player_id, player_name, days=7, limit=12)


def format_news_age(published_at: datetime) -> str:
    elapsed = datetime.now(timezone.utc) - published_at.astimezone(timezone.utc)
    minutes = max(0, int(elapsed.total_seconds() // 60))
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def resolve_data_path() -> Path:
    versioned = sorted(VERSIONED_DATA_DIR.glob("player_games_*.csv.gz"), reverse=True)
    return versioned[0] if versioned else LEGACY_DATA_PATH


def load_active_metadata(data_path: Path) -> dict | None:
    if data_path.parent != VERSIONED_DATA_DIR:
        return None
    filename = data_path.name.removesuffix(".csv.gz") + ".json"
    metadata_path = METADATA_DIR / filename
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def safe_average(frame: pd.DataFrame, column: str) -> str:
    value = frame[column].mean()
    return "N/A" if pd.isna(value) else f"{value:.1f}"


def render_split_strip(summary: pd.DataFrame) -> None:
    cards = []
    for _, row in summary.iterrows():
        games = int(row["GAMES"])
        hits = int(row["HITS"])
        rate = "N/A" if pd.isna(row["HIT_RATE"]) else f"{row['HIT_RATE']:.1%}"
        average = "N/A" if pd.isna(row["AVERAGE"]) else f"{row['AVERAGE']:.1f} avg"
        category = str(row["REST_CATEGORY"])
        cards.append(
            f'<div class="split-card"><div class="split-badge">{REST_SHORT_NAMES[category]}</div>'
            f'<div><div class="split-name">{escape(category)}</div><div class="split-rate">{rate}</div>'
            f'<div class="split-record">{hits} above / {games} games</div></div>'
            f'<div class="split-price">{average}</div></div>'
        )
    st.html(
        '<div class="rest-strip"><div class="strip-header"><span>Rest splits</span>'
        '<span class="strip-note">Historical results by rest category</span></div>'
        '<div class="split-cards">' + "".join(cards) + "</div></div>"
    )


def make_momentum_chart(
    player_games: pd.DataFrame, stat_column: str, line: float, market_name: str
) -> go.Figure:
    recent = player_games.dropna(subset=[stat_column]).tail(24).copy()
    recent["MARGIN"] = recent[stat_column] - line
    recent["DATE_LABEL"] = recent["GAME_DATE"].dt.strftime("%b %d")
    colors = [COLORS["lime"] if value > 0 else COLORS["purple"] for value in recent["MARGIN"]]
    figure = go.Figure(
        go.Bar(
            x=recent["DATE_LABEL"],
            y=recent["MARGIN"],
            marker={"color": colors},
            customdata=recent[["MATCHUP", stat_column]],
            hovertemplate=(
                "%{x}<br>%{customdata[0]}<br>Recorded: %{customdata[1]:.0f}<br>"
                "Margin vs threshold: %{y:+.1f}<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line_color=COLORS["ink"], line_width=2)
    figure.update_layout(
        title={
            "text": f"{market_name.upper()} MOMENTUM VS {line:.1f}",
            "font": {"family": "Arial", "size": 16, "color": COLORS["ink"]},
        },
        height=390,
        margin={"l": 38, "r": 22, "t": 62, "b": 36},
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["card"],
        font={"family": "Arial", "color": COLORS["muted"]},
        showlegend=False,
        bargap=0.28,
        xaxis={"showgrid": False, "tickangle": -45, "tickfont": {"size": 9}},
        yaxis={
            "title": "Margin vs selected threshold",
            "gridcolor": COLORS["line"],
            "zeroline": False,
        },
    )
    return figure


def make_line_sensitivity_chart(
    player_games: pd.DataFrame, stat_column: str, selected_line: float
) -> go.Figure:
    lower = max(0.5, selected_line - 4)
    lines = [lower + index for index in range(9)]
    eligible = player_games.dropna(subset=[stat_column])
    rates = [float((eligible[stat_column] > line).mean()) for line in lines]
    figure = go.Figure(
        go.Scatter(
            x=lines,
            y=rates,
            mode="lines+markers",
            line={"color": COLORS["purple"], "width": 3},
            marker={"color": COLORS["lime_dark"], "size": 8},
            hovertemplate="Threshold %{x:.1f}<br>Historical above rate %{y:.1%}<extra></extra>",
        )
    )
    figure.add_vline(x=selected_line, line_color=COLORS["ink"], line_dash="dash")
    figure.update_layout(
        height=330,
        margin={"l": 45, "r": 20, "t": 30, "b": 45},
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["card"],
        font={"family": "Arial", "color": COLORS["muted"]},
        xaxis={"title": "Statistic threshold", "gridcolor": COLORS["line"]},
        yaxis={"title": "Historical above rate", "tickformat": ".0%", "range": [0, 1], "gridcolor": COLORS["line"]},
        showlegend=False,
    )
    return figure


def make_model_chart(predictions: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=predictions["GAME_DATE"],
            y=predictions["BASELINE_PROBABILITY"],
            name="Rolling baseline",
            line={"color": COLORS["muted"], "width": 2},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=predictions["GAME_DATE"],
            y=predictions["REST_PROBABILITY"],
            name="Rest-aware",
            line={"color": COLORS["purple"], "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=predictions["GAME_DATE"],
            y=predictions["OUTCOME"].astype(int),
            name="Actual above-threshold result",
            mode="markers",
            marker={"color": COLORS["lime_dark"], "size": 7},
        )
    )
    figure.update_layout(
        height=360,
        margin={"l": 45, "r": 20, "t": 35, "b": 45},
        paper_bgcolor=COLORS["card"],
        plot_bgcolor=COLORS["card"],
        font={"family": "Arial", "color": COLORS["muted"]},
        yaxis={"title": "Above-threshold probability", "tickformat": ".0%", "range": [0, 1], "gridcolor": COLORS["line"]},
        xaxis={"title": "Historical prediction date", "gridcolor": COLORS["line"]},
        legend={"orientation": "h", "y": 1.12},
    )
    return figure


def render_player_card(
    player_id: int,
    team_id: int,
    player_name: str,
    team_abbreviation: str,
    player_games: pd.DataFrame,
) -> None:
    headshot_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{int(player_id)}.png"
    team_logo_url = f"https://cdn.nba.com/logos/nba/{int(team_id)}/primary/L/logo.svg"
    st.html(
        f"""
        <div class="player-card">
            <div class="player-card-top"><div class="player-team">{escape(team_abbreviation)} Player Profile</div>
                <div class="player-name">{escape(player_name)}</div></div>
            <div class="team-watermark">{escape(team_abbreviation)}</div>
            <img class="player-headshot" src="{headshot_url}" alt="{escape(player_name)} headshot">
            <img src="{team_logo_url}" alt="" style="position:absolute;left:16px;top:165px;width:54px;height:54px;object-fit:contain;z-index:2">
            <div class="profile-stats">
                <div class="profile-stat"><div class="profile-value">{safe_average(player_games, 'PTS')}</div><div class="profile-label">Points</div></div>
                <div class="profile-stat"><div class="profile-value">{safe_average(player_games, 'REB')}</div><div class="profile-label">Rebounds</div></div>
                <div class="profile-stat"><div class="profile-value">{safe_average(player_games, 'AST')}</div><div class="profile-label">Assists</div></div>
            </div>
        </div>
        """
    )


def render_performance_summary(overall: dict, market_name: str) -> None:
    average = "N/A" if pd.isna(overall["average"]) else f"{overall['average']:.1f}"
    rate = "N/A" if pd.isna(overall["hit_rate"]) else f"{overall['hit_rate']:.1%}"
    misses = int(overall["games"]) - int(overall["hits"])
    record = f"{overall['hits']}-{misses}"
    st.html(
        f"""
        <div class="odds-summary">
            <div class="odds-cell"><div class="odds-value">{overall['games']}</div><div class="odds-label">Games</div></div>
            <div class="odds-cell"><div class="odds-value">{average}</div><div class="odds-label">Avg {escape(market_name)}</div></div>
            <div class="odds-cell"><div class="odds-value">{rate}</div><div class="odds-label">Above Threshold</div></div>
            <div class="odds-cell"><div class="odds-value">{record}</div><div class="odds-label">Above-Below Record</div></div>
        </div>
        """
    )


def render_recent_games(
    recent_games: pd.DataFrame, stat_column: str, line: float, market_name: str
) -> None:
    rows = []
    for _, game in recent_games.sort_values("GAME_DATE", ascending=False).head(6).iterrows():
        is_over = game[stat_column] > line
        result = "ABOVE" if is_over else "BELOW"
        result_class = "over" if is_over else "under"
        date = game["GAME_DATE"].strftime("%b %d")
        rest_value = game["TEAM_DAYS_OFF"]
        rest_text = "N/A" if pd.isna(rest_value) else f"{int(rest_value)}d rest"
        rows.append(
            f'<div class="recent-row"><div class="result-pill {result_class}">{result}</div>'
            f'<div><div class="recent-matchup">{escape(str(game["MATCHUP"]))}</div>'
            f'<div class="recent-date">{date}</div></div>'
            f'<div class="recent-stat">{game[stat_column]:g} {escape(market_name[:3].upper())}</div>'
            f'<div class="recent-rest">{rest_text}</div></div>'
        )
    st.html('<div class="recent-list">' + "".join(rows) + "</div>")


def render_rest_table(summary: pd.DataFrame) -> None:
    display_summary = summary.copy()
    display_summary["AVERAGE"] = display_summary["AVERAGE"].map(
        lambda value: "N/A" if pd.isna(value) else f"{value:.1f}"
    )
    display_summary["HIT_RATE"] = display_summary["HIT_RATE"].map(
        lambda value: "N/A" if pd.isna(value) else f"{value:.1%}"
    )
    display_summary = display_summary.rename(
        columns={
            "REST_CATEGORY": "Rest", "GAMES": "Games", "AVERAGE": "Average",
            "HITS": "Above", "HIT_RATE": "Above rate",
        }
    )
    rows = []
    for _, row in display_summary.iterrows():
        values = [row["Rest"], row["Games"], row["Average"], row["Above"], row["Above rate"]]
        cells = "".join(f'<div class="rest-table-cell">{escape(str(value))}</div>' for value in values)
        rows.append(f'<div class="rest-table-row">{cells}</div>')
    header = "".join(
        f'<div class="rest-table-cell">{label}</div>'
        for label in ["Rest", "Games", "Average", "Above", "Above rate"]
    )
    st.html('<div class="rest-table"><div class="rest-table-row header">' + header + "</div>" + "".join(rows) + "</div>")


def render_rest_insights(
    summary: pd.DataFrame, overall: dict, market_name: str, line: float
) -> None:
    cards = []
    for insight in build_all_rest_insights(summary, overall, market_name, line):
        signal = {
            "HISTORICAL OVER LEAN": "HIGHER HISTORICAL RATE",
            "HISTORICAL UNDER LEAN": "LOWER HISTORICAL RATE",
            "NO CLEAR REST EDGE": "NO CLEAR REST DIFFERENCE",
        }.get(insight.signal, insight.signal)
        explanation = (
            insight.explanation
            .replace("The over finished", "Results finished")
            .replace("The over rate", "The above-threshold rate")
            .replace(" over rate", " above-threshold rate")
        )
        sample_note = insight.sample_note.split(" Historical-frequency price:", 1)[0]
        cards.append(
            f'<div class="insight-card {escape(insight.tone)}">'
            f'<div class="insight-category">{escape(insight.category)} · {insight.games} games</div>'
            f'<div class="insight-signal">{escape(signal)}</div>'
            f'<div class="insight-copy">{escape(explanation)}</div>'
            f'<div class="insight-note">{escape(sample_note)}</div></div>'
        )
    st.html('<div class="insight-grid">' + "".join(cards) + "</div>")


def player_context(
    games: pd.DataFrame,
    catalog: pd.DataFrame,
    player_labels: dict,
    page: str,
) -> dict:
    st.html('<div class="control-title">Player performance controls</div>')
    control_columns = st.columns([2.1, 1.05, 0.9, 1.25])
    player_ids = catalog["PLAYER_ID"].tolist()
    default_rows = catalog[catalog["PLAYER_NAME"] == "LeBron James"]
    default_index = 0
    if not default_rows.empty:
        default_index = player_ids.index(default_rows.iloc[0]["PLAYER_ID"])

    with control_columns[0]:
        selected_player_id = st.selectbox(
            "Player",
            options=player_ids,
            index=default_index,
            format_func=player_labels.get,
            key=f"{page}_player",
        )
    with control_columns[1]:
        market_name = st.selectbox(
            "Statistic", options=list(MARKETS), key=f"{page}_market"
        )
    market = MARKETS[market_name]
    with control_columns[2]:
        line = st.number_input(
            "Threshold",
            min_value=market["min_line"],
            max_value=market["max_line"],
            value=market["default_line"],
            step=1.0,
            key=f"{page}_line_{market['column']}",
        )
    with control_columns[3]:
        rest_basis = st.selectbox(
            "Rest definition",
            options=["Team schedule", "Player appearances"],
            key=f"{page}_rest_basis",
        )

    rest_column = "TEAM_DAYS_OFF" if rest_basis == "Team schedule" else "PLAYER_DAYS_OFF"
    selected_games = games[games["PLAYER_ID"] == selected_player_id].copy().sort_values("GAME_DATE")
    latest_game = selected_games.iloc[-1]
    stat_column = market["column"]
    summary = summarize_by_rest(selected_games, stat_column, line, rest_column)
    overall = overall_performance(selected_games, stat_column, line, rest_column)
    return {
        "player_id": selected_player_id,
        "player_games": selected_games,
        "player_name": str(latest_game["PLAYER_NAME"]),
        "team_abbreviation": str(latest_game["TEAM_ABBREVIATION"]),
        "team_id": int(latest_game["TEAM_ID"]),
        "market_name": market_name,
        "market": market,
        "stat_column": stat_column,
        "line": line,
        "rest_basis": rest_basis,
        "rest_column": rest_column,
        "summary": summary,
        "overall": overall,
    }


def news_player_context(
    games: pd.DataFrame,
    catalog: pd.DataFrame,
    player_labels: dict,
) -> dict:
    st.html('<div class="control-title">Player news search</div>')
    player_ids = catalog["PLAYER_ID"].tolist()
    default_rows = catalog[catalog["PLAYER_NAME"] == "LeBron James"]
    default_index = 0
    if not default_rows.empty:
        default_index = player_ids.index(default_rows.iloc[0]["PLAYER_ID"])
    selected_player_id = st.selectbox(
        "Player",
        options=player_ids,
        index=default_index,
        format_func=player_labels.get,
        key="news_player",
    )
    selected_games = games[games["PLAYER_ID"] == selected_player_id].copy().sort_values("GAME_DATE")
    latest_game = selected_games.iloc[-1]
    return {
        "player_id": selected_player_id,
        "player_games": selected_games,
        "player_name": str(latest_game["PLAYER_NAME"]),
        "team_abbreviation": str(latest_game["TEAM_ABBREVIATION"]),
        "team_id": int(latest_game["TEAM_ID"]),
    }


def render_data_health(games: pd.DataFrame, metadata: dict | None = None) -> None:
    latest = games["GAME_DATE"].max().strftime("%b %d, %Y")
    earliest = games["GAME_DATE"].min().strftime("%b %d, %Y")
    duplicate_count = int(games.duplicated(subset=["PLAYER_ID", "GAME_ID"]).sum())
    render_metric_cards(
        [
            ("Coverage", f"{len(games):,}", "Player-game records"),
            ("Players", f"{games['PLAYER_ID'].nunique():,}", "Unique NBA players"),
            ("Teams", str(games["TEAM_ID"].nunique()), "Unique NBA teams"),
            ("Latest game", latest, f"Coverage begins {earliest}"),
        ]
    )
    status = "Healthy" if duplicate_count == 0 else "Review required"
    st.html(
        f'<div class="status-panel"><div class="status-title">Dataset integrity: {status}</div>'
        f'<div class="status-copy">Duplicate player-game rows: {duplicate_count}. Team rest is missing for the first recorded team game and player rest is missing for each player\'s first recorded appearance, which is expected.</div>'
        f'<div class="status-badge">{escape("Daily current-season dataset" if metadata else "Historical dataset")}</div></div>'
    )


def render_slate_page(games: pd.DataFrame, metadata: dict | None = None) -> None:
    latest_date = games["GAME_DATE"].max()
    latest = games[games["GAME_DATE"] == latest_date].copy()
    eyebrow = "Current-season completed slate" if metadata else "Historical slate"
    description = (
        "The most recent completed game date stored by the daily 2026-27 updater. "
        "This page does not represent games currently in progress."
        if metadata
        else "The most recent game date stored in the historical fallback dataset."
    )
    render_page_heading(
        eyebrow,
        latest_date.strftime("%B %d, %Y"),
        description,
    )
    render_visual_guide(
        "Slate cards",
        "Each card represents one recorded game. The leader is the highest scorer in the stored player-game rows, and the back-to-back count shows players whose team had zero full days off.",
    )
    cards = []
    for game_id, game_rows in latest.groupby("GAME_ID"):
        teams = sorted(game_rows["TEAM_ABBREVIATION"].dropna().unique().tolist())
        matchup = " vs. ".join(teams) if len(teams) >= 2 else str(game_rows.iloc[0]["MATCHUP"])
        leader = game_rows.sort_values("PTS", ascending=False).iloc[0]
        back_to_back = int((game_rows["TEAM_DAYS_OFF"] == 0).sum())
        cards.append(
            f'<div class="slate-card"><div class="slate-matchup">{escape(matchup)}</div>'
            f'<div class="slate-meta">Game {escape(str(game_id))} · {len(game_rows)} player records · {back_to_back} B2B players</div>'
            f'<div class="slate-leader"><strong>Scoring leader:</strong> {escape(str(leader["PLAYER_NAME"]))} · {int(leader["PTS"])} PTS</div></div>'
        )
    st.html('<div class="slate-grid">' + "".join(cards) + "</div>")
    if metadata:
        fetched_at = datetime.fromisoformat(metadata["fetched_at_utc"]).strftime("%b %d, %Y %H:%M UTC")
        st.html(
            '<div class="status-panel" style="margin-top:.8rem"><div class="status-title">Current-season tracking active</div>'
            f'<div class="status-copy">Completed 2026–27 player-game records are refreshed daily. The active dataset was checked {escape(fetched_at)} and currently includes games through {escape(metadata["last_game_date"])}. This is not an in-game feed.</div>'
            '<div class="status-badge">Daily completed-game updates</div></div>'
        )
    else:
        st.html(
            '<div class="status-panel" style="margin-top:.8rem"><div class="status-title">Historical slate status</div>'
            '<div class="status-copy">This page is using the checked-in historical fallback dataset rather than current-season records.</div>'
            '<div class="status-badge">Historical fallback</div></div>'
        )


def render_news_page(context: dict) -> None:
    render_visual_guide(
        "News timeline",
        "Headlines are searched using the selected player's exact name plus NBA, limited to the last seven days. Each card shows the publisher, publication time, freshness, and whether the headline appears to be an official, injury, or general report.",
    )
    refresh_column, status_column = st.columns([0.25, 0.75])
    with refresh_column:
        if st.button("Refresh latest news", key="refresh_player_news", use_container_width=True):
            load_live_player_news.clear()

    live_enabled = os.getenv("RESTEDGE_LIVE_NEWS", "1") != "0"
    live_result = (
        load_live_player_news(context["player_id"], context["player_name"])
        if live_enabled
        else None
    )
    local_items = load_player_news(NEWS_PATH, context["player_id"])
    live_items = list(live_result.items) if live_result else []
    news_items = merge_news_items(live_items, local_items)
    injury_count = sum(item.item_type in {"official_update", "injury_update"} for item in news_items)
    source_count = len({item.source for item in news_items})

    with status_column:
        if live_result and live_result.error:
            st.html(
                '<div class="status-panel"><div class="status-title">Live news temporarily unavailable</div>'
                '<div class="status-copy">RestEdge could not reach the headline feed. Any validated local records are still shown below. Try the refresh button again later.</div>'
                '<div class="status-badge">Offline fallback active</div></div>'
            )
        elif live_result:
            checked = live_result.fetched_at.strftime("%b %d, %Y %H:%M UTC")
            st.html(
                '<div class="status-panel"><div class="status-title">Live player news connected</div>'
                f'<div class="status-copy">Checked {escape(checked)} through {escape(live_result.provider)}. Results refresh automatically every hour or immediately when you press refresh.</div>'
                '<div class="status-badge">Seven-day freshness window</div></div>'
            )
        else:
            st.html(
                '<div class="status-panel"><div class="status-title">Live news disabled for this run</div>'
                '<div class="status-copy">Set RESTEDGE_LIVE_NEWS=1 to enable the external headline feed.</div>'
                '<div class="status-badge">Local feed only</div></div>'
            )

    render_metric_cards(
        [
            ("Fresh headlines", str(len(news_items)), "Past seven days"),
            ("Status or injury", str(injury_count), "Headline classification"),
            ("Publishers", str(source_count), "Distinct attributed sources"),
            ("Player", context["team_abbreviation"], context["player_name"]),
        ]
    )

    if news_items:
        news_cards = []
        for item in news_items[:12]:
            published = item.published_at.strftime("%b %d, %Y %H:%M UTC")
            item_label = item.item_type.replace("_", " ").title()
            card_class = "official" if item.item_type == "official_update" else "injury" if item.item_type == "injury_update" else "reporting"
            news_cards.append(
                f'<div class="news-card {card_class}"><div class="news-title"><a href="{escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item.title)}</a></div>'
                f'<div class="news-meta"><span class="news-tag">{escape(item_label)}</span>{escape(item.source)} · {escape(published)} · {escape(format_news_age(item.published_at))}</div></div>'
            )
        st.html("".join(news_cards))
    else:
        st.html(
            f'<div class="status-panel"><div class="status-title">No recent headlines found for {escape(context["player_name"])}</div>'
            '<div class="status-copy">The live search returned no matching NBA headlines from the last seven days. This does not prove the player is healthy or available; always verify official team and NBA injury reports.</div>'
            '<div class="status-badge">No fresh matches</div></div>'
        )
    st.html(
        '<div class="method-grid">'
        '<div class="method-card"><h3>Official availability</h3><p>NBA.com headlines are marked as official updates. Headline classification does not replace the league injury report or a team announcement.</p></div>'
        '<div class="method-card"><h3>Reporting timeline</h3><p>Results are ordered newest first, attributed to their publisher, and restricted to a seven-day window.</p></div>'
        '<div class="method-card"><h3>Potential model impact</h3><p>News remains informational. RestEdge never changes projections automatically from a headline; use Scenario Lab to enter an explicit minutes or role assumption.</p></div>'
        "<div class=\"method-card\"><h3>Coverage limits</h3><p>The feed searches every selectable player's exact name, but publishers can omit names, revise articles, or delay reports. Verify material news at the linked source.</p></div>"
        '</div>'
    )


def render_scenario_page(context: dict) -> None:
    columns = st.columns(3)
    recent_minutes = float(context["player_games"]["MIN"].tail(10).median())
    with columns[0]:
        expected_minutes = st.number_input(
            "Expected minutes", min_value=1.0, max_value=60.0, value=round(recent_minutes, 1), step=1.0, key="scenario_minutes"
        )
    with columns[1]:
        rest_scenario = st.selectbox(
            "Rest scenario", options=list(REST_SHORT_NAMES), index=1, key="scenario_rest"
        )
    with columns[2]:
        manual_adjustment = st.number_input(
            "Manual stat adjustment", min_value=-20.0, max_value=20.0, value=0.0, step=0.5, key="scenario_manual"
        )
    projection = build_scenario_projection(
        context["player_games"], context["stat_column"], expected_minutes, rest_scenario, manual_adjustment
    )
    render_metric_cards(
        [
            ("Scenario projection", f"{projection.projection:.1f}", context["market_name"]),
            ("Selected line", f"{context['line']:.1f}", "User-selected threshold"),
            ("Expected minutes", f"{projection.expected_minutes:.1f}", "Manual scenario assumption"),
            ("Rest sample", str(projection.rest_sample), f"Historical {rest_scenario.lower()} games"),
        ],
        dark=True,
    )
    render_visual_guide(
        "Scenario projection",
        "Recent per-minute production is multiplied by expected minutes, then the historical rest-rate difference and your manual adjustment are added. This is an assumption calculator, not a trained forecast.",
    )
    component_table = pd.DataFrame(
        [
            ["Recent median rate", f"{projection.recent_per_minute_rate:.3f} per minute", "Last 10 eligible appearances"],
            ["Minutes component", f"{projection.recent_per_minute_rate * projection.expected_minutes:.1f}", "Rate multiplied by expected minutes"],
            ["Rest adjustment", f"{projection.rest_adjustment:+.1f}", "Applied only with at least five matching rest games"],
            ["Manual adjustment", f"{projection.manual_adjustment:+.1f}", "Explicit user-entered scenario change"],
        ],
        columns=["Component", "Value", "Meaning"],
    )
    render_html_table(component_table)


def render_model_page(context: dict) -> None:
    predictions, metrics = chronological_player_backtest(
        context["player_games"], context["stat_column"], context["line"], context["rest_column"]
    )
    if predictions.empty:
        st.warning("This player does not have enough eligible games for a chronological backtest.")
        return
    render_visual_guide(
        "Probability history",
        "The gray line is the rolling recent-form baseline, the purple line adds a prior-game rest adjustment, and green dots show whether the over actually occurred. Every point is generated without using future games.",
    )
    st.plotly_chart(make_model_chart(predictions), width="stretch")
    display = metrics.copy()
    for column in ["Brier score", "Log loss", "Mean absolute error"]:
        display[column] = display[column].map(lambda value: f"{value:.3f}")
    for column in ["Average predicted over", "Observed over rate"]:
        display[column] = display[column].map(lambda value: f"{value:.1%}")
    render_visual_guide(
        "Validation table",
        "Lower Brier score, log loss, and mean absolute error are better. Average predicted over should be reasonably close to the observed over rate; this is a basic calibration check.",
    )
    render_html_table(display)
    st.html(
        '<div class="status-panel" style="margin-top:.7rem"><div class="status-title">Model maturity: prototype</div>'
        '<div class="status-copy">This backtest is leakage-aware but intentionally simple. It does not yet include opponent, venue, expected minutes, injuries, pace, or role changes and must not be presented as a production forecasting model.</div>'
        '<div class="status-badge">Research model</div></div>'
    )


def render_methodology_page(games: pd.DataFrame, metadata: dict | None = None) -> None:
    render_page_heading(
        "Research framework",
        "Methodology",
        "How RestEdge calculates rest, player averages, and historical threshold rates.",
    )
    st.html(
        """
        <div class="method-grid">
            <div class="method-card"><h3>Rest definitions</h3><p>Team rest measures full days between team games. Player rest measures full days between that player's recorded appearances. The two are intentionally kept separate.</p></div>
            <div class="method-card"><h3>Rest groups</h3><p>Back-to-back means zero full days off, regular rest means one full day off, and extended rest means two or more full days off.</p></div>
            <div class="method-card"><h3>Above-threshold rate</h3><p>A result is counted above the threshold only when the recorded statistic is greater than the selected value. The displayed rate is above-threshold results divided by eligible games.</p></div>
            <div class="method-card"><h3>Performance comparison</h3><p>The dashboard compares sample size, average production, and above-threshold frequency across rest conditions without converting those results into prices or payouts.</p></div>
            <div class="method-card"><h3>Current limitations</h3><p>The descriptive release does not yet control for opponent, venue, expected minutes, injuries, teammate availability, pace, or role changes.</p></div>
            <div class="method-card"><h3>Responsible interpretation</h3><p>Small samples can move sharply after one result. RestEdge reports sample sizes and treats rest splits as descriptive context rather than guaranteed future performance.</p></div>
        </div>
        """
    )
    st.html('<div class="panel-title"><span>Data Health Center</span><span class="panel-kicker">Coverage and integrity</span></div>')
    data_scope = (
        "These cards describe the checked-in daily current-season dataset. "
        if metadata
        else "These cards describe the checked-in historical dataset. "
    )
    render_visual_guide(
        "Data health",
        data_scope
        + "The integrity panel checks duplicate player-game rows and explains expected missing rest values.",
    )
    render_data_health(games, metadata)


apply_styles()
active_data_path = resolve_data_path()
games = load_data(str(active_data_path))
active_metadata = load_active_metadata(active_data_path)
catalog = build_player_catalog(games)
player_labels = dict(zip(catalog["PLAYER_ID"], catalog["LABEL"]))
page = current_page()
season_values = games.get("SEASON_YEAR", pd.Series(dtype=str)).dropna().astype(str)
season_label = season_values.mode().iloc[0] if not season_values.empty else "Historical"
render_navigation(page, season_label)

if page == "slate":
    render_slate_page(games, active_metadata)
elif page == "methodology":
    render_methodology_page(games, active_metadata)
else:
    page_headings = {
        "home": ("Dashboard", "Player Performance Overview", "Player form, rest splits, historical averages, and clearly labeled research context."),
        "markets": ("Stat comparison", "Performance Splits", "Study rest splits and how historical above-threshold frequency changes across nearby values."),
        "players": ("Player intelligence", "Players", "Inspect a player's season profile, recent form, and recorded outcomes against a selected line."),
        "scenario-lab": ("Assumption testing", "Scenario Lab", "Test minutes, rest, and explicit manual adjustments without disguising assumptions as model outputs."),
        "news": ("Information center", "News", "Player-specific news infrastructure with source, timestamp, and freshness requirements."),
        "model-lab": ("Validation workspace", "Model Lab", "Chronologically compare a recent-form baseline with a simple rest-aware probability model."),
    }
    render_page_heading(*page_headings[page])
    context = (
        news_player_context(games, catalog, player_labels)
        if page == "news"
        else player_context(games, catalog, player_labels, page)
    )

    if page == "home":
        render_split_strip(context["summary"])
        st.html('<div class="panel-title"><span>Rest Interpretation</span><span class="panel-kicker">Historical performance context</span></div>')
        render_visual_guide(
            "Interpretation cards",
            "Each card compares one rest category with the player's overall above-threshold rate. A difference is highlighted only when the split has at least 10 games and differs by at least eight percentage points.",
        )
        render_rest_insights(context["summary"], context["overall"], context["market_name"], context["line"])
        profile_column, momentum_column = st.columns([0.72, 1.28])
        with profile_column:
            st.html('<div class="panel-title"><span>Player Spotlight</span><span class="panel-kicker">Season profile</span></div>')
            render_visual_guide("Player profile", "Season averages summarize all recorded appearances and do not adjust for opponent or role.")
            render_player_card(context["player_id"], context["team_id"], context["player_name"], context["team_abbreviation"], context["player_games"])
            render_performance_summary(context["overall"], context["market_name"])
        with momentum_column:
            st.html('<div class="panel-title"><span>Threshold Momentum</span><span class="panel-kicker">Last 24 appearances</span></div>')
            render_visual_guide("Momentum chart", "Bars show the recorded statistic minus the selected threshold. Green bars finished above the threshold; purple bars finished below it.")
            st.plotly_chart(make_momentum_chart(context["player_games"], context["stat_column"], context["line"], context["market_name"]), width="stretch")
        stats_column, recent_column = st.columns([0.9, 1.1])
        with stats_column:
            st.html('<div class="panel-title"><span>Rest Split Stats</span><span class="panel-kicker">Observed performance</span></div>')
            render_visual_guide("Rest split table", "Games is the sample size, Average is the selected statistic, Above counts results greater than the threshold, and Above rate is Above divided by Games.")
            render_rest_table(context["summary"])
        with recent_column:
            st.html('<div class="panel-title"><span>Recent Games</span><span class="panel-kicker">Latest qualifying results</span></div>')
            render_visual_guide("Recent games", "The list shows the latest appearances, whether each result finished above or below the selected threshold, the recorded statistic, and team days off.")
            render_recent_games(context["player_games"].dropna(subset=[context["rest_column"]]), context["stat_column"], context["line"], context["market_name"])

    elif page == "markets":
        render_split_strip(context["summary"])
        st.html('<div class="panel-title"><span>Threshold Sensitivity</span><span class="panel-kicker">Historical above rate by value</span></div>')
        render_visual_guide("Line sensitivity curve", "Each point recalculates the player's historical over rate at a different line. The dashed vertical marker is the currently selected threshold.")
        st.plotly_chart(make_line_sensitivity_chart(context["player_games"], context["stat_column"], context["line"]), width="stretch")
        market_summary, market_table = st.columns([0.65, 1.35])
        with market_summary:
            st.html('<div class="panel-title"><span>Selected Statistic</span><span class="panel-kicker">Historical frequency</span></div>')
            render_visual_guide("Performance summary", "These figures combine every eligible game under the selected rest definition and show actual results around the selected threshold.")
            render_performance_summary(context["overall"], context["market_name"])
        with market_table:
            st.html('<div class="panel-title"><span>Rest Split Comparison</span><span class="panel-kicker">Observed performance</span></div>')
            render_visual_guide("Comparison table", "Compare sample size, average performance, above-threshold count, and above-threshold rate across the three rest conditions.")
            render_rest_table(context["summary"])
        st.html('<div class="panel-title"><span>Rest Interpretation</span><span class="panel-kicker">Descriptive evidence</span></div>')
        render_rest_insights(context["summary"], context["overall"], context["market_name"], context["line"])

    elif page == "players":
        profile_column, momentum_column = st.columns([0.72, 1.28])
        with profile_column:
            st.html('<div class="panel-title"><span>Player Spotlight</span><span class="panel-kicker">Season profile</span></div>')
            render_visual_guide("Player profile", "The image card displays the latest recorded team and full-season points, rebounds, and assists averages.")
            render_player_card(context["player_id"], context["team_id"], context["player_name"], context["team_abbreviation"], context["player_games"])
            render_performance_summary(context["overall"], context["market_name"])
        with momentum_column:
            st.html('<div class="panel-title"><span>Threshold Momentum</span><span class="panel-kicker">Last 24 appearances</span></div>')
            render_visual_guide("Momentum chart", "Positive bars finished above the selected line and negative bars finished below it. Bar height measures the margin, not prediction confidence.")
            st.plotly_chart(make_momentum_chart(context["player_games"], context["stat_column"], context["line"], context["market_name"]), width="stretch")
        st.html('<div class="panel-title"><span>Recent Games</span><span class="panel-kicker">Latest qualifying results</span></div>')
        render_visual_guide("Recent results", "Use this list to inspect actual outcomes and rest context rather than relying only on averages.")
        render_recent_games(context["player_games"].dropna(subset=[context["rest_column"]]), context["stat_column"], context["line"], context["market_name"])

    elif page == "scenario-lab":
        render_scenario_page(context)
    elif page == "news":
        render_news_page(context)
    elif page == "model-lab":
        render_model_page(context)

st.html(
    '<div class="method-note"><strong>Research use only.</strong> RestEdge summarizes player performance and does not provide financial or wagering recommendations. Player and team images load from the NBA content delivery network when available.</div>'
)
