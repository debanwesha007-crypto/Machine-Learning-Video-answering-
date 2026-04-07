"""
github_ingestor.py
Fetches raw data from a GitHub repo using PyGithub.
"""

from github import Github, GithubException
from dataclasses import dataclass, field
from typing import List, Optional
import re


@dataclass
class RepoData:
    repo_name: str
    description: str
    readme: str
    commits: List[dict]          # [{message, author, date, additions, deletions}]
    file_tree: List[str]         # list of file paths
    contributors: List[str]      # list of contributor logins
    languages: dict              # {lang: bytes}
    stars: int
    forks: int
    open_issues: int
    has_wiki: bool
    topics: List[str]
    total_commits_fetched: int


def parse_github_url(url: str) -> Optional[tuple]:
    """Extract owner and repo name from a GitHub URL."""
    patterns = [
        r"github\.com/([^/]+)/([^/\s]+?)(?:\.git)?(?:/.*)?$",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url.strip())
        if m:
            return m.group(1), m.group(2).rstrip("/")
    return None


def fetch_repo_data(github_url: str, token: Optional[str] = None, max_commits: int = 100) -> RepoData:
    """
    Fetches repository data from GitHub.
    Args:
        github_url: Full GitHub URL or 'owner/repo' string
        token: Optional GitHub personal access token (avoids rate limits)
        max_commits: Max number of commits to fetch (default 100)
    Returns:
        RepoData dataclass
    """
    parsed = parse_github_url(github_url)
    if not parsed:
        raise ValueError(f"Could not parse GitHub URL: {github_url}")

    owner, repo_name = parsed
    g = Github(token) if token else Github()

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
    except GithubException as e:
        raise ValueError(f"Could not access repo '{owner}/{repo_name}': {e.data.get('message', str(e))}")

    # --- README ---
    readme = ""
    try:
        readme_file = repo.get_readme()
        readme = readme_file.decoded_content.decode("utf-8", errors="ignore")[:3000]
    except GithubException:
        readme = ""

    # --- COMMITS ---
    commits = []
    try:
        for commit in repo.get_commits()[:max_commits]:
            c = commit.commit
            commits.append({
                "message": c.message.strip(),
                "author": c.author.name if c.author else "unknown",
                "date": str(c.author.date) if c.author else "",
                "additions": commit.stats.additions if commit.stats else 0,
                "deletions": commit.stats.deletions if commit.stats else 0,
            })
    except GithubException:
        commits = []

    # --- FILE TREE ---
    file_tree = []
    try:
        contents = repo.get_git_tree(repo.default_branch, recursive=True)
        file_tree = [item.path for item in contents.tree if item.type == "blob"][:500]
    except GithubException:
        file_tree = []

    # --- CONTRIBUTORS ---
    contributors = []
    try:
        for c in repo.get_contributors()[:20]:
            contributors.append(c.login)
    except GithubException:
        contributors = []

    # --- LANGUAGES ---
    languages = {}
    try:
        languages = repo.get_languages()
    except GithubException:
        languages = {}

    # --- TOPICS ---
    topics = []
    try:
        topics = repo.get_topics()
    except GithubException:
        topics = []

    return RepoData(
        repo_name=repo.full_name,
        description=repo.description or "",
        readme=readme,
        commits=commits,
        file_tree=file_tree,
        contributors=contributors,
        languages=languages,
        stars=repo.stargazers_count,
        forks=repo.forks_count,
        open_issues=repo.open_issues_count,
        has_wiki=repo.has_wiki,
        topics=topics,
        total_commits_fetched=len(commits),
    )
