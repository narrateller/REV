# Assessment exit coverage

220 functional cases, 8/8 assessment returns executed. Every return calls the common finish. This measures assessment exits; it is not a claim about every boolean expression or physical behaviour. Detailed cases and input digests: cases.json.

| Exit | Source line | Executed cases | BLOCKED | INDETERMINATE | ALLOWED_ASSUMED |
|---|---|---|---|---|---|
| unsupported/unavailable definitions | 59 | 5 | 0 | 5 | 0 |
| non-object context | 67 | 5 | 0 | 5 | 0 |
| non-object proof | 161 | 134 | 54 | 80 | 0 |
| missing/invalid/unknown target | 163 | 21 | 6 | 15 | 0 |
| unsupported proof action/guard | 166 | 20 | 7 | 13 | 0 |
| rejected snapshots/schema/history | 229 | 26 | 16 | 10 | 0 |
| frozen policy exception | 240 | 3 | 2 | 1 | 0 |
| admitted policy outcome | 243 | 6 | 1 | 0 | 5 |

Definition/context exits have no trustworthy independent source to assert FALSE. Other exits preserve confirmed own/causal prohibitions. A missing target never becomes a guessed fault. Fault operation metadata is required only where its guard is operation-specific (EVENT_FRESH); it does not erase a known resource/causal prohibition.
