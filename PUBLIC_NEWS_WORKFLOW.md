# Public News Desk submissions

Implemented 25 October 2026. Review assignment confirmed by the owner: Super Admin reviews submissions for now; no existing user was assigned as an editor.

## Reader flow

1. Open News Desk and select **Share your news** (`/news/share/`). No account registration is required.
2. Verify a ten-digit Indian mobile number with a six-digit SMS OTP. Codes expire after ten minutes and are single-use. News verification is separate from account-registration/password-reset verification.
3. First submission: provide name, supported six-digit PIN code, address, Aadhaar document and profile photo. PDF/JPEG/PNG/WebP Aadhaar files and JPEG/PNG/WebP photos are supported, up to 5 MB each. Masked Aadhaar is accepted.
4. Add a topic/headline and up to 200 words. Accept the news-sharing terms and confirm that the news is not fabricated or misleading.
5. Submit to the editor. The receipt shows a permanent Contributor ID and a separate Submission ID. The same verified phone reuses the same Contributor ID and private profile on subsequent submissions.
6. Pending submissions are not public. The contributor can reopen their status/history after verifying the same phone. Verified access expires after 30 minutes; **Finish / verify a different number** ends only news verification and does not log the user out of their account.
7. After publication, the receipt links to the public story. Rejection notes are visible privately to the contributor.

## Editorial flow

- Super Admin → **News & Local Stories → Reader submissions**, or `/news/desk/submissions/`.
- Review the original news and private contributor details, download the Aadhaar privately, and inspect the profile photo.
- Edit the headline/body/category as needed, confirm document review, and choose **Approve and publish**, or reject with an explanation.
- Publishing creates a normal published News Desk story, visible through existing PIN-code filters. Double submission/review does not create duplicate stories. The original submission and acceptance timestamps are retained.
- Super Admin can review all submissions. Existing active News Agents can act as editors only for their assigned PIN code; inactive/unassigned users cannot review. Future editors can be assigned through the existing News Agent management page.
- Eligible editors and Super Admin receive dashboard notifications for new submissions. A linked account receives a review notification only when its account phone matches the verified contributor phone. Anonymous contributors use their receipt/history.

## Identity and access

- Aadhaar, profile photos, phone and address are not copied into public stories or public news API responses. Profile photos are used for editorial identity review, not as public article images.
- Identity files have no public media URL. They are stored outside `MEDIA_ROOT`, by default in `MEDIA_ROOT.parent / news-identities-private`, with owner-only file/directory permissions.
- Downloads require a valid contributor verification session or an authorised editor with access to that contributor's submissions. Aadhaar is served as a download with no-store and nosniff headers. Identity documents are never sent to an AI service.
- OTP verification confirms access to the phone. Editor document review is recorded separately; neither is represented as UIDAI/government Aadhaar authentication.
- SMS uses the existing `TWO_FACTOR_API_KEY` and `TWO_FACTOR_OTP_TEMPLATE`. Missing/failed SMS delivery fails closed; production never exposes OTPs. Phone/IP sending limits and phone verification-attempt limits apply.
- CSRF, active-PIN validation, upload content/size checks, required consent, server-side word counting, private receipt ownership and editorial scope are enforced server-side. Private upload files are cleaned up when database creation fails.

## Validation and deployment

- 93 automated tests passed across the new workflow, existing News Desk, previous usability/Report 2 fixes and admin permissions.
- End-to-end Chromium checks covered anonymous OTP (including incorrect codes), upload, 200-word limit, consent, stable contributor IDs, private pending state, editor download/approval, public publication, contributor history, verification finish, network-error recovery and mobile layouts at 1440/1024/768/390/320 pixels.
- Upload and pending-editor forms were additionally checked at 768/390/320 pixels. Tests used synthetic identity images and a mocked SMS sender in a separate local database. No real SMS or production test stories were created.
- Production preflight confirmed that SMS configuration is present and the private-storage parent is writable. This verifies configuration, not actual carrier delivery.
- Apply additive migration `newsdesk.0002_newscontributor_newssubmission` after a database backup. Collect static files and restart both application services. The change is isolated in `D:\Mypincode\public-news`, branch `feature/public-news`.
