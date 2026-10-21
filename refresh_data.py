"""Rebuild the offline dashboard data from all PDFs in the project directory."""
from pathlib import Path
from datetime import datetime, timezone
import re
import json
import hashlib
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / 'dist'

def number(value):
    return float(value.strip().replace('.', '').replace(',', '.'))

def numbers(text):
    return [number(v) for v in re.findall(r'-?\d[\d.]*(?:,\d+)?', text)]

def rows(page, label):
    matches = []
    for line in page.splitlines():
        if re.search(label, line, re.I):
            parts = line.strip('º ').split('³')
            vals = []
            for part in parts[1:]:
                vals += numbers(part)
            if vals:
                matches.append(vals)
    return matches

def row(page, label, default=None):
    found = rows(page, label)
    return found[0] if found else default

def scalar(page, label, scale=1, index=0):
    vals = row(page, label)
    return vals[index] * scale if vals and len(vals) > index else None

def page_for(pages, text, fallback):
    for i, page in enumerate(pages):
        if text.lower() in page.lower():
            return i
    return min(fallback, len(pages) - 1)

def report(doc):
    pages, name = doc['pages'], doc['name']
    summary = pages[0]
    period = re.search(r'für\s+Periode\s+(\d+)', summary, re.I)
    if not period or 'EXECUTIVE SUMMARY' not in summary:
        return None
    p = int(period[1])
    ids = {
        'operations': page_for(pages, 'TEILNEHMERBERICHT 2:', 1),
        'types': page_for(pages, 'TEILNEHMERBERICHT 3:', 2),
        'costs': page_for(pages, 'TEILNEHMERBERICHT 4:', 3),
        'finance': page_for(pages, 'TEILNEHMERBERICHT 5:', 4),
        'income': page_for(pages, 'TEILNEHMERBERICHT 6:', 5),
        'market': page_for(pages, 'TEILNEHMERBERICHT 7:', 6),
        'decisions': page_for(pages, 'Entscheidungsprotokoll', len(pages)-1),
    }
    op, typ, cost, fin, inc, dec = [pages[ids[k]] for k in ['operations','types','costs','finance','income','decisions']]
    def rg(pattern):
        match = re.search(pattern, summary, re.I | re.S)
        return number(match[1]) if match else None
    metrics = {
        'retailUnits': rg(r'Absatz.*?betrug\s+([\d.,]+)\s+Stück'),
        'potentialUnits': rg(r'potentieller Absatz von\s+([\d.,]+)'),
        'marketShare': rg(r'Marktanteil\s+von\s+([\d.,]+)'),
        'technology': rg(r'Technologieindex von\s+([\d.,]+)'),
        'productivity': rg(r'Ein Mitarbeiter kann pro\s+Periode\s+([\d.,]+)'),
        'manufacturingUnit': rg(r'Herstellkosten.*?betrugen\s+([\d.,]+)'),
        'revenue': scalar(inc, 'UMSATZERLÖSE', 1000),
        'profit': scalar(inc, 'PERIODENÜBERSCHUSS / PERIODENFEHLBETRAG', 1000),
        'operatingProfit': scalar(inc, r'=\s+BETRIEBSERGEBNIS', 1000),
        'interest': scalar(inc, 'Zinsen und ähnliche', 1000),
        'tax': scalar(inc, 'Steuern vom Einkommen', 1000),
        'margin': rg(r'Umsatzrendite beträgt\s+([\d.,]+)'),
        'marginVsIndustry': rg(r'Abweichung zum Branchendurchschnitt von\s+(-?[\d.,]+)'),
        'plannedRevenue': scalar(inc, 'Plan-Wert', 1000),
        'potentialRevenue': scalar(inc, 'Ist-Wert', 1000),
        'planningQuality': scalar(inc, 'Planungsqualität aktuell'),
        'planningDeviation': scalar(inc, 'Abweichung in %'),
        'selfCostUnit': scalar(cost[cost.find('pro Stück'):], '= SELBSTKOSTEN'),
        'cash': scalar(fin, 'KASSENENDBESTAND', 1000),
        'receivables': scalar(fin, 'Ford. aus Lief', 1000),
        'equity': None,
        'assets': scalar(fin, 'BILANZSUMME', 1000),
        'credit': None,
        'overdraft': None,
        'temporaryCost': scalar(typ, 'bezogene Fremdleistungen', 1000),
        'payroll': scalar(typ, 'Löhne/Gehälter', 1000),
        'payrollBenefits': scalar(typ, 'Personalnebenkosten', 1000),
    }
    # Balance sheet has two labels side by side.
    eq = re.search(r'EIGENKAPITAL\s+³\s*([\d.,]+)', fin)
    metrics['equity'] = number(eq[1])*1000 if eq else None
    for key,label in [('credit','Restlaufzeit unter 1 Jahr'),('overdraft','Überziehungskredit')]:
        match=re.search(label+r'\s+³\s*([\d.,]+)',fin)
        metrics[key]=number(match[1])*1000 if match else 0
    for key in ['revenue','profit','operatingProfit','credit','cash']:
        if metrics[key] is None:
            raise ValueError(f'{name}: required metric missing: {key}')
    decisions = {}
    for key, label in {'price':'Preis','advertising':'Printwerbung','wholesale':'Großabnehmer',
        'promotion':'Verkaufsförderung','salesStaff':'Endbestand Vertrieb','research':'Aufwendungen',
        'nylon':'Ripstop-Nylon','rods':'Gestänge','newMachines':'Investition Typ A',
        'hires':'Mitarbeiter Einstell','dismissals':'Mitarbeiter Entlass','production':r'\(Menge\).*Produktion',
        'loan':'Kurzfristiger Kredit','planRevenue':'Planumsatz'}.items():
        vals = row(dec, label)
        decisions[key] = vals[-1] if vals else None
    if decisions['production'] is None:
        decisions['production'] = scalar(op, 'tats. produzierte Menge')
    metrics['production'] = decisions['production']
    metrics['retailRevenue'] = (decisions['price'] or 0)*(metrics['retailUnits'] or 0)
    metrics['wholesaleRevenue'] = metrics['revenue']-metrics['retailRevenue']
    metrics['wholesalePriceDerived'] = metrics['wholesaleRevenue']/decisions['wholesale'] if decisions['wholesale'] else None
    metrics['marginIndustry'] = metrics['margin']-metrics['marginVsIndustry'] if metrics['marginVsIndustry'] is not None else None
    staff = {}
    for key, label in {'start':'Personalanfangsbestand','end':'Personalendbestand','attrition':'Fluktuation',
                       'salary':'Löhne/Gehälter','benefits':'Personalnebenkosten','cost':'Summe Personalkosten'}.items():
        staff[key] = row(op, label)
    metrics['productionStaff'] = staff['end'][2] if staff.get('end') else None
    metrics['salesStaff'] = staff['end'][1] if staff.get('end') else None
    metrics['temporaryFte'] = scalar(op, 'ggf. MA der Zeitarbeitsfirma', index=1)
    if metrics['temporaryFte'] is None:
        match = re.search(r'Zeitarbeitsfirma\s+³\s*([\d.,]+)', op)
        metrics['temporaryFte'] = number(match[1]) if match else 0
    assets = []
    for line in op.splitlines():
        if 'Anlage Nr.' in line:
            v = numbers(line.split('³',1)[1])
            if len(v)>=8:
                assets.append(dict(zip(['capacity','boughtPeriod','purchasePrice','remainingLife','depreciation','bookValue','fixed','maintenance'],v[:8]), id=int(re.search(r'Nr\.\s*(\d+)',line)[1])))
    metrics['capacity'] = sum(x['capacity'] for x in assets)
    metrics['utilization'] = metrics['production']/metrics['capacity']*100 if metrics['capacity'] else None
    fgpart = op[op.find('FERTIGPRODUKTE'):]
    inventory = {}
    for key,label in {'opening':'Lageranfangsbestand','closing':'Lagerendbestand','produced':'Zugang Fertigung','sold':'Abgang Vertrieb'}.items():
        inventory[key] = row(fgpart,label)
    metrics['inventory'] = inventory['closing'][0] if inventory.get('closing') else None
    metrics['inventoryValue'] = inventory['closing'][2] if inventory.get('closing') else None
    raw = {}
    for key,label in {'opening':'Lageranfangsbestand','orders':'Bestellungen','shortages':'Fehlmengenzukäufe','closing':'Lagerendbestand'}.items():
        raw[key] = row(op[:op.find('FERTIGPRODUKTE')], label)
    unitpart = cost[cost.find('pro Stück'):]
    costUnits = {}
    for key,label in {'parts':'Einsatzstoffe/Teile','supplies':'Betriebsstoffe','directLabour':'Fertigungs-Einzelkosten',
        'factoryOverhead':'Fertigungs-Gemeinkosten','research':'F & E.*Einzelkosten',
        'advertising':'Verkauf.*Einzelkosten','sellingOverhead':r'^.*\+\s+Gemeinkosten \(Kostenstelle Verkauf\)',
        'adminDirect':'Einkauf/Verwaltung Einzelkosten','adminOverhead':r'^.*\+\s+Gemeinkosten \(Kostenstelle Einkauf/Verwaltung\)'}.items():
        costUnits[key] = scalar(unitpart,label)
    # These report labels contain wide spaces and names on adjacent rows.
    cu = rows(unitpart,'Gemeinkosten')
    if len(cu)>=4:
        costUnits['factoryOverhead'],costUnits['sellingOverhead'],costUnits['adminOverhead'] = cu[0][0],cu[2][0],cu[3][0]
    income = {}
    for key,label in {'cogs':'Herstellkosten des','selling':'Vertriebskosten','research':'-  F & E','admin':'Verwaltungskosten',
                       'depreciation':'Abschr.auf Vermögensgegenst.','otherExpenses':'Sonstiger Aufwand','dividend':'Auszuschüttender Betrag'}.items():
        income[key] = scalar(inc,label,1000)
    industry=pages[page_for(pages,'Geschäftsberichte der Branche',8)]
    for key,label in {'cogs':'Herstellkosten des Umsatzes','selling':'Vertriebskosten',
                      'research':'Aufwendungen für F&E','admin':'Verwaltungskosten'}.items():
        income[key]=scalar(industry,label,1000)
    cashflow = {}
    for key,label in {'openingCash':'KASSENANFANGSBESTAND','currentReceipts':'Einzahlungen aus aktueller',
        'previousReceipts':'Einzahlungen aus Vorperiode','purchases':'Einkauf Einsatzstoffe',
        'external':'Bezogene Fremdleistungen','personnel':'Personalaufwand','other':'Sonstige Auszahlungen',
        'repayment':'Rückzahlung kurzfr','interest':'Zinsaufwand','investment':'Kauf von Fertigungsanlagen',
        'tax':'Steuern','dividend':'Auszahlung Dividende'}.items():
        cashflow[key] = scalar(fin,label,1000)
    competitors = {}
    for i,page in enumerate(pages):
        if 'Marktforschungsbericht' not in page:
            continue
        section=None
        for line in page.splitlines():
            for token,key in [('PREIS','price'),('ABSATZ ','units'),('MARKTANTEIL','share'),('KOMMUNIKATION','communication'),('SONSTIGE DATEN','other')]:
                if token in line:
                    section=key
            match=re.search(r'Unternehmen\s+(\d+)\s+³',line)
            if match and section:
                company=int(match[1]); v=numbers(line.split('³',1)[1]); c=competitors.setdefault(company,{'company':company,'sources':{}})
                if v:
                    if section=='communication': c['advertising'],c['promotion']=v[:2]
                    elif section=='other':
                        c['technology'],c['awareness']=v[:2]
                        if len(v)>=4: c['wholesale'],c['staff']=v[-2:]
                        elif len(v)>=3: c['staff']=v[-1]
                    else: c[section]=v[0]
                    c['sources'][section]=i+1
    metrics['priceAverage'] = sum(c.get('price',0) for c in competitors.values())/len(competitors) if competitors else None
    metrics['awareness'] = competitors.get(1,{}).get('awareness')
    for k in ids: ids[k]+=1
    return {'period':p,'doc':name,'metrics':metrics,'decisions':decisions,'staff':staff,'assets':assets,
            'inventory':inventory,'raw':raw,'costUnits':costUnits,'income':income,'cashflow':cashflow,
            'competitors':list(competitors.values()),'pages':ids}

