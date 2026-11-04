# Network

`/network/` is a signed-in, pincode-local invitation feed. It uses the user's
existing registered `User.pincode`; no second registration is required. Missing
or invalid six-digit pincodes lead to a profile-completion prompt. Submitted or
URL pincodes never override the registered pincode.

Users post up to 500 characters. Activity words automatically select an emoji
(for example cricket → 🏏) in the composer and saved post. Detection is local,
deterministic, and does not call an external AI service. The original text is
preserved. Posts stay open until their author closes them, with no automatic expiry.

Connect is a CSRF-protected POST. It verifies both users' current pincodes,
creates a unique response per post/person, reuses the existing general chat,
sends one introductory chat message and an in-app notification, then opens
Messages. Repeated clicks don't duplicate the introduction or notification.
Only the author sees the list of responders; other readers see a count.
Closed posts stop accepting connections, and existing chats remain available.
Posts by inactive authors or authors who changed pincodes leave the local feed.
Authors can see their own history under My posts.

Apply `python manage.py migrate` before deploying the code. The additive portal
migration creates NetworkPost and NetworkConnection; it changes no existing
user, coupon, or chat records. No scheduler or external service is required.

Tests: `python manage.py test portal.test_network --settings=jobportal.test_settings`.
