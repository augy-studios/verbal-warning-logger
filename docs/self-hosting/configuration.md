# Configuration

All configuration is done through a `.env` file in the root of the repository. Copy `.env.example` to get started:

```bash
cp .env.example .env
```

---

## Required variables

These must be set or the bot will refuse to start.

### DISCORD_TOKEN

Your Discord bot token from the Developer Portal.

```env
DISCORD_TOKEN=your_bot_token_here
```

### LOG_CHANNEL_ID

The ID of the channel where all warning add / edit / delete actions are logged.

```env
LOG_CHANNEL_ID=123456789012345678
```

### STAFF_ROLE_ID

The minimum role required to use `/verbal` commands. Members with this role or any role higher in the server hierarchy are granted access.

```env
STAFF_ROLE_ID=123456789012345678
```

---

## Optional variables

### EMBED_COLOR

The accent color used in all bot embeds. Accepts hex format with or without the `0x` prefix.

```env
EMBED_COLOR=0x007FFF
# or
EMBED_COLOR=007FFF
```

Defaults to `0x007FFF` (a blue) if not set.

---

## Auttaja / Supabase

These variables are only required if you want to use the `/auttaja` commands. The bot loads without them, but the entire Auttaja cog will be unavailable.

### SUPABASE_URL

The URL of your Supabase project.

```env
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
```

### SUPABASE_KEY

A Supabase **service role** key (not the anon key). The service role key bypasses row-level security and is needed to read and write punishment records.

```env
SUPABASE_KEY=your_supabase_service_role_key_here
```

> Store this key carefully. It has full access to your Supabase project.

---

## Complete .env example

```env
# Required
DISCORD_TOKEN=your_bot_token_here
LOG_CHANNEL_ID=123456789012345678
STAFF_ROLE_ID=987654321098765432

# Optional
EMBED_COLOR=0x007FFF

# Optional — Auttaja integration
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=your_supabase_service_role_key_here
```
