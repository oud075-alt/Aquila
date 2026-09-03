const assert = require("node:assert/strict");

const UA = process.env.SEC_USER_AGENT;
if (!UA) throw new Error("SEC_USER_AGENT missing");

async function secJson(url) {
  const r = await fetch(url, { headers: { "User-Agent": UA, "Accept": "application/json" } });
  const text = await r.text();
  if (!r.ok) throw new Error("SEC HTTP " + r.status + " " + text.slice(0,120));
  if (!(r.headers.get("content-type")||"").toLowerCase().includes("json")) throw new Error("SEC non-JSON");
  return JSON.parse(text);
}
function vals(cf, tag) {
  return cf?.facts?.["us-gaap"]?.[tag]?.units?.USD || [];
}
function latestAnnual(a) {
  return a.filter(x => /^10-K/.test(x.form||"") && x.start && x.end)
    .filter(x => (Date.parse(x.end)-Date.parse(x.start))/86400000 >= 300)
    .sort((a,b)=>(b.end||"").localeCompare(a.end||"") || (b.filed||"").localeCompare(a.filed||""))[0] || null;
}
function ytd(a) {
  return a.filter(x => /^10-Q/.test(x.form||"") && x.start && x.end)
    .filter(x => { const d=(Date.parse(x.end)-Date.parse(x.start))/86400000; return d>=60 && d<=320; })
    .sort((a,b)=>(b.end||"").localeCompare(a.end||"") || (b.filed||"").localeCompare(a.filed||""));
}
function ttm(a) {
  const ann=latestAnnual(a); assert(ann,"annual missing");
  const after=ytd(a).filter(x=>x.end>ann.end); 
  if(!after.length) return Number(ann.val);
  const end=after[0].end;
  const cur=after.filter(x=>x.end===end).sort((a,b)=>(Date.parse(b.end)-Date.parse(b.start))-(Date.parse(a.end)-Date.parse(a.start)))[0];
  const dur=(Date.parse(cur.end)-Date.parse(cur.start))/86400000;
  const prior=ytd(a).filter(x=>x.end<cur.end).map(x=>({x,g:Math.abs((Date.parse(cur.end)-Date.parse(x.end))/86400000-365),d:Math.abs((Date.parse(x.end)-Date.parse(x.start))/86400000-dur)})).filter(o=>o.g<=100&&o.d<=50).sort((a,b)=>(a.g+a.d)-(b.g+b.d))[0]?.x;
  assert(prior,"prior ytd missing");
  return Number(ann.val)+Number(cur.val)-Number(prior.val);
}
function firstTag(cf,tags){for(const t of tags){const a=vals(cf,t);if(a.length)return {t,a};}throw new Error("tag missing "+tags.join(","));}

(async()=>{
  const url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000796343.json";
  const cf=await secJson(url);
  assert.equal(Number(cf.cik),796343);
  assert.match(cf.entityName,/ADOBE/i);

  const rev=firstTag(cf,["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"]);
  const ni=firstTag(cf,["NetIncomeLoss","ProfitLoss"]);
  const ocf=firstTag(cf,["NetCashProvidedByUsedInOperatingActivities"]);
  const cap=firstTag(cf,["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsForAdditionsToPropertyPlantAndEquipment"]);

  const revTTM=ttm(rev.a), niTTM=ttm(ni.a), ocfTTM=ttm(ocf.a), capTTM=ttm(cap.a), fcfTTM=ocfTTM-Math.abs(capTTM);

  // Exact truth anchors from Adobe FY2025 10-K + Q2 FY2026 10-Q:
  assert.equal(ocfTTM, 10481000000);
  assert.equal(Math.abs(capTTM), 201000000);
  assert.equal(fcfTTM, 10280000000);
  assert.equal(revTTM, 25198000000);
  assert.equal(niTTM, 7229000000);

  console.log(JSON.stringify({PASS:true,source:"data.sec.gov",entity:cf.entityName,cik:cf.cik,tags:{rev:rev.t,ni:ni.t,ocf:ocf.t,cap:cap.t},revTTM,niTTM,ocfTTM,capTTM,fcfTTM}));
})().catch(e=>{console.error(e.stack||e);process.exit(1);});