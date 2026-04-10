# RustChain Autonomous Bounty Hunter Agent

An AI agent that autonomously discovers, evaluates, and claims RustChain bounties on GitHub.

**This agent is itself a bounty submission** — it was built autonomously and has already submitted multiple PRs to RustChain bounties.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scanner    │────▶│  Evaluator   │────▶│   Developer  │
│  (GitHub)    │     │  (AI Score)  │     │  (AI Agent)  │
└─────────────┘     └──────────────┘     └──────────────┘
                           │                      │
                    ┌──────▼──────┐        ┌──────▼──────┐
                    │   Tracker   │        │  Submitter  │
                    │  (SQLite)   │        │  (gh CLI)   │
                    └─────────────┘        └─────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys and wallet

# Run a scan (dry-run)
python main.py --scan --dry-run

# Run full pipeline
python main.py --auto

# Run single task
python main.py --issue 2869 --repo Scottcjn/rustchain-bounties
```

## Components

| File | Description |
|------|-------------|
| `main.py` | Entry point — scan, evaluate, develop, submit |
| `scanner.py` | GitHub issue scanner using `gh` CLI |
| `evaluator.py` | AI-powered bounty evaluation (score 0-100) |
| `developer.py` | Autonomous code generation and testing |
| `submitter.py` | PR creation with quality checks |
| `tracker.py` | SQLite-based earnings tracker |
| `config.py` | Configuration management |

## Evaluation Scoring

| Factor | Weight | Description |
|--------|--------|-------------|
| Amount | 40% | Higher bounty = higher priority |
| Complexity | 30% | Can the agent complete it? |
| Competition | 20% | Fewer existing PRs = better |
| Time | 10% | Estimated completion time |

## Safety Features

- **Rate limiting**: Respects GitHub API limits (5000/hr)
- **Quality gates**: Code must pass lint + tests before PR
- **Dry-run mode**: Preview what the agent would do
- **Human override**: Can pause/resume via tracker DB
- **Clean commits**: Meaningful messages, no kitchen-sink dumps

## Earnings Tracking

```bash
# View earnings
python main.py --stats

# Output:
# Total bounties: 5
# Submitted PRs: 3
# Merged: 1 (25 RTC)
# Pending: 2 (35 RTC)
# Earnings: ~$6.00 USD
```

## LLM Support

| Provider | Model | Status |
|----------|-------|--------|
| Anthropic | Claude 3.5 Sonnet | ✅ Supported |
| OpenAI | GPT-4o | ✅ Supported |
| Local | llama.cpp | ✅ Supported |
| Zhipu | GLM-5 | ✅ Supported |
| LongCat | Flash-Lite | ✅ Supported |

## Tech Stack

- Python 3.11+
- `anthropic` SDK / `openai` SDK
- `PyGithub` or `gh` CLI
- SQLite for tracking
- pytest for testing

## License

MIT

## Wallet

zhaog100
