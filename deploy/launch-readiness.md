# LOCALFROM launch preparation — 4 November 2026

Code-side preparation and local regression validation are complete. **The public
site has not been deployed or approved as operationally ready.** The Droplet,
real OTP account/template, production database, Redis, TLS and backup recovery
still need configuration and verification. This report supersedes the earlier
pilot report's dependency and regression results, not its infrastructure caveats.

## Validation

- Full suite: **514 run, 414 passed, 100 existing skips, zero failures/errors**.
- Targeted changed-area suite: **100 run, 83 passed, 17 existing skips, zero
  failures/errors**. No additional tests were skipped to obtain these results.
- Django system checks: zero issues.
- Python syntax checks passed for all 17 changed/new Python files.
- The 34 failures/errors remaining after Phase 2 were resolved in test fixtures,
  isolation and obsolete UI/access expectations. Production authentication and
  authorization policies were preserved; retired features were not restored.
- Ten tests were added: seven deployment configuration guards and three
  canonical-domain cases.
- Final runtime dependency graph: 57 packages, no missing dependencies or
  violated version constraints in the validation environment.
- Public PyPI advisory lookup completed for all 57 resolved versions: zero
  reported advisories and zero lookup errors on this date. This is a known-advisory
  check, not a guarantee that packages contain no vulnerabilities or a Linux lock.
- Wheel downloads were checked against official PyPI SHA256 metadata. Loaded
  Django, Pillow, Requests, Twisted, OpenSSL and Autobahn versions were checked
  against their distribution metadata, avoiding a namespace-package collision
  encountered in an earlier candidate install.
- The production environment template correctly fails deployment checks with its
  placeholder credentials. With synthetic configuration, deployment checks have
  no errors and retain the deliberate HSTS warning until real HTTPS is verified.
  These checks do not authenticate with an SMS provider, database or Redis.

The final dependency/advisory and load evidence is in
`.local-data/launch-ready/`. The validation environment uses Windows/Python 3.14,
an isolated package overlay and inherited dependencies. It is not a clean Ubuntu
Python 3.12 installation. Docker's engine was unavailable locally; MySQL 8.4,
actual Redis, Nginx and Linux permissions remain server acceptance checks.

The existing development server/virtualenv and global package installation were
left intact. The patched code was loaded through the verified overlay for tests;
production must install the updated requirements into its own fresh virtualenv.

### Updated local load check

The patched Daphne stack completed **1,032 measured requests with zero HTTP or
application-result errors**. Each virtual user fetched current member pages and
sent a CSRF-protected message using disposable fixtures. Signup/SMS, media
transfer, WebSocket soak, TLS and internet traffic were not measured.

| Concurrent virtual users | Requests | Median | p95 | Maximum |
|---|---|---|---|---|
| 1 | 12 | 34.7 ms | 86.5 ms | 86.5 ms |
| 10 | 120 | 107.4 ms | 198.2 ms | 219.8 ms |
| 25 | 300 | 341.4 ms | 566.9 ms | 753.3 ms |
| 50 | 600 | 737.6 ms | 1,705.3 ms | 2,522.7 ms |

These are short Windows/SQLite loopback bursts without the proposed CPU/RAM
limit; they do not equate monthly/daily visitors with concurrent users. The
temporary server was terminated and disposable data removed after the run.

## Changes in this preparation

No project files were deleted. Existing source changes and uploaded/user data
were retained. No production database, migration, deployment, DNS, purchase or
real SMS operation was executed. Only disposable test databases/media were used.

