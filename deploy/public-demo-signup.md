# Temporary public demo signup

This is an explicitly approved temporary exception, not verified SMS onboarding.
Keep `DJANGO_DEBUG=false`, `DJANGO_DEMO_SIGNUP_OTP=false` and
`DJANGO_DEMO_PASSWORD_RESET_OTP=false`. Set `DJANGO_PUBLIC_DEMO_SIGNUP=true`
only for the temporary public signup flow.

Signup displays a random, session-bound testing code. Expiry, wrong-phone and
wrong-purpose checks, attempt limits, single-use consumption and duplicate
account checks remain enabled. API responses label displayed codes as demo and
state `phone_ownership_verified=false`. The signup page explains the limitation.
The User model has no phone-verification field; this change does not add one or
mark an account as SMS verified. The OTP cache distinguishes a completed demo
challenge from actual phone ownership. News contributor SMS verification remains
separate and does not accept signup demo proofs.

Existing accounts require their password. All account OTP recovery paths reject
issue, verification and consumption while public demo signup is enabled,
including reset proofs issued before the mode was enabled. Admin authentication
and payment blocking remain unchanged. Deployment checks retain the other
production requirements and emit `localfrom.W001` for this exception.

## Accepted limitation

Someone can claim another person's unregistered number. Uniqueness prevents a
second signup; it cannot establish that the first claimant owns the number.
Do not treat the account's phone number as verified identity or use a demo code
to recover an account. Any features relying only on the entered number inherit
this limitation. No code or provider credentials should be added to logs.

## Enabling after the reviewed update is deployed

1. Keep the site in maintenance until HTTPS, media authorization, backups and
   runtime checks are complete.
2. Configure the flag privately in `/etc/localfrom/localfrom.env`; do not publish
   that file or paste its contents into chat.
3. Run deployment checks. Expect the explicit demo warning and the deliberate
   HSTS warning until HTTPS acceptance is complete. Other errors still block startup.
4. Verify duplicate signup, expiry/replay, password-only login, and recovery
   rejection through the public HTTPS proxy. Keep payment routes blocked.

## Moving to real SMS

Configure the real SMS credentials/template privately and confirm delivery on
an authorized phone. Set `DJANGO_PUBLIC_DEMO_SIGNUP=false` and keep both legacy
demo flags false, then restart the app after checks pass. Outstanding demo
proofs become invalid and no signup code is displayed. Existing accounts and
passwords remain unchanged; they are not retroactively SMS verified. Existing
numbers require a separate real ownership-verification process before they can
be treated as verified. OTP recovery then requires real SMS verification.

No models or migrations are changed. Reverting to the prior application version
without real SMS configuration will block startup again; keep maintenance enabled
if rolling back.
