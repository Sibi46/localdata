# Google Analytics 4

The existing hardcoded GA4 tag has been replaced with a shared, environment-configured tag. No custom events or packages are added.

Set the following in the deployment environment or project `.env`, then restart Django:

```dotenv
GA4_MEASUREMENT_ID=G-SPHLTP6M4P
```

This is the ID previously present in `templates/base.html`. Confirm it matches your Google Analytics property under Admin > Data streams > your web stream. Use that stream's Measurement ID if different. An empty or missing variable disables the tag; set it before deploying to retain existing tracking.

`templates/includes/ga4.html` is included once by each HTML page layout, including the homepage, dashboards and portal. Pages inheriting those layouts receive it automatically.

## Test

1. Open the site in a browser with ad blocking disabled and visit a few pages.
2. View page source: there should be one `googletagmanager.com/gtag/js` script using your Measurement ID.
3. Open the matching Google Analytics property, then Reports > Realtime. Look for your active user and page views; allow a few minutes for data to arrive.
4. If missing, check the browser Network tab for `gtag/js` and `g/collect`, and confirm the ID matches your stream. Browser blocking or property traffic filters may exclude your visit.

Automated checks: `.venv\Scripts\python.exe manage.py test jobportal.test_ga4 --settings=jobportal.test_settings`.

## Changed files

- `jobportal/settings.py`
- `jobportal/context_processors.py`
- `jobportal/test_ga4.py`
- `templates/includes/ga4.html`
- `GA4_SETUP.md`
- `templates/403.html`
- `templates/404.html`
- `templates/500.html`
- `templates/about.html`
- `templates/admin_base.html`
- `templates/base.html`
- `templates/business_profile.html`
- `templates/campus/auth_landing.html`
- `templates/campus/hr_login.html`
- `templates/campus/hr_signup.html`
- `templates/campus/po_login.html`
- `templates/campus/po_signup.html`
- `templates/campus/student_login.html`
- `templates/campus/student_signup.html`
- `templates/coupons/salesman/base.html`
- `templates/coupons/salesman/login.html`
- `templates/coupons/shop/verify_redemption.html`
- `templates/edit_job.html`
- `templates/employer_dashboard.html`
- `templates/index.html`
- `templates/job_list.html`
- `templates/jobseeker_dashboard.html`
- `templates/marketing/layout.html`
- `templates/messages.html`
- `templates/offer_letter_print.html`
- `templates/portal/base_portal.html`
- `templates/post_job.html`
- `templates/profile_edit.html`
- `templates/register.html`
- `templates/seeker_profile.html`
- `templates/smart_marketing_story.html`