| File | Change and reason |
|---|---|
| `requirements.txt` | Patch Django, Pillow, Requests and Gunicorn; align tested Channels/Daphne; pin patched existing transitive dependencies and their required typing support. No application dependency was removed. |
| `jobportal/settings.py` | Use localfrom.com/www.localfrom.com production defaults, canonical site origin and sender domain. Environment overrides remain available. |
| `jobs/apps.py` | Register deployment-only checks. |
| `jobs/production_checks.py` (new) | Reject DEBUG, demo OTP, placeholder credentials, local/non-shared OTP cache, insecure transport and unsafe host configuration during deployment checks. No external requests or secret values in diagnostics. |
| `jobs/test_production_checks.py` (new) | Verify valid/invalid startup configurations and secret-free diagnostics. |
| `jobportal/seo.py` | Derive apex/www canonicalization from SITE_URL. Keep POSTs, localhost and unrelated hosts unchanged. |
| `jobportal/test_seo.py` | Add apex-to-www, canonical/local host and POST regression cases. |
| `templates/about.html` | Replace the obsolete hardcoded domain with configured SITE_URL. |
| `jobportal/test_production.py` | Isolate machine-local overrides in the relevant environment test; retain separate broken/missing-local-settings tests; update current branding expectations. |
| `jobs/tests.py` | Read production DB environment configuration in an isolated settings namespace rather than reloading development settings into a shared module. |
| `jobs/test_account_features.py` | Use complete current profile fixtures, current dashboard/company context, member-only discovery, active-area context and a nested-header-aware parser. Test preference privacy as an unrelated member. |
| `jobs/test_discovery_navigation.py` | Assert shop discovery links instead of a retired home layout comment. |
| `jobs/test_corrections.py` | Follow the current account redirect and public-shop dashboard link. |
| `jobs/test_offer_contacts.py` | Authenticate an unrelated reader so contact/availability assertions reach the protected views. |
| `jobs/test_report_regressions.py` | Authenticate the reader, explicitly select all areas and check paginated list results/current empty-state controls. |
| `jobs/test_usability_report.py` | Use valid saved category values, member access and current offer category controls; retain expiry/inactive/filter assertions. |
| `jobs/test_pdf_report.py` | Test current registration/member navigation, authenticated sponsored links and persisted photo/context behavior. Keep retired routes out of the current navigation test. |
| `jobs/test_fourteen_report.py` | Test current offer cards, Instagram configuration and registration back link. |
| `deploy/localfrom.service` | Run deployment checks before Daphne starts. |
| `deploy/nginx-localfrom.conf` | Sandbox public uploaded documents with CSP alongside nosniff; retain private-chat denial and payment interlock. |
| `deploy/pilot-launch.md` | Update dependency/startup requirements and explicit data/migration/credential acceptance steps. |
| `scripts/pilot_load_check.py` | Allow a separate output directory so new checks preserve earlier evidence. |
| `deploy/launch-readiness.md` (new) | This current change/validation/launch-handoff report. |

Models, migration files, URL declarations, login/OTP/payment business handlers and
production access policies were not edited in this preparation. The canonical
GET/HEAD redirect changes to follow the configured domain; route definitions
remain intact. Payment provider work remains pending as explicitly requested.

## Required server acceptance before public access

1. Create the proposed Basic Regular 2 GB / 1 vCPU / 50 GB Bangalore Ubuntu 24.04
   Droplet using an SSH public key. Supply its public IP and SSH username; never
   send a private key/password in chat. The small pilot does not justify a larger
   server solely from monthly user count; measure real resource use first.
2. Install requirements in a fresh Python 3.12 virtualenv without inherited
   system packages. Verify dependency constraints/advisories again on Linux and
   build/test mysqlclient against the intended MySQL installation.
3. Configure private MySQL 8.4 and Redis, least-privilege credentials, real secrets
   and the approved SMS template. Test actual OTP delivery, expiry, replay and
   cross-worker proof consumption. Replace previously shared/demo administrator
   passwords and revoke old sessions before opening the site.
4. Review migration status on a disposable copy of existing data. In particular,
   the existing `jobs/migrations/0064_remove_retired_feature_tables.py` deletes
   retired tables/fields. This change did not edit or apply it to user data. Do
   not migrate imported history without reviewing and preserving required data.
5. Configure firewall/SSH, DNS, certificates and Nginx. Keep Daphne, Redis and
   MySQL private. Run nginx configuration validation and real HTTPS checks;
   template review is not runtime verification. Confirm renewal/security updates.
6. Verify raw old chat URLs fail at the public proxy and unrelated users cannot
   download private files. Test both participants and ordinary media/video
   playback. Private chats and news identity files must never enter public Spaces.
7. Choose filesystem pilot storage with off-server backups or complete a reviewed
   Spaces integration. Spaces is not implemented by these configuration files.
   Test database AND public/private media restoration before transferring users.
8. Repeat load/smoke tests on Nginx/Daphne/MySQL/Redis with realistic media, mobile
   clients and CPU/RAM/disk monitoring. Local burst results are not a 2 GB capacity
   guarantee. Monitor errors, latency, storage and SMS delivery during the pilot.

Payments must remain unavailable at the public proxy until the provider contract
and trusted verification are separately approved. Do not expose the application
port directly: its unchanged legacy simulated payment handler is not safe for
accepting production payments.

## Evidence and sources

Final local logs: `checks-final.log`, `targeted-final.log`, `full-suite-final.log`,
`install-validated.log`, `runtime-closure-final.json`,
`runtime-advisories-final.json`, `production-settings-check.json`, and `load/`
under `.local-data/launch-ready/`. Earlier failed candidate attempts are retained;
they are not the final test result. DATABASES override warnings in guard tests
are test-harness warnings; they are not failed database connections.

- https://docs.djangoproject.com/en/5.2/releases/5.2.19/
- https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html
- https://github.com/psf/requests/releases/tag/v2.33.0
- https://github.com/benoitc/gunicorn/releases/tag/23.0.0
- https://pypi.org/ (version-specific advisory metadata and wheel hashes)
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
