import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const dashboard = path.resolve(here, '..');
const repo = path.resolve(dashboard, '..');
const privateArchive = process.env.TECHJAM_EXPERIMENTS || 'C:/Users/ian/Documents/Projects/techjam-conversational-search-private/experiments';
const csv = path.join(privateArchive, 'summary.csv');
const read = (p) => fs.existsSync(p) ? fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '') : '';
const csvRows = (text) => { const [head, ...rows] = text.trim().split(/\r?\n/); const keys=head.split(','); return rows.map(line => { const out=[]; let s='', q=false; for (const c of line+',') { if(c==='"') q=!q; else if(c===','&&!q){out.push(s);s=''}else s+=c; } return Object.fromEntries(keys.map((k,i)=>[k,out[i]??''])); }); };
const descriptions = { E000:'Official BM25 starter baseline', E004:'Clarification-driven candidate split', E010:'Answerability-aware clarification', E021:'Intent fingerprint retrieval', E022:'Other + fingerprint evaluator track', E025D:'Field-aware evidence aggregation', E035B:'Exhaustion recovery', E058:'Phrase-IDF key correction', P001D:'Popularity / rating_number RRF fusion', P002A:'Constraint-safe popularity RRF', P006C:'Wildcard facts and override reset', K004:'P006C × conservative exposure', P007D:'Wildcard-aware exposure', P008A:'Named-information-aware exposure', E060:'Target-propensity reranker', E061:'Phrase matching, final score' };
const manual = [
 ['E000','baseline','KEEP',.10671],['E004','clarification','KEEP',.727529,.739691],['E010','clarification','KEEP',.769408,.785664],['E021','retrieval','KEEP',.792059,.811433],['E022','clarification','KEEP',.854294,.855697],['E025D','retrieval','KEEP',.808106,.824324],['E035B','retrieval','KEEP',.821151,.830124],['E058','retrieval','KEEP',.871721,.865174,.870084],['P001D','popularity','KEEP',.866824,.858864],['P002A','hardening','KEEP',.866894,.859198],['P006C','wildcard','KEEP',.899220,.869145],['K001','exposure','KEEP',.887375],['K004','exposure','KEEP',.922933,.900400],['P007D','exposure','KEEP',.931986,.924000],['P008A','exposure','KEEP',.937169],['E060','target propensity','KEEP',.957400],['E061','ranking','KEEP',.958363],['E065','category','REJECT',.955800],['W001A','exposure','REJECT',.955933]
].map(([id,family,status,dev,holdout,full])=>({id,family,status,dev,holdout,full,description:descriptions[id]||id,source:'curated historical milestone'}));
const rows = csvRows(read(csv));
const latest = new Map();
for (const r of rows) { const key=r.id; const ex=latest.get(key)||{id:key,description:r.name.replaceAll('_',' '),status:r.decision,family:'diagnostic',source:'artifact: summary.csv'}; ex[r.split==='development'?'dev':r.split==='holdout'?'holdout':r.split==='full'?'full':r.split]=Number(r.technical_score)||undefined; ex.mrr=Number(r.mrr)||ex.mrr; ex.hr=Number(r.hit_rate_at_10)||ex.hr; ex.mttc=Number(r.mttc)||ex.mttc; ex.status=r.decision||ex.status; ex.lesson=r.notes; latest.set(key,ex); }
const merged = new Map([...manual.map(x=>[x.id,x]), ...latest]);
for (const m of manual) { const current=merged.get(m.id); merged.set(m.id,{...current,...m, mrr:current?.mrr,hr:current?.hr,mttc:current?.mttc,lesson:current?.lesson}); }
const noteRoots=[path.join(repo,'experiments'),path.join(privateArchive,'notes')];
const notes=[]; for(const root of noteRoots){ if(!fs.existsSync(root))continue; for(const ent of fs.readdirSync(root,{recursive:true,withFileTypes:true})){if(ent.isFile()&&ent.name.endsWith('.md')){const p=path.join(ent.parentPath,ent.name);const body=read(p);notes.push({file:path.relative(repo,p).replaceAll('\\','/'),title:(body.match(/^#\s+(.+)$/m)||[])[1]||ent.name,excerpt:body.replace(/```[\s\S]*?```/g,'').replace(/\s+/g,' ').slice(0,700)});}}}
const diagnostics=[]; for(const root of [path.join(repo,'experiments','diagnostics'),path.join(privateArchive,'diagnostics')]){if(!fs.existsSync(root))continue;for(const ent of fs.readdirSync(root,{recursive:true,withFileTypes:true})){if(ent.isFile()&&ent.name.endsWith('.json')){const p=path.join(ent.parentPath,ent.name);try{const value=JSON.parse(read(p));diagnostics.push({file:path.relative(repo,p).replaceAll('\\','/'),keys:Array.isArray(value)?['array',`length:${value.length}`]:Object.keys(value).slice(0,20)});}catch{diagnostics.push({file:path.relative(repo,p).replaceAll('\\','/'),keys:['unparseable JSON']});}}}}
const data={generatedAt:new Date().toISOString(), archiveAvailable:fs.existsSync(csv), experiments:[...merged.values()].sort((a,b)=>a.id.localeCompare(b.id,undefined,{numeric:true})), notes, diagnostics, sourcePaths:{local:'experiments/', private:privateArchive}};
fs.mkdirSync(path.join(dashboard,'public'),{recursive:true}); fs.writeFileSync(path.join(dashboard,'public','dashboard-data.json'),JSON.stringify(data,null,2));
console.log(`Wrote ${data.experiments.length} experiments, ${notes.length} note excerpts, and ${diagnostics.length} diagnostics.`);
