/* Explicit translations for this screen. Shop and product data stay unchanged. */
(() => {
  'use strict';
  if (window.LocalfromProductLanguage || !document.querySelector('[data-easy-products], [data-home-language], [data-owner-language]')) return;
  const home = document.querySelector('[data-home-language]');
  const easy = document.querySelector('[data-easy-products]');
  const originalTitle = document.title;
  const tamil = {
    'Share shop & QR code':'கடையைப் பகிர் & QR குறியீடு',
    'Share your shop':'உங்கள் கடையைப் பகிருங்கள்',
    'Share shop':'கடையைப் பகிர்',
    'Share on WhatsApp':'WhatsApp-ல் பகிர்',
    'Your shop link':'உங்கள் கடையின் இணைப்பு',
    'Copy link':'இணைப்பை நகலெடு',
    'Download QR code':'QR குறியீட்டைப் பதிவிறக்கு',
    'Shop link copied.':'கடை இணைப்பு நகலெடுக்கப்பட்டது.',
    'Select and copy your shop link.':'உங்கள் கடை இணைப்பைத் தேர்ந்தெடுத்து நகலெடுக்கவும்.',
    'Scan to open this shop on Local From.':'Local From-ல் இந்தக் கடையைத் திறக்க ஸ்கேன் செய்யுங்கள்.',
    'Send your shop link to customers or print this QR code for your counter.':'கடை இணைப்பை வாடிக்கையாளர்களுக்கு அனுப்புங்கள் அல்லது இந்த QR குறியீட்டை அச்சிட்டுக் கடையில் வையுங்கள்.',
    'Use WhatsApp or copy the shop link below.':'WhatsApp-ல் பகிருங்கள் அல்லது கீழே உள்ள கடை இணைப்பை நகலெடுங்கள்.',
    'Offer published. Customers can see it now.':'சலுகை வெளியிடப்பட்டது. வாடிக்கையாளர்கள் இப்போது பார்க்கலாம்.',
    'Offers appear immediately after you publish.':'வெளியிட்டவுடன் சலுகைகள் வாடிக்கையாளர்களுக்குத் தெரியும்.',
    'Share a shop offer. It appears publicly as soon as you publish.':'கடைச் சலுகையைப் பகிருங்கள். வெளியிட்டவுடன் அனைவருக்கும் தெரியும்.',
    'Publish offer':'சலுகையை வெளியிடு',
    'Forgot your password?':'கடவுச்சொல் மறந்துவிட்டதா?',
    'Contact Local From support for help getting back into your account.':'உங்கள் கணக்கை மீட்க Local From உதவிக் குழுவைத் தொடர்புகொள்ளுங்கள்.',
    'Contact admin on WhatsApp':'WhatsApp மூலம் நிர்வாகியைத் தொடர்புகொள்ளுங்கள்',
    'The admin will verify account ownership before helping you reset your password.':'கடவுச்சொல்லை மாற்ற உதவுவதற்கு முன் கணக்கு உங்களுடையதா என்பதை நிர்வாகி சரிபார்ப்பார்.',
    'Admin WhatsApp:':'நிர்வாகியின் WhatsApp:',
    'Do not share your password or OTP on WhatsApp.':'உங்கள் கடவுச்சொல் அல்லது OTP-ஐ WhatsApp-ல் பகிர வேண்டாம்.',
    'Crop / adjust':'படத்தை வெட்டு / சரிசெய்',
    'Product views':'பொருட்களைப் பார்த்தவர்கள்',
    'Product photo unavailable':'பொருளின் படம் இல்லை',
    'Total opens':'மொத்த பார்வைகள்',
    'Members':'உறுப்பினர்கள்',
    'My shop dashboard':'என் கடை முகப்பு',
    'No products yet.':'இன்னும் பொருட்கள் இல்லை.',

    'Your product has been added to LOCALFROM.':'உங்கள் பொருள் LOCALFROM-இல் சேர்க்கப்பட்டது.',
    '{number} products have been added to LOCALFROM.':'{number} பொருட்கள் LOCALFROM-இல் சேர்க்கப்பட்டன.',
    'Edit this product':'இந்தப் பொருளைத் திருத்து', 'Manage products / delete':'பொருட்களை நிர்வகி / நீக்கு',
    'Open LOCALFROM using HTTPS to use the microphone.':'மைக் பயன்படுத்த LOCALFROM-ஐ HTTPS முகவரியில் திறக்கவும்.',
    'Voice entry is not supported here. Use the microphone on your phone keyboard, or type the name.':'இந்த உலாவியில் குரல் உள்ளீடு இல்லை. உங்கள் போன் கீபோர்டு மைக்கைப் பயன்படுத்தவும் அல்லது பெயரைத் தட்டச்சு செய்யவும்.',
    'Listening. Say the product name clearly.':'கேட்கிறது. பொருளின் பெயரைத் தெளிவாகச் சொல்லுங்கள்.',
    'Product name entered. Check it before publishing.':'பொருளின் பெயர் சேர்க்கப்பட்டது. வெளியிடுவதற்கு முன் சரிபார்க்கவும்.',
    'Allow microphone access for this site in Chrome settings, then try again. You can also use your keyboard microphone.':'Chrome அமைப்பில் இந்தத் தளத்திற்கு மைக் அனுமதி கொடுத்து மீண்டும் முயற்சிக்கவும். கீபோர்டு மைக்கையும் பயன்படுத்தலாம்.',
    'Chrome voice recognition is unavailable. Use your keyboard microphone or type the name.':'Chrome குரல் உள்ளீடு கிடைக்கவில்லை. கீபோர்டு மைக்கைப் பயன்படுத்தவும் அல்லது பெயரைத் தட்டச்சு செய்யவும்.',
    'No microphone is available. Check your phone microphone permissions, or use keyboard typing.':'மைக் கிடைக்கவில்லை. போனில் மைக் அனுமதியைச் சரிபார்க்கவும் அல்லது தட்டச்சு செய்யவும்.',
    'Voice recognition needs an internet connection. Check your connection, or use your keyboard microphone.':'குரல் உள்ளீட்டிற்கு இணையம் தேவை. இணையத்தைச் சரிபார்க்கவும் அல்லது கீபோர்டு மைக்கைப் பயன்படுத்தவும்.',
    'No speech was heard. Tap the microphone and speak again.':'குரல் கேட்கவில்லை. மைக்கைத் தொட்டு மீண்டும் பேசுங்கள்.',
    'This speech language is unavailable. Try the other page language or your keyboard microphone.':'இந்த மொழியில் குரல் உள்ளீடு கிடைக்கவில்லை. வேறு மொழியைத் தேர்வு செய்யவும் அல்லது கீபோர்டு மைக்கைப் பயன்படுத்தவும்.',
    'Voice entry stopped. Try again or use your keyboard microphone.':'குரல் உள்ளீடு நின்றுவிட்டது. மீண்டும் முயற்சிக்கவும் அல்லது கீபோர்டு மைக்கைப் பயன்படுத்தவும்.',
    'Voice entry could not start. Try again or use your keyboard microphone.':'குரல் உள்ளீட்டைத் தொடங்க முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது கீபோர்டு மைக்கைப் பயன்படுத்தவும்.',
    'Language':'மொழி', 'Page language':'பக்கத்தின் மொழி', 'Add products':'பொருட்களைச் சேர்',
    'My products':'என் பொருட்கள்', 'Add photos. Enter a name & price. Publish.':'படங்களைத் தேர்வு செய்து, பெயர் மற்றும் விலை கொடுத்து வெளியிடுங்கள்.',
    'Photo':'படம்', 'Name and price':'பெயர் மற்றும் விலை', 'Publish':'வெளியிடு',
    'product slots available.':'பொருட்களைச் சேர்க்கலாம்.', 'Request more':'மேலும் அனுமதி கேட்க', 'Choose photos':'படங்களைத் தேர்வு செய்',
    'Each photo starts a separate product. Up to 20 products per batch. Add extra views inside its card.':'ஒவ்வொரு படமும் ஒரு தனிப் பொருள். ஒரு முறையில் 20 பொருட்கள் வரை சேர்க்கலாம். அதே பொருளின் கூடுதல் படங்களை அதன் கீழே சேர்க்கலாம்.',
    'Drafts stay in this browser on this device. Use one tab. Clear drafts on shared devices.':'வரைவுகள் இந்தக் கருவியின் உலாவியில் மட்டும் சேமிக்கப்படும். ஒரே தாவலைப் பயன்படுத்துங்கள். பகிர்ந்து பயன்படுத்தும் கருவியில் வரைவை நீக்குங்கள்.',
    'Review products':'பொருட்களைச் சரிபார்', 'Clear draft':'வரைவை நீக்கு', 'Ready to publish?':'வெளியிடத் தயாரா?',
    'These products will be visible in your shop. Published products stay in your catalog when you clear this draft.':'இந்தப் பொருட்கள் உங்கள் கடையில் தெரியும். வரைவை நீக்கினாலும் வெளியிட்ட பொருட்கள் கடையில் இருக்கும்.',
    'Publish products':'பொருட்களை வெளியிடு', 'Edit':'திருத்து', 'Full product form':'முழு விவரங்களுடன் சேர்க்க',
    'Need help?':'உதவி வேண்டுமா?', 'Call LOCALFROM: 9361240355':'LOCALFROM-ஐ அழைக்கவும்: 9361240355',
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
    'Extra views ({number}/2)':'கூடுதல் படங்கள் ({number}/2)', 'Maximum 2 images for one product.':'ஒரு பொருளுக்கு அதிகபட்சம் 2 படங்கள் மட்டும்.',
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
    'Enter a whole discount percentage from 0 to 100.':'0 முதல் 50 வரை முழு எண்ணில் தள்ளுபடி சதவீதத்தை உள்ளிடுங்கள்.',
    'Need more product slots?':'மேலும் பொருட்கள் சேர்க்க வேண்டுமா?',
    'Your first 20 products are free. Your current product slots are full.':'முதல் 20 பொருட்கள் இலவசம். உங்களுக்கான பொருட்கள் சேர்க்கும் அனுமதி முடிந்தது.',
    'Call an admin for more product slots.':'மேலும் பொருட்கள் சேர்க்க நிர்வாகியை அழையுங்கள்.',
'Admin · 9361240355':'நிர்வாகி · 9361240355', '☎ Call':'☎ அழைக்கவும்',
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
  Object.assign(tamil, {"1. Photo": "1. \u0baa\u0b9f\u0bae\u0bcd", "2. Details": "2. \u0bb5\u0bbf\u0bb5\u0bb0\u0bae\u0bcd", "3. Add to shop": "3. \u0b95\u0b9f\u0bc8\u0baf\u0bbf\u0bb2\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95", "Choose product photos": "\u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bbf\u0ba9\u0bcd \u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bc1\u0bae\u0bcd", "Each photo is a separate product.": "\u0b92\u0bb5\u0bcd\u0bb5\u0bca\u0bb0\u0bc1 \u0baa\u0b9f\u0bae\u0bc1\u0bae\u0bcd \u0b92\u0bb0\u0bc1 \u0ba4\u0ba9\u0bbf \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd.", "Price (optional)": "\u0bb5\u0bbf\u0bb2\u0bc8 (\u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bae\u0bcd)", "Selling price": "\u0bb5\u0bbf\u0bb1\u0bcd\u0baa\u0ba9\u0bc8 \u0bb5\u0bbf\u0bb2\u0bc8", "Ask shop for price": "\u0bb5\u0bbf\u0bb2\u0bc8\u0baf\u0bc8 \u0b95\u0b9f\u0bc8\u0baf\u0bbf\u0bb2\u0bcd \u0b95\u0bc7\u0b9f\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Price is optional. Leave it blank if you prefer.": "\u0bb5\u0bbf\u0bb2\u0bc8 \u0ba4\u0bc7\u0bb5\u0bc8\u0baf\u0bbf\u0bb2\u0bcd\u0bb2\u0bc8 \u0b8e\u0ba9\u0bcd\u0bb1\u0bbe\u0bb2\u0bcd \u0b95\u0bbe\u0bb2\u0bbf\u0baf\u0bbe\u0b95 \u0bb5\u0bbf\u0b9f\u0bb2\u0bbe\u0bae\u0bcd.", "Next product": "\u0b85\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4 \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd", "Product {number} of {total}": "\u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd {number} / {total}", "Check products": "\u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bc8 \u0b9a\u0bb0\u0bbf\u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Check your products": "\u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bc8 \u0b9a\u0bb0\u0bbf\u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Add to shop": "\u0b95\u0b9f\u0bc8\u0baf\u0bbf\u0bb2\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Go back": "\u0ba4\u0bbf\u0bb0\u0bc1\u0bae\u0bcd\u0baa \u0b9a\u0bc6\u0bb2\u0bcd\u0bb2\u0bb5\u0bc1\u0bae\u0bcd", "Back": "\u0baa\u0bbf\u0ba9\u0bcd\u0b9a\u0bc6\u0bb2\u0bcd", "More options": "\u0bae\u0bc7\u0bb2\u0bc1\u0bae\u0bcd", "Add more photos": "\u0bae\u0bc7\u0bb2\u0bc1\u0bae\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bbf\u0ba9\u0bcd \u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95", "Clear saved photos": "\u0b9a\u0bc7\u0bae\u0bbf\u0ba4\u0bcd\u0ba4 \u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0ba8\u0bc0\u0b95\u0bcd\u0b95", "Photos are saved on this phone. Clear them on shared phones.": "\u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b87\u0ba8\u0bcd\u0ba4 \u0baa\u0bcb\u0ba9\u0bbf\u0bb2\u0bcd \u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bc1\u0bae\u0bcd. \u0bae\u0bb1\u0bcd\u0bb1\u0bb5\u0bb0\u0bcd \u0baa\u0bcb\u0ba9\u0bcd \u0b8e\u0ba9\u0bcd\u0bb1\u0bbe\u0bb2\u0bcd \u0bae\u0bc1\u0b9f\u0bbf\u0ba8\u0bcd\u0ba4\u0ba4\u0bc1\u0bae\u0bcd \u0ba8\u0bc0\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.", "Customers can see these products after you add them.": "\u0b9a\u0bc7\u0bb0\u0bcd\u0ba4\u0bcd\u0ba4 \u0baa\u0bbf\u0ba9\u0bcd \u0bb5\u0bbe\u0b9f\u0bbf\u0b95\u0bcd\u0b95\u0bc8\u0baf\u0bbe\u0bb3\u0bb0\u0bcd\u0b95\u0bb3\u0bcd \u0b87\u0ba8\u0bcd\u0ba4 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bc8 \u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb2\u0bbe\u0bae\u0bcd.", "Photos ready. Enter a name below. Price is optional.": "\u0baa\u0b9f\u0bae\u0bcd \u0ba4\u0baf\u0bbe\u0bb0\u0bcd. \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bbf\u0ba9\u0bcd \u0baa\u0bc6\u0baf\u0bb0\u0bc8 \u0b95\u0bca\u0b9f\u0bc1\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd. \u0bb5\u0bbf\u0bb2\u0bc8 \u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bae\u0bcd.", "Add another photo ({number}/2)": "\u0b87\u0ba4\u0bc7 \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bbf\u0ba9\u0bcd \u0b87\u0ba9\u0bcd\u0ba9\u0bca\u0bb0\u0bc1 \u0baa\u0b9f\u0bae\u0bcd ({number}/2)"});
  Object.assign(tamil, {"My shop": "\u0b8e\u0ba9\u0bcd \u0b95\u0b9f\u0bc8", "Call for help": "\u0b89\u0ba4\u0bb5\u0bbf\u0b95\u0bcd\u0b95\u0bc1 \u0b85\u0bb4\u0bc8\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Add a product": "\u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Choose a photo": "\u0baa\u0b9f\u0ba4\u0bcd\u0ba4\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bc1\u0bae\u0bcd", "View my shop": "\u0b8e\u0ba9\u0bcd \u0b95\u0b9f\u0bc8\u0baf\u0bc8 \u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95", "Products": "\u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Photos": "\u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Videos": "\u0bb5\u0bc0\u0b9f\u0bbf\u0baf\u0bcb\u0b95\u0bcd\u0b95\u0bb3\u0bcd", "Shop details": "\u0b95\u0b9f\u0bc8 \u0bb5\u0bbf\u0bb5\u0bb0\u0bae\u0bcd", "Photo and name are enough. Price is optional.": "\u0baa\u0b9f\u0bae\u0bcd \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0baa\u0bc6\u0baf\u0bb0\u0bcd \u0baa\u0bcb\u0ba4\u0bc1\u0bae\u0bcd. \u0bb5\u0bbf\u0bb2\u0bc8 \u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bae\u0bcd.", "Add your first product": "\u0bae\u0bc1\u0ba4\u0bb2\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Choose a photo of your product.": "\u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bbf\u0ba9\u0bcd \u0baa\u0b9f\u0ba4\u0bcd\u0ba4\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bc1\u0bae\u0bcd.", "Offers appear after approval.": "\u0b9a\u0bb2\u0bc1\u0b95\u0bc8\u0b95\u0bb3\u0bcd \u0b85\u0ba9\u0bc1\u0bae\u0ba4\u0bbf \u0b95\u0bbf\u0b9f\u0bc8\u0ba4\u0bcd\u0ba4\u0baa\u0bbf\u0ba9\u0bcd \u0ba4\u0bc6\u0bb0\u0bbf\u0baf\u0bc1\u0bae\u0bcd.", "Shop or product video, up to 50 MB.": "\u0b95\u0b9f\u0bc8 \u0b85\u0bb2\u0bcd\u0bb2\u0ba4\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bbf\u0ba9\u0bcd \u0bb5\u0bc0\u0b9f\u0bbf\u0baf\u0bcb. \u0b85\u0ba4\u0bbf\u0b95\u0baa\u0b9f\u0bcd\u0b9a\u0bae\u0bcd 50 MB.", "Save details": "\u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0b9a\u0bc7\u0bae\u0bbf\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Edit": "\u0ba4\u0bbf\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4", "Delete": "\u0ba8\u0bc0\u0b95\u0bcd\u0b95", "Add your shop": "\u0b95\u0b9f\u0bc8\u0baf\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Enter your shop name, category and area.": "\u0b95\u0b9f\u0bc8 \u0baa\u0bc6\u0baf\u0bb0\u0bcd, \u0bb5\u0b95\u0bc8, \u0b8a\u0bb0\u0bcd \u0bae\u0b9f\u0bcd\u0b9f\u0bc1\u0bae\u0bcd \u0b95\u0bca\u0b9f\u0bc1\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd.", "Find a listed shop": "\u0baa\u0b9f\u0bcd\u0b9f\u0bbf\u0baf\u0bb2\u0bbf\u0bb2\u0bcd \u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b95\u0b9f\u0bc8\u0baf\u0bc8 \u0ba4\u0bc7\u0b9f\u0bb5\u0bc1\u0bae\u0bcd", "Optional details": "\u0bae\u0bc7\u0bb2\u0bc1\u0bae\u0bcd \u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Create my shop": "\u0b95\u0b9f\u0bc8\u0baf\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Shop name": "\u0b95\u0b9f\u0bc8 \u0baa\u0bc6\u0baf\u0bb0\u0bcd", "Shop categories": "\u0b95\u0b9f\u0bc8 \u0bb5\u0b95\u0bc8\u0b95\u0bb3\u0bcd", "Pincode": "\u0b85\u0b9e\u0bcd\u0b9a\u0bb2\u0bcd \u0b95\u0bc1\u0bb1\u0bbf\u0baf\u0bc0\u0b9f\u0bc1", "Town or village": "\u0b8a\u0bb0\u0bcd", "Add your own category": "\u0baa\u0bc1\u0ba4\u0bbf\u0baf \u0b95\u0b9f\u0bc8 \u0bb5\u0b95\u0bc8", "Add tag": "\u0bb5\u0b95\u0bc8\u0baf\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95", "Shop photos": "\u0b95\u0b9f\u0bc8 \u0baa\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Shop videos": "\u0b95\u0b9f\u0bc8 \u0bb5\u0bc0\u0b9f\u0bbf\u0baf\u0bcb\u0b95\u0bcd\u0b95\u0bb3\u0bcd", "Personal details": "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Business details": "\u0b95\u0b9f\u0bc8 \u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Location & preferred areas": "\u0b8a\u0bb0\u0bcd \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa \u0baa\u0b95\u0bc1\u0ba4\u0bbf\u0b95\u0bb3\u0bcd", "Request more products": "\u0bae\u0bc7\u0bb2\u0bc1\u0bae\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95 \u0b85\u0ba9\u0bc1\u0bae\u0ba4\u0bbf \u0b95\u0bc7\u0b9f\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", "Back to home \u2197": "\u0bae\u0bc1\u0b95\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bcd\u0b95\u0bc1 \u0b9a\u0bc6\u0bb2\u0bcd\u0bb2\u0bb5\u0bc1\u0bae\u0bcd \u2197", "Choose up to 5 categories or add your own. Food categories also appear on the Food page.": "5 \u0b95\u0b9f\u0bc8 \u0bb5\u0b95\u0bc8\u0b95\u0bb3\u0bcd \u0bb5\u0bb0\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb2\u0bbe\u0bae\u0bcd. \u0baa\u0bc1\u0ba4\u0bbf\u0baf \u0bb5\u0b95\u0bc8\u0baf\u0bc8\u0baf\u0bc1\u0bae\u0bcd \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb2\u0bbe\u0bae\u0bcd."});
  Object.assign(tamil, {"Shop address (optional)": "\u0b95\u0b9f\u0bc8 \u0bae\u0bc1\u0b95\u0bb5\u0bb0\u0bbf (\u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bae\u0bcd)", "Account type": "\u0b95\u0ba3\u0b95\u0bcd\u0b95\u0bc1 \u0bb5\u0b95\u0bc8", "Logo and banner (optional)": "\u0bb2\u0bcb\u0b95\u0bcb \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0baa\u0bc7\u0ba9\u0bb0\u0bcd (\u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa\u0bae\u0bcd)", "You can edit these details later.": "\u0b87\u0ba8\u0bcd\u0ba4 \u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0baa\u0bbf\u0ba9\u0bcd\u0ba9\u0bb0\u0bcd \u0ba4\u0bbf\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bb2\u0bbe\u0bae\u0bcd.", "Edit shop details": "\u0b95\u0b9f\u0bc8 \u0bb5\u0bbf\u0bb5\u0bb0\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0ba4\u0bbf\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bb5\u0bc1\u0bae\u0bcd"});
  Object.assign(tamil, {"Choose a category": "\u0b95\u0b9f\u0bc8 \u0bb5\u0b95\u0bc8\u0baf\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb5\u0bc1\u0bae\u0bcd", "Add another category": "\u0baa\u0bc1\u0ba4\u0bbf\u0baf \u0b95\u0b9f\u0bc8 \u0bb5\u0b95\u0bc8\u0baf\u0bc8 \u0b9a\u0bc7\u0bb0\u0bcd\u0b95\u0bcd\u0b95", "{number} of 5 categories selected": "{number} / 5 \u0bb5\u0b95\u0bc8\u0b95\u0bb3\u0bcd \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1", "Choose up to 5 categories, within 100 characters in total.": "5 \u0bb5\u0b95\u0bc8\u0b95\u0bb3\u0bcd \u0bb5\u0bb0\u0bc8 \u0ba4\u0bc7\u0bb0\u0bcd\u0bb5\u0bc1 \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb2\u0bbe\u0bae\u0bcd. \u0bae\u0bca\u0ba4\u0bcd\u0ba4\u0bae\u0bcd 100 \u0b8e\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1\u0b95\u0bb3\u0bc1\u0b95\u0bcd\u0b95\u0bc1\u0bb3\u0bcd \u0b87\u0bb0\u0bc1\u0b95\u0bcd\u0b95 \u0bb5\u0bc7\u0ba3\u0bcd\u0b9f\u0bc1\u0bae\u0bcd.", "Remove {name}": "{name} \u0ba8\u0bc0\u0b95\u0bcd\u0b95", "Food": "\u0b89\u0ba3\u0bb5\u0bc1", "Restaurant": "\u0b89\u0ba3\u0bb5\u0b95\u0bae\u0bcd", "Bakery": "\u0baa\u0bc7\u0b95\u0bcd\u0b95\u0bb0\u0bbf", "Cafe": "\u0b95\u0b83\u0baa\u0bc7", "Tea shop": "\u0ba4\u0bc7\u0ba8\u0bc0\u0bb0\u0bcd \u0b95\u0b9f\u0bc8", "Sweets & Snacks": "\u0b87\u0ba9\u0bbf\u0baa\u0bcd\u0baa\u0bc1 \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0ba4\u0bbf\u0ba9\u0bcd\u0baa\u0ba3\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Catering": "\u0b9a\u0bae\u0bc8\u0baf\u0bb2\u0bcd \u0b9a\u0bc7\u0bb5\u0bc8", "Groceries": "\u0bae\u0bb3\u0bbf\u0b95\u0bc8", "Supermarket": "\u0baa\u0bb2\u0bcd\u0baa\u0bca\u0bb0\u0bc1\u0bb3\u0bcd \u0b85\u0b99\u0bcd\u0b95\u0bbe\u0b9f\u0bbf", "Vegetables": "\u0b95\u0bbe\u0baf\u0bcd\u0b95\u0bb1\u0bbf\u0b95\u0bb3\u0bcd", "Fruits": "\u0baa\u0bb4\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Meat & Fish": "\u0b87\u0bb1\u0bc8\u0b9a\u0bcd\u0b9a\u0bbf \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0bae\u0bc0\u0ba9\u0bcd", "Milk & Dairy": "\u0baa\u0bbe\u0bb2\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Clothing": "\u0b86\u0b9f\u0bc8\u0b95\u0bb3\u0bcd", "Menswear": "\u0b86\u0ba3\u0bcd\u0b95\u0bb3\u0bcd \u0b86\u0b9f\u0bc8\u0b95\u0bb3\u0bcd", "Womenswear": "\u0baa\u0bc6\u0ba3\u0bcd\u0b95\u0bb3\u0bcd \u0b86\u0b9f\u0bc8\u0b95\u0bb3\u0bcd", "Kidswear": "\u0b95\u0bc1\u0bb4\u0ba8\u0bcd\u0ba4\u0bc8\u0b95\u0bb3\u0bcd \u0b86\u0b9f\u0bc8\u0b95\u0bb3\u0bcd", "Sarees": "\u0baa\u0bc1\u0b9f\u0bb5\u0bc8\u0b95\u0bb3\u0bcd", "Tailoring": "\u0ba4\u0bc8\u0baf\u0bb2\u0bcd", "Footwear": "\u0b95\u0bbe\u0bb2\u0ba3\u0bbf\u0b95\u0bb3\u0bcd", "Bags": "\u0baa\u0bc8\u0b95\u0bb3\u0bcd", "Jewellery": "\u0ba8\u0b95\u0bc8\u0b95\u0bb3\u0bcd", "Cosmetics": "\u0b85\u0bb4\u0b95\u0bc1 \u0b9a\u0bbe\u0ba4\u0ba9\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Beauty salon": "\u0b85\u0bb4\u0b95\u0bc1 \u0ba8\u0bbf\u0bb2\u0bc8\u0baf\u0bae\u0bcd", "Electronics": "\u0bae\u0bbf\u0ba9\u0bcd\u0ba9\u0ba3\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Appliance": "\u0bb5\u0bc0\u0b9f\u0bcd\u0b9f\u0bc1 \u0b89\u0baa\u0baf\u0bcb\u0b95 \u0b9a\u0bbe\u0ba4\u0ba9\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Mobiles": "\u0b95\u0bc8\u0baa\u0bcd\u0baa\u0bc7\u0b9a\u0bbf\u0b95\u0bb3\u0bcd", "Mobile accessories": "\u0b95\u0bc8\u0baa\u0bcd\u0baa\u0bc7\u0b9a\u0bbf \u0b89\u0ba4\u0bbf\u0bb0\u0bbf \u0baa\u0bbe\u0b95\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Computer store": "\u0b95\u0ba3\u0bbf\u0ba9\u0bbf \u0b95\u0b9f\u0bc8", "Furniture": "\u0bae\u0bb0\u0b9a\u0bcd\u0b9a\u0bbe\u0bae\u0bbe\u0ba9\u0bcd\u0b95\u0bb3\u0bcd", "Home essentials": "\u0bb5\u0bc0\u0b9f\u0bcd\u0b9f\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Kitchenware": "\u0b9a\u0bae\u0bc8\u0baf\u0bb2\u0bb1\u0bc8 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Electrical": "\u0bae\u0bbf\u0ba9\u0bcd\u0b9a\u0bbe\u0bb0 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Hardware": "\u0b87\u0bb0\u0bc1\u0bae\u0bcd\u0baa\u0bc1 \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd \u0b95\u0bb0\u0bc1\u0bb5\u0bbf\u0b95\u0bb3\u0bcd", "Plumbing": "\u0b95\u0bc1\u0bb4\u0bbe\u0baf\u0bcd \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Paints": "\u0baa\u0bc6\u0baf\u0bbf\u0ba3\u0bcd\u0b9f\u0bcd", "Building materials": "\u0b95\u0b9f\u0bcd\u0b9f\u0bc1\u0bae\u0bbe\u0ba9 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Stationery": "\u0b8e\u0bb4\u0bc1\u0ba4\u0bc1\u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Books": "\u0baa\u0bc1\u0ba4\u0bcd\u0ba4\u0b95\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Toys": "\u0baa\u0bca\u0bae\u0bcd\u0bae\u0bc8\u0b95\u0bb3\u0bcd", "Gifts": "\u0baa\u0bb0\u0bbf\u0b9a\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Sports goods": "\u0bb5\u0bbf\u0bb3\u0bc8\u0baf\u0bbe\u0b9f\u0bcd\u0b9f\u0bc1 \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Watch shop": "\u0b95\u0b9f\u0bbf\u0b95\u0bbe\u0bb0 \u0b95\u0b9f\u0bc8", "Optical shop": "\u0b95\u0ba3\u0bcd\u0ba3\u0bbe\u0b9f\u0bbf \u0b95\u0b9f\u0bc8", "Medical store": "\u0bae\u0bb0\u0bc1\u0ba8\u0bcd\u0ba4\u0b95\u0bae\u0bcd", "Auto parts": "\u0bb5\u0bbe\u0b95\u0ba9 \u0b89\u0ba4\u0bbf\u0bb0\u0bbf \u0baa\u0bbe\u0b95\u0b99\u0bcd\u0b95\u0bb3\u0bcd", "Vehicle service": "\u0bb5\u0bbe\u0b95\u0ba9 \u0baa\u0bb4\u0bc1\u0ba4\u0bc1 \u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bc1\u0bae\u0bcd \u0b9a\u0bc7\u0bb5\u0bc8", "Pet shop": "\u0b9a\u0bc6\u0bb2\u0bcd\u0bb2\u0baa\u0bcd\u0baa\u0bbf\u0bb0\u0bbe\u0ba3\u0bbf \u0b95\u0b9f\u0bc8", "Laundry": "\u0b9a\u0bb2\u0bb5\u0bc8", "Printing": "\u0b85\u0b9a\u0bcd\u0b9a\u0b95\u0bae\u0bcd", "Photography": "\u0baa\u0bc1\u0b95\u0bc8\u0baa\u0bcd\u0baa\u0b9f\u0bae\u0bcd", "Agriculture": "\u0bb5\u0bbf\u0bb5\u0b9a\u0bbe\u0baf \u0baa\u0bca\u0bb0\u0bc1\u0b9f\u0bcd\u0b95\u0bb3\u0bcd", "Other": "\u0bae\u0bb1\u0bcd\u0bb1\u0bb5\u0bc8"});
  Object.assign(tamil, window.LocalfromHomeTranslations || {});
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
    document.title = home ? (language === 'ta' ? 'Local From | வந்தவாசி' : originalTitle) : easy ? `${t('Add products')} | ${document.querySelector('.easy-intro .eyebrow').textContent}` : originalTitle;
    document.querySelectorAll('[data-product-text]').forEach(element => { element.textContent = t(element.dataset.productText); });
    document.querySelectorAll('.easy-products, [data-home-language-scope], [data-owner-language-scope], .auth-header, .site-header, .market-mobile-nav, .local-footer, .skip-link, #product-limit-dialog, #guest-account-dialog').forEach(scope => {
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const text = walker.currentNode;
        if (text.parentElement.closest('[data-product-content], .brand, .auth-brand, .owner-heading h1, .social-profile h1, .social-profile-bio, .social-shop-body h2, .social-shop-bio, .product-detail-copy h1, .product-seller strong, .product-description, .shop-gallery figcaption, .category-selected, .category-suggestions, .shop-category-tags, .dashboard-product h3, .dashboard-offer h3, .shop-video-grid h3, .shop-video-grid p, .owner-account-note, .local-footer-brand a, .easy-cards, [data-review-list], select, .easy-intro .eyebrow, [data-feedback], [data-draft-status], .business-card, .notices, script, style')) continue;
        if (text.parentElement.closest('.product-card, .spotlight-card') && !text.parentElement.closest('.product-shop-link, .product-prices, .discount-badge, .sponsor-label, .spotlight-card .text-link')) continue;
        if (!originals.has(text)) originals.set(text, text.textContent);
        const source = originals.get(text), key = source.trim();
        if (tamil[key]) text.textContent = source.replace(key, t(key));
        else if (key.endsWith(':') && tamil[key.slice(0, -1)]) text.textContent = source.replace(key, t(key.slice(0, -1)) + ':');
        else if (text.parentElement.closest('.discount-badge') && /^\d+% off$/.test(key)) text.textContent = source.replace(key, t('{number}% off', {number: key.split('%')[0]}));
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
    document.querySelectorAll('[data-product-language]').forEach(control => { control.value = language; });
    const greeting = home && document.querySelector('.home-greeting h2');
    if (greeting) {
      if (!greeting.dataset.originalGreeting) greeting.dataset.originalGreeting = greeting.textContent;
      greeting.textContent = language === 'ta' ? greeting.dataset.originalGreeting.replace(/^Hello, neighbour$/, 'வணக்கம்').replace(/^Hello,/, 'வணக்கம்,') : greeting.dataset.originalGreeting;
    }
  }
  window.LocalfromProductLanguage = {t, apply, get language() { return language; },
    error(message) { return language === 'ta' && !tamil[message] ? t('Check the product details.') : t(message); }};
  document.querySelectorAll('[data-product-language]').forEach(control => control.addEventListener('change', () => {
    language = control.value === 'ta' ? 'ta' : 'en';
    try { localStorage.setItem('localfrom-product-language', language); } catch (_) {}
    apply(); document.dispatchEvent(new Event('product-language-change'));
  }));
  apply();
})();
