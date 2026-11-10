"""Independent event-partition oracle; synthetic integer AABBs only."""
import sys, random, json
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"models/kinematic_press"))
from model import overlap_time
rng=random.Random(50101)
for n in range(3000):
    bodies=[]
    for _ in range(2):
        lo=[F(rng.randrange(-5,6)) for i in range(3)]
        bodies.append((lo,[x+rng.randrange(1,4) for x in lo],[F(rng.randrange(-7,8)) for i in range(3)]))
    a,b=bodies
    events={F(0),F(1)}
    for i in range(3):
        for x in ((a[0][i]-b[1][i],a[1][i]-b[0][i])):
            v=a[2][i]-b[2][i]
            if v and 0<=-x/v<=1: events.add(-x/v)
    ts=sorted(events)
    candidates=ts+[(l+r)/2 for l,r in zip(ts,ts[1:])]
    def present(t):
        return all(max(a[0][i]+t*a[2][i],b[0][i]+t*b[2][i])<=min(a[1][i]+t*a[2][i],b[1][i]+t*b[2][i]) for i in range(3))
    expected=any(present(t) for t in candidates)
    assert (overlap_time(a,b) is not None)==expected,(n,a,b)
print("PASS: 3000 independent event-partition comparisons; seed 50101")
