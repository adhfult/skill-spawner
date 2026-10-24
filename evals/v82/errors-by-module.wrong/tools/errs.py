import re
from collections import Counter
c = Counter()
for line in open('app.log'):
    m = re.search(r'(\w+):', line.split(' ', 3)[3]) if 'ERROR' in line else None
    if m:
        c[m.group(1)] += 1
for mod, n in c.most_common():
    print(f'{mod}: {n}')
