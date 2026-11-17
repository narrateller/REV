"""Bounded documentary text search; findings never resolve source ambiguities alone."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
PATTERNS={'explicit_moisture_basis':r'wet[ -]basis|dry[ -]basis|dry[ -]matter|Trockenmasse|Trockensubstanz|Nassbasis|base.{0,20}(secca|asciutta)|bezogen.{0,30}(trocken|nass)',
 'moisture_navigation':r'moist|humidi|feucht|umid', 'power_navigation':r'\bkW\b|installed power|main motor|cooling system', 'pressure_unit_navigation':r'kg\s*/\s*c[mn]|kgf|\bbar\b|compaction pressure'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'source_text_search.json');output=ap.parse_args().output
 manifest=json.loads((ROOT/'verification/r1_force_inputs_intake/source_manifest.json').read_text())['sources'];results=[]
 with tempfile.TemporaryDirectory(prefix='rev-source-desk-') as tmp:
  for sid,row in manifest.items():
   raw=(ROOT/row['path']).read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==row['sha256']
   out=Path(tmp)/(sid+'.txt');p=subprocess.run(['pdftotext','-layout',str(ROOT/row['path']),str(out)],capture_output=True,text=True)
   text=out.read_text(errors='replace') if out.exists() else '';pages=text.split('\f');matches={}
   for name,pat in PATTERNS.items():
    hits=[]
    for number,page in enumerate(pages,1):
     lines=[line.strip() for line in page.splitlines() if re.search(pat,line,re.I)]
     if lines:hits.append(dict(pdf_page=number,line_count=len(lines),excerpts=lines[:8] if sid=='BP500' else [],excerpt_scope='RAW source quote only; not REV parameter or ambiguity resolution' if sid=='BP500' else 'Navigation only; no new numerical transcription/adoption'))
    matches[name]=hits
   results.append(dict(source=sid,path=row['path'],sha256=digest,command='pdftotext -layout SOURCE TEMP',returncode=p.returncode,stderr=p.stderr[:1000],extracted_text_bytes=len(text.encode()),extracted_text_sha256=hashlib.sha256(text.encode()).hexdigest(),pdf_pages_with_extracted_text=sum(bool(x.strip()) for x in pages),searches=matches,scope='Text-layer navigation/limited matching only, no full semantic reread; absence of a match is not proof of absence in scans, images or other languages'))
 result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),patterns=PATTERNS,sources=results,source_issues_resolved=False,engineering_values_adopted=False,new_numerical_or_physical_calculations=False)
 output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([dict(source=x['source'],text_pages=x['pdf_pages_with_extracted_text'],explicit_basis_pages=[y['pdf_page'] for y in x['searches']['explicit_moisture_basis']],power_pages=[y['pdf_page'] for y in x['searches']['power_navigation']] if x['source']=='BP500' else []) for x in results]))
if __name__=='__main__':main()
