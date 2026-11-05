# LOCALFROM search launch

## Current indexing scope

The existing registration policy allows guests to read the homepage and About
page. Shops, products, offers and news require an account. SEO must not bypass
this policy for crawlers or expose imported shop contacts, private media, account
information or moderation drafts.

`jobportal/seo.py` explicitly allows only `home` and `about` as search landing
pages. The sitemap index advertises only its nonempty public-pages section.
Existing business/news sitemap routes remain available as empty XML documents;
no routes have been removed. Signed-in views of protected pages are also
`noindex`, so sitemap behavior does not depend on cookies or authentication.

Home metadata describes the Vandavasi pilot, shops, products, discounts and news.
Organization/WebSite/WebPage JSON-LD uses the actual logo, published support
contacts and official Instagram profile. No ratings, reviews, coordinates,
opening hours or unverified shop facts are invented. English/Tamil currently
share one URL and browser preference; no separate-language `hreflang` URLs are
claimed.

## After deployment

1. Confirm `SITE_URL=https://www.localfrom.com` in the protected environment.
   Never paste environment file contents into chat or logs.
2. Check the public homepage, `/about/`, `/robots.txt`, `/sitemap.xml` and
   `/sitemaps/pages.xml` over HTTPS. Sitemap locations should be canonical
   absolute HTTPS URLs and return 200 without a session.
3. Confirm apex-to-www redirects, one canonical and one description per public
   page. Search/filter URLs remain noindex; tracking parameters consolidate to
   the clean canonical.
4. Open Google Search Console, add the `localfrom.com` domain property and
   complete its ownership verification. Add only the verification TXT record
   provided by Google; preserve existing DNS records.
5. Submit `https://www.localfrom.com/sitemap.xml`, inspect the homepage and About
   page with URL Inspection, and request indexing if the live tests succeed.
6. Validate homepage structured data using Google's Rich Results Test. Valid
   markup does not guarantee a rich result or search ranking.
7. Monitor indexing, sitemap errors and mobile page experience in Search
   Console. Search Console setup is external account work and is not completed
   by this code change.

No backend migration, dependency installation, DNS edit, Nginx change or
Search Console submission is required/executed by the code patch itself.

## Expanding shop/product/news SEO later

Obtain approval to change anonymous access before expanding indexing. A proper
change must provide the same public information to ordinary guests and crawlers,
preserve all private actions and media protections, and align public querysets,
metadata, templates, sitemap eligibility and moderation. Do not special-case
Googlebot. Do not add login redirects to the sitemap.

## Official references

- https://developers.google.com/search/docs/fundamentals/get-started-developers
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/search/docs/appearance/structured-data/organization
