MIGRATION CONFLICT HOLDING AREA
================================

These migrations exist on production but CANNOT be applied to the local
migration chain without first resolving the following numbering conflicts:

LOCAL (already committed):
  jobs/migrations/0041_jobapplication_extra_fields.py
  jobs/migrations/0042_adpost_clicks_field.py

PRODUCTION (applied on server):
  jobs/migrations/0041_merge_20260828_1513.py     ← conflicts with local 0041
  jobs/migrations/0042_alter_localoffer_valid_days.py  ← conflicts with local 0042
  (+ 0043, 0044, 0045, 0046 depend on the above)

RESOLUTION OPTIONS (choose one before committing):
  A. Keep production chain: move local 0041+0042 here, use production's 0041_merge
     chain (0041_merge → 0042_alter → 0043 → 0044 → 0045 → 0046)
  B. Create new merge migrations: write a 0047_merge that depends on both
     the production chain tail (0046) and local's 0042
  C. Renumber local 0041+0042 to higher numbers and add new merges

Do NOT delete files here or in migrations/ until the resolution is decided.
