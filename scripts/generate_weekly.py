#!/usr/bin/env python3
"""从 GitHub Trending 生成一篇中文周热榜 Markdown。"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


TRENDING_URL = "https://github.com/trending?since=weekly"
USER_AGENT = "github-weekly-trending-bot/1.0 (+https://github.com)"
FOCUS_KEYWORDS = (
    "ai",
    "agent",
    "llm",
    "mcp",
    "claude",
    "codex",
    "gpt",
    "gemini",
    "model",
    "machine learning",
    "developer",
    "coding",
    "code",
    "terminal",
    "api",
    "cli",
    "sandbox",
    "automation",
)
INTERESTING_KEYWORDS = ("video", "design", "wifi", "meeting", "privacy", "diagram")
EXCLUDED_KEYWORDS = ("leak", "jailbreak", "penetration", "pentest", "exploit", "malware")


@dataclass(frozen=True)
class Project:
    repo: str
    description: str
    total_stars: int
    weekly_stars: int

    @property
    def weekly_share(self) -> float:
        return self.weekly_stars / self.total_stars if self.total_stars else 0.0

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}"


def get_trending_html() -> str:
    request = urllib.request.Request(TRENDING_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def plain_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def parse_number(value: str) -> int:
    return int(value.replace(",", ""))


def parse_projects(page: str) -> list[Project]:
    projects: list[Project] = []
    articles = re.findall(r"(?s)<article\b.*?</article>", page)
    for article in articles:
        repo_match = re.search(r'(?s)<h2\b.*?<a[^>]+href="/([^"?#]+)"', article)
        description_match = re.search(r"(?s)<p\b[^>]*>(.*?)</p>", article)
        weekly_match = re.search(r"([\d,]+)\s+stars\s+this\s+week", article)
        total_match = re.search(r"(?s)octicon-star.*?</svg>\s*([\d,]+)", article)
        if not (repo_match and weekly_match and total_match):
            continue

        description = plain_text(description_match.group(1)) if description_match else "暂无项目简介。"
        project = Project(
            repo=html.unescape(repo_match.group(1)).strip(),
            description=description,
            total_stars=parse_number(total_match.group(1)),
            weekly_stars=parse_number(weekly_match.group(1)),
        )
        if project.repo not in {item.repo for item in projects}:
            projects.append(project)

    if len(projects) < 5:
        raise RuntimeError("未能从 GitHub Trending 解析出足够项目，页面结构可能已变化。")
    return projects


def is_focus(project: Project) -> bool:
    text = f"{project.repo} {project.description}".lower()
    return not any(keyword in text for keyword in EXCLUDED_KEYWORDS) and any(keyword in text for keyword in FOCUS_KEYWORDS)


def is_interesting(project: Project) -> bool:
    text = f"{project.repo} {project.description}".lower()
    return not any(keyword in text for keyword in EXCLUDED_KEYWORDS) and any(keyword in text for keyword in INTERESTING_KEYWORDS)


def markdown_safe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def build_report(projects: list[Project], limit: int) -> str:
    eligible = [project for project in projects if not any(keyword in f"{project.repo} {project.description}".lower() for keyword in EXCLUDED_KEYWORDS)]
    focus = sorted((project for project in eligible if is_focus(project)), key=lambda item: item.weekly_stars, reverse=True)
    primary = focus[:limit]
    if len(primary) < limit:
        existing = {project.repo for project in primary}
        primary.extend(project for project in sorted(eligible, key=lambda item: item.weekly_stars, reverse=True) if project.repo not in existing)
        primary = primary[:limit]

    breakout = sorted(primary, key=lambda item: item.weekly_share, reverse=True)[:3]
    existing = {project.repo for project in primary}
    supplemental = [project for project in eligible if project.repo not in existing and is_interesting(project)]
    supplemental = sorted(supplemental, key=lambda item: item.weekly_stars, reverse=True)[:2]

    now = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# GitHub 周热榜｜{now:%Y-%m-%d}",
        "",
        "本期聚焦 AI 与开发工具，另附少量有趣项目。数据来自 GitHub Trending 近一周榜单，Star 数为生成时快照。",
        "",
        f"> 生成时间：北京时间 {timestamp} ｜ 数据源：[GitHub Trending]({TRENDING_URL})",
        "",
        "## 热度 Top 项目",
        "",
        "| 项目 | 总 Star | 近一周新增 | 项目简介 |",
        "|---|---:|---:|---|",
    ]
    for project in primary:
        lines.append(
            f"| [{project.repo}]({project.url}) | {project.total_stars:,} | +{project.weekly_stars:,} | {markdown_safe(project.description)} |"
        )

    lines.extend(["", "## 爆发观察", ""])
    for project in breakout:
        lines.append(
            f"- [{project.repo}]({project.url})：近一周新增 Star 约占当前总 Star 的 **{project.weekly_share:.0%}**，短期关注度非常高。"
        )

    if supplemental:
        lines.extend(["", "## 趣味补充", ""])
        for project in supplemental:
            lines.append(
                f"- [{project.repo}]({project.url})（+{project.weekly_stars:,} Star）：{markdown_safe(project.description)}"
            )

    lines.extend(
        [
            "",
            "## 本周观察",
            "",
            "AI 的热度正在从单一模型能力，转向可直接接入终端、文件、办公软件与浏览器的执行型工具。",
            "",
            "---",
            "自动生成；项目数据以 GitHub 页面实时展示为准。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 GitHub 周热榜 Markdown")
    parser.add_argument("--output", type=Path, required=True, help="生成的 Markdown 文件路径")
    parser.add_argument("--limit", type=int, default=8, help="主榜项目数，默认 8")
    args = parser.parse_args()

    if args.limit < 3:
        raise SystemExit("--limit 至少为 3")

    report = build_report(parse_projects(get_trending_html()), args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"已生成周热榜：{args.output}")


if __name__ == "__main__":
    main()
