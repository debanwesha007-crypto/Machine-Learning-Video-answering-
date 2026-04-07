"""
app.py  —  Codebase Personality Profiler
Streamlit UI: input a GitHub URL → get a personality radar + narrative report.
"""

import streamlit as st
import plotly.graph_objects as go
import os
import sys

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Codebase Personality Profiler",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1b2d; }
    .stApp { background-color: #0f1b2d; color: #f0f4f8; }
    h1, h2, h3 { color: #14b8a6 !important; }
    .trait-card {
        background: #1e3a52;
        border-left: 4px solid #0d9488;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .strength-pill {
        display: inline-block;
        background: #0d9488;
        color: white;
        border-radius: 20px;
        padding: 4px 14px;
        margin: 4px;
        font-size: 0.85em;
    }
    .evidence-box {
        background: #1a2f4a;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 0.82em;
        color: #94a3b8;
        margin-top: 4px;
    }
    .metric-box {
        background: #1e3a52;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .sig-badge {
        background: linear-gradient(135deg, #0d9488, #0891b2);
        color: white;
        border-radius: 24px;
        padding: 8px 24px;
        font-size: 1.1em;
        font-weight: bold;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ── Imports (local modules) ────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from github_ingestor import fetch_repo_data, parse_github_url
from feature_extractor import extract_features
from embedder import get_embedding_features
from personality_scorer import score_personality, TRAITS

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    anthropic_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Required for personality analysis via Claude."
    )
    github_token = st.text_input(
        "GitHub Token (optional)",
        type="password",
        placeholder="ghp_...",
        help="Increases rate limit from 60 → 5000 req/hr."
    )
    max_commits = st.slider("Max commits to analyse", 20, 200, 100, step=10)

    st.markdown("---")
    st.markdown("### 🔬 Try these repos")
    examples = {
        "torvalds/linux": "github.com/torvalds/linux",
        "karpathy/nanoGPT": "github.com/karpathy/nanoGPT",
        "tensorflow/tensorflow": "github.com/tensorflow/tensorflow",
        "fastapi/fastapi": "github.com/fastapi/fastapi",
        "psf/requests": "github.com/psf/requests",
    }
    for label, url in examples.items():
        if st.button(f"📂 {label}", use_container_width=True):
            st.session_state["repo_url"] = url

    st.markdown("---")
    st.caption("Built with Claude API · sentence-transformers · Streamlit · Plotly")

# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("# 🧬 Codebase Personality Profiler")
st.markdown("*Reveal the human behind the code — instantly.*")
st.markdown("---")

# ── URL Input ─────────────────────────────────────────────────────────────────
default_url = st.session_state.get("repo_url", "")
repo_url = st.text_input(
    "GitHub Repository URL",
    value=default_url,
    placeholder="https://github.com/owner/repo  or  owner/repo",
    label_visibility="collapsed",
)

col_btn, col_hint = st.columns([1, 4])
with col_btn:
    analyse = st.button("🔍 Analyse Repo", type="primary", use_container_width=True)
with col_hint:
    st.caption("Fetches last 100 commits, file tree, README, contributors and more.")

# ── Analysis pipeline ─────────────────────────────────────────────────────────
if analyse:
    if not repo_url.strip():
        st.error("Please enter a GitHub repository URL.")
        st.stop()

    if not anthropic_key.strip():
        st.error("Please enter your Anthropic API key in the sidebar.")
        st.stop()

    parsed = parse_github_url(repo_url.strip())
    if not parsed:
        st.error("Could not parse that URL. Try: `https://github.com/owner/repo` or `owner/repo`")
        st.stop()

    owner, repo_name = parsed

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    with st.status(f"📡 Fetching data from **{owner}/{repo_name}**...", expanded=True) as status:
        st.write("Connecting to GitHub API...")
        try:
            repo_data = fetch_repo_data(
                repo_url,
                token=github_token.strip() or None,
                max_commits=max_commits,
            )
            st.write(f"✅ Fetched {repo_data.total_commits_fetched} commits, {len(repo_data.file_tree)} files")
        except ValueError as e:
            status.update(label="❌ Failed", state="error")
            st.error(str(e))
            st.stop()

        # ── Step 2: Extract features ──────────────────────────────────────────
        st.write("⚙️ Extracting features (commit style, naming, docs, collaboration)...")
        features = extract_features(repo_data)

        # ── Step 3: Embed commits ─────────────────────────────────────────────
        st.write("🤖 Embedding commit messages with sentence-transformers...")
        messages = [c["message"] for c in repo_data.commits]
        embedding_features = get_embedding_features(messages)
        features.update(embedding_features)

        # ── Step 4: Score personality ─────────────────────────────────────────
        st.write("🧠 Asking Claude to analyse personality...")
        personality = score_personality(features, api_key=anthropic_key.strip())

        status.update(label="✅ Analysis complete!", state="complete", expanded=False)

    # ── Results ───────────────────────────────────────────────────────────────
    traits = personality.get("traits", {t: 50 for t in TRAITS})
    summary = personality.get("summary", "")
    strengths = personality.get("strengths", [])
    growth = personality.get("growth_area", "")
    sig_trait = personality.get("signature_trait", "")
    evidence = personality.get("evidence", {})

    st.markdown("---")

    # Repo meta row
    c1, c2, c3, c4, c5 = st.columns(5)
    meta = [
        ("⭐ Stars", f"{repo_data.stars:,}"),
        ("🍴 Forks", f"{repo_data.forks:,}"),
        ("👥 Contributors", str(len(repo_data.contributors))),
        ("📝 Commits", str(repo_data.total_commits_fetched)),
        ("📁 Files", str(len(repo_data.file_tree))),
    ]
    for col, (label, val) in zip([c1, c2, c3, c4, c5], meta):
        with col:
            st.markdown(f"""<div class="metric-box">
                <div style="font-size:1.5em;font-weight:bold;color:#14b8a6">{val}</div>
                <div style="color:#94a3b8;font-size:0.8em">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Signature trait + summary
    st.markdown(f"""<div style="text-align:center;margin-bottom:16px">
        <div style="color:#94a3b8;font-size:0.9em;margin-bottom:8px">SIGNATURE TRAIT</div>
        <span class="sig-badge">🏆 {sig_trait}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="trait-card" style="font-size:1.05em;color:#f0f4f8;font-style:italic">
        "{summary}"
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Radar chart + trait cards side by side ────────────────────────────────
    left, right = st.columns([1, 1])

    with left:
        st.markdown("### 📊 Personality Radar")

        trait_names = list(traits.keys())
        trait_values = list(traits.values())
        # Close the radar loop
        trait_names_plot = trait_names + [trait_names[0]]
        trait_values_plot = trait_values + [trait_values[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=trait_values_plot,
            theta=trait_names_plot,
            fill="toself",
            fillcolor="rgba(13, 148, 136, 0.25)",
            line=dict(color="#0d9488", width=2.5),
            marker=dict(color="#14b8a6", size=8),
            name="Personality",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(color="#94a3b8", size=10),
                    gridcolor="#1e3a52",
                    linecolor="#1e3a52",
                ),
                angularaxis=dict(
                    tickfont=dict(color="#f0f4f8", size=13),
                    gridcolor="#1e3a52",
                    linecolor="#243f5c",
                ),
                bgcolor="#0f1b2d",
            ),
            paper_bgcolor="#0f1b2d",
            plot_bgcolor="#0f1b2d",
            font=dict(color="#f0f4f8"),
            showlegend=False,
            margin=dict(t=20, b=20, l=40, r=40),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### 🎯 Trait Breakdown")
        for trait in TRAITS:
            score = traits.get(trait, 50)
            bar_color = "#0d9488" if score >= 60 else "#1e3a52"
            ev = evidence.get(trait, "")
            st.markdown(f"""<div class="trait-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-weight:bold;color:#f0f4f8">{trait}</span>
                    <span style="color:#14b8a6;font-weight:bold">{score}/100</span>
                </div>
                <div style="background:#0f1b2d;border-radius:4px;height:6px;margin:8px 0">
                    <div style="background:{bar_color};width:{score}%;height:6px;border-radius:4px;
                         transition:width 0.5s ease"></div>
                </div>
                <div class="evidence-box">💡 {ev}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Strengths & Growth ────────────────────────────────────────────────────
    s1, s2 = st.columns([1, 1])

    with s1:
        st.markdown("### 💪 Top Strengths")
        pills_html = "".join(f'<span class="strength-pill">✓ {s}</span>' for s in strengths)
        st.markdown(f'<div style="margin-top:8px">{pills_html}</div>', unsafe_allow_html=True)

    with s2:
        st.markdown("### 🌱 Growth Area")
        st.markdown(f"""<div class="trait-card" style="color:#f0f4f8">
            📈 {growth}
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Raw features expander ─────────────────────────────────────────────────
    with st.expander("🔬 View raw extracted features"):
        import json
        st.json(features)

# ── Empty state ───────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#94a3b8">
        <div style="font-size:4em">🧬</div>
        <div style="font-size:1.3em;margin:16px 0">Enter a GitHub URL above to get started</div>
        <div>The profiler analyses commits, file structure, documentation quality,<br>
        and collaboration patterns to reveal the personality behind the code.</div>
    </div>
    """, unsafe_allow_html=True)

    # How it works
    st.markdown("---")
    st.markdown("### 🔬 How it works")
    cols = st.columns(6)
    steps = [
        ("📡", "Ingest", "Fetches commits, file tree, README via GitHub API"),
        ("⚙️", "Extract", "Analyses commit style, naming conventions, doc quality"),
        ("🤖", "Embed", "Clusters commits with sentence-transformers"),
        ("🧠", "Score", "Claude maps features to 6 personality dimensions"),
        ("📊", "Visualise", "Radar chart + trait breakdown with evidence"),
        ("📝", "Report", "Plain-English summary, strengths & growth area"),
    ]
    for col, (icon, title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"""<div style="text-align:center;padding:12px;background:#1e3a52;
                border-radius:8px;height:140px">
                <div style="font-size:1.8em">{icon}</div>
                <div style="font-weight:bold;color:#14b8a6;margin:6px 0">{title}</div>
                <div style="font-size:0.78em;color:#94a3b8">{desc}</div>
            </div>""", unsafe_allow_html=True)
