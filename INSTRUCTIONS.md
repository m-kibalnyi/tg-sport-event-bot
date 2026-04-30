# ⚽ Sport Event Bot - Setup & Deployment Guide

This guide will help you set up and deploy your Sport Event Bot using PostgreSQL (Neon.tech).

## 1. Local Setup

### Prerequisites
- Python 3.11+
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Neon.tech Database credentials (provided in `.env.example`)

### Installation
1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <your-repo-url>
    cd tg-sport-event-bot
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    ```bash
    cp .env.example .env
    # Edit .env and add your TELEGRAM_BOT_TOKEN
    ```

5.  **Initialize Database**:
    The bot will automatically create the necessary tables on the first run.

6.  **Run the Bot**:
    ```bash
    python3 -m sport_event_bot.bot
    ```

---

## 2. Production Deployment

### Option A: Render (Easiest, Free Tier)
Render is the easiest way to get started.

1.  **Create a new "Web Service"** on Render.
2.  **Connect your GitHub repository**.
3.  **Configure Service**:
    - **Language**: `Python`
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `python3 -m sport_event_bot.bot`
4.  **Add Environment Variables**:
    Go to the "Env Vars" tab and add all the variables from your `.env` file.
    - `TELEGRAM_BOT_TOKEN`
    - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_SSLMODE`
    - `PORT` (Optional, Render sets this automatically to 10000)
5.  **Note on Health Checks**: The bot now includes a built-in health-check server that listens on the Render-provided `PORT`. This prevents Render's Free Tier from repeatedly restarting the service.


### Option B: OCI / AWS Always Free (Recommended for Performance)
This is slightly more advanced but provides a 24/7 "always-on" bot.

1.  **Provision a VM**: Create an Ubuntu/Oracle Linux instance on OCI or AWS.
2.  **Connect via SSH**.
3.  **Install Python & Git**:
    ```bash
    sudo apt update
    sudo apt install python3-pip python3-venv git -y
    ```
4.  **Clone & Setup**: Follow the "Local Setup" steps above inside the VM.
5.  **Set up systemd** (To run the bot in the background):
    Create a service file:
    ```bash
    sudo nano /etc/systemd/system/sport-bot.service
    ```
    Paste the following (adjust paths):
    ```ini
    [Unit]
    Description=Sport Event Bot
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/home/ubuntu/tg-sport-event-bot
    ExecStart=/home/ubuntu/tg-sport-event-bot/venv/bin/python3 -m sport_event_bot.bot
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
    Enable and start:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable sport-bot
    sudo systemctl start sport-bot
    ```

---

## 3. Command Reference

### Admin Commands (Group Admins only)
- **/event [name]** - Start a guided conversation to create a new event.
- **/event {json}** - **One-shot event creation**: Creates an event immediately using provided details.
- **/event_remove** - Permanently close and remove the current event.
- **/event_update [text]** - Change the description of the active event.
- **/event_datetime [datetime]** - Update the date and time of the active event.
- **/limit [number]** - Change the player limit.
- **/blik [phone]** - Set/Update the BLIK phone number for payments.
- **/penalty [user]** - Give a "Yellow Card" (penalty) to a user. Supports replies, @usernames, or names.
- **/penalty_remove [user]** - Remove a penalty from a user.
- **/payments** - Generate a Telegraph link with the current payment log.
- **/stat** - View group-wide player participation statistics.
- **/fix** - Refreshes the event message UI (useful if buttons get stuck or message is deleted).
- **/set_lists_topic** - Configure the current forum thread/topic as the primary place for event lists.
- **/set_logs_topic** - Configure the current forum thread/topic for administrative logs.

### Player Commands
- **/info** - Display the current event message with details and participation buttons.
- **/add** - Join the current event.
- **/remove** - Leave the current event.
- **/add_leg** - Add a guest player (legioneer).
- **/rem_leg** - Remove one of your guest players.
- **/pay** - Toggle payment confirmation status.
- **/lang** - Open the language selection menu.
- **/help** - Show the list of available commands.

---

## 4. Advanced Event Creation
You can bypass the step-by-step conversation by providing a JSON-like structure. If the JSON contains at least a `name`, the event will be created **instantly**.

**Example:**
```text
/event {name: "Futsal Night", limit: 16, datetime: "Friday 20:00", location: "Stadium X", free: false, blik: "123456789"}
```

**Supported Keys:**
- `name`: (String) Name of the event.
- `limit`: (Number) Player capacity (default: 14).
- `datetime`: (String) Time/Date (e.g., "tomorrow 18:00"). Supports natural language.
- `location`: (String) Custom location name or map link.
- `free`: (Boolean) `true` for free, `false` for paid.
- `blik`: (String) BLIK phone number for payments.

## 5. Troubleshooting
- **Database Connection**: Ensure `DB_SSLMODE=require` is set for Neon DB.
- **Bot Not Responding**: Check logs with `journalctl -u sport-bot -f` (on Linux) or the Render logs.
