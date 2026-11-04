# Phase 2 production requirements

No deployment, credentials, real SMS transmission, database migration or historic
media relocation was performed as part of this code change.

## Account OTP

Production requires `DJANGO_DEBUG=false`, reachable private Redis and a configured
2Factor account. `OTP_REDIS_URL` defaults to `REDIS_URL`. The dedicated `otp` cache
uses Redis for cross-worker, atomic claims. Do not replace this production alias
with a per-process or non-atomic cache. Redis failure rejects verification and
account creation/reset; it never falls back to an unverified operation.

Set `TWO_FACTOR_API_KEY` and `TWO_FACTOR_OTP_TEMPLATE` through the deployment's
secret/environment configuration. The adapter uses the provider's JSON OTP SEND
endpoint with an API-key header. Confirm the approved template and account support
this endpoint, then perform an authorized real delivery smoke test before launch.
Automated tests mock delivery and never use real SMS credits.

Demo codes require BOTH DEBUG and the relevant explicit demo flag. They cannot be
enabled by demo flags alone when DEBUG is false. Production templates and API
responses do not disclose codes. Provider errors and request bodies are not logged
by the adapter. Do not enable HTTP wire/body logging in production.

Old session flags and plaintext legacy OTP session values are not accepted as
proof. Existing verification sessions must request a fresh OTP after this update.
Routes remain available. Legacy register-OTP callers may submit the password with
issuance (stored only as a password hash) or with verification. Direct legacy
registration now requires server-verified signup proof for the same phone.

## Private chat attachments

`CHAT_PRIVATE_ROOT` defaults to a sibling of MEDIA_ROOT and must be outside every
public media/static location. Add it to private storage backups. It must never be
an Nginx alias or a public Spaces prefix. New chat uploads are written there;
message records and attachment names retain their existing format.

Existing uploads are retained in their original location. The authenticated
attachment handler can read them after checking conversation participation.
Include `nginx-chat-private.conf` in the production server block before allowing
public media traffic. Django independently denies raw chat-file URLs, including
normalized path variants, but cannot control requests Nginx serves directly.
Adapt the deny prefix if MEDIA_URL changes. Historical files must not be copied
into a public bucket. Any external service already serving legacy files needs an
equivalent deny/private-storage policy before launch; Django alone cannot revoke
public objects or existing caches on an external service.

Verify raw legacy URLs are rejected at the actual public proxy/CDN and that guest
and unrelated-member downloads are rejected while both participants can download.

## Payments: explicitly pending

The existing page labels payments as simulated and suggests Razorpay/PayU. No
implemented provider, webhook/signature contract or trusted order lookup was
identified. The user explicitly requested keeping payment work pending. Payment
handlers, models, routes and templates remain unchanged; do not enable production
payment acceptance through this simulation. Provider-specific signature, amount,
order, replay/idempotency and ownership tests cannot be completed until the
integration contract is approved.
