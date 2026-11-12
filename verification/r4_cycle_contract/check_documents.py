#!/usr/bin/env python3
"""Read-only document consistency check; no material/CAD/physical computation.

The expected examples are authored hypothetical guard assignments. Matching
them checks the written truth table, not the truth of any REV observation.
"""
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(name):
    return json.loads((HERE / name).read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(rows):
    result = {r['id']: r for r in rows}
    require(len(result) == len(rows), 'duplicate document ID')
    return result


def classify(transition, before, guards):
    require(set(guards) == set(transition['required_guards']), 'missing/extra guard in example')
    require(set(guards.values()) <= {'TRUE', 'FALSE', 'UNKNOWN'}, 'invalid truth value')
    if before not in transition['from_states'] or 'FALSE' in guards.values():
        return 'BLOCKED'
    if 'UNKNOWN' in guards.values():
        return 'INDETERMINATE'
    return 'ALLOWED_ASSUMED'


def main():
    c = read('contract.json')
    questions = index(read('questions.json'))
    guards = index(c['guards'])
    transitions = index(c['transitions'])
    states = {s for values in c['states'].values() for s in values}
    require(sum(map(len, c['states'].values())) == len(states), 'duplicate state')
    require(len(c['events']) == len(set(c['events'])), 'duplicate event')
    source_rows = {r['id'] for r in json.loads((HERE.parent / 'r3_cycle_trace/cycle_table.json').read_text())}
    for g in guards.values():
        require(g['question'] in questions, 'unowned guard')
        require(g['actual_value'] is None and g['status'] == 'UNKNOWN' and g['unknown_reason'], 'actual guard fabricated')
    for t in transitions.values():
        require(t['event'] in c['events'], 'unsupported event in document')
        require(set(t['from_states'] + [t['to_state']]) <= set(c['states'][t['variant']]), 'state/variant mismatch')
        require(set(t['required_guards']) <= guards.keys(), 'undefined guard')
        require(len(t['required_guards']) == len(set(t['required_guards'])), 'duplicate required guard')
        require(set(t['source_rows']) <= source_rows and t['source_rows'], 'missing source trace')
        require(t['evidence'] and t['inventory_effect'], 'missing evidence/effect')
        if t['event'] == 'REQUEST_READY':
            require(t['from_states'] == [t['to_state']], 'READY changes material')
        if t['event'] == 'REMOVE_GEOMETRY':
            require({'RECEIPT_VALID', 'WHOLE_BEYOND_EXIT', 'NO_MODEL_INTERACTION'} <= set(t['required_guards']), 'unsafe documentary REMOVE')
    for target, ready in c['ready_targets'].items():
        observed = [t for t in transitions.values() if t['event'] == 'REQUEST_READY' and (t['id'] == target or t['id'].startswith(target+'-'))]
        require({s for t in observed for s in t['from_states']} == set(ready['from_states']), 'READY target not covered')
        require(all(set(t['required_guards']) == set(ready['required_guards']) for t in observed), 'READY guards drift')
    for q in questions.values():
        require(q['response'] is None and q['status'] == 'AWAITING_RESPONSE', 'invented role response')
        require(set(q['blocked_guards']) == {g['id'] for g in guards.values() if g['question'] == q['id']}, 'question/guard drift')
        require(set(q['blocked_transitions']) == {t['id'] for t in transitions.values() if set(t['required_guards']) & set(q['blocked_guards'])}, 'question/transition drift')
    examples = read('transition_examples.json')
    index(examples)
    outcomes = collections.Counter()
    for e in examples:
        t = transitions[e['transition']]
        require(e['event'] == t['event'], 'example event mismatch')
        require(e['before'] in states, 'undefined example state')
        result = classify(t, e['before'], e['guard_values'])
        require(result == e['expected'], 'unexpected example: ' + e['id'])
        require(e['after'] == (t['to_state'] if result == 'ALLOWED_ASSUMED' else e['before']), 'blocked example changes state')
        require(e['physical_permission'] is False and e['guard_evidence'] and e['reason'], 'example claims physical evidence')
        require(e['id'] in (HERE / 'transition_examples.md').read_text(), 'example missing from readable table')
        outcomes[result] += 1
    require(set(outcomes) == {'ALLOWED_ASSUMED', 'BLOCKED', 'INDETERMINATE'}, 'missing truth-table category')
    sequences = read('sequence_examples.json')
    index(sequences)
    for sequence in sequences:
        state = sequence['initial_state']
        require(sequence['physical_permission'] is False, 'sequence claims physical permission')
        index([dict(step, id=step['step_id']) for step in sequence['steps']])
        for step in sequence['steps']:
            t = transitions[step['transition']]
            require(state == step['before'], 'sequence discontinuity')
            require(classify(t, state, step['guard_values']) == 'ALLOWED_ASSUMED', 'invalid hypothetical sequence')
            require(step['after'] == t['to_state'], 'sequence state mismatch')
            state = step['after']
        require(state == sequence['final_state'], 'wrong sequence final state')
    resources = read('resources.json')
    require(len(resources) == len(source_rows) and {r['source_row'] for r in resources} == source_rows, 'incomplete resource stages')
    for r in resources:
        require(r['start_end'] and r['predecessors'] and r['consumers'] and r['material_interface'], 'missing resource interface')
        require((r['kind'] == 'RESOURCE_OVERLAY') == (r['source_row'] in {'A8','B8'}), 'resource overlay treated as timed stage')
        for v in r['quantities'].values():
            require(v['value'] is None and v['status'] == 'UNKNOWN' and v['unit'] and v['unknown_reason'], 'hidden numeric resource input')
    trace = read('traceability.json')
    require(len(trace) == len(source_rows) and {r['source_row'] for r in trace} == source_rows, 'incomplete source trace')
    for r in trace:
        require(set(r['transitions']) == {t['id'] for t in transitions.values() if r['source_row'] in t['source_rows']}, 'trace drift')
        require(r['status'] == 'OPEN' and set(r['questions']) <= questions.keys(), 'trace closes source issue')
    audit, preflight = read('input_acceptance.json'), read('preflight.json')
    require(audit['owner_session'] == 'r4-linked-20261111' and audit['lease_valid'], 'input audit owner/lease')
    for src in preflight['sources']:
        data = git('show', src['commit'] + ':' + src['path'])
        require(hashlib.sha256(data).hexdigest() == src['sha256'], 'immutable input mismatch: ' + src['path'])
        if src['in_current_main_worktree']:
            require((ROOT / src['path']).read_bytes() == data, 'changed current source: ' + src['path'])
    for path, tree in preflight['protected_main_git_trees'].items():
        require(git('rev-parse', audit['main'] + ':' + path).decode().strip() == tree, 'protected base drift: ' + path)
        require(not git('diff', audit['main'], '--', path), 'protected working diff: ' + path)
        require(not git('ls-files', '--others', '--exclude-standard', '--', path), 'untracked protected file: ' + path)
    for path, tree in preflight['protected_unmerged_CAD_git_trees'].items():
        require(git('rev-parse', preflight['protected_unmerged_CAD_commit'] + ':' + path).decode().strip() == tree, 'candidate CAD changed')
    print(json.dumps(dict(scope='DOCUMENT_CONSISTENCY_ONLY',document_checks='MATCH',examples=len(examples),sequences=len(sequences),outcomes=dict(sorted(outcomes.items())),source_rows=len(source_rows),questions=len(questions),transitions=len(transitions),guards=len(guards),source_blobs=len(preflight['sources']),protected_main_trees=len(preflight['protected_main_git_trees']),sources_and_protected_trees='UNCHANGED',real_REV='UNKNOWN',numerical_solvers_CAD_rebuild_physical_tests='NOT_RUN',independent_review='NOT_RUN',G1='OPEN'),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('DOCUMENT_CHECK_FAILED: ' + str(error), file=sys.stderr)
        sys.exit(1)
