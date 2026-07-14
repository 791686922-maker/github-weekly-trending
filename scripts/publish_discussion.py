#!/usr/bin/env python3
"""将已生成的周热榜发布为 GitHub Discussion。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def graphql(query: str, fields: dict[str, str]) -> dict:
    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in fields.items():
        command.extend(["-f", f"{key}={value}"])
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="发布 GitHub 周热榜 Discussion")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="只检查目标分类，不创建 Discussion")
    args = parser.parse_args()

    repository = os.environ.get("GH_REPO", "")
    category_name = os.environ.get("DISCUSSION_CATEGORY", "Announcements")
    if "/" not in repository:
        raise SystemExit("请设置 GH_REPO，例如 owner/repository")
    owner, name = repository.split("/", 1)
    body = args.report.read_text(encoding="utf-8")
    title = body.splitlines()[0].removeprefix("# ").strip()

    category_query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 100) { nodes { id name } }
        discussions(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes { title url }
        }
      }
    }
    """
    category_data = graphql(category_query, {"owner": owner, "name": name})["data"]["repository"]
    categories = category_data["discussionCategories"]["nodes"]
    category = next((item for item in categories if item["name"] == category_name), None)
    if category is None:
        available = ", ".join(item["name"] for item in categories) or "无"
        raise SystemExit(f"找不到 Discussion 分类“{category_name}”。可用分类：{available}")
    if args.dry_run:
        print(f"检查通过：将发布到 {repository} 的 Discussion 分类“{category_name}”。")
        return

    existing = next((item for item in category_data["discussions"]["nodes"] if item["title"] == title), None)
    if existing:
        print(f"已存在同标题周榜，跳过重复发布：{existing['url']}")
        return

    create_mutation = """
    mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {
        repositoryId: $repositoryId,
        categoryId: $categoryId,
        title: $title,
        body: $body
      }) { discussion { url } }
    }
    """
    result = graphql(
        create_mutation,
        {
            "repositoryId": category_data["id"],
            "categoryId": category["id"],
            "title": title,
            "body": body,
        },
    )
    print(f"已发布：{result['data']['createDiscussion']['discussion']['url']}")


if __name__ == "__main__":
    main()
