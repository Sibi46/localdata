# Local Ride and hospital launch placeholder

## Included behavior

- Home includes Local Ride and Hospital tokens icons. Hospital opens only a
  native dialog announcing **January 1, 2027**; there is no hospital booking,
  appointment intake, medical data model or automatic activation on that date.
- Existing guest policy remains: home is readable, ride pages/actions require
  an active signed-in account. Hospital launch notice is available to guests.
- `/rides/` lists upcoming active-owner bike/car journeys, with route filters.
  `/rides/post/` accepts origin/destination, IST departure (5 minutes to 90 days
  ahead), passenger capacity, meeting area and notes. Bike capacity is one;
  car capacity is one to seven. Each join request reserves one passenger place
  only after owner acceptance.
- `/rides/mine/` shows the account's posts and requests. A trip detail page
  exposes passenger notes only to its owner and existing Superadmin role.
  Account phone numbers and phone-shaped usernames are not used as traveller
  contact labels. Public notes remain user-provided content.
- One request per account per journey. Repeated joins/reviews are idempotent;
  withdrawn/declined requests remain in history and cannot be silently recreated.
  Posting is capped at five journeys and requesting at thirty journeys in a
  rolling 24 hours, using account row locks and persistent database counts.
- Accept/decline, withdraw, cancel, complete and ride-chat actions are POST with
  CSRF. Trip row locks serialize capacity-changing actions. Withdrawal reopens
  a full trip when a place becomes free. Past/closed trips refuse new joins or
  acceptances. Completion is allowed to the owner after departure only.
- Acceptance creates/reuses the two participants' existing private conversation,
  posts an acceptance message, refreshes the conversation's activity timestamp,
  and sends a bell notification. Ride-specific chat checks both participation
  and accepted status. Existing general chat routes and attachment protections
  are unchanged; cancellation does not erase/revoke historical general chats.
- Owner and existing Superadmin role can cancel. Superadmin has
  `/super-admin/rides/` and a dashboard navigation link; state admins/unrelated
  users cannot mutate others' trips. Notification, chat and seat updates share
  a transaction so database failures roll back the acceptance.
- No payment provider, fare collection, maps, automatic route matching, driver
  verification, SMS delivery or background worker is introduced. This is an
  account-based journey connection feature.

## Migration review and deployment

`jobs/migrations/0075_local_ride.py` creates only `RideTrip` and `RideRequest`,
their indexes, foreign keys and validation constraints. It references existing
User/Conversation rows but does not rewrite or delete existing application data.
Historical migrations and existing routes are preserved. No production migration
is run by development/testing. Back up first and review/approve this migration
before applying it on production. Stop the old application process before code
checkout/migrations, then collect static files and start the new process after
checks. Keep existing private media and payment Nginx rules in place.

Before public release, validate on the target MySQL version with two separate
database connections accepting the same last place concurrently. Local SQLite
regression tests validate sequential capacity/authorization/rollback behavior;
they do not prove MySQL locking under load. Confirm exactly one acceptance,
one accepted-chat message, correct full/open state and no overbooking. Also
exercise simultaneous accept/withdraw/cancel and retry behavior on staging.

## Smoke checks

1. Guest clicks Hospital tokens: launch dialog, no signup interruption; dismiss
   by button/Escape. Guest clicks Local Ride: existing create-account prompt.
2. Account A posts a bike trip Vandavasi to Chennai, one place; B and C request.
3. A accepts B; C remains pending and cannot be accepted while full. B opens
   chat; C cannot open B's ride chat or read B's private request note.
4. B withdraws before departure; one place reopens. A may then accept C.
5. A cancels another trip; pending/accepted participants receive notifications
   and further acceptance/join actions fail. Existing history remains.
6. Confirm Superadmin moderation access and rejection of unrelated/state-admin
   mutations; verify normal products, shop registration and private attachments.
7. Test 320–412px Android layouts, keyboard date/time entry in IST, no horizontal
   overflow, and persisted English/Tamil home selection. Ride forms themselves
   use English labels and accept Tamil place names/notes; the home icons and
   hospital notice have English/Tamil translations.
