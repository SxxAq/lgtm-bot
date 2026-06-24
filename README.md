# LGTM Bot 🤖

A production-ready Telegram bot for the Eventyay contributor community to centralize and streamline PR reviews.

## What it does

- **Review queue** — track which PRs need reviews in one place
- **Reviewer assignment** — claim PRs to review, prevent overlap or neglect
- **Auto-pick** — bot assigns you the most-needy PR automatically
- **Priority reviews** — flag urgent PRs and notify the group
- **Review board** — visual snapshot of all PRs grouped by status
- **Statistics & leaderboard** — see who's reviewing the most
- **Daily digest** — automatic 8 PM summary posted to the group
- **Auto-sync** — PR statuses stay up-to-date with GitHub every 30 minutes

---

## Quickstart (5 minutes)

### 1. Create your bot

1. Open Telegram → search **@BotFather** → `/newbot`
2. Follow the prompts → copy your `BOT_TOKEN`

### 2. Get your Group Chat ID

1. Add your bot to the Telegram group
2. Send any message in the group
3. Open: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find `"chat": {"id": -1001234567890}` — that's your `GROUP_CHAT_ID`

### 3. Clone and configure

```bash
git clone https://github.com/your-org/lgtm-bot.git
cd lgtm-bot
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=your_bot_token_from_botfather
GROUP_CHAT_ID=-1001234567890
GITHUB_TOKEN=your_github_pat          # Optional but recommended
ADMIN_USERNAMES=saalim,rachit          # Your Telegram usernames
```

### 4. Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # Create database tables
python -m app.main          # Start the bot (polling mode)
```

That's it. The bot is live. Open your group and try `/pr help`.

---

## Commands

### PR Management

| Command | Description |
|---------|-------------|
| `/pr add <number>` | Add a PR to the review queue |
| `/pr take <number>` | Claim a PR for review |
| `/pr done <number>` | Mark your review as complete |
| `/pr priority <number>` | Flag as priority — notifies the group |
| `/pr board` | Show the full review board |
| `/pr pick` | Auto-assign the best PR to you |
| `/pr pending` | List all waiting/in-review PRs |
| `/pr mine` | Show your active reviews |

### Statistics

| Command | Description |
|---------|-------------|
| `/pr stats` | Reviewer activity summary |
| `/pr leaderboard` | Top reviewers ranked |
| `/pr streak` | Review streaks 🔥 |
| `/pr aging` | Show PR age report |

### Admin Only

| Command | Description |
|---------|-------------|
| `/pr sync` | Sync all PR statuses with GitHub |
| `/pr force-close <number>` | Force-close a PR |
| `/pr remove <number>` | Remove PR from queue entirely |
| `/pr status <number> <STATUS>` | Manually set PR status |

Valid statuses: `WAITING_REVIEW`, `IN_REVIEW`, `READY_TO_MERGE`, `CHANGES_REQUESTED`, `MERGED`, `CLOSED`

---

## Status Logic

| Status | Condition |
|--------|-----------|
| `WAITING_REVIEW` | No active reviewers |
| `IN_REVIEW` | At least 1 active reviewer |
| `READY_TO_MERGE` | 2+ reviewers completed |
| `CHANGES_REQUESTED` | Set manually by admin |
| `MERGED` | Detected via GitHub sync |
| `CLOSED` | Detected via GitHub sync |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Telegram bot token from @BotFather |
| `GROUP_CHAT_ID` | ✅ | — | Target group chat ID (negative number) |
| `GITHUB_TOKEN` | ⬜ | — | GitHub PAT (raises rate limit to 5000/hr) |
| `GITHUB_REPO` | ⬜ | `fossasia/eventyay-talk` | Repository to track |
| `DATABASE_URL` | ⬜ | `sqlite+aiosqlite:///./lgtm.db` | SQLite path |
| `ADMIN_USERNAMES` | ⬜ | — | Comma-separated admin usernames |
| `DIGEST_HOUR` | ⬜ | `14` | Daily digest hour (UTC) |
| `DIGEST_MINUTE` | ⬜ | `30` | Daily digest minute (UTC) |
| `WEBHOOK_URL` | ⬜ | — | Public HTTPS URL for webhook mode |

---

## Running Tests

```bash
pytest --cov=app --cov-report=term-missing
```

Expected coverage: **≥ 80%**

---

## Deployment

### Option 1: Local / VPS (simplest)

```bash
# Install as a systemd service for 24/7 uptime
sudo nano /etc/systemd/system/lgtm-bot.service
```

```ini
[Unit]
Description=LGTM Bot
After=network.target

[Service]
User=youruser
WorkingDirectory=/home/youruser/lgtm-bot
Environment=PATH=/home/youruser/lgtm-bot/.venv/bin
ExecStart=/home/youruser/lgtm-bot/.venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now lgtm-bot
```

### Option 2: Docker

```bash
docker-compose up -d --build
```

### Option 3: Railway (free tier)

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variables in the Railway dashboard
4. Deploy

### Option 4: Fly.io (free tier)

```bash
fly auth login
fly launch --no-deploy
# Set secrets:
fly secrets set BOT_TOKEN=xxx GROUP_CHAT_ID=-xxx GITHUB_TOKEN=xxx
fly deploy
```

---

## Project Structure

```
lgtm-bot/
├── app/
│   ├── main.py              # Entry point (polling or webhook)
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Async SQLAlchemy setup
│   ├── models/              # ORM models: PR, ReviewerAssignment, User
│   ├── services/            # Business logic (pr_service, user_service)
│   ├── github/              # GitHub API client + parser
│   ├── telegram/            # Bot factory, formatters, keyboards
│   ├── commands/            # PTB command handlers + inline buttons
│   ├── scheduler/           # APScheduler jobs (sync, digest)
│   └── utils/               # Exceptions, decorators
├── migrations/              # Alembic migrations
├── tests/                   # pytest test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Architecture

```
Telegram Update
      ↓
CommandHandler (/pr)
      ↓
pr_commands.py (dispatcher)
      ↓
pr_service.py (business logic)
      ↓         ↓
  database    github_client
  (SQLite)  (GitHub REST API)
```

- **Polling mode** by default — works locally with no server
- **Webhook mode** — set `WEBHOOK_URL` for production
- **Async throughout** — `aiosqlite` + `httpx.AsyncClient`
- **APScheduler** — sync every 30 min, daily digest at configured time
