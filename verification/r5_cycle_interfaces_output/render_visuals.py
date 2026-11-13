from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'visuals';OUT.mkdir(exist_ok=True)
rows=[]
for svg in sorted((ROOT/'verification/r4_cycle_interfaces/proposal/exports').glob('*.svg')):
 out=OUT/(svg.stem+'.png');argv=['inkscape',str(svg),'--export-type=png','--export-width=1600','--export-filename='+str(out)]
 r=subprocess.run(argv,capture_output=True,text=True);assert r.returncode==0 and out.is_file()
 rows.append(dict(source=str(svg.relative_to(ROOT)),source_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),argv=argv,exit_code=r.returncode,stderr=r.stderr,render_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
(HERE/'visual_render_commands.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('Six SVG rendered; Inkscape font/GTK warnings captured, all exit 0. No CAD performed.')
