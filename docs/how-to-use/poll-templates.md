# Poll Templates

Poll templates let you save a poll structure (title, description, and options) and reuse it without re-entering all the details each time. Useful for recurring evaluations that always use the same format.

---

## /poll_template create

Create a new template via a modal form.

Fill in:

- **Name** — internal name to identify the template
- **Title** — the poll title that will be used when posting
- **Description** — context shown under the title
- **Options** — one option per line

---

## /poll_template from_poll

Convert an existing poll into a reusable template.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Poll ID to convert |

Copies the poll's title, description, and options into a new template.

---

## /poll_template edit

Edit an existing template.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Template ID |

---

## /poll_template delete

Soft-delete a template (hides it from listings without destroying data).

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Template ID |

---

## /poll_template list

List available templates.

| Option | Required | Description |
|--------|----------|-------------|
| `filter` | No | `active` (default) or `all` (includes deleted) |

---

## /poll_template preview

Preview what a template's poll will look like without actually posting it.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Template ID |

The response is ephemeral (only visible to you).

---

## /poll_template use

Create and post a poll from a template.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Template ID |
| `channel` | No | Channel to post in (defaults to current) |
| `anonymous` | No | Hide voter identities (default: false) |
| `max_votes` | No | Max options per voter (0 = unlimited) |
