import re
from collections import Counter
c = Counter()
for line in open('app.log'):
    m = re.match(r'\S+ \S+ ERROR (\w+):', line)
    if m:
        c[m.group(1)] += 1
for mod, n in c.most_common():
    print(f'{mod}: {n}')
