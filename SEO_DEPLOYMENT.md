# OURPINCODE SEO

## Scope and indexing policy

Existing login permissions, analytics, static/media configuration, navigation and UI are retained. The unrelated local `.env.example` changes are not part of this work.

Canonical origin comes from the existing `SITE_URL` setting (production: `https://ourpincode.com`). GET/HEAD requests to the production `www` alias redirect permanently; POST requests are preserved to avoid disrupting forms.

`/robots.txt` allows crawling and advertises `/sitemap.xml`. Private URLs are deliberately not disallowed: Google must be allowed to observe their `X-Robots-Tag: noindex, follow` responses. Authentication still protects private content. Static assets remain crawlable.

The paginated sitemap index omits empty sections and covers:

- Homepage; jobs and business directories only when eligible records exist.
- Approved active free/paid jobs from active employer accounts, with a title, location and at least 80 characters of description. Expired application dates and expired plans are excluded.
- Active employer business profiles with a name, industry, company ID and pincode.
- Published, non-future news in active pincodes, with a title and at least 80 characters of body. Birthday wishes are excluded.

The 80-character floor is a conservative completeness check, not a Google ranking requirement or a guarantee of content quality. Review low-quality, duplicate and test records editorially.

Other routes are excluded from the sitemap and receive noindex headers, including login, admin, APIs, Network, account pages, coupon actions, personal birthday cards and modules not yet approved as search landing pages. News feed pages depend on a selected pincode and are excluded; public story pages are eligible. Smart Marketing currently requires login and remains private. Search/filter/pagination variants are noindex with a clean canonical. Tracking-only parameters consolidate to the clean canonical without noindex.

Metadata is shared by the base layout and the three independent public layouts (homepage, job list, business profile). Structured data describes only the actual homepage Organization and WebSite; no invented ratings, contacts or business facts are added. Other standalone private layouts are covered by response headers.

## Validation

```powershell
.\.venv\Scripts\python.exe manage.py test jobportal.test_seo jobportal.test_production newsdesk.tests --settings=jobportal.test_settings --noinput
```

## Production commands

From the deployment server, after reviewing and pushing the changes:

```sh
cd /var/www/ourpincode
sudo -u ourpincode git pull --ff-only origin feature/ourpincode-production
sudo -u ourpincode .venv/bin/python manage.py check
sudo systemctl restart ourpincode
sudo systemctl is-active ourpincode
```

No database migration or static collection is required by these changes. Do not overwrite `.env`; verify the existing `SITE_URL=https://ourpincode.com` setting.

The existing nginx HTTP block redirects to `https://$host$request_uri`. Back up `/etc/nginx/sites-available/ourpincode` and change only its two HTTP redirect destinations to `https://ourpincode.com$request_uri`. Preserve the TLS, WebSocket, proxy, static and upload settings. Django handles the HTTPS www page redirect. Validate with `sudo nginx -t` before `sudo systemctl reload nginx`.

Verify responses:

```sh
curl -I http://ourpincode.com/
curl -I http://www.ourpincode.com/
curl -I https://www.ourpincode.com/
curl -I https://ourpincode.com/
curl -A Googlebot https://ourpincode.com/robots.txt
curl https://ourpincode.com/sitemap.xml
curl https://ourpincode.com/sitemaps/pages.xml
curl -I https://ourpincode.com/login/
```

Expect the three aliases to redirect to HTTPS non-www, the canonical homepage/crawler files to return 200, and private responses to include noindex. Django sitemap section responses can themselves carry `noindex` (this does not prevent discovery of URLs within them).

## Google Search Console

1. Add a Domain property for `ourpincode.com` and verify the supplied TXT record with the DNS provider. Keep any existing verification record.
2. Submit `https://ourpincode.com/sitemap.xml` under Sitemaps.
3. Use URL Inspection / Test Live URL for the homepage and representative eligible job, business and news pages. Confirm crawling is allowed and the user-declared canonical is HTTPS non-www.
4. Request indexing for these representative pages. Google schedules crawling; submission does not guarantee indexing.
5. Monitor Page indexing and Sitemaps after recrawling. Inspect unexpected exclusions, server errors, manual actions and security issues. Private-page noindex exclusions are expected.
6. Check homepage markup in Schema.org Validator. Organization/WebSite markup may not produce a Rich Results Test enhancement; this is not itself an error.

Search Console coverage, Google-selected canonicals, manual actions and historical indexing cannot be confirmed without access to the site's Search Console property. No ownership verification or indexing request is made automatically.
