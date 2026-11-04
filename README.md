# Local From

A Django application with nine main features: products and discounts, shops and business profiles, offers, Local News Desk, flicks/videos, advertising applications, private messaging, business/shop registration, and personal accounts/profiles.

The Offers feed at `/advertise/` supports category, shop/title search, pincode, and followed-shop filters. Customers can follow/unfollow shops directly from offers, shop cards, or public profiles and start a private shop conversation. Follow buttons and follower counts update immediately; signing in is required to follow or message.

Shop registration opens a single dashboard at `/employer/dashboard/` for products, percentage discounts, shop offers, photos, videos, and profile details. Products include an image and price. The homepage and `/products/` show searchable product cards with links to each shop's full catalog, current approved offers, photos, videos, and contact details. Offers retain the existing approval process. Images support JPG, PNG, and WebP (5 MB each); shop videos support MP4 and WebM (50 MB each).

Shop setup accepts an optional logo and banner with previews. Product publishing accepts up to six images in one selection: the first is the cover and up to five additional images are stored by migration `0065_product_gallery_images`. Product cards open `/products/<id>/` with thumbnails, previous/next controls, touch swiping, and an enlarged image view. The seller name and logo link to the full shop profile. Editing without new images keeps the gallery; selecting new images replaces it.

My Ask, jobs, campus, family, rewards and gift points, coupons, gift vouchers, spin prizes, quiz, tuition, school, health, events, Smart Marketing, Network, community portals, and birthday-card creation are retired from the active site. Community/portal URLs, their admin editors, community points signals, and the family birthday notification command are disabled. Retired models, migration history, archived templates, uploaded files, and historical records are retained; this retirement performs no database migration or data deletion. The compatibility birthday command exits with an explanation and must be removed from any external scheduler.

Shop following, reviews, pincode selection, notifications, and administration (including analytics, ad approvals, shop imports, and product allowances) support the nine main features. The community category in local news is editorial content, not the retired community portal.

Migration `0064_remove_retired_feature_tables` removes 20 retired jobs, rewards, marketing, wallet, referral, and subscription tables, their permissions, and job links on messages/conversations. Back up any existing database before applying this destructive migration. Shared personal-profile data and migration history remain for active accounts and fresh installations. The local database backup and removed source snapshots are kept under `.local-data/backups/`.

Use `requirements.txt` to install dependencies and configure the environment from `.env.example`. Keep the `jobs` and `jobportal` Python package names: they own the existing user model and project configuration.

Personal signup at `/register/` uses name and phone, a session-bound demo OTP, and password creation. `/login/` accepts phone and password; `/account/` offers optional business/shop creation at `/business/create/` using the same identity and credentials. The demo code is displayed on screen (no SMS), expires after 10 minutes, and allows up to five failed attempts. Demo signup is enabled by `DEMO_SIGNUP_OTP` (defaults to `DEBUG`); configure real phone verification before using this flow outside demo environments.

Run validation with:

```powershell
python manage.py check --settings=jobportal.test_settings
python manage.py test jobs.test_shop_catalog jobportal.test_local_form newsdesk.tests newsdesk.test_public_submissions --settings=jobportal.test_settings --noinput
```

Set `SITE_URL`, allowed hosts, trusted origins, and email settings for the deployment's actual domain. Branding is Local From; the domain is configured separately.
