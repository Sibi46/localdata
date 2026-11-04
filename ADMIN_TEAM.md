# Admin team

The current `super_admin` keeps full access. Existing state/district admins are unchanged. New accounts created at `/super-admin/team/` use the separate `scoped_admin` role without Django staff or superuser privileges.

## Use

1. Open Super Admin > Admin Team > Create admin.
2. Enter name, unique username and password with confirmation. Mobile number is optional.
3. Select a state (for example Tamil Nadu or Delhi), or choose All states.
4. Use the ON/OFF switches for the sections the admin may moderate. All are initially enabled for a state admin; use Disable all and enable only Jobs or Flicks for a section admin.
5. Share `/admin-workspace/login/` with the admin. They sign in using their username and password and reach their named state dashboard automatically. Existing accounts keep their original login usernames.

Edit access or suspend/reactivate accounts in Admin Team. Changes apply to existing sessions on the next request. These accounts cannot create other admins, use Django admin, or enter the older unrestricted admin panels.
All sections can be turned off for an existing admin. Disabled sections appear as OFF cards without record counts or action links. Dashboard totals include only enabled sections within the assigned state; financial and account-management tools remain with the Main Super Admin.

## Activity monitoring

The Main Super Admin dashboard shows recent activity; `/super-admin/team/activity/` provides paginated history filtered by admin username and section. Records include successful admin sign-ins, account creation, permission updates, suspension/reactivation, and successful moderation actions performed in the assigned workspace. Content changes and their audit record are saved in the same transaction. Failed/denied actions are not recorded as successful actions.

History starts with this release, not retroactively. Existing legacy back-office actions are outside this log. Passwords are never recorded. Actor and target names are retained when a referenced account or moderated Flick is deleted. Assigned admins cannot access the global activity log; their dashboard shows only their own activity for their current scope.

## Sections

| Section | Delegated actions |
| --- | --- |
| Jobs | Approve or suspend postings; employer is notified |
| News | Publish or unpublish stories; original publication dates are preserved |
| Offers | Activate or suspend offers |
| Ads | Approve or reject ads, using the existing ad duration; owner is notified |
| Communities | Verify/activate or suspend communities |
| Quiz | Activate or suspend quizzes |
| Coupon shops | Activate or suspend shops |
| Voucher businesses | Approve or suspend businesses |
| Flicks | Review and permanently delete a flick, with explicit confirmation |

Billing, coupon issuance, rewards, voucher purchases, paid plan verification, geography and global settings remain with the Main Super Admin. New roles use dedicated moderation screens; they are not given blanket access to existing section back offices.

State access uses the record's pincode and the existing PinCode > District > State mapping. Offers use the owner's pincode; Flicks use the uploader's pincode. Unmapped locations are invisible to state-scoped admins, but remain available to the Main Super Admin and national section admins. Missing/deleted/inactive state assignments fail closed.

## Deployment

Apply the additive migration before restarting the application:

```sh
python manage.py migrate
python manage.py seed_states
python manage.py check
```

No existing roles are converted and no accounts are created automatically.
`seed_states` adds missing states and union territories for the Assigned State dropdown. It preserves existing state records, inactive states and pincode mappings, and is safe to run again.

## Validation

```sh
python manage.py test jobs.test_assigned_admin jobs.test_marketing jobportal.test_ga4 --settings=jobportal.test_settings
```

Tests cover role creation, forged privilege fields, state/section isolation, legacy endpoint bypass attempts, account suspension, permission changes, CSRF, login routing and preservation of Main Super Admin access.
