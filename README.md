# GitHub 周热榜自动化

每周一北京时间 10:30 从 GitHub Trending 的近一周榜单中筛选 AI、开发工具与少量有趣项目，生成中文 Markdown，并自动发布到本仓库的 GitHub Discussions。

同一日期标题的周榜只会发布一次，因此可安全地重新运行工作流排查失败。

## 排名规则

- 主榜：优先保留 AI、Agent、MCP、编码、CLI、自动化等项目，按近一周新增 Star 排名。
- 爆发观察：主榜中“近一周新增 Star / 当前总 Star”比例最高的三个项目。
- 趣味补充：从其余趋势项目中挑选视频、设计、会议、隐私、Wi-Fi 等题材项目。

数据来自 GitHub Trending；因此“近一周”是趋势页的滚动统计窗口，不是自然周精确结算。

## 手动运行

GitHub 仓库页面打开 **Actions**，选择“发布 GitHub 周热榜”，点击 **Run workflow**。

本地仅生成草稿：

```powershell
python scripts/generate_weekly.py --output report.md
```

本地发布前需设置仓库和 GitHub 凭据：

```powershell
$env:GH_REPO = "owner/repository"
$env:GH_TOKEN = gh auth token
python scripts/publish_discussion.py --report report.md
```

仅检查目标 Discussion 分类而不发布：

```powershell
python scripts/publish_discussion.py --report report.md --dry-run
```

## 配置

工作流默认发布到 `Announcements` Discussion 分类。若仓库分类名称不同，修改 [.github/workflows/weekly-trending.yml](.github/workflows/weekly-trending.yml) 中的 `DISCUSSION_CATEGORY`。
