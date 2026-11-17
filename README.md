<div dir="rtl">

# קרנות איריות בתל אביב: סקילים ל-Claude

שישה סקילים בעברית להשקעה פסיבית לטווח ארוך בקרנות איריות צוברות שנסחרות בבורסה בתל אביב. 43 קרנות של iShares ו-Invesco, מניות ואגח. חינם, קוד פתוח, בלי הרשמה ובלי התקנות.

**למחקר וללימוד בלבד. זה לא ייעוץ השקעות.** הפירוט בקובץ [DISCLAIMER.md](DISCLAIMER.md).

## לא מתכנתים? מתחילים כאן
פותחים בדפדפן, מהטלפון או מהמחשב:

1. [בונה התיק](https://yontanbe.github.io/irish-funds-il-skills/tik.html): שבע שאלות ותיק לדוגמה.
2. [טבלת הקרנות](https://yontanbe.github.io/irish-funds-il-skills/kranot.html): 43 קרנות עם מספרי נייר, דמי ניהול וסוג עקיבה.
3. [מחשבון דמי ניהול](https://yontanbe.github.io/irish-funds-il-skills/dmei-nihul.html): כמה דמי הניהול אוכלים ב-20 שנה.

הכל רץ אצלכם בדפדפן. שום נתון לא נשלח לשום מקום.

## מה יש בפנים
| סקיל | מה הוא עושה |
|---|---|
| `irish-funds-basics` | מסביר מה זה קרן אירית ומה זה השקעה במדדים לטווח ארוך |
| `irish-funds-finder` | עוזר למצוא קרנות ולהבדיל ביניהן |
| `portfolio-builder` | שואל שבע שאלות ובונה תיק לדוגמה לפי רמת הסיכון |
| `portfolio-templates` | מסביר שלושה מבני תיק ואת כל הגרסאות שלהם |
| `portfolio-checkup` | בודק תיק קיים לפי נתונים שאתם מזינים |
| `funds-performance` | מביא מחירים עדכניים בכל הרצה ומציג ביצועים לשנה, 3, 5 ו-10 שנים |

## שלושת מבני התיק
1. **תיק 1, עולמי אחד**: קרן אחת של כל המניות בעולם. Invesco או iShares, עם השוואת מחיר.
2. **תיק 2, מניות עולם ואגח**: קרן מניות עולמית וקרן אגח. אגח עולמי כללי אירי, או אגח כללי ישראלי.
3. **תיק 3, טריאתלון**: שליש טכנולוגיה, שליש S&P 500, שליש עולמי.
   - טכנולוגיה: S&P 500 טכנולוגיה או נאסדק 100, של iShares או של Invesco.
   - S&P 500: רגיל, משקל שווה, משולב, ערך, או מנוטרל מטבע.
   - עולמי: כל העולם, או עולם בלי ארה"ב.

ליד כל קרן מוצגות תמיד החלופות על אותו סוג מדד והפרש העלות השנתית.

## התקנה ב-Claude Code
```bash
git clone https://github.com/yontanbe/irish-funds-il-skills.git
cp -r irish-funds-il-skills/skills/* ~/.claude/skills/
```
ואז פשוט שואלים את Claude: תבנה לי תיק קרנות איריות.

כדי שהסקילים יוכלו להריץ את המנוע, עובדים מתוך תיקיית הריפו.

## שימוש בלי Claude
צריך רק Python 3.9 ומעלה. אין מה להתקין.

```bash
python3 -m engine.cli funds
python3 -m engine.cli quiz
python3 -m engine.cli build --template olami-ve-agach --answers examples/answers-balanced.json --bond global_agg
python3 -m engine.cli build --template triathlon --answers examples/answers-balanced.json --tech sp_tech_ishares --sp equal --global ex_us
python3 -m engine.cli checkup --holdings '{"1159250": 60000, "1159243": 40000}'
python3 -m engine.cli fees --monthly 2000 --years 20 --return 7 --fee 0.8
python3 -m engine.performance --group sp500
```

## ביצועים
הפקודה `python3 -m engine.performance` מביאה מחירים מ-Yahoo Finance בכל הרצה ומדפיסה שלוש טבלאות: תשואה מצטברת, תשואה שנתית ממוצעת, ושנה מול שנה. הריפו לא שומר מחירים.

שימו לב: המחירים הם של יחידת הקרן בבורסה אירופית ולא של המסחר בתל אביב. רק לחלק מהקרנות יש סימול שאומת ידנית. לשאר הסקריפט מחפש סימול לפי ISIN או לפי שם, ומסמן את השורה כלא מאומתת.

## על הנתונים
1. הקרנות נמצאות בקובץ `data/funds.json`, עם מקורות לכל קרן. זה כל מה שנמצא במחקר של iShares ו-Invesco בתל אביב. חסרה קרן? פתחו Issue.
2. הנתונים נאספו ממקורות משניים בתאריך 17.11.2026. לפני כל פעולה מאמתים בעמוד הקרן במאיה.
3. כשמקורות חלוקים על דמי ניהול, הטווח מוצג.
4. מה נמצא ומה לא נמצא במחקר: [RESEARCH.md](RESEARCH.md).

## בדיקות
```bash
pip install pytest
python3 -m pytest -q
```
הבדיקות מכסות את הדאטה, שאלון הסיכון, בניית התיקים, השוואת החלופות, חישוב הביצועים, מבנה הסקילים, נגישות הדפים, והתאמה מלאה בין מנוע הפייתון למנוע הדפדפן. בדיקות הביצועים רצות מול תשובות רשת מדומות.

## רוצים לתקן או להוסיף קרן?
[CONTRIBUTING.md](CONTRIBUTING.md)

## רישיון
MIT. עשו עם זה מה שאתם רוצים.

נבנה על ידי Jonathan AI.

</div>
