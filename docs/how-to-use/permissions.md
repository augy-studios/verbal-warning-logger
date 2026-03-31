# Permissions

Verbal Warning Logger uses Discord's role hierarchy to determine who can run commands, rather than hardcoded per-user permission grants.

---

## Who can use /verbal commands?

Access is granted if **any** of the following is true:

1. The member has the **Administrator** permission on the server.
2. The member has the role configured as `STAFF_ROLE_ID`.
3. The member has any role that is **positioned higher** than the staff role in the server's role list.

This means you don't need to grant every individual moderator the exact staff role — anyone with a higher role (e.g. Senior Moderator, Head Admin) is automatically included.

### Example role ladder

```
Owner           ← can use /verbal ✓ (above staff role)
Head Admin      ← can use /verbal ✓ (above staff role)
Moderator       ← STAFF_ROLE_ID — can use /verbal ✓
Trial Mod       ← cannot use /verbal ✗ (below staff role)
Member          ← cannot use /verbal ✗
```

---

## /retrieveids permissions

These commands check for specific Discord permissions rather than the staff role:

| Command | Required permission |
|---------|-------------------|
| `/retrieveids channels` | Manage Channels |
| `/retrieveids users` | Manage Roles |
| `/retrieveids leaderboard` | Staff role or above |
| `/retrieveids searchusers` | Staff role or above |

---

## Changing the staff role

The staff role is set via the `STAFF_ROLE_ID` environment variable. See [Configuration](../self-hosting/configuration.md) for details. Changing this value requires restarting the bot.
