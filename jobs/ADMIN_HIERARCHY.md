# Admin hierarchy

Super Admin manages all new team accounts. Country/state/district/PIN-code filters and country-name or phone search show scoped accounts and counts by role. Child locations appear after selecting their parent. Each role has a dashboard titled for that role. Each country admin creates state admins;
state admins create district admins; district admins create area admins; area admins
create salesmen. An area is one existing PIN code. Super Admin alone creates one
State IT Admin per state, assigns existing complaints to that admin, and monitors activity.
IT access is limited to assigned complaints in that state; it grants no content moderation.

Entry: /admin-team/ from the Super Admin sidebar. Login: /admin-workspace/login/.
First use Countries and state mapping to create a country and associate existing states.
No country is inferred or automatically assigned to existing data.
Creation requires a 10-digit phone number and password; the phone is also the internal username. Existing username logins remain valid. Super Admin creates only Country Admin and State IT Admin, while every other admin creates the next level. Staff privileges are never granted.
Super Admin and ancestor admins can suspend/reactivate descendants and reset passwords.
Suspending any ancestor blocks the descendant workspace immediately. Existing legacy
section admins remain separate and cannot be edited through the new hierarchy.

Migration jobs/0055 is additive: Country plus nullable geographic links and blank-by-default
hierarchy level. Back up the database before release, apply migrations before restarting
new code. No account conversion or data deletion. Do not reverse migrations as rollback;
retain additive schema when rolling back application code.

Salesman accounts reuse coupons.Salesman, but this hierarchy release provides their
assigned-area workspace only. Existing coupon sales routes are deliberately not granted
because they do not enforce the new PIN-code boundary. Legacy sales accounts are unchanged.

IT uniqueness is serialized using a State row lock in the account creation workflow;
manual database/Django-admin writes must not bypass this workflow. SQLite tests do not
prove MySQL concurrency. Production deployment and browser/device verification are separate.

Validation (local SQLite, 2026-10-13): 34 tests passed across
jobs.test_admin_hierarchy and jobs.test_assigned_admin, including hierarchy scopes,
creation, ancestor suspension, password access, IT isolation and legacy permissions.
Django system check passed; makemigrations --check --dry-run reported no changes.
No production migration, push or deployment performed.

Phone-login and hierarchy-filter update: 38 tests passed across the same two suites; Django checks, migration drift check and node --check static/js/admin-hierarchy.js passed. No new schema change. Browser/device interaction has not been manually verified.

Country dropdown repair: migration 0056 creates India if its code/name do not conflict
and links only recognized existing Indian state names with no country assignment.
Existing country assignments, unknown states, districts and PIN codes are preserved.
The reverse operation intentionally leaves reference data intact. seed_states now
links newly created states to an existing India record. Missing districts/PIN codes
are never fabricated; import or explicitly map the existing geography where needed.

World country list: migration 0057 adds missing ISO 3166-1 entries (249 countries
and territories) from the frozen pycountry/iso-codes dataset, alphabetically displayed.
No runtime package or network request. Existing names, IDs, inactive countries and
state assignments are retained; code/name conflicts are skipped rather than overwritten.
This does not import overseas states, districts or postal codes. They require separately
configured geography. Reverse migration leaves reference records intact.

## Worldwide states and districts

Migration 0058 adds nullable unique GeoNames IDs to State and District and widens
State.code from 5 to 16 characters. Existing names, keys, PIN codes and admin
assignments remain unchanged. Global names that collide with the existing globally
unique State.name receive a source-code suffix (for example Central (UG.C)).
Names already present in the same parent are reused only when unambiguous; no fuzzy
or cross-country matching. Inactive records are not reactivated.

The bundled GeoNames snapshot and attribution are in jobs/data/geonames/README.md.
No external service or Python package is needed at runtime. Country/State/District
selectors already read these existing models, so imported locations become available
without a separate API or duplicate geography models.

After approved deployment and a verified database backup:

```bash
.venv/bin/python manage.py migrate --noinput
# Read-only database preview; inspect skipped_counts and missing-country lists.
.venv/bin/python manage.py import_world_geography
# Explicit database write, atomic and repeatable; no deletions or reparenting.
.venv/bin/python manage.py import_world_geography --apply
```

Optional --report /chosen/path.json writes detailed skipped source codes to that file.
The import is a separate command, not an automatic bulk data migration. Take a fresh
backup before applying it. On an error, its database transaction rolls back; rerun
only after resolving the reported conflict. Do not reverse geography migrations to
roll back application code: retain added reference data and compatible schema.

Coverage is limited to GeoNames administrative levels 1 and 2. Some countries use
provinces/counties/regions instead of states/districts. Missing parents, unsupported
country codes (including non-ISO codes) and ambiguous matches are reported and skipped.
A country without source subdivisions remains selectable but has no fabricated
children. Overseas postal-code support is not part of this import; creating Area
Admins still requires an existing compatible PIN-code record.

Validation 2026-10-13: 49 SQLite tests passed (world geography, hierarchy, legacy
assigned-admin and seed-state suites), including the full snapshot import, repeat
import, read-only preview, existing PIN/status preservation and rollback on error.
Django checks and migration drift checks passed. Test snapshot coverage: 3,858
supported state-level and 47,604 district-level records; 7 unsupported-country state
rows and 38 missing-parent district rows reported. 22 ISO territories/countries have
no state rows and 61 no supported district rows in this snapshot. No guarantee of
complete or current worldwide administrative boundaries. MySQL bulk import and
production/device verification have not been performed for this update.

Country Admin creation now requires phone number, email address and password. Existing phone numbers (including business phones/usernames) and case-insensitive email/login collisions are rejected. Other hierarchy roles retain phone/password creation. Existing accounts are not changed; no schema migration.
