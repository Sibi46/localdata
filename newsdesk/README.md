> LOCALFROM now exposes only the nine main features described in the root README. Birthday-card routes and editors are retired; their model and stored cards remain as historical data.

# OURPINCODE News Desk (MVP)

News Desk is an additive Django app. It reuses `jobs.User`, `jobs.PinCode`, the
existing login/session/CSRF flow, base navigation and local Poppins styles.
It does not modify coupons, Network, wallets or existing user types.

## Screens and roles

- `/news/`: public pincode selection, category/kind filters and paginated news.
- `/news/stories/<id>/`: published story/event, ratings, comments and sharing.
- `/news/desk/`: assigned-pincode stories, ratings, comments and open reports.
- `/news/desk/new/`, `/news/desk/<id>/edit/`: draft/publish news or events.
- `/news/desk/agents/`: admin assignment/deactivation of existing users.
- `/news/birthday/`: signed-in residents create cards; preview and SVG download.
- `/admin/newsdesk/`: full Django admin management; existing `/admin/jobs/`
  manages pincodes/users. Portal Super Admins can use existing management screens.

A News Agent has one active `NewsAgent` assignment and can manage all content in
that assigned pincode, including stories created by another agent. Assignment
does not grant Django staff access. Reassignment immediately removes old desk
access. Inactive users, pincodes, districts or states block agent access.

Global desk access requires a superuser, existing `admin_role=super_admin`, or an
active staff account with the explicit `newsdesk.manage_newsdesk` permission.
Staff status alone is insufficient. Existing user/pincode administration retains
its own permissions. Agents and residents cannot change assignments.

## Business rules

- Drafts and future publications are never in the public feed/detail/API.
- Publish time is assigned server-side on first publication and preserved through
  edits and draft/republish cycles. Pincode cannot change after story creation.
- Comments are accepted only while `published_at <= now < published_at + 7 days`.
  No scheduler is required: every write checks the window under a database lock.
  Existing visible comments remain readable indefinitely. Whitespace-only and
  over-160-character comments are rejected server-side.
- One rating per resident/story, 1–5 stars. Subsequent ratings update it. Database
  constraints enforce uniqueness and range. Ratings can continue after day seven.
- One report per resident/comment. Agents/admins can hide/restore comments or
  dismiss reports. Hiding resolves open reports and records moderator/time.
  Hidden comments are omitted from public HTML and JSON.
- Events require start time and venue; end time cannot precede the start.
- Birthday cards are independent personal cards, not automatically published
  articles. Agents can publish curated stories in the Birthday Wishes category.
  Cards are private by default; optional link sharing uses UUID URLs. Only the
  owner may remove a card and revoke its shared link. No birth dates are collected.
- All displayed text is escaped; no rich HTML is accepted. Public contributor
  labels use full names or a resident number, never phone-based usernames.

## Uploads and deployment

Run `python manage.py migrate newsdesk` and `python manage.py collectstatic --noinput`.
Migration 0001 depends on the existing pincode migration (`jobs.0004`) to avoid
pulling unrelated pending app changes into production.

Uploads use randomized names in `NEWSDESK_MEDIA_ROOT`, defaulting to
`Path(MEDIA_ROOT).parent / 'newsdesk-private'`. The app user must be able to write
there. Keep this directory outside all publicly served media/static aliases,
include it in backups, and do not expose its filesystem path via a web server.
The authorized `/news/media/<id>/photo|video/` endpoint serves files.

Photos: JPEG/PNG/WebP, maximum 5 MB and 20 megapixels, decoded/verified with Pillow.
Videos: MP4/WebM container signature and extension validation, maximum 25 MB.
Video transcoding and malware scanning are outside this MVP. Configure the reverse
proxy request-body limit to at least 32 MB to allow a photo and video together.
Replacing/deleting content does not delete old files automatically; retain them
for backups and use a separately reviewed cleanup policy if needed.

## JSON APIs

Use the same session login and CSRF token as the website. Send `X-CSRFToken` and
the session/CSRF cookies for mutations. POST accepts JSON or form data; file
uploads require multipart form data. No tokens or CSRF exemptions are introduced.

| Endpoint under `/news/api/` | Methods | Purpose |
| --- | --- | --- |
| `pincodes/?q=600&page=1` | GET | Active pincode lookup, 50/page |
| `stories/?pincode=600001&category=sports&kind=event&page=1` | GET | Public feed, 12/page |
| `stories/<id>/` | GET | Public detail, rating aggregate, comments (30/page) |
| `stories/<id>/comments/` | POST | `text` (1–160 characters) |
| `stories/<id>/rating/` | POST | `stars` (1–5) |
| `comments/<id>/report/` | POST | `reason` (1–200 characters) |
| `desk/?tab=stories|comments|reports&page=1` | GET | Scoped desk queue, 20/page |
| `desk/new/` | POST | Create draft or published item |
| `desk/<id>/` | GET, POST | Scoped read/edit |
| `desk/comments/<id>/` | POST | `action`: hide, restore, resolve |
| `agents/`, `agents/<id>/` | GET, POST | Admin assignment list/create/read/update |
| `birthday/` | GET, POST | Own recent cards / create a card |

Story fields: `title` (180), `body` (20000), `category`, `kind` (news/event),
`status` (draft/published), optional photo/video, event_start/event_end (ISO
datetime) and venue (200). Admins supply the **pincode record ID** when creating;
agents' pincodes are always derived from their assignment. Feed filters use the
six-digit **pincode code**. Author and publication timestamp cannot be supplied.
Agent assignment fields: user ID, pincode record ID, is_active.
Birthday fields: recipient (60), message (160), theme (sunshine/rose/sky),
is_public (false by default).

Responses use 400 for invalid inputs, 401 for unauthenticated API writes, 403 for
role violations and 404 for unavailable/out-of-scope records. Lists include
results/page/pages/total (birthday lists return the twelve most recent own cards).

## Verification

`python manage.py test newsdesk --settings=jobportal.test_settings --noinput`

Tests cover all roles, pincode/category filtering, draft and future visibility,
event validation, exact seven-day boundary, preserved publication times,
comment limits/XSS, unique ratings/reports, moderation scope, CSRF, uploads,
private/shared birthday cards, admin forms and JSON APIs.
