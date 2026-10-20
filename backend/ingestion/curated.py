"""Hand-written chunks that are added to some pages when they are chunked.

Why: the contact page is a long table with one block per department, so a question such as
"what is the customer service phone number?" matches no single block well. This short summary matches it.
Rule: write ONLY facts that are on that page of fnx.co.il (checked against the live page). If the page changes,
update the text here and run the ingestion again.
"""

CONTACT_SUMMARY = """## סיכום: איך יוצרים קשר עם שירות הלקוחות של הפניקס
מספר הטלפון של מוקד שירות הלקוחות: *3455
וואטסאפ עם נציג שירות: 054-9893455
שעות הפעילות של שירות הלקוחות: ימים א'-ה', 8:30-16:00
הזמנת שיחה עם נציג אפשרית באתר, בעמוד "הזמנת שיחה".

מספרי טלפון לפי תחום:
- בריאות, סיעוד, שיניים, ביטוח חיים ומנהלים, חיות מחמד, פנסיה וגמל: *3455
- ביטוח רכב וביטוח דירה: *5432
- ביטוח נסיעות לחו"ל: 03-7141000
- תביעות רכב ורכוש: *5070 או 074-7311147
- מוקד חירום לשוהים בחו"ל: 074-7897016, וואטסאפ 050-224-1953, פעיל 24 שעות ביממה, 7 ימים בשבוע

בהמשך הדף מופיעים פרטי המוקד של כל תחום: כתובות דוא"ל, וואטסאפ ושעות פעילות."""

# page url -> pieces added at the START of the page (so they get chunk index 0).
# The same contact page exists under three addresses on the site.
CURATED_CHUNKS = {
    "https://www.fnx.co.il/customer-service/contact-us/": [CONTACT_SUMMARY],
    "https://www.fnx.co.il/customer-service/contact-us/be-in-touch/": [CONTACT_SUMMARY],
    "https://www.fnx.co.il/claims-customer-service/be-in-touch/": [CONTACT_SUMMARY],
}