def main():
    DIST.mkdir(parents=True,exist_ok=True)
    docs=[]; reports={}; profit_candidates=[]; news=[]
    for path in ROOT.glob('*.pdf'):
        pages=[(pg.extract_text() or '').replace('Groá','Groß').replace('Auáer','Außer') for pg in PdfReader(path).pages]
        text='\n'.join(pages)
        kind='other'
        if 'probe' in path.name.lower(): kind='practice'
        elif 'teilnehmerhandbuch' in path.name.lower(): kind='manual'
        elif 'EXECUTIVE SUMMARY' in text: kind='report'
        elif 'Business news' in text or 'news++++' in text: kind='news'
        elif re.search(r'Periode\s+1\s+[\d.,]+',text): kind='profits'
        elif 'Entscheidungsformular' in text: kind='form'
        doc={'name':path.name,'kind':kind,'pages':pages,'modified':path.stat().st_mtime,
             'hash':hashlib.sha256(path.read_bytes()).hexdigest()[:16]}
        docs.append(doc)
        if kind=='report':
            r=report(doc)
            if r:
                old=reports.get(r['period'])
                if not old or ('korrigiert' in path.name.lower()) or doc['modified']>old.get('_modified',0):
                    r['_modified']=doc['modified']; reports[r['period']]=r
        if kind=='profits':
            values={}
            for line in text.splitlines():
                m=re.match(r'Periode\s+(\d+)\s+(.+)',line.strip())
                if m:
                    vals=numbers(m[2])
                    if len(vals)==10: values[int(m[1])]=[round(v*1000,2) for v in vals]
            if values: profit_candidates.append((len(values),doc['modified'],path.name,values))
        if kind=='news':
            m=re.search(r'Periode\s+(\d+)',text)
            if m: news.append({'period':int(m[1]),'doc':path.name,'text':text})
    profit_doc=None; profits={}
    if profit_candidates:
        _,_,profit_doc,profits=max(profit_candidates)
    periods=sorted(set(reports)|set(profits))
    latest=max(periods); detailed=max(reports)
    nextnews=next((n for n in news if n['period']==latest+1),None)
    data={'schema':1,'generatedAt':datetime.now(timezone.utc).isoformat(),'latestPeriod':latest,
        'latestDetailedPeriod':detailed,'periods':periods,'reports':reports,'profits':profits,
        'profitDoc':profit_doc,'nextNews':nextnews,'news':news,'documents':docs}
    (DIST/'data.js').write_text('window.PLAN_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    (HERE/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(docs)} Dokumente; Detailberichte {sorted(reports)}; letzte Periode {latest}; nächste Meldung {nextnews["period"] if nextnews else "fehlt"}.')

if __name__=='__main__': main()
