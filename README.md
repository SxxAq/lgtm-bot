<div align="center">

# LGTM Bot 🤖

**A production-ready Telegram ChatOps bot for open-source communities and dev teams to streamline PR code reviews.**

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Database](https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-blueviolet.svg)](https://www.sqlalchemy.org/)

[Features](#-key-features) • [Quickstart](#-quickstart-5-minutes) • [Commands](#-bot-commands) • [Deployment](#-deployment-guides) • [Architecture](#-architecture)

</div>

---

## ⚡ Why LGTM Bot?

In open-source communities and engineering teams, code reviews frequently get delayed because nobody knows who is reviewing what, PRs get neglected, and priority reviews are hard to track.

**LGTM Bot** solves this directly inside Telegram through **ChatOps & Gamification**:
- 📌 **Centralized Review Board**: Visual snapshot of all open PRs categorized by review status with interactive buttons.
- 🔗 **Direct GitHub Anchors**: Clickable PR tags in Telegram that link straight to GitHub for instant code review.
- 🎯 **Smart Auto-Pick (`/pr pick`)**: Automatically assigns reviewers to the oldest, most-neglected PRs.
- 🌐 **Multi-Repository Triage**: Track PRs across any organization repository (`eventyay`, `eventyay-socialmedia`, `eventyay-hubspot`, `eventyay-teamshifts`, etc.).
- 🔥 **Gamified Review Streaks & Leaderboards**: Track completed reviews and reward active reviewers with streaks and medals.
- 📊 **Automated Daily Digests & GitHub Sync**: Keeps status strictly in sync with GitHub every 30 minutes and posts an 8 PM daily summary report to the group.

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| 📋 **Review Queue** | Track pending reviews in one central, organized board |
| 🔍 **Multi-Reviewer Claims** | Prevent duplicate reviews or assignment overlap |
| 🎯 **Auto-Pick System** | Intelligently routes unreviewed PRs based on age & workload |
| 🚨 **Priority Escalation** | Flag urgent PRs and alert team members instantly |
| 🏆 **Streaks & Leaderboard** | Reward active community reviewers with streaks 🔥 and medals 🥇 |
| 🔄 **Automatic GitHub Sync** | Auto-detects merged/closed PRs every 30 minutes |
| 🗄️ **Dual Database Support** | Zero-config SQLite locally, or PostgreSQL/asyncpg for cloud production |

---

## 📋 Bot Commands

### Public Commands (Available to Everyone)

| Command | Description |
|---------|-------------|
| `/pr add [<repo>] <number>` | Add a PR to the queue *(e.g., `/pr add 3975` or `/pr add eventyay-socialmedia 12`)* |
| `/pr take <number>` | Claim a PR for review |
| `/pr done <number>` | Mark your review as completed |
| `/pr remove <number>` | Remove a PR from the queue after merge or cleanup |
| `/pr status <number> <STATUS>` | Manually set PR status (`WAITING_REVIEW`, `IN_REVIEW`, `READY_TO_MERGE`, `CHANGES_REQUESTED`, `MERGED`, `CLOSED`) |
| `/pr merged <number>` | Shortcut to mark a PR as merged |
| `/pr priority <number>` | Flag PR for urgent review and alert the group |
| `/pr board` | Display the interactive visual review board |
| `/pr pick` | Auto-assign an unreviewed PR to yourself |
| `/pr pending` | List all PRs waiting for review |
| `/pr mine` | Show your active reviews |
| `/pr stats` | Display reviewer activity summary |
| `/pr leaderboard` | Ranked list of top reviewers |
| `/pr streak` | Reviewer streaks 🔥 |
| `/pr aging` | Show PR age report with staleness warnings ⚠️ |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/pr sync` | Force sync all PR statuses with GitHub REST API |
| `/pr force-close <number>` | Force-close a PR record in the queue |

---

## 🛠️ Quickstart (5 Minutes)

### 1. Create your Telegram Bot
1. Search **@BotFather** in Telegram and send `/newbot`.
2. Follow prompts and copy your `BOT_TOKEN`.

### 2. Get your Group Chat ID
1. Add your bot to your target Telegram group.
2. Send a message in the group starting with a slash (e.g., `/start`).
3. Open `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser.
4. Locate `"chat": {"id": -100XXXXXXXXXX}` — that negative number is your `GROUP_CHAT_ID`.

### 3. Clone & Run Locally
```bash
git clone https://github.com/SxxAq/lgtm-bot.git
cd lgtm-bot

# Configure environment
cp .env.example .env
nano .env  # Add your BOT_TOKEN and GROUP_CHAT_ID

# Set up virtual environment & run
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.main
```
Your bot is live! Open Telegram and send `/pr help` or `/pr board`.

---

## ☁️ Deployment Guides

### Option 1: Railway (Recommended — $5 Free Monthly Credit)
1. Go to [railway.app](https://railway.app) and click **+ New Project** → **Deploy from GitHub repo**.
2. Select `SxxAq/lgtm-bot`.
3. In your Railway service dashboard, go to **Variables** and add:
   - `BOT_TOKEN` = `your_telegram_bot_token`
   - `GROUP_CHAT_ID` = `your_group_chat_id`
   - `ADMIN_USERNAMES` = `your_username`
   - `GITHUB_REPO` = `fossasia/eventyay`
4. Deploy! Railway automatically detects the `Dockerfile` and builds your service.

### Option 2: Koyeb (100% Free — No Credit Card Required)
1. Sign up at [koyeb.com](https://www.koyeb.com) using GitHub.
2. Click **Create Service** → **GitHub** → select `SxxAq/lgtm-bot`.
3. Add environment variables (`BOT_TOKEN`, `GROUP_CHAT_ID`, `ADMIN_USERNAMES`).
4. Click **Deploy**. Koyeb runs 24/7 without sleeping.

### Option 3: Docker Compose (Self-Hosted VPS)
```bash
docker-compose up -d --build
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Telegram bot token from @BotFather |
| `GROUP_CHAT_ID` | ✅ | `0` | Target Telegram group chat ID (negative integer) |
| `GITHUB_TOKEN` | ⬜ | `""` | GitHub Personal Access Token (raises rate limit to 5000 req/hr) |
| `GITHUB_REPO` | ⬜ | `fossasia/eventyay` | Primary default GitHub repository |
| `DATABASE_URL` | ⬜ | `sqlite+aiosqlite:///./lgtm.db` | Async database connection URL (supports SQLite & PostgreSQL) |
| `ADMIN_USERNAMES` | ⬜ | `""` | Comma-separated admin usernames (without `@`) |
| `DIGEST_HOUR` | ⬜ | `14` | Daily digest hour (UTC) |
| `DIGEST_MINUTE` | ⬜ | `30` | Daily digest minute (UTC) |

---

## 🧪 Testing

The repository features full test coverage for core business logic, status state machines, and message formatters using `pytest` and `pytest-asyncio`.

```bash
BOT_TOKEN=test_token GROUP_CHAT_ID=12345 pytest --cov=app --cov-report=term-missing
```

---

## 📐 Architecture & Tech Stack

```text
Telegram Update (Polling / Webhook)
            │
            ▼
   PTB Application Router (/pr)
            │
            ▼
   pr_service.py (Business Logic)
      │                     │
      ▼                     ▼
Async Database         GitHub REST API
(SQLite / PostgreSQL)   (httpx client)
```

- **Framework**: `python-telegram-bot` 21.6 (Async)
- **ORM & DB**: SQLAlchemy 2.0 (Async) + `aiosqlite` / `asyncpg` + Alembic
- **Validation**: Pydantic v2 & `pydantic-settings`
- **Scheduler**: APScheduler 3.10
- **HTTP Client**: `httpx`

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
