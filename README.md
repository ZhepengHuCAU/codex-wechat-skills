# Codex 微信公众号技能集

本仓库保存三个可复用的 Codex 技能：

- `create-wechat-data-cards`：将可信数据制作成适合微信公众号阅读的中文数据卡片。
- `create-wechat-publish-package`：将中文文章和配图整理成可审计的微信公众号发布包。
- `fetch-cftc-data`：下载CFTC管理基金持仓，保存原始数据、CSV与来源，核验历史同期排名和样本覆盖年份。

每个技能目录均包含必需的 `SKILL.md`，以及运行所需的脚本、参考资料、界面元数据和图片资产。技能结构遵循 [OpenAI 官方 Build skills 文档](https://learn.chatgpt.com/docs/build-skills)。

## 在另一台 Windows 电脑上安装

先克隆本仓库，然后将三个技能复制到用户级技能目录：

```powershell
git clone https://github.com/ZhepengHuCAU/codex-wechat-skills.git
$skillsRoot = Join-Path $env:USERPROFILE ".agents\skills"
New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null
Copy-Item -Recurse -Force ".\codex-wechat-skills\create-wechat-data-cards" $skillsRoot
Copy-Item -Recurse -Force ".\codex-wechat-skills\create-wechat-publish-package" $skillsRoot
Copy-Item -Recurse -Force ".\codex-wechat-skills\fetch-cftc-data" $skillsRoot
py -m pip install Pillow python-docx
```

## 在 macOS 或 Linux 上安装

```bash
git clone https://github.com/ZhepengHuCAU/codex-wechat-skills.git
mkdir -p "$HOME/.agents/skills"
cp -R ./codex-wechat-skills/create-wechat-data-cards "$HOME/.agents/skills/"
cp -R ./codex-wechat-skills/create-wechat-publish-package "$HOME/.agents/skills/"
cp -R ./codex-wechat-skills/fetch-cftc-data "$HOME/.agents/skills/"
python3 -m pip install Pillow python-docx
```

也可以在 Codex 中调用 `$skill-installer`，让它从本仓库安装这三个技能。由于本仓库是私有仓库，目标电脑需要先登录有权访问该仓库的 GitHub 账号。

Codex 通常会自动检测技能变化；如果技能没有立即出现，请重启 Codex。

## 更新

在仓库目录运行 `git pull`，然后再次执行上面的复制命令即可覆盖本地旧版本。

## 依赖

`fetch-cftc-data` 仅使用 Python 标准库，不需要 API 密钥；下面的 Pillow、python-docx 和字体用于图卡及发布包技能。

- Python 3.10 或更高版本
- Pillow
- python-docx
- 数据卡片需要 Microsoft YaHei 或 Noto Sans CJK 等中文字体

## 调用示例

```text
$fetch-cftc-data 下载大豆和玉米管理基金仅期货历史持仓，并核验最新一期的历史同期排名。
$create-wechat-data-cards 根据这份数据制作公众号图卡。
$create-wechat-publish-package 把这篇文章整理成完整公众号发布包。
```

