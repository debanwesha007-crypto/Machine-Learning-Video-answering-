# 🧬 Codebase Personality Profiler

> *Reveal the human behind the code — instantly.*

Enter any public GitHub repo URL and get a **personality radar chart + narrative report** 
across 6 developer archetypes: Perfectionist, Hacker, Academic, Pragmatist, Lone Wolf, Collaborator.

---

## 🚀 Quick Start

### 1. Clone / unzip the project
```bash
cd codebase_profiler
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🔑 API Keys

| Key | Where to get | Required? |
|-----|-------------|-----------|
| **Anthropic API Key** | https://console.anthropic.com | ✅ Yes |
| **GitHub Token** | https://github.com/settings/tokens (read-only) | Optional (raises rate limit) |

Enter both in the **sidebar** of the app. No `.env` file needed.

---

## 🏗️ Architecture

```
GitHub URL
    │
    ▼
github_ingestor.py   ← PyGithub: commits, files, README, contributors
    │
    ▼
feature_extractor.py ← commit tone, naming style, doc quality, collab signals
    │
    ▼
embedder.py          ← sentence-transformers: cluster commit semantics
    │
    ▼
personality_scorer.py← Claude API: maps features → 6 trait scores + report
    │
    ▼
app.py               ← Streamlit UI + Plotly radar chart
```

---

## 🎯 The 6 Personality Traits

| Trait | Signals |
|-------|---------|
| **Perfectionist** | Conventional commits, tests, detailed README, low commit variance |
| **Hacker** | Short commits, emojis, fast iteration, minimal docs |
| **Academic** | Long README, doc files, topic tags, detailed messages |
| **Pragmatist** | Balanced style, config files, practical naming |
| **Lone Wolf** | Single contributor, no wiki, few forks |
| **Collaborator** | Many contributors, issue refs, wiki, high forks |

---

## 📦 Tech Stack

| Layer | Tool |
|-------|------|
| Data Ingestion | PyGithub |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Claude API (claude-opus-4-5) |
| Feature Eng. | pandas, scikit-learn, regex |
| UI | Streamlit |
| Charts | Plotly |

---

## 🧪 Demo Repos to Try

- `torvalds/linux` — Pragmatist + Lone Wolf
- `karpathy/nanoGPT` — Hacker + Perfectionist  
- `tensorflow/tensorflow` — Academic + Collaborator
- `fastapi/fastapi` — Pragmatist + Collaborator
- `psf/requests` — Perfectionist + Collaborator

---

## 📁 Project Structure

```
codebase_profiler/
├── app.py                  # Streamlit UI (main entry point)
├── github_ingestor.py      # GitHub API data fetching
├── feature_extractor.py    # Feature engineering
├── embedder.py             # Sentence-transformer embeddings
├── personality_scorer.py   # Claude API integration
├── requirements.txt        # Python dependencies
└── README.md
```
