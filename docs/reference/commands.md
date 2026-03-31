# Command Reference

Quick-reference table of every slash command.

## Verbal Warnings

| Command | Options | Description |
|---------|---------|-------------|
| `/verbal add` | `user`, `reason`, `evidence_link`, `[mod]` | Add a new verbal warning |
| `/verbal list` | — | Paginated list of all warnings |
| `/verbal search` | `user` | Filter warnings by user |
| `/verbal delete` | `id` | Permanently delete a warning |
| `/verbal edit` | `id` | Edit a warning via modal |
| `/verbal lb` | `type` (offender / mod) | Warning count leaderboard |

## Auttaja

| Command | Options | Description |
|---------|---------|-------------|
| `/auttaja offender` | `user`, `[show_removed]` | Punishments received by a user |
| `/auttaja punisher` | `user`, `[show_removed]` | Punishments issued by a staff member |
| `/auttaja lb` | `type` (offender / punisher) | Punishment leaderboard |
| `/auttaja edit` | `id` | Edit a punishment record via modal |

## Polls

| Command | Options | Description |
|---------|---------|-------------|
| `/poll create` | `[channel]`, `[anonymous]`, `[max_votes]` | Create a poll via modal |
| `/poll edit` | `id` | Edit poll content |
| `/poll delete` | `id` | Close and disable a poll |
| `/poll list` | `[filter]`, `[channel]`, `[user]` | List polls |
| `/poll view` | `id` | View live poll results |

## Poll Templates

| Command | Options | Description |
|---------|---------|-------------|
| `/poll_template create` | — | Create a template via modal |
| `/poll_template from_poll` | `id` | Convert a poll to a template |
| `/poll_template edit` | `id` | Edit a template |
| `/poll_template delete` | `id` | Soft-delete a template |
| `/poll_template list` | `[filter]` | List templates |
| `/poll_template preview` | `id` | Preview a template (ephemeral) |
| `/poll_template use` | `id`, `[channel]`, `[anonymous]`, `[max_votes]` | Post a poll from a template |

## Utility

| Command | Options | Description |
|---------|---------|-------------|
| `/ping` | — | Bot latency |
| `/about` | — | Bot info |
| `/help` | — | Interactive help menu |
| `/retrieveids channels` | `category` | Channel IDs in a category |
| `/retrieveids users` | `role` | User IDs with a role |
| `/retrieveids leaderboard` | `type` (offender / mod) | User IDs from warning leaderboard |
| `/retrieveids searchusers` | `text` | Search members by name |
