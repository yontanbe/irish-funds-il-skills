<div dir="rtl">

# קרנות איריות בתל אביב: סקילים ל-Claude

חמישה סקילים בעברית להשקעה פסיבית לטווח ארוך בקרנות איריות צוברות שנסחרות בבורסה בתל אביב. חינם, קוד פתוח, בלי הרשמה ובלי התקנות.

**למחקר וללימוד בלבד. זה לא ייעוץ השקעות.** הפירוט בקובץ [DISCLAIMER.md](DISCLAIMER.md).

## לא מתכנתים? מתחילים כאן
פותחים בדפדפן, מהטלפון או מהמחשב:

1. [בונה התיק](https://yontanbe.github.io/irish-funds-il-skills/tik.html): שבע שאלות ותיק לדוגמה.
2. [טבלת הקרנות](https://yontanbe.github.io/irish-funds-il-skills/kranot.html): מספרי נייר, דמי ניהול וסוג עקיבה.
3. [מחשבון דמי ניהול](https://yontanbe.github.io/irish-funds-il-skills/dmei-nihul.html): כמה דמי הניהול אוכלים ב-20 שנה.

הכל רץ אצלכם בדפדפן. שום נתון לא נשלח לשום מקום.

## מה יש בפנים
| סקיל | מה הוא עושה |
|---|---|
| `irish-funds-basics` | מסביר מה זה קרן אירית ומה זה השקעה במדדים לטווח ארוך |
| `irish-funds-finder` | עוזר למצוא קרנות ולהבדיל ביניהן |
| `portfolio-builder` | שואל שבע שאלות ובונה תיק לדוגמה לפי רמת הסיכון |
| `portfolio-templates` | מסביר ארבעה הרכבי תיק, כולל טריאתלון |
| `portfolio-checkup` | בודק תיק קיים לפי נתונים שאתם מזינים |

## ארבעת ההרכבים
1. **עולמי אחד**: קרן אחת של כל העולם.
2. **עולמי מפותח ועוד מתפתחים**: 85 מול 15.
3. **שלושה אזורים**: ארה"ב, אירופה ומתפתחים.
4. **טריאתלון**: טכנולוגיה, S&P 500 ועולמי. ל-S&P 500 יש ארבע גרסאות (רגיל, משקל שווה, מנוטרל מטבע, משולב) ולרגל העולמית שתיים (כל העולם, או בלי ארה"ב).

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
python3 -m engine.cli build --template triathlon --answers examples/answers-balanced.json --sp equal --global ex_us
python3 -m engine.cli checkup --holdings '{"1159250": 60000, "1159243": 40000}'
python3 -m engine.cli fees --monthly 2000 --years 20 --return 7 --fee 0.8
```

## על הנתונים
1. הקרנות נמצאות בקובץ `data/funds.json`, עם מקורות לכל קרן.
2. הנתונים נאספו ממקורות משניים בתאריך 17.11.2026. לפני כל פעולה מאמתים בעמוד הקרן במאיה.
3. כשמקורות חלוקים על דמי ניהול, הטווח מוצג.
4. מה נמצא ומה לא נמצא במחקר: [RESEARCH.md](RESEARCH.md).

## בדיקות
```bash
pip install pytest
python3 -m pytest -q
```
הבדיקות מכסות את הדאטה, שאלון הסיכון, בניית התיקים, מבנה הסקילים, נגישות הדפים, והתאמה מלאה בין מנוע הפייתון למנוע הדפדפן.

## רוצים לתקן או להוסיף קרן?
[CONTRIBUTING.md](CONTRIBUTING.md)

## רישיון
MIT. עשו עם זה מה שאתם רוצים.

נבנה על ידי Jonathan AI.

</div>
