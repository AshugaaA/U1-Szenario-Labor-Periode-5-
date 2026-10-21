(function (root) {
  'use strict';
  const n = (v, fallback = 0) => Number.isFinite(+v) ? +v : fallback;
  const positive = v => Math.max(0, n(v));
  const copy = value => JSON.parse(JSON.stringify(value));
  function defaults(data) {
    const r = data.reports[data.latestDetailedPeriod], m = r.metrics, d = r.decisions;
    const news = (data.nextNews?.text || '').replace(/\s+/g, ' ');
    const extract = (re, fallback) => { const match = news.match(re); return match ? Number(match[1].replace(',', '.')) : fallback; };
    const raw = r.raw.orders || [0, 120, 0, 0, 20, 0];
    const salary = r.staff.salary || [7000, 46500, 77500];
    const staff = r.staff.end || [.5, 3, 5];
    const benefits = (m.payrollBenefits || 0)/(m.payroll || 1);
    const hiringNews = data.news.filter(x => x.period <= (data.nextNews?.period || data.latestPeriod+1))
      .sort((a,b)=>b.period-a.period).find(x => /Kosten für\s+Einstellungen\s+([\d.]+)/.test(x.text));
    const hiringMatch = hiringNews?.text.match(/Kosten für\s+Einstellungen\s+([\d.]+)/);
    const fte = m.production/m.productivity - m.productionStaff;
    return {
      price:d.price, advertising:d.advertising, promotion:d.promotion, salesStaff:staff[1], research:d.research,
      wholesale:d.wholesale || 0, wholesalePrice:extract(/Preis in €\s+(\d+)/, m.wholesalePriceDerived || 0),
      wholesaleMax:extract(/max\. Menge\s+(\d+)/, 0),
      nylon:d.nylon ?? m.production, rods:d.rods ?? m.production,
      newMachines:0, sellMachines:0, hires:0, dismissals:0, production:m.production,
      loan:d.loan, planRevenue:d.planRevenue,
      demand:Math.round(m.retailUnits*1.02), attrition:0,
      nylonPrice:raw[1], rodPrice:raw[4], priceMode:'observed', supplies:extract(/Pro prod\. Einheit in €\s+(\d+)/, r.costUnits.supplies),
      productivity:m.productivity, salary:salary[2]/staff[2], salesSalary:salary[1]/staff[1],
      adminStaff:staff[0], adminSalary:salary[0]/staff[0], benefits:Math.round(benefits*100),
      hiringCost:hiringMatch ? Number(hiringMatch[1].replaceAll('.','')) : 2000, dismissalCost:1000,
      tempRate:fte > 0 ? Math.round(m.temporaryCost/fte/100)*100 : 25000,
      loanRate:Math.round(m.interest/m.credit*1000)/10, overdraftRate:7,
      taxRate:Math.round(m.tax/(m.operatingProfit-m.interest)*100), receiptRate:75,
      fgStorage:8, nylonStorage:4, rodStorage:1, researchFactor:extract(/Wirkung\s+Faktor\s+([\d,]+)/,1),
      cashBuffer:20000, rent:15000, utilities:3750, adminFixed:5000, adminRevenueRate:2,
      otherDepreciation:3750, machinePrice:55000, machineCapacity:500, machineFixed:2500,
      machineMaintenance:5000, machineDepreciation:5000, saleRate:25,
    };
  }
  function tier(q, material) {
    // Historical P3 schedule, never silently treated as confirmed P5 prices.
    return material==='nylon' ? (q>=2400?102:q>=1200?109:115) : (q>=2400?15:q>=1200?17:18);
  }
  function calculate(input, report, override = {}) {
    const s = {...copy(input), ...override}, m = report.metrics;
    const soldCount = Math.min(Math.floor(positive(s.sellMachines)), Math.max(0, report.assets.length-1));
    const removed = report.assets.slice(0,soldCount);
    const newCount = Math.floor(positive(s.newMachines));
    const machineCount = report.assets.length-soldCount+newCount;
    const capacity = machineCount*positive(s.machineCapacity);
    const requested = Math.floor(positive(s.production));
    const production = Math.min(requested,capacity);
    const hires = Math.floor(positive(s.hires));
    const fires = Math.min(Math.floor(positive(s.dismissals)),m.productionStaff+hires);
    const prodStaff = Math.max(0,m.productionStaff+hires-fires-Math.floor(positive(s.attrition)));
    const salesStaff = Math.floor(positive(s.salesStaff));
    const productivity = Math.max(.01,n(s.productivity,215));
    const permanentCapacity=prodStaff*productivity;
    const temporaryFte = Math.max(0,production/productivity-prodStaff);
    const temporaryCost = temporaryFte*positive(s.tempRate);
    const salaryFactor=1+positive(s.benefits)/100;
    const prodPayroll=prodStaff*positive(s.salary)*salaryFactor;
    const salesPayroll=salesStaff*positive(s.salesSalary)*salaryFactor;
    const adminPayroll=positive(s.adminStaff)*positive(s.adminSalary)*salaryFactor;
    const salesHires=Math.max(0,salesStaff-m.salesStaff), salesFires=Math.max(0,m.salesStaff-salesStaff);
    const prodFees=hires*positive(s.hiringCost)+fires*positive(s.dismissalCost);
    const salesFees=salesHires*positive(s.hiringCost)+salesFires*positive(s.dismissalCost);
    const payroll=prodPayroll+salesPayroll+adminPayroll;
    const fgOpen=positive(m.inventory), fgOpenValue=positive(m.inventoryValue);
    const available=fgOpen+production;
    const wholesaleRequested=Math.min(Math.floor(positive(s.wholesale)),positive(s.wholesaleMax));
    const wholesaleSold=Math.min(available,wholesaleRequested);
    const retailAvailable=Math.max(0,available-wholesaleSold);
    const demand=Math.floor(positive(s.demand));
    const retailSold=Math.min(retailAvailable,demand);
    const lostRetail=Math.max(0,demand-retailSold);
    const totalSold=retailSold+wholesaleSold;
    const closing=available-totalSold;
    const retailRevenue=retailSold*positive(s.price), wholesaleRevenue=wholesaleSold*positive(s.wholesalePrice);
    const revenue=retailRevenue+wholesaleRevenue;
    const rawOpening=report.raw.closing || [0,0,0,0,0,0];
    function raw(q, unit, i, emergency) {
      const order=Math.floor(positive(q));
      const start=positive(rawOpening[i]), startValue=positive(rawOpening[i+2]);
      const shortage=Math.max(0,production-start-order);
      const all=start+order+shortage;
      const purchased=order*positive(unit)+shortage*emergency;
      const avg=all ? (startValue+purchased)/all : 0;
      const closing=Math.max(0,all-production);
      return {order,shortage,closing,purchased,used:production*avg,unit:avg};
    }
    const np=s.priceMode==='historical'?tier(positive(s.nylon),'nylon'):positive(s.nylonPrice);
    const rp=s.priceMode==='historical'?tier(positive(s.rods),'rods'):positive(s.rodPrice);
    const nylon=raw(s.nylon,np,0,120), rods=raw(s.rods,rp,3,20);
    const supplies=production*positive(s.supplies);
    const materialUsed=nylon.used+rods.used+supplies;
    const materialCash=nylon.purchased+rods.purchased+supplies;
    const rawStorage=nylon.closing*positive(s.nylonStorage)+rods.closing*positive(s.rodStorage);
    const fgStorage=closing*positive(s.fgStorage);
    const plantCash=machineCount*(positive(s.machineFixed)+positive(s.machineMaintenance));
    const plantDepreciation=machineCount*positive(s.machineDepreciation);
    const depreciation=plantDepreciation+positive(s.otherDepreciation);
    const adminOther=positive(s.adminFixed)+revenue*positive(s.adminRevenueRate)/100;
    const commonOverhead=positive(s.rent)+positive(s.utilities)+positive(s.otherDepreciation)+adminOther;
    const allocation=prodStaff/Math.max(1,prodStaff+salesStaff+positive(s.adminStaff));
    const manufacturing=materialUsed+prodPayroll+temporaryCost+prodFees+plantCash+plantDepreciation+commonOverhead*allocation;
    const manufacturingUnit=production ? manufacturing/production : null;
    const weightedUnit=available ? (fgOpenValue+(production?manufacturing:0))/available : 0;
    const closingValue=closing*weightedUnit;
    const inventoryChange=closingValue-fgOpenValue;
    const cashOperating=materialCash+payroll+prodFees+salesFees+temporaryCost+plantCash+
      positive(s.rent)+positive(s.utilities)+adminOther+positive(s.advertising)+positive(s.promotion)+positive(s.research)+rawStorage+fgStorage;
    const expenses= cashOperating-materialCash+materialUsed+depreciation;
    const operatingProfit=revenue-expenses+inventoryChange;
    const removedBook=removed.reduce((sum,x)=>sum+x.bookValue,0);
    const saleProceeds=removedBook*positive(s.saleRate)/100;
    const disposalLoss=removedBook-saleProceeds;
    const capex=newCount*positive(s.machinePrice);
    const loan=positive(s.loan), loanInterest=loan*positive(s.loanRate)/100;
    const repayment=positive(m.credit)+positive(m.overdraft);
    const dividend=positive(m.profit)*.5;
    const receipts=positive(m.receivables)+revenue*positive(s.receiptRate)/100;
    const cashPreFinance=positive(m.cash)+receipts+saleProceeds-cashOperating-repayment-capex-dividend;
    let overdraft=0, tax=0, profitBeforeTax=0;
    for(let i=0;i<80;i++) {
      const interest=loanInterest+overdraft*positive(s.overdraftRate)/100;
      profitBeforeTax=operatingProfit-disposalLoss-interest;
      tax=Math.max(0,profitBeforeTax)*positive(s.taxRate)/100;
      const cashWithoutOd=cashPreFinance+loan-interest-tax;
      const next=Math.max(0,-cashWithoutOd);
      if(Math.abs(next-overdraft)<.001) {overdraft=next; break;}
      overdraft=next;
    }
    const interest=loanInterest+overdraft*positive(s.overdraftRate)/100;
    profitBeforeTax=operatingProfit-disposalLoss-interest;
    tax=Math.max(0,profitBeforeTax)*positive(s.taxRate)/100;
    const profit=profitBeforeTax-tax;
    const cash=Math.max(0,cashPreFinance+loan+overdraft-interest-tax);
    return {production,requested,capacity,machineCount,permanentCapacity,prodStaff,temporaryFte,temporaryCost,
      payroll,prodPayroll,salesPayroll,adminPayroll,prodFees,salesFees,manufacturing,manufacturingUnit,
      available,wholesaleSold,wholesaleRequested,retailSold,retailAvailable,lostRetail,closing,totalSold,
      retailRevenue,wholesaleRevenue,revenue,nylon,rods,materialUsed,materialCash,rawStorage,fgStorage,
      plantCash,depreciation,adminOther,expenses,inventoryChange,closingValue,operatingProfit,
      capex,saleProceeds,disposalLoss,repayment,dividend,receipts,loan,interest,tax,profit,
      overdraft,cash,netDebt:loan+overdraft-cash,weightedUnit,
      effectiveResearch:positive(s.research)*positive(s.researchFactor),
      potentialRetailRevenue:demand*positive(s.price),planDifference:positive(s.planRevenue)-demand*positive(s.price)};
  }
  function requiredLoan(s,report) {
    let lo=0,hi=2000000;
    for(let i=0;i<35;i++) {
      const mid=(lo+hi)/2; const r=calculate(s,report,{loan:mid});
      if(r.overdraft>.01 || r.cash<positive(s.cashBuffer))lo=mid;else hi=mid;
    }
    return Math.ceil(hi/5000)*5000;
  }
  function presets(s, report) {
    const safe={...copy(s),newMachines:0,sellMachines:0,dismissals:0,attrition:0,
      production:report.metrics.capacity,nylon:report.metrics.capacity,rods:report.metrics.capacity};
    safe.hires=Math.max(0,Math.ceil(safe.production/safe.productivity-report.metrics.productionStaff));
    safe.wholesale=Math.min(safe.wholesaleMax,Math.max(0,Math.floor((safe.production+report.metrics.inventory-safe.demand-20)/10)*10));
    safe.planRevenue=Math.round(safe.demand*safe.price/5000)*5000;
    safe.loan=requiredLoan(safe,report);
    const growth={...copy(safe),newMachines:1,wholesale:safe.wholesaleMax};
    growth.production=Math.ceil(Math.max(0,growth.demand+growth.wholesale+20-report.metrics.inventory)/50)*50;
    growth.nylon=growth.rods=growth.production;
    growth.hires=Math.max(0,Math.ceil(growth.production/growth.productivity-report.metrics.productionStaff));
    growth.loan=requiredLoan(growth,report);
    return {safe,growth};
  }
  const api={defaults,calculate,requiredLoan,presets,copy};
  root.PlanModel=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
