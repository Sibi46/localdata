# LOCALFROM pilot: www.localfrom.com

This is a prepared deployment plan, not a completed deployment. No Droplet exists
yet, no DNS was changed, no live database was migrated, and no SMS was sent.

## Initial server

For the intended 10-20 daily pilot users, start with the Basic Regular 2 GB / one
vCPU / 50 GB Droplet in Bangalore, Ubuntu 24.04 LTS. Current listed price is $12
per month, excluding backup/storage/tax. This is a starting estimate, not a load
capacity guarantee. Use an SSH public key when creating it. Never share a private
key or put credentials into this repository. Check region/size availability in the
DigitalOcean dashboard before purchase.

## Files prepared for review

- `localfrom.env.example`: production domain, MySQL, Redis, OTP and storage paths.
- `localfrom.service`: unprivileged, loopback-only Daphne process; requires the
  existing `localfrom` OS user and directories before installation.
- `nginx-localfrom.conf`: HTTPS/media/WebSocket proxy template. Its map belongs
  in Nginx's http context (as in an included sites-enabled file). Certificate paths
  are examples for a certificate named localfrom.com covering apex and www.
  Install a working HTTP-only ACME bootstrap configuration first; the HTTPS block
  cannot pass configuration checks before its certificate exists. Unknown hosts
  should be rejected by a separate default server.

The production proxy deliberately returns 503 for the existing simulated ad
payment URLs. This does not implement a provider or modify the application's
payment handler. Keep payments pending until a provider contract is approved.

## Storage and access

Use `/srv/localfrom/app` for source, `/srv/localfrom/venv` for a fresh Python 3.12
virtualenv, and `/srv/localfrom/storage` for writable data. Create the virtualenv
without system-site-packages; the local development environment inherits user-site
packages and is not proof that requirements.txt installs cleanly on Ubuntu.

Public static files are in storage/static and public uploads in storage/media.
Chat, newsdesk-private and news-identities-private are separate private folders.
Nginx must not alias any private folder. The OS user localfrom must own writable
storage; www-data needs read access only to public static/media. Protect the real
environment file and include all private media in backups.

Spaces integration has not been implemented or verified. Do not assume setting
Spaces credentials uploads files there. A filesystem pilot is possible only with
off-server backups and storage monitoring; videos can consume the boot disk.

## Steps requiring the actual Droplet

1. Configure SSH keys, a non-root application user, firewall access for SSH and
   HTTP/HTTPS only. Keep MySQL, Redis and Daphne private/loopback-only.
2. Install and validate the production dependency set in a clean environment.
   Use requirements.txt, including the validated security update pins. Do not
   start Gunicorn as a second server; this deployment uses Daphne.
3. Install MySQL 8.4 and Redis; provision a least-privilege database account and
   real environment values. Do not reuse local/test passwords or signing keys.
4. Back up and inspect the existing database and media before transferring real
   data. Test migration history and restoration on a disposable MySQL copy first.
   No live migration or historic data rewrite is authorized by these templates.
   In particular, the existing `jobs/migrations/0064_remove_retired_feature_tables.py`
   drops retired feature tables and removes old job references. Do not blindly
   apply it to an imported historical database: first inspect its applied state,
   preserve any required history in a verified backup/archive, and review the
   migration plan. This readiness change does not edit that migration.
5. Point the apex A record to the new IPv4 and www to the apex (CNAME) or same IP.
   Configure AAAA only if working IPv6 is actually assigned. Obtain a certificate
   covering both names, validate Nginx, then enable the service/proxy.
6. Configure a real 2Factor account/approved template and test an authorized phone.
   Verify no production code is displayed or logged, Redis consumption works across
   workers, and failed delivery cannot grant account/reset proof.
7. Run Django deployment checks with actual production settings and inspect every
   warning. The service also runs `check --deploy --fail-level ERROR` before
   starting: demo OTP, placeholder delivery/signing/database credentials,
   non-Redis proof storage and insecure transport prevent startup. These are
   configuration checks, not proof of real database/SMS/Redis connectivity.
   HSTS is deliberately zero until HTTPS and recovery are verified.
8. Smoke-test signup/login/reset, shop registration, product images, offers/news,
   messages and notifications. Verify the raw historical chat URL and unrelated
   member downloads fail at the public proxy, and both participants can download.
9. Repeat the local load scenarios against the actual Nginx/Daphne/MySQL/Redis
   stack. Include image/video transfer, mobile browser behavior and peak CPU/RAM.
   The loopback SQLite results are not a DigitalOcean benchmark.
10. Enable off-server database and media backups, test restore, review logs and
    watch disk, RAM, error rate and response times during the small pilot.
    Enable Ubuntu security updates and verify automatic TLS certificate renewal.

Before opening registration, replace every shared/demo administrator password
and revoke old sessions using a reviewed maintenance procedure. Never reuse the
administrator credentials previously shared in chat. Enable account-level MFA
for DigitalOcean, the domain registrar, DNS and SMS provider where available.

Public media is served with nosniff and a sandbox CSP. Keep the historical chat
deny rule ahead of the public alias, and verify browser image/video playback and
direct document responses on the real proxy. Private folders must never be
included in a public Spaces bucket or CDN origin.

## Regression evidence

See `deploy/launch-readiness.md` and `.local-data/launch-ready/` for the current
run. Retired feature tests keep their existing explicit skips. Updated member
tests exercise the real registration gate; production access rules are unchanged.

## Dependency launch blockers found on 4 November 2026

Requirements now pin Django 5.2.19, Pillow 13.0.0 and Requests 2.33.0. The initial
patch download stalls were resolved using bounded downloads verified against
PyPI SHA256 metadata. Earlier candidate versions and their failed attempts remain
in local evidence; final validation must use the final-packages environment.

Channels 4.3.2 and Daphne 4.2.2 now match the tested versions. channels-redis 4.2.0
is present in the isolated validation environment. A clean Ubuntu Python 3.12
installation, native mysqlclient build and real Redis validation remain necessary.

The retained Gunicorn pin was patched from 21.2.0 to 23.0.0; no feature or optional
server was removed. This deployment template uses Daphne and never starts Gunicorn.

References:
- https://www.digitalocean.com/pricing/droplets
- https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://www.djangoproject.com/weblog/2026/nov/03/security-releases/
- https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html
- https://github.com/psf/requests/releases/tag/v2.33.0
- https://github.com/advisories/GHSA-hc5x-x2vx-497g
