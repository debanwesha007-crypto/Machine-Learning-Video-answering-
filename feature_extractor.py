"""
feature_extractor.py
Extracts personality-relevant features from raw RepoData.
"""

import re
import math
from collections import Counter
from typing import List
from github_ingestor import RepoData


# ── Commit message analysis ────────────────────────────────────────────────────

IMPERATIVE_VERBS = {"add", "fix", "update", "remove", "refactor", "change",
                    "improve", "implement", "merge", "revert", "delete", "create",
                    "move", "rename", "bump", "release", "hotfix", "init"}

def analyze_commits(commits: List[dict]) -> dict:
    if not commits:
        return {}

    messages = [c["message"] for c in commits]
    first_words = []
    lengths = []
    has_emoji = 0
    has_issue_ref = 0
    multiline = 0
    conventional_commits = 0   # feat:, fix:, chore: etc.

    conventional_pattern = re.compile(r"^(feat|fix|chore|docs|style|refactor|test|perf|ci|build)(\(.+\))?!?:")
    issue_pattern = re.compile(r"(#\d+|closes|fixes|resolves)", re.IGNORECASE)
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]|[\u2600-\u27BF]", re.UNICODE)

    for msg in messages:
        lines = msg.strip().split("\n")
        first_line = lines[0].strip()
        lengths.append(len(first_line))

        words = first_line.lower().split()
        if words:
            first_words.append(words[0].rstrip(":!?,"))

        if emoji_pattern.search(first_line):
            has_emoji += 1
        if issue_pattern.search(msg):
            has_issue_ref += 1
        if len(lines) > 1 and any(l.strip() for l in lines[1:]):
            multiline += 1
        if conventional_pattern.match(first_line):
            conventional_commits += 1

    n = len(messages)
    imperative_count = sum(1 for w in first_words if w in IMPERATIVE_VERBS)

    return {
        "avg_commit_length": sum(lengths) / n,
        "emoji_ratio": has_emoji / n,
        "issue_ref_ratio": has_issue_ref / n,
        "multiline_ratio": multiline / n,
        "conventional_commit_ratio": conventional_commits / n,
        "imperative_ratio": imperative_count / n,
        "commit_length_variance": _variance(lengths),
        "unique_authors": len(set(c["author"] for c in commits)),
    }


# ── File & naming style analysis ──────────────────────────────────────────────

def analyze_file_tree(file_tree: List[str]) -> dict:
    if not file_tree:
        return {}

    snake = sum(1 for f in file_tree if re.search(r'[a-z]_[a-z]', f.split("/")[-1]))
    camel = sum(1 for f in file_tree if re.search(r'[a-z][A-Z]', f.split("/")[-1]))
    kebab = sum(1 for f in file_tree if re.search(r'[a-z]-[a-z]', f.split("/")[-1]))

    # Doc files
    doc_files = sum(1 for f in file_tree if any(
        f.lower().endswith(ext) for ext in [".md", ".rst", ".txt", ".adoc", "license", "changelog"]
    ))
    test_files = sum(1 for f in file_tree if re.search(r'test|spec', f, re.IGNORECASE))
    config_files = sum(1 for f in file_tree if any(
        f.lower().endswith(ext) for ext in [".yml", ".yaml", ".toml", ".cfg", ".ini", ".json", ".env"]
    ))

    n = len(file_tree)
    dominant_style = "snake_case" if snake >= camel and snake >= kebab else \
                     "camelCase" if camel >= kebab else "kebab-case"

    # Folder depth
    depths = [len(f.split("/")) for f in file_tree]
    avg_depth = sum(depths) / n if depths else 0

    return {
        "snake_ratio": snake / n,
        "camel_ratio": camel / n,
        "kebab_ratio": kebab / n,
        "dominant_naming": dominant_style,
        "doc_file_ratio": doc_files / n,
        "test_file_ratio": test_files / n,
        "config_file_ratio": config_files / n,
        "avg_folder_depth": avg_depth,
        "total_files": n,
    }


# ── Documentation quality ──────────────────────────────────────────────────────

def analyze_readme(readme: str) -> dict:
    if not readme:
        return {"readme_length": 0, "has_badges": False, "has_code_blocks": False,
                "has_sections": False, "readme_score": 0}

    has_badges = bool(re.search(r'!\[.*?\]\(.*?shield|badge', readme, re.IGNORECASE))
    has_code_blocks = "```" in readme or "    " in readme
    sections = re.findall(r'^#{1,3} .+', readme, re.MULTILINE)
    word_count = len(readme.split())

    score = 0
    if word_count > 100: score += 1
    if word_count > 500: score += 1
    if has_badges:       score += 1
    if has_code_blocks:  score += 1
    if len(sections) >= 3: score += 1

    return {
        "readme_length": word_count,
        "has_badges": has_badges,
        "has_code_blocks": has_code_blocks,
        "section_count": len(sections),
        "has_sections": len(sections) >= 2,
        "readme_score": score,   # 0–5
    }


# ── Collaboration signals ──────────────────────────────────────────────────────

def analyze_collaboration(repo_data: RepoData) -> dict:
    n_contributors = len(repo_data.contributors)
    is_solo = n_contributors <= 1

    return {
        "contributor_count": n_contributors,
        "is_solo": is_solo,
        "has_wiki": repo_data.has_wiki,
        "open_issues": repo_data.open_issues,
        "stars": repo_data.stars,
        "forks": repo_data.forks,
        "topic_count": len(repo_data.topics),
    }


# ── Master extractor ──────────────────────────────────────────────────────────

def extract_features(repo_data: RepoData) -> dict:
    """Run all extractors and return a unified feature dict."""
    features = {}
    features.update(analyze_commits(repo_data.commits))
    features.update(analyze_file_tree(repo_data.file_tree))
    features.update(analyze_readme(repo_data.readme))
    features.update(analyze_collaboration(repo_data))
    features["languages"] = list(repo_data.languages.keys())[:5]
    features["primary_language"] = features["languages"][0] if features["languages"] else "Unknown"
    return features


# ── Helpers ───────────────────────────────────────────────────────────────────

def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)
