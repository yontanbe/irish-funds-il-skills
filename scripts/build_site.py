"""בונה את דפי ה-HTML בתיקיית docs מתוך הדאטה והמנוע.

כל דף עומד בפני עצמו: עיצוב, מנוע ונתונים בתוך קובץ אחד, בלי תלות ברשת.
הרצה: python3 scripts/build_site.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.core import DISCLAIMER, load_data  # noqa: E402

DOCS = ROOT / "docs"

CSS = """
:root{--bg:#f6f4ef;--card:#fff;--ink:#1c2321;--muted:#5b6663;--line:#d9d5cb;--accent:#0b6e4f;--accent-ink:#fff;--warn-bg:#fff4d6;--warn-ink:#5c4400;--focus:#1a56db}
@media (prefers-color-scheme:dark){:root{--bg:#121615;--card:#1b2120;--ink:#eef2f0;--muted:#a9b4b0;--line:#33403c;--accent:#4fd1a1;--accent-ink:#06231a;--warn-bg:#3a3110;--warn-ink:#ffe69a;--focus:#8ab4ff}}
*{box-sizing:border-box}
html{font-size:112.5%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Arial,sans-serif;line-height:1.65}
main{max-width:46rem;margin:0 auto;padding:1.25rem 1rem 4rem}
h1{font-size:1.7rem;line-height:1.25;margin:.5rem 0 .25rem}
h2{font-size:1.25rem;margin:2rem 0 .5rem}
p{margin:.5rem 0}
a{color:var(--accent)}
.lead{color:var(--muted)}
nav.top{display:flex;gap:.5rem;flex-wrap:wrap;margin:0 0 1rem;padding:0;list-style:none}
nav.top a{display:inline-block;padding:.45rem .8rem;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--ink);background:var(--card);min-height:44px;line-height:1.6}
nav.top a[aria-current=page]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;margin:1rem 0}
fieldset{border:0;padding:0;margin:0}
legend{font-weight:700;font-size:1.1rem;padding:0;margin-bottom:.2rem}
.help{color:var(--muted);font-size:.92rem;margin:0 0 .6rem}
label.opt{display:flex;gap:.7rem;align-items:flex-start;padding:.7rem .8rem;border:1px solid var(--line);border-radius:10px;margin:.4rem 0;cursor:pointer;min-height:48px}
label.opt:has(input:checked){border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
input[type=radio]{width:1.25rem;height:1.25rem;margin-top:.2rem;accent-color:var(--accent);flex:none}
label.fld{display:block;font-weight:600;margin:.8rem 0 .25rem}
input[type=number],select{width:100%;font:inherit;padding:.65rem .7rem;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);min-height:48px}
button{font:inherit;font-weight:700;padding:.8rem 1.2rem;border-radius:12px;border:0;background:var(--accent);color:var(--accent-ink);cursor:pointer;min-height:48px}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.warn{background:var(--warn-bg);color:var(--warn-ink);border-radius:10px;padding:.7rem .9rem;margin:.5rem 0}
.disclaimer{font-size:.9rem;color:var(--muted);border-top:1px solid var(--line);margin-top:2.5rem;padding-top:1rem}
.big{font-size:2rem;font-weight:800;line-height:1.2}
.tablewrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{text-align:right;padding:.55rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:700;white-space:nowrap}
td.num,th.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{height:.75rem;border-radius:999px;background:var(--accent);min-width:2px}
.row{display:grid;grid-template-columns:3.2rem 1fr;gap:.7rem;align-items:center;margin:.55rem 0}
.row .w{font-weight:800;font-variant-numeric:tabular-nums}
.small{font-size:.88rem;color:var(--muted)}
.alt{font-size:.85rem;color:var(--muted);border-inline-start:3px solid var(--line);padding-inline-start:.5rem;margin-top:.35rem}
.progress{font-size:.9rem;color:var(--muted)}
.btns{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}
[hidden]{display:none!important}
"""

NAV = [
    ("index.html", "ראשי"),
    ("tik.html", "בונה התיק"),
    ("kranot.html", "טבלת הקרנות"),
    ("dmei-nihul.html", "מחשבון דמי ניהול"),
]


def page(filename: str, title: str, body: str, script: str, data: dict | None) -> str:
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if href == filename else ""}>{label}</a>'
        for href, label in NAV
    )
    engine_js = (DOCS / "assets" / "engine.js").read_text(encoding="utf-8")
    data_js = "window.IF_DATA=" + json.dumps(data, ensure_ascii=False) + ";" if data else ""
    return f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | קרנות איריות בתל אביב</title>
<meta name="description" content="כלי מחקר חינמי בקוד פתוח לקרנות איריות צוברות שנסחרות בבורסה בתל אביב.">
<style>{CSS}</style>
</head>
<body>
<main>
<nav class="top" aria-label="ניווט ראשי">{nav}</nav>
{body}
<p class="disclaimer" role="note">{DISCLAIMER}</p>
</main>
<script>{data_js}</script>
<script>{engine_js}</script>
<script>{script}</script>
</body>
</html>
"""


INDEX_BODY = """
<h1>קרנות איריות בתל אביב, בפשטות</h1>
<p class="lead">כלי מחקר חינמי בקוד פתוח למשקיע לטווח ארוך. בלי הרשמה, בלי מעקב, הכל רץ אצלכם בדפדפן.</p>
<div class="card"><h2 style="margin-top:0">בונה התיק</h2><p>שבע שאלות קצרות, ותקבלו תיק לדוגמה לפי רמת הסיכון שלכם: עולמי אחד, מניות ואג"ח, או טריאתלון. ליד כל קרן מוצגת החלופה והפרש העלות.</p><p><a href="tik.html">להתחיל בשאלון</a></p></div>
<div class="card"><h2 style="margin-top:0">טבלת הקרנות</h2><p>כל קרנות iShares ו-Invesco האיריות שבדאטה, מניות ואג"ח, עם מספר נייר, דמי ניהול וסוג עקיבה.</p><p><a href="kranot.html">לטבלה</a></p></div>
<div class="card"><h2 style="margin-top:0">מחשבון דמי ניהול</h2><p>כמה כסף דמי הניהול אוכלים לכם לאורך 20 או 30 שנה.</p><p><a href="dmei-nihul.html">למחשבון</a></p></div>
<h2>מה זה קרן אירית, בשני משפטים</h2>
<p>קרן סל שמאוגדת באירלנד, עוקבת אחרי מדד כמו S&amp;P 500, ונסחרת בשקלים בבורסה בתל אביב. רובן צוברות: הדיבידנד מושקע חזרה בתוך הקרן, ומס רווחי הון משלמים רק במכירה.</p>
<p class="small">הנתונים נבדקו בתאריך <span id="checked"></span>. דמי ניהול משתנים, ולכן חובה לאמת כל קרן בעמוד שלה במאיה לפני פעולה.</p>
"""
INDEX_JS = "document.getElementById('checked').textContent=window.IF_DATA.funds.meta.checked_at;"

TIK_BODY = """
<h1>בונה התיק</h1>
<p class="lead">עונים על שבע שאלות ומקבלים תיק לדוגמה. אפשר לחזור אחורה ולשנות.</p>
<form id="quiz" class="card" novalidate>
  <p class="progress" id="progress" aria-live="polite"></p>
  <div id="qbox"></div>
  <p class="warn" id="qerr" role="alert" hidden>צריך לבחור תשובה כדי להמשיך.</p>
  <div class="btns">
    <button type="button" class="ghost" id="back">חזרה</button>
    <button type="submit" id="next">המשך</button>
  </div>
</form>
<section id="result" hidden aria-live="polite">
  <div class="card">
    <p class="small">הפרופיל שלכם לפי התשובות</p>
    <p class="big" id="profile"></p>
    <p id="equity"></p>
    <div id="warnings"></div>
  </div>
  <div class="card">
    <label class="fld" for="template">איזה הרכב תיק להציג</label>
    <select id="template"></select>
    <p class="small" id="tsummary"></p>
    <div id="opts"></div>
  </div>
  <div class="card">
    <h2 style="margin-top:0" id="ptitle"></h2>
    <div id="lines"></div>
    <p id="stats" class="small"></p>
    <div id="notes"></div>
  </div>
  <div class="btns"><button type="button" class="ghost" id="restart">להתחיל מחדש</button></div>
</section>
"""
TIK_JS = r"""
(function(){
var D=window.IF_DATA,E=window.IrishFunds,Q=D.questionnaire.questions,answers={},i=0,risk=null,opts={};
var byNum=E.fundsByNumber(D.funds);
function el(t,a,txt){var e=document.createElement(t);for(var k in a||{})e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}
function $(id){return document.getElementById(id);}
function renderQ(){
  var q=Q[i],box=$('qbox');box.textContent='';
  $('progress').textContent='שאלה '+(i+1)+' מתוך '+Q.length;
  var fs=el('fieldset');fs.appendChild(el('legend',{},q.text));fs.appendChild(el('p',{'class':'help'},q.help));
  q.options.forEach(function(o){
    var lab=el('label',{'class':'opt'});var inp=el('input',{type:'radio',name:'q',value:o.id});
    if(answers[q.id]===o.id)inp.checked=true;
    lab.appendChild(inp);lab.appendChild(el('span',{},o.text));fs.appendChild(lab);
  });
  box.appendChild(fs);$('back').hidden=i===0;$('next').textContent=i===Q.length-1?'לתוצאה':'המשך';$('qerr').hidden=true;
  var first=box.querySelector('input:checked')||box.querySelector('input');if(first&&i>0)first.focus();
}
$('quiz').addEventListener('submit',function(ev){
  ev.preventDefault();var c=document.querySelector('input[name=q]:checked');
  if(!c){$('qerr').hidden=false;return;}
  answers[Q[i].id]=c.value;
  if(i<Q.length-1){i++;renderQ();}else showResult();
});
$('back').addEventListener('click',function(){if(i>0){i--;renderQ();}});
$('restart').addEventListener('click',function(){answers={};i=0;opts={};$('result').hidden=true;$('quiz').hidden=false;renderQ();window.scrollTo(0,0);});
function showResult(){
  risk=E.scoreRisk(answers,D.questionnaire);
  $('quiz').hidden=true;$('result').hidden=false;
  $('profile').textContent=risk.profile_name;
  $('equity').textContent='חלק מנייתי לדוגמה: '+risk.equity_pct+' אחוז. השאר ברכיב סולידי או באג"ח.';
  var w=$('warnings');w.textContent='';risk.warnings.forEach(function(t){w.appendChild(el('p',{'class':'warn'},t));});
  var sel=$('template');sel.textContent='';
  D.portfolios.templates.forEach(function(t){sel.appendChild(el('option',{value:t.id},'תיק '+t.number+': '+t.name));});
  renderTemplate();$('profile').setAttribute('tabindex','-1');$('profile').focus();
}
$('template').addEventListener('change',function(){opts={};renderTemplate();});
function renderTemplate(){
  var t=D.portfolios.templates.filter(function(x){return x.id===$('template').value;})[0];
  $('tsummary').textContent=t.summary;
  var box=$('opts');box.textContent='';
  Object.keys(t.options||{}).forEach(function(key){
    var spec=t.options[key],id='opt_'+key;
    box.appendChild(el('label',{'class':'fld','for':id},spec.label));
    var s=el('select',{id:id});
    Object.keys(spec.choices).forEach(function(c){var o=el('option',{value:c},spec.choices[c]);if((opts[key]||spec['default'])===c)o.selected=true;s.appendChild(o);});
    s.addEventListener('change',function(){opts[key]=s.value;renderPortfolio(t);});
    box.appendChild(s);
  });
  renderPortfolio(t);
}
function renderPortfolio(t){
  var p=E.buildPortfolio(t.id,risk.equity_pct,D.portfolios,opts);
  $('ptitle').textContent='תיק לדוגמה: '+p.template_name;
  var L=$('lines');L.textContent='';
  p.lines.forEach(function(line){
    var f=line.fund?byNum[line.fund]:null;
    var row=el('div',{'class':'row'});row.appendChild(el('div',{'class':'w'},line.weight+'%'));
    var d=el('div');d.appendChild(el('div',{},line.label));
    d.appendChild(el('div',{'class':'small'},f?f.name+' | מספר נייר '+f.tase_number+' | עלות '+E.totalCostPct(f)+'%':'בוחרים לבד'));
    var bar=el('div',{'class':'bar','aria-hidden':'true'});bar.style.width=line.weight+'%';d.appendChild(bar);
    if(f){E.alternatives(f.tase_number,D.funds).forEach(function(a){
      var sign=a.diff_pct>0?'יקרה ב-'+a.diff_pct+'%':(a.diff_pct<0?'זולה ב-'+Math.abs(a.diff_pct)+'%':'אותה עלות');
      d.appendChild(el('div',{'class':'alt'},'חלופה: '+a.name+' | מספר נייר '+a.tase_number+' | עלות '+a.cost_pct+'% | '+sign));
    });}
    row.appendChild(d);L.appendChild(row);
  });
  var s=E.portfolioStats(p.lines,D.funds);
  $('stats').textContent=s.covered_weight?'עלות שנתית משוקללת על החלק המנייתי: '+s.weighted_cost_pct+'%. חשיפה משוערת לארה"ב בחלק המנייתי: '+s.us_share_pct+'%.':'';
  var N=$('notes');N.textContent='';p.notes.forEach(function(n){N.appendChild(el('p',{'class':'warn'},n));});
}
renderQ();
})();
"""

KRANOT_BODY = """
<h1>טבלת הקרנות</h1>
<p class="lead">כל קרנות iShares ו-Invesco האיריות שנמצאו כנסחרות בשקלים בבורסה בתל אביב, מניות ואג"ח. אפשר לסנן לפי סוג.</p>
<label class="fld" for="cat">סינון לפי סוג</label>
<select id="cat"></select>
<div class="card tablewrap">
<table>
<caption class="small" id="cap"></caption>
<thead><tr><th scope="col">קרן</th><th scope="col" class="num">מספר נייר</th><th scope="col">מדד</th><th scope="col" class="num">עלות שנתית</th><th scope="col">עקיבה</th><th scope="col">בסיס מס</th></tr></thead>
<tbody id="rows"></tbody>
</table>
</div>
<p class="small">עלות שנתית כוללת דמי ניהול ועמלת SWAP כשיש. כשהמקורות חלוקים מוצג גם הטווח. בסיס מס: לפי מה נמדד הרווח הריאלי במכירה, מדד המחירים לצרכן או שער הדולר.</p>
<p class="small" id="note"></p>
"""
KRANOT_JS = r"""
(function(){
var D=window.IF_DATA,E=window.IrishFunds;
var CAT={us_large:'ארה"ב, S&P 500',us_equal_weight:'ארה"ב, משקל שווה',us_tech:'ארה"ב, נאסדק 100',us_small:'ארה"ב, חברות קטנות',us_sector:'ארה"ב, לפי ענף',global_all:'עולמי, מפותחים ומתפתחים',global_developed:'עולמי, מפותחים בלבד',europe:'אירופה',emerging:'שווקים מתפתחים',country:'מדינה',sector:'ענף עולמי',thematic:'נושא',bond_global:'אג"ח עולמי',bond_us_gov:'אג"ח ממשלת ארה"ב',bond_corp:'אג"ח קונצרני',bond_em:'אג"ח שווקים מתפתחים'};
var REP={physical:'פיזית',synthetic:'סינתטית',unknown:'לא אומת'};
var TAX={cpi:'מדד המחירים לצרכן',usd:'שער הדולר',unknown:'לא אומת'};
var sel=document.getElementById('cat');
function opt(v,t){var o=document.createElement('option');o.value=v;o.textContent=t;sel.appendChild(o);}
opt('','הכל');Object.keys(CAT).forEach(function(k){if(D.funds.funds.some(function(f){return f.category===k;}))opt(k,CAT[k]);});
function td(t,c){var e=document.createElement('td');if(c)e.className=c;e.textContent=t;return e;}
function render(){
  var rows=document.getElementById('rows');rows.textContent='';
  var list=D.funds.funds.filter(function(f){return !sel.value||f.category===sel.value;});
  list.forEach(function(f){
    var tr=document.createElement('tr');
    var th=document.createElement('th');th.scope='row';th.textContent=f.name;th.style.whiteSpace='normal';tr.appendChild(th);
    tr.appendChild(td(f.tase_number,'num'));tr.appendChild(td(f.index));
    var cost=E.totalCostPct(f)+'%';if(f.fee_range[0]!==f.fee_range[1])cost+=' (דווח '+f.fee_range[0]+' עד '+f.fee_range[1]+')';
    tr.appendChild(td(cost,'num'));tr.appendChild(td(REP[f.replication]));tr.appendChild(td(TAX[f.tax_link]));
    rows.appendChild(tr);
  });
  document.getElementById('cap').textContent='מוצגות '+list.length+' קרנות. נבדק בתאריך '+D.funds.meta.checked_at+'.';
}
sel.addEventListener('change',render);render();
document.getElementById('note').textContent=D.funds.meta.note;
})();
"""

FEES_BODY = """
<h1>מחשבון דמי ניהול</h1>
<p class="lead">אותה השקעה, אותה תשואה, דמי ניהול שונים. כמה זה שווה בסוף?</p>
<form id="f" class="card" novalidate>
  <label class="fld" for="initial">סכום התחלתי בשקלים</label><input id="initial" type="number" inputmode="decimal" min="0" value="0">
  <label class="fld" for="monthly">הפקדה חודשית בשקלים</label><input id="monthly" type="number" inputmode="decimal" min="0" value="2000">
  <label class="fld" for="years">מספר שנים</label><input id="years" type="number" inputmode="numeric" min="1" max="60" value="20">
  <label class="fld" for="ret">הנחת תשואה שנתית באחוזים, לפני דמי ניהול</label><input id="ret" type="number" inputmode="decimal" step="0.1" value="7">
  <label class="fld" for="feeA">דמי ניהול א באחוזים, למשל קרן זולה</label><input id="feeA" type="number" inputmode="decimal" step="0.01" min="0" value="0.07">
  <label class="fld" for="feeB">דמי ניהול ב באחוזים, למשל קרן יקרה</label><input id="feeB" type="number" inputmode="decimal" step="0.01" min="0" value="0.8">
  <p class="warn" id="err" role="alert" hidden>יש שדה עם ערך לא תקין.</p>
  <div class="btns"><button type="submit">לחשב</button></div>
</form>
<section id="out" class="card" aria-live="polite" hidden>
  <p class="small">ההפרש בין שתי האפשרויות בסוף התקופה</p>
  <p class="big" id="diff"></p>
  <div class="tablewrap"><table>
  <thead><tr><th scope="col"></th><th scope="col" class="num">אפשרות א</th><th scope="col" class="num">אפשרות ב</th></tr></thead>
  <tbody>
  <tr><th scope="row">שווי בסוף</th><td class="num" id="a1"></td><td class="num" id="b1"></td></tr>
  <tr><th scope="row">הלך לדמי ניהול</th><td class="num" id="a2"></td><td class="num" id="b2"></td></tr>
  </tbody></table></div>
  <p class="small" id="dep"></p>
  <p class="small">זו הדגמה חשבונית לפי ההנחות שהזנתם. היא לא תחזית, ותשואות עבר לא מבטיחות תשואות עתיד.</p>
</section>
"""
FEES_JS = r"""
(function(){
var E=window.IrishFunds;
function v(id){return parseFloat(document.getElementById(id).value);}
function nis(x){return Math.round(x).toLocaleString('he-IL')+' ש"ח';}
function set(id,t){document.getElementById(id).textContent=t;}
function calc(ev){
  if(ev)ev.preventDefault();
  var err=document.getElementById('err'),out=document.getElementById('out');
  try{
    var vals=['initial','monthly','years','ret','feeA','feeB'].map(v);
    if(vals.some(function(x){return isNaN(x);}))throw new Error('nan');
    var a=E.feeDrag(vals[0],vals[1],Math.round(vals[2]),vals[3],vals[4]);
    var b=E.feeDrag(vals[0],vals[1],Math.round(vals[2]),vals[3],vals[5]);
    set('diff',nis(Math.abs(a.with_fee-b.with_fee)));
    set('a1',nis(a.with_fee));set('b1',nis(b.with_fee));set('a2',nis(a.lost_to_fees));set('b2',nis(b.lost_to_fees));
    set('dep','סך הכל הופקד: '+nis(a.deposited)+'.');
    err.hidden=true;out.hidden=false;
  }catch(e){err.hidden=false;out.hidden=true;}
}
document.getElementById('f').addEventListener('submit',calc);calc();
})();
"""

PAGES = [
    ("index.html", "ראשי", INDEX_BODY, INDEX_JS, True),
    ("tik.html", "בונה התיק", TIK_BODY, TIK_JS, True),
    ("kranot.html", "טבלת הקרנות", KRANOT_BODY, KRANOT_JS, True),
    ("dmei-nihul.html", "מחשבון דמי ניהול", FEES_BODY, FEES_JS, False),
]


def build() -> dict:
    data = load_data()
    out = {}
    for filename, title, body, script, needs_data in PAGES:
        out[filename] = page(filename, title, body, script, data if needs_data else None)
    return out


def main() -> None:
    for filename, html in build().items():
        (DOCS / filename).write_text(html, encoding="utf-8")
        print("נבנה", filename)


if __name__ == "__main__":
    main()
