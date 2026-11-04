/* Explicit translations for this screen. Shop and product data stay unchanged. */
(() => {
  'use strict';
  if (!document.querySelector('[data-easy-products]')) return;
  const tamil = {
    'Language':'மொழி', 'Page language':'பக்கத்தின் மொழி', 'Add products':'பொருட்களைச் சேர்',
    'My products':'என் பொருட்கள்', 'Add photos. Enter a name & price. Publish.':'படங்களைத் தேர்வு செய்து, பெயர் மற்றும் விலை கொடுத்து வெளியிடுங்கள்.',
    'Photo':'படம்', 'Name and price':'பெயர் மற்றும் விலை', 'Publish':'வெளியிடு',
    'product slots available.':'பொருட்களைச் சேர்க்கலாம்.', 'Request more':'மேலும் அனுமதி கேட்க', 'Choose photos':'படங்களைத் தேர்வு செய்',
    'Each photo starts a separate product. Up to 20 products per batch. Add extra views inside its card.':'ஒவ்வொரு படமும் ஒரு தனிப் பொருள். ஒரு முறையில் 20 பொருட்கள் வரை சேர்க்கலாம். அதே பொருளின் கூடுதல் படங்களை அதன் கீழே சேர்க்கலாம்.',
    'Drafts stay in this browser on this device. Use one tab. Clear drafts on shared devices.':'வரைவுகள் இந்தக் கருவியின் உலாவியில் மட்டும் சேமிக்கப்படும். ஒரே தாவலைப் பயன்படுத்துங்கள். பகிர்ந்து பயன்படுத்தும் கருவியில் வரைவை நீக்குங்கள்.',
    'Review products':'பொருட்களைச் சரிபார்', 'Clear draft':'வரைவை நீக்கு', 'Ready to publish?':'வெளியிடத் தயாரா?',
    'These products will be visible in your shop. Published products stay in your catalog when you clear this draft.':'இந்தப் பொருட்கள் உங்கள் கடையில் தெரியும். வரைவை நீக்கினாலும் வெளியிட்ட பொருட்கள் கடையில் இருக்கும்.',
    'Publish products':'பொருட்களை வெளியிடு', 'Edit':'திருத்து', 'Full product form':'முழு விவரங்களுடன் சேர்க்க',
    'Need help?':'உதவி வேண்டுமா?', 'Call LOCALFROM: 7305675201':'LOCALFROM-ஐ அழைக்கவும்: 7305675201',
    'Draft saved on this device. Clear it on shared devices.':'வரைவு இந்தக் கருவியில் சேமிக்கப்பட்டது. பகிர்ந்து பயன்படுத்தும் கருவியில் வரைவை நீக்குங்கள்.',
    'Draft could not be saved. Keep this page open until you publish.':'வரைவைச் சேமிக்க முடியவில்லை. வெளியிடும் வரை இந்தப் பக்கத்தைத் திறந்து வைத்திருங்கள்.',
    'Saved draft restored.':'சேமித்த வரைவு மீண்டும் திறக்கப்பட்டது.',
    'Draft saving is unavailable in this browser. Keep this page open until you publish.':'இந்த உலாவியில் வரைவைச் சேமிக்க முடியவில்லை. வெளியிடும் வரை இந்தப் பக்கத்தைத் திறந்து வைத்திருங்கள்.',
    'Choose JPG, PNG or WebP photos.':'JPG, PNG அல்லது WebP படங்களைத் தேர்வு செய்யுங்கள்.',
    'Choose a photo smaller than 25 MB.':'25 MB-க்குக் குறைவான படத்தைத் தேர்வு செய்யுங்கள்.',
    'This photo is too large. Choose a smaller photo.':'இந்தப் படம் மிகவும் பெரியது. சிறிய படத்தைத் தேர்வு செய்யுங்கள்.',
    'Mic unavailable. You can type the product name.':'ஒலிவாங்கியைப் பயன்படுத்த முடியவில்லை. பொருளின் பெயரைத் தட்டச்சு செய்யுங்கள்.',
    'Speak product name':'பொருளின் பெயரைச் சொல்லுங்கள்', 'Product {number}':'பொருள் {number}',
    'Product {number}, image {image}':'பொருள் {number}, படம் {image}', 'Remove image {number}':'படம் {number}-ஐ நீக்கு',
    'Product name':'பொருளின் பெயர்', 'Price ₹':'விலை ₹', 'Discount % (optional)':'தள்ளுபடி % (விருப்பம்)',
    'Extra views ({number}/6)':'கூடுதல் படங்கள் ({number}/6)', 'Maximum 6 images for one product.':'ஒரு பொருளுக்கு அதிகபட்சம் 6 படங்கள் மட்டும்.',
    'Remove product':'பொருளை நீக்கு', '✓ View product':'✓ வெளியிட்ட பொருளைப் பார்', 'Uploading…':'பதிவேற்றுகிறது…',
    'Choose up to 20 products per batch. Clear completed drafts to start another batch.':'ஒரு முறையில் 20 பொருட்கள் வரை தேர்வு செய்யுங்கள். அடுத்த தொகுப்பைச் சேர்க்க முடிந்த வரைவை நீக்குங்கள்.',
    'Photos ready. Enter a name and price below.':'படங்கள் தயார். கீழே பெயர் மற்றும் விலை கொடுங்கள்.',
    'Only {number} product slots remain. Remove extra drafts or request more slots.':'இன்னும் {number} பொருட்களை மட்டுமே சேர்க்கலாம். கூடுதல் வரைவுகளை நீக்குங்கள் அல்லது மேலும் அனுமதி கேளுங்கள்.',
    '{number}% off':'{number}% தள்ளுபடி',
    'Clear the draft photos and details on this device? Published products will remain in your shop.':'இந்தக் கருவியில் உள்ள வரைவு படங்களையும் விவரங்களையும் நீக்க வேண்டுமா? வெளியிட்ட பொருட்கள் உங்கள் கடையில் இருக்கும்.',
    'Draft cleared. You can choose more photos.':'வரைவு நீக்கப்பட்டது. மேலும் படங்களைத் தேர்வு செய்யலாம்.',
    'Uploading {number} / {total}… Keep this page open.':'{number} / {total} பதிவேற்றுகிறது… இந்தப் பக்கத்தைத் திறந்து வைத்திருங்கள்.',
    'Session expired or upload interrupted. Check My products, sign in again, then return to this draft.':'உள்நுழைவு காலாவதியானது அல்லது பதிவேற்றம் தடைபட்டது. என் பொருட்கள் பக்கத்தைச் சரிபார்த்து, மீண்டும் உள்நுழைந்து இந்த வரைவைத் திறக்கவும்.',
    'Upload failed. Check My products before retrying.':'பதிவேற்ற முடியவில்லை. மீண்டும் முயலும் முன் என் பொருட்கள் பக்கத்தைச் சரிபாருங்கள்.',
    'Check the product details.':'பொருளின் பெயர், விலை, தள்ளுபடி மற்றும் படங்களைச் சரிபாருங்கள்.',
    'Your shop has no product slots left. Ask Superadmin for more.':'உங்கள் கடையின் பொருட்களுக்கான அனுமதி முடிந்தது. மேலும் அனுமதி பெற நிர்வாகியைத் தொடர்பு கொள்ளுங்கள்.',
    'This product may already be publishing. Check My products before trying again.':'இந்தப் பொருள் ஏற்கெனவே பதிவேற்றப்பட்டிருக்கலாம். மீண்டும் முயலும் முன் என் பொருட்கள் பக்கத்தைச் சரிபாருங்கள்.',
    'Reload this page before publishing.':'வெளியிடும் முன் இந்தப் பக்கத்தை மீண்டும் திறக்கவும்.',
    '✓ {number} products published. Clear this draft to add the next batch.':'✓ {number} பொருட்கள் வெளியிடப்பட்டன. அடுத்த தொகுப்பைச் சேர்க்க இந்த வரைவை நீக்குங்கள்.',
    'Enter a product name.':'பொருளின் பெயரை உள்ளிடுங்கள்.', 'Enter a valid price greater than zero.':'பூஜ்ஜியத்தைவிட அதிகமான சரியான விலையை உள்ளிடுங்கள்.',
    'Enter a whole discount percentage from 0 to 100.':'0 முதல் 100 வரை முழு எண்ணில் தள்ளுபடி சதவீதத்தை உள்ளிடுங்கள்.',
    'Need more product slots?':'மேலும் பொருட்கள் சேர்க்க வேண்டுமா?',
    'Your first 10 products are free. Your current product slots are full.':'முதல் 10 பொருட்கள் இலவசம். உங்களுக்கான பொருட்கள் சேர்க்கும் அனுமதி முடிந்தது.',
    'Call an admin for more product slots.':'மேலும் பொருட்கள் சேர்க்க நிர்வாகியை அழையுங்கள்.',
    'Admin · 7305675201':'நிர்வாகி · 7305675201', 'Admin · 9361240355':'நிர்வாகி · 9361240355', '☎ Call':'☎ அழைக்கவும்',
    'Send a request':'கோரிக்கை அனுப்பு', 'Admin approval is required to increase your allowance.':'மேலும் பொருட்கள் சேர்க்க நிர்வாகியின் அனுமதி தேவை.',
    'Close':'மூடு', 'Shops':'கடைகள்', 'Offers':'சலுகைகள்', 'Home':'முகப்பு', 'Products':'பொருட்கள்', 'Account':'என் கணக்கு',
    'My account':'என் கணக்கு', 'Search products or shops':'பொருட்கள் அல்லது கடைகளைத் தேடு', 'Skip to content':'உள்ளடக்கத்திற்குச் செல்',
    'Good things, closer to home.':'நல்லவை உங்கள் அருகிலேயே.', 'Starting in Vandavasi':'வந்தவாசியில் தொடங்குகிறோம்',
    'Explore Local From':'Local From-ஐ அறியுங்கள்', 'About us':'எங்களைப் பற்றி', 'Messages':'செய்திகள்',
    'Privacy policy':'தனியுரிமைக் கொள்கை', 'Terms & conditions':'விதிமுறைகள்', 'Contact Local From':'Local From-ஐ தொடர்புகொள்ள',
    'Superadmin login':'முதன்மை நிர்வாகி உள்நுழைவு', 'Mobile navigation':'கைபேசி வழிசெலுத்தல்', 'Footer navigation':'அடிப்பகுதி வழிசெலுத்தல்',
    'Notifications':'அறிவிப்புகள்', 'Recent notifications':'சமீபத்திய அறிவிப்புகள்', 'Close notifications':'அறிவிப்புகளை மூடு',
    'YOUR LOCAL UPDATES':'உங்கள் உள்ளூர் தகவல்கள்', 'Mark all as read':'அனைத்தையும் படித்ததாகக் குறி', 'Loading your updates…':'தகவல்கள் ஏற்றப்படுகின்றன…',
    'View all notifications →':'அனைத்து அறிவிப்புகளையும் பார் →',
  };
  let language = 'en';
  try { if (localStorage.getItem('localfrom-product-language') === 'ta') language = 'ta'; } catch (_) {}
  const originals = new WeakMap();
  const selector = document.querySelector('[data-product-language]');
  function t(key, params = {}) {
    const value = language === 'ta' ? (tamil[key] || key) : key;
    return value.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
  }
  function apply() {
    document.documentElement.lang = language;
    document.title = `${t('Add products')} | ${document.querySelector('.easy-intro .eyebrow').textContent}`;
    document.querySelectorAll('[data-product-text]').forEach(element => { element.textContent = t(element.dataset.productText); });
    document.querySelectorAll('.easy-products, .site-header, .market-mobile-nav, .local-footer, .skip-link, #product-limit-dialog').forEach(scope => {
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const text = walker.currentNode;
        if (text.parentElement.closest('.brand, .local-footer-brand a, .easy-cards, [data-review-list], select, .eyebrow, [data-feedback], [data-draft-status]')) continue;
        if (!originals.has(text)) originals.set(text, text.textContent);
        const source = originals.get(text), key = source.trim();
        if (tamil[key]) text.textContent = source.replace(key, t(key));
      }
    });
    document.querySelectorAll('[aria-label], [placeholder], [title]').forEach(element => {
      ['aria-label', 'placeholder', 'title'].forEach(attribute => {
        if (!element.hasAttribute(attribute)) return;
        const marker = `productOriginal${attribute.replace('-', '')}`;
        if (!element.dataset[marker]) element.dataset[marker] = element.getAttribute(attribute);
        const key = element.dataset[marker];
        if (tamil[key]) element.setAttribute(attribute, t(key));
      });
    });
    selector.value = language;
  }
  window.LocalfromProductLanguage = {t, apply, get language() { return language; },
    error(message) { return language === 'ta' && !tamil[message] ? t('Check the product details.') : t(message); }};
  selector.addEventListener('change', () => {
    language = selector.value === 'ta' ? 'ta' : 'en';
    try { localStorage.setItem('localfrom-product-language', language); } catch (_) {}
    apply(); document.dispatchEvent(new Event('product-language-change'));
  });
  apply();
})();
