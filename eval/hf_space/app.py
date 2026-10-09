"""Policy RAG evaluation dashboard. Safe to run locally or in a Docker Space."""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Policy RAG | Evaluation Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

HERE = Path(__file__).resolve().parent


def first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists() and path.is_file()), None)


def read_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_upload(uploaded):
    if uploaded is None:
        return None
    try:
        data = json.loads(uploaded.getvalue().decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        st.sidebar.error(f"Could not parse {uploaded.name} as a JSON report.")
        return None


def report_path(name: str) -> Path | None:
    return first_existing([
        HERE / name,
        HERE.parent / name,
        HERE.parent.parent / name,
    ])


def questions_path() -> Path | None:
    return first_existing([
        HERE / "questions.json",
        HERE.parent / "questions.json",
        HERE.parent.parent / "data" / "eval" / "questions.json",
        HERE / "data" / "eval" / "questions.json",
    ])


def load_questions() -> list[dict]:
    data = read_json(questions_path())
    return data if isinstance(data, list) else []


def fmt_pct(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return "—"


def fmt_ms(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.0f} ms"
    except (ValueError, TypeError):
        return "—"


def fmt_number(value, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (ValueError, TypeError):
        return "—"


def timestamp_label(report) -> str:
    value = report.get("generated_at") if isinstance(report, dict) else None
    if not value:
        return "Not run"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y · %H:%M UTC")
    except (TypeError, ValueError):
        return str(value)


# Theme: neutral canvas, indigo accents, clear hierarchy, no fake demo scores.
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: radial-gradient(ellipse at 80% 0%, rgba(83, 92, 255, .08), transparent 34%), #f6f8fc; }
      .block-container { max-width: 1400px; padding-top: 1.6rem; padding-bottom: 3rem; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -0.035em; color: #182448 !important; }
      [data-testid="stSidebar"] { background: #10162a; }
      [data-testid="stSidebar"] * { color: #e8ecff !important; }
      [data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] { color: #1f2937 !important; }
      .hero { background: linear-gradient(118deg, #131d42 0%, #28377a 52%, #394ad1 100%); padding: 2rem 2.1rem; border-radius: 22px; color: #fff; margin-bottom: 1.1rem; box-shadow: 0 18px 48px rgba(31, 42, 103, .17); }
      .hero h1 { color: #fff !important; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.05; margin: .45rem 0 .65rem 0; }
      .hero p { color: #e2e7ff; font-size: 1.02rem; max-width: 760px; margin-bottom: 0; }
      .eyebrow { color: #bfcaff; text-transform: uppercase; font-size: .72rem; font-weight: 800; letter-spacing: .16em; }
      .pill { display: inline-block; border: 1px solid rgba(255,255,255,.28); background: rgba(255,255,255,.12); border-radius: 999px; padding: .3rem .7rem; font-size: .76rem; margin-bottom: .2rem; }
      .section-kicker { color: #424f91; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; font-size: .72rem; margin: .3rem 0 .25rem 0; }
      .subtle { color: #46516b; font-size: .92rem; }
      .status-card { background: white; border: 1px solid #e3e8f3; border-radius: 16px; padding: 1rem 1.1rem; min-height: 108px; box-shadow: 0 4px 18px rgba(29, 42, 87, .035); }
      .status-label { color: #717b95; font-size: .8rem; font-weight: 700; margin-bottom: .55rem; }
      .status-value { color: #182448; font-family: 'Manrope', sans-serif; font-size: 1.12rem; font-weight: 800; }
      .status-caption { color: #838ca2; font-size: .75rem; margin-top: .35rem; }
      .info-strip { border: 1px solid #d9e4ff; background: #eef3ff; border-radius: 13px; padding: .85rem 1rem; color: #293b72; }
      .warn-strip { border: 1px solid #f1ddb0; background: #fff8e9; border-radius: 13px; padding: .85rem 1rem; color: #7a5211; }
      .stTabs [data-baseweb="tab-list"] { gap: .35rem; background: #edf1fa; border-radius: 13px; padding: .35rem; }
      .stTabs [data-baseweb="tab"] {
    color: #25304a !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
} { border-radius: 9px; padding: .6rem 1rem; color: #39445e !important; }
      .stTabs [aria-selected="true"] { background: #fff !important; color: #29358d !important; box-shadow: 0 2px 8px rgba(24, 36, 72, .08); }
      div[data-testid="stMetric"] { background: #fff; border: 1px solid #e3e8f3; padding: 1rem 1.1rem; border-radius: 15px; box-shadow: 0 4px 18px rgba(29, 42, 87, .035); }
      div[data-testid="stMetricLabel"] { color: #46516b !important; font-weight: 700; }
      div[data-testid="stMetricValue"] { color: #182448 !important; font-family: 'Manrope', sans-serif; }
      .footer { color: #7b8499; font-size: .78rem; border-top: 1px solid #e0e6f1; margin-top: 2rem; padding-top: 1rem; }
      .small-code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background: #eef1f8; border-radius: 6px; padding: .15rem .35rem; color: #38416b; }

      /* High-contrast labels and navigation */
      div[data-testid="stMetricLabel"],
      div[data-testid="stMetricLabel"] *,
      div[data-testid="stMetricLabel"] p {
        color: #39445e !important;
        opacity: 1 !important;
      }
      .stTabs [data-baseweb="tab"] {
    color: #25304a !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
},
      .stTabs [data-baseweb="tab"] {
    color: #25304a !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
} *,
      .stTabs [data-baseweb="tab"] {
    color: #25304a !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
} p,
      .stTabs [data-baseweb="tab"] {
    color: #25304a !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p {
    color: #25304a !important;
    opacity: 1 !important;
} span {
        color: #39445e !important;
        opacity: 1 !important;
      }
      .stTabs [aria-selected="true"],
      .stTabs [aria-selected="true"] * {
        color: #28377a !important;
      }
      [data-testid="stMarkdownContainer"] h2,
      [data-testid="stMarkdownContainer"] h3 {
        color: #182448 !important;
      }
      .status-label, .status-value, .status-caption {
        opacity: 1 !important;
      }
      div[data-testid="stMetricValue"],
      div[data-testid="stMetricValue"] * {
        color: #182448 !important;
        opacity: 1 !important;
      }
    
      /* Final hero and code contrast fix */

      /* Restore contrast inside the blue hero banner */
      .stApp .hero,
      .stApp .hero * {
        color: #f4f6ff !important;
        -webkit-text-fill-color: #f4f6ff !important;
      }

      .stApp .hero h1 {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }

      .stApp .hero p {
        color: #e5eaff !important;
        -webkit-text-fill-color: #e5eaff !important;
      }

      .stApp .hero .eyebrow {
        color: #cbd5ff !important;
        -webkit-text-fill-color: #cbd5ff !important;
      }

      .stApp .hero .pill {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        background: rgba(255,255,255,.13) !important;
        border-color: rgba(255,255,255,.35) !important;
      }

      /* Use light code surfaces with readable dark text */
      .stApp [data-testid="stMarkdownContainer"] code,
      .stApp code {
        background: #e9edf6 !important;
        color: #263451 !important;
        -webkit-text-fill-color: #263451 !important;
        border: 1px solid #d9e0ed !important;
        border-radius: 5px !important;
      }

      .stApp [data-testid="stCode"],
      .stApp [data-testid="stCode"] pre,
      .stApp [data-testid="stCode"] code,
      .stApp pre,
      .stApp pre code {
        background: #f0f3f9 !important;
        color: #263451 !important;
        -webkit-text-fill-color: #263451 !important;
        border-color: #d9e0ed !important;
        text-shadow: none !important;
      }

      .stApp [data-testid="stCode"] *,
      .stApp pre span {
        color: #263451 !important;
        -webkit-text-fill-color: #263451 !important;
      }

    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">POLICYGUARD AI · QUALITY ENGINEERING</div>
      <h1>Evaluation Lab</h1>
      <p>Measure retrieval quality, evidence availability, answer grounding and latency. Every number on this dashboard comes from a saved evaluation report—not demo or placeholder scores.</p>
      <div style="margin-top:1rem"><span class="pill">Hybrid retrieval</span>&nbsp; <span class="pill">Cross-encoder reranking</span>&nbsp; <span class="pill">LLM-as-judge</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

questions = load_questions()
retrieval_file = report_path("results_retrieval.json")
generation_file = report_path("results_generation.json")
retrieval_report = read_json(retrieval_file)
generation_report = read_json(generation_file)

with st.sidebar:
    st.markdown("## 📊 Evaluation controls")
    st.caption("This dashboard reads reports generated by the repository's evaluation scripts. It does not call the LLM or require an API key.")
    st.markdown("---")
    st.markdown("**Load a report for preview**")
    retrieval_upload = st.file_uploader("Retrieval report (.json)", type="json", key="retrieval_upload")
    generation_upload = st.file_uploader("Generation report (.json)", type="json", key="generation_upload")
    uploaded_retrieval = read_upload(retrieval_upload)
    uploaded_generation = read_upload(generation_upload)
    if uploaded_retrieval is not None:
        retrieval_report = uploaded_retrieval
    if uploaded_generation is not None:
        generation_report = uploaded_generation
    if retrieval_upload or generation_upload:
        st.caption("Uploaded reports are preview-only; they are not saved to disk.")
    st.markdown("---")
    st.markdown("**Run locally**")
    st.code("python -m eval.hit_rate\npython -m eval.judge", language="powershell")
    st.caption("Run from the repository root after building the local Chroma index and configuring your private .env.")

retrieval_ready = isinstance(retrieval_report, dict) and isinstance(retrieval_report.get("metrics"), list)
generation_ready = isinstance(generation_report, dict) and isinstance(generation_report.get("metrics"), dict)
retrieval_rows = retrieval_report.get("metrics", []) if retrieval_ready else []
gen_metrics = generation_report.get("metrics", {}) if generation_ready else {}
retrieval_count = retrieval_report.get("n_questions") if retrieval_ready else None
generation_count = generation_report.get("n_questions") if generation_ready else None

status_cols = st.columns(4)
status_values = [
    ("Evaluation set", str(len(questions)) if questions else str(retrieval_count or generation_count or "—"), "labelled questions"),
    ("Retrieval benchmark", "Ready" if retrieval_ready else "Not run", timestamp_label(retrieval_report) if retrieval_ready else "Waiting for results_retrieval.json"),
    ("Generation benchmark", "Ready" if generation_ready else "Not run", timestamp_label(generation_report) if generation_ready else "Waiting for results_generation.json"),
    ("Evaluation posture", "Evidence-first", "Scores include stated limitations"),
]
for col, (label, value, caption) in zip(status_cols, status_values):
    col.markdown(
        f'<div class="status-card"><div class="status-label">{escape(label)}</div><div class="status-value">{escape(value)}</div><div class="status-caption">{escape(caption)}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)
if not retrieval_ready or not generation_ready:
    missing = []
    if not retrieval_ready:
        missing.append("retrieval")
    if not generation_ready:
        missing.append("generation")
    st.markdown(
        "<div class='warn-strip'><b>Benchmark results are incomplete.</b> "
        + escape("Missing report: " + " and ".join(missing) + ". Run the evaluation commands from the repository root, then refresh this dashboard. Until the reports exist, no metric scores are displayed.")
        + "</div>",
        unsafe_allow_html=True,
    )

summary_tab, retrieval_tab, generation_tab, explorer_tab, method_tab = st.tabs(
    ["Overview", "Retrieval quality", "Answer quality", "Question explorer", "Methodology"]
)

with summary_tab:
    st.markdown("<div class='section-kicker'>At a glance</div>", unsafe_allow_html=True)
    st.subheader("Benchmark snapshot")
    if retrieval_ready:
        best = max(retrieval_rows, key=lambda row: row.get("hit_rate_at_k", -1)) if retrieval_rows else None
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Best hit rate@{retrieval_report.get('k', 5)}", fmt_pct(best.get("hit_rate_at_k")) if best else "—")
        if best:
            c1.caption(best.get("label", ""))
        c2.metric("Best MRR@k", fmt_number(max((row.get("mrr_at_k", 0) for row in retrieval_rows), default=None)))
        c3.metric("Questions in retrieval run", str(retrieval_count or "—"))
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Best hit rate@k", "Not measured")
        c2.metric("Best MRR@k", "Not measured")
        c3.metric("Questions in retrieval run", "—")
    if generation_ready:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Answered rate", fmt_pct(gen_metrics.get("answered_rate")))
        c2.metric("LLM-judged groundedness", fmt_pct(gen_metrics.get("llm_judged_groundedness_rate")))
        c3.metric("Gold evidence retrieved", fmt_pct(gen_metrics.get("gold_source_page_retrieved_rate")))
        c4.metric("p95 latency", fmt_ms(gen_metrics.get("p95_latency_ms")))
    else:
        st.info("Generation metrics will appear after `python -m eval.judge` produces a JSON report.")

    if retrieval_ready and retrieval_rows:
        st.markdown("#### Retrieval comparison")
        comparison = pd.DataFrame([
            {"Mode": row.get("label", row.get("mode", "unknown")), "Metric": "Hit rate@k", "Score": row.get("hit_rate_at_k", 0)}
            for row in retrieval_rows
        ] + [
            {"Mode": row.get("label", row.get("mode", "unknown")), "Metric": "MRR@k", "Score": row.get("mrr_at_k", 0)}
            for row in retrieval_rows
        ])
        fig = px.bar(comparison, x="Mode", y="Score", color="Metric", barmode="group", range_y=[0, 1],
                     color_discrete_sequence=["#4857d8", "#1a9eac"], template="plotly_white")
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), legend_title_text="", height=340, yaxis_title="Score (0–1)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("<div class='info-strip'>Once the retrieval run is complete, this section will compare semantic-only, hybrid and hybrid + reranking performance.</div>", unsafe_allow_html=True)

    st.markdown("#### How to read these scores")
    st.markdown(
        "- **Hit rate@k:** share of questions with the exact labelled source file and page in the first *k* results.\n"
        "- **MRR@k:** rewards a correct source/page ranked nearer the top.\n"
        "- **Groundedness:** an LLM judge's estimate that answer claims are supported by retrieved context—not a human audit.\n"
        "- **p95 latency:** the 95th-percentile measured request time for that evaluation run."
    )

with retrieval_tab:
    st.markdown("<div class='section-kicker'>Retrieval benchmark</div>", unsafe_allow_html=True)
    st.subheader("Which retrieval strategy finds the labelled evidence?")
    if not retrieval_ready:
        st.info("No retrieval report has been loaded. Run `python -m eval.hit_rate` locally, or upload a generated `results_retrieval.json` in the sidebar.")
    else:
        k = retrieval_report.get("k", 5)
        st.caption(f"{retrieval_count or 'Unknown'} questions · exact source + page match · top {k} · {timestamp_label(retrieval_report)}")
        table_rows = []
        for row in retrieval_rows:
            table_rows.append({
                "Retrieval mode": row.get("label", row.get("mode", "unknown")),
                "Hits": f"{row.get('hits', 0)}/{retrieval_count or '?'}",
                f"Hit rate@{k}": fmt_pct(row.get("hit_rate_at_k")),
                f"MRR@{k}": fmt_number(row.get("mrr_at_k")),
                "Mean latency": fmt_ms(row.get("mean_latency_ms")),
                "p95 latency": fmt_ms(row.get("p95_latency_ms")),
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        if retrieval_rows:
            latency_df = pd.DataFrame([
                {"Mode": row.get("label", row.get("mode", "unknown")), "Latency (ms)": row.get("mean_latency_ms", 0), "Tail latency (p95 ms)": row.get("p95_latency_ms", 0)}
                for row in retrieval_rows
            ]).melt(id_vars="Mode", var_name="Measurement", value_name="Milliseconds")
            fig = px.bar(latency_df, x="Mode", y="Milliseconds", color="Measurement", barmode="group",
                         color_discrete_sequence=["#4857d8", "#f39c4a"], template="plotly_white")
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), legend_title_text="", height=300)
            st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download retrieval JSON", json.dumps(retrieval_report, indent=2),
                            file_name="results_retrieval.json", mime="application/json")
        for note in retrieval_report.get("limitations", []):
            st.caption("• " + str(note))

with generation_tab:
    st.markdown("<div class='section-kicker'>Generation benchmark</div>", unsafe_allow_html=True)
    st.subheader("Does the answer stay grounded in retrieved evidence?")
    if not generation_ready:
        st.info("No generation report has been loaded. Run `python -m eval.judge` locally, or upload `results_generation.json` in the sidebar.")
    else:
        st.caption(f"{generation_count or 'Unknown'} questions · judge coverage {fmt_pct(gen_metrics.get('judge_coverage'))} · {timestamp_label(generation_report)}")
        cards = st.columns(4)
        cards[0].metric("Answered", fmt_pct(gen_metrics.get("answered_rate")))
        cards[1].metric("Groundedness¹", fmt_pct(gen_metrics.get("llm_judged_groundedness_rate")))
        cards[2].metric("Question relevance¹", fmt_pct(gen_metrics.get("llm_judged_question_relevance_rate")))
        cards[3].metric("Evidence page found", fmt_pct(gen_metrics.get("gold_source_page_retrieved_rate")))
        latency_cols = st.columns(3)
        latency_cols[0].metric("Median latency", fmt_ms(gen_metrics.get("median_latency_ms")))
        latency_cols[1].metric("p95 latency", fmt_ms(gen_metrics.get("p95_latency_ms")))
        latency_cols[2].metric("Judge coverage", fmt_pct(gen_metrics.get("judge_coverage")))
        st.markdown("<div class='warn-strip'><b>¹ LLM-as-judge estimate.</b> This repository has source/page labels but no gold reference answers, so it cannot claim directly measured factual answer accuracy. Treat scores as a quality signal, not proof of correctness.</div>", unsafe_allow_html=True)
        generation_rows = generation_report.get("per_question", [])
        if generation_rows:
            generation_df = pd.DataFrame([{
                "Question": row.get("question", ""),
                "Answered": "Yes" if row.get("answered") else "No / error",
                "Gold page retrieved": "Yes" if row.get("gold_source_page_retrieved") else "No",
                "Grounded": ("Yes" if row.get("judgement", {}).get("supported") else "No") if isinstance(row.get("judgement"), dict) else "Not judged",
                "Relevant": ("Yes" if row.get("judgement", {}).get("answers_question") else "No") if isinstance(row.get("judgement"), dict) else "Not judged",
                "Latency (ms)": row.get("latency_ms"),
            } for row in generation_rows])
            st.dataframe(generation_df, use_container_width=True, hide_index=True, height=420)
        st.download_button("Download generation JSON", json.dumps(generation_report, indent=2),
                            file_name="results_generation.json", mime="application/json")
        for note in generation_report.get("limitations", []):
            st.caption("• " + str(note))

with explorer_tab:
    st.markdown("<div class='section-kicker'>Question-level diagnostics</div>", unsafe_allow_html=True)
    st.subheader("Trace failures back to a question")
    search = st.text_input("Filter questions", placeholder="Search by topic or wording…")
    source_filter = st.text_input("Optional source-file filter", placeholder="e.g. Health Protector")
    view = st.radio("Report", ["Retrieval", "Generation"], horizontal=True)
    if view == "Retrieval":
        per_question = retrieval_report.get("per_question", []) if retrieval_ready else []
        flat_rows = []
        for row in per_question:
            for mode, result in row.get("modes", {}).items():
                flat_rows.append({
                    "Question": row.get("question", ""), "Expected source": row.get("expected_source", ""),
                    "Expected page": row.get("expected_page", ""), "Mode": mode,
                    "Hit": "✓" if result.get("hit") else "—", "Rank": result.get("rank") or "Miss",
                    "Latency (ms)": result.get("latency_ms"),
                })
        df = pd.DataFrame(flat_rows)
    else:
        per_question = generation_report.get("per_question", []) if generation_ready else []
        df = pd.DataFrame([{
            "Question": row.get("question", ""), "Expected source": row.get("expected_source", ""),
            "Expected page": row.get("expected_page", ""), "Answered": "Yes" if row.get("answered") else "No / error",
            "Gold page retrieved": "Yes" if row.get("gold_source_page_retrieved") else "No",
            "Grounded": ("Yes" if row.get("judgement", {}).get("supported") else "No") if isinstance(row.get("judgement"), dict) else "Not judged",
            "Latency (ms)": row.get("latency_ms"),
        } for row in per_question])
    if df.empty:
        st.info("No question-level report data is available yet. Run an evaluation or upload a report.")
    else:
        if search:
            df = df[df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
        if source_filter and "Expected source" in df.columns:
            df = df[df["Expected source"].astype(str).str.contains(source_filter, case=False, na=False)]
        st.caption(f"Showing {len(df)} matching row(s).")
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)
        st.download_button("Download filtered CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name="evaluation_question_diagnostics.csv", mime="text/csv")

with method_tab:
    st.markdown("<div class='section-kicker'>Benchmark contract</div>", unsafe_allow_html=True)
    st.subheader("How these numbers are produced")
    st.markdown("""
    **Retrieval evaluation** compares three modes against each dataset entry's labelled `source` and `page`:
    semantic-only, hybrid (semantic + BM25 reciprocal-rank fusion), and hybrid plus cross-encoder reranking.

    **Generation evaluation** runs retrieval + answer generation, then asks an LLM judge whether the answer is supported by the retrieved context and whether it addresses the question. The report also tracks whether the labelled source/page was retrieved and records latency.

    **Important limitations**
    - Questions were generated from chunks that were already in the index. They are not fully independent, held-out test questions.
    - Exact source/page matching can mark useful neighbouring evidence as a miss.
    - LLM judging is approximate and may be biased because the generator and judge use the same configured model.
    - The current test set does not contain a curated set of unanswerable questions, and there are no human-authored gold answers.
    - Do not use these results alone to make insurance coverage decisions. Review missed questions and claims with a qualified human reviewer.
    """)
    st.markdown("#### Reproduce locally")
    st.code("# From the project root, after building the local index\npython -m eval.hit_rate --k 5\npython -m eval.judge --limit 30 --delay 4", language="bash")
    st.markdown("#### Report files")
    st.markdown("- `eval/results_retrieval.json` and `.md` — ranking measurements and per-question ranks.\n- `eval/results_generation.json` and `.md` — answer/grounding/judging measurements and per-question labels.\n- `data/eval/questions.json` — current 40-question labelled dataset.")

st.markdown(
    "<div class='footer'>Policy RAG Evaluation Lab · Transparent metrics, explicit limitations, no hard-coded benchmark scores.</div>",
    unsafe_allow_html=True,
)
