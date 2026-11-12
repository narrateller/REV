"""NEW reporting, not a modification of the reviewed collision tool.

Enumerates every non-CLEAR pair (including negative controls) without exclusions.
Native samples prove penetration at a pose, never absence on an entire stroke.
"""
import argparse, collections, gzip, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'cad/layout_correction'))
from assess import NativeWitness, POLICY


def inventory(models, destination, extra_raw=None):
    models, destination = Path(models), Path(destination)
    scenes = json.loads(gzip.decompress((models/'raw_checked_tool/all_pairs.json.gz').read_bytes()))
    scenes += json.loads(gzip.decompress((models/'service_scenes.json.gz').read_bytes()))
    lookup = {(s['variant'], s['case'], st['phase']): st for s in scenes for st in s['stages']}
    records = {}
    with gzip.open(models/'classifications.jsonl.gz', 'rt') as stream:
        for line in stream:
            r = json.loads(line)
            if r['class'] == 'CLEAR':
                continue
            key = (r['variant'], *r['pair'])
            record = records.setdefault(key, {'variant': r['variant'], 'pair': r['pair'], 'classes': collections.Counter(), 'contexts': set(), 'representatives': {}})
            record['classes'][r['class']] += 1
            record['contexts'].add((r['case'], r['phase']))
            record['representatives'].setdefault(r['class'], r)
    native = NativeWitness(models)
    try:
        for key, record in sorted(records.items()):
            witnesses = []
            for cls, r in sorted(record.pop('representatives').items()):
                stage = lookup[(r['variant'], r['case'], r['phase'])]
                time = next((e['witness_time'] for e in r.get('regions', []) if e['kind'] == 'PENETRATION'), stage['time'][0])
                w = native.at(r['variant'], r['pair'], stage['state'], time, stage['time'])
                witnesses.append({'case': r['case'], 'phase': r['phase'], 'raw_class': cls, **w})
            record['native_representatives'] = witnesses
            record['contexts'] = [{'case': c, 'phase': p} for c, p in sorted(record['contexts'])]
            classes = record['classes']
            positive = any(w.get('common_volume_mm3', 0) > 1e-5 for w in witnesses)
            conditional = set(classes) == {'ALLOWED_SYNTHETIC_TOUCH'}
            envelope = set(classes) <= {'ENVELOPE_INTERSECTION'}
            record['classification'] = ('NATIVE_PENETRATION' if positive else 'CONDITIONAL_MATING' if conditional else 'CONDITIONAL_ENVELOPE_INTERSECTION' if envelope else 'INDETERMINATE')
            record['basis'] = ('positive native Part.common at specified pose; full-interval evidence remains in classifications' if positive else 'existing reviewed positive-area nominal face policy, no physical joint approval' if conditional else 'conservative bounds overlap; native continuous geometry not established' if envelope else 'unclassified/tiny/curved/contact/unknown motion; no unsupported CLEAR inference')
            record['control_context'] = any(n.startswith('research_obstacle') for n in record['pair']) or all(c['case'] == 'unknown' for c in record['contexts'])
            record['status'] = 'NEGATIVE_CONTROL' if record['control_context'] else 'OPEN' if not conditional else 'ASSUMED_INTERFACE_ONLY'
        rows = list(records.values())
        for i, r in enumerate(sorted(rows, key=lambda x: (x['variant'], x['pair']))):
            r['id'] = 'FM-' + str(i+1).zfill(4)
        result = {'scope': 'finite registry of every non-CLEAR pair in the published work/return/service scenes, not arbitrary plant states', 'rows': sorted(rows, key=lambda x: x['id']), 'summary': dict(collections.Counter(r['classification'] for r in rows)), 'whole_press_READY': 'INDETERMINATE', 'physical_parameters': 'UNKNOWN', 'G1': 'OPEN'}
        destination.mkdir(parents=True, exist_ok=True)
        (destination/'inventory.json').write_text(json.dumps(result, indent=2)+'\n')
        lines = ['# Конечный реестр непустых конфликтов и контактов', '', 'Каждая пара приведена один раз; все фазы, классы и нативные свидетельства — в JSON. Отрицательные synthetic-контроли отмечены отдельно. Это конечный список для заданных сцен, не исчерпывающий список состояний реального пресса.', '', '| ID | Вариант | Пара | Класс | Статус |', '|---|---|---|---|---|']
        lines += [f"| {r['id']} | {r['variant']} | {' / '.join(r['pair'])} | {r['classification']} | {r['status']} |" for r in result['rows']]
        lines += ['', 'Native witness доказывает положительное внедрение в указанном положении. Нулевой объём в выборке не доказывает свободный ход. CONDITIONAL_MATING — условный геометрический интерфейс с UNKNOWN крепежом/прочностью; INDETERMINATE не разрешает эксплуатацию. G1 OPEN.']
        (destination/'inventory.md').write_text('\n'.join(lines)+'\n')
        return result
    finally:
        native.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--models', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); r = inventory(a.models, a.out); print(json.dumps({'pairs': len(r['rows']), 'summary': r['summary']}))
