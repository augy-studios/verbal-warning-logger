# Discord Bot Setup

You need a Discord application and bot token before you can run the bot.

---

## 1. Create an application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**.
3. Give it a name (e.g. "Verbal Warning Logger") and click **Create**.

---

## 2. Create a bot user

1. In the left sidebar, click **Bot**.
2. Click **Add Bot** → **Yes, do it!**
3. Under the bot's username, click **Reset Token**, then copy the token.

> Keep this token secret. Anyone with it can control your bot. Store it in your `.env` file and never commit it to version control.

---

## 3. Configure intents

On the same **Bot** page, scroll down to **Privileged Gateway Intents** and enable:

- **Server Members Intent** — required for role hierarchy permission checks

The **Message Content Intent** is not required for core functionality.

---

## 4. Invite the bot to your server

1. In the left sidebar, click **OAuth2 → URL Generator**.
2. Under **Scopes**, select:
   - `bot`
   - `applications.commands`
3. Under **Bot Permissions**, select:
   - `Send Messages`
   - `Embed Links`
   - `Read Message History`
   - `View Channels`
4. Copy the generated URL, open it in your browser, and select the server to add the bot to.

---

## 5. Gather your server IDs

You will need a few IDs from your Discord server for the `.env` configuration:

| Value | How to get it |
|-------|--------------|
| **Log channel ID** | Right-click the channel → Copy Channel ID (Developer Mode must be on) |
| **Staff role ID** | Server Settings → Roles → right-click the role → Copy Role ID |

To enable Developer Mode: User Settings → Advanced → Developer Mode.
