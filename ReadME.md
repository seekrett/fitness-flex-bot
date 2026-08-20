# Discord Bot Setup

## Prerequisites
- Python 3.x installed
- A Discord bot token inside of .env

## 1. Create a Virtual Environment
It's recommended to work inside a virtual environment to keep dependencies isolated.

```bash
python -m venv nameOfEnv
```

## 2. Activate the Virtual Environment

**macOS / Linux:**
```bash
source nameOfEnv/bin/activate
```

**Windows:**
```bash
nameOfEnv\Scripts\activate
```

To deactivate at any time:
```bash
deactivate
```

## 3. Install Dependencies
Run this once after cloning the repo (or whenever `requirements.txt` changes):

```bash
pip install -r requirements.txt
```

## 4. Set Up Environment Variables
Create a file named **`.env`** (make sure it starts with a dot) in the project root:

```env
DISCORD_TOKEN=your_token_here
```

> ⚠️ Double-check the filename is exactly `.env`, not `env` — the app won't detect it otherwise.

## 5. Run the Bot
```bash
python bot.py
```

Test on Discord once started succesfully