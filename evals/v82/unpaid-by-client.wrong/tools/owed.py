import csv
from collections import defaultdict
tot = defaultdict(float)
for r in csv.DictReader(open('invoices.csv')):
    tot[r['client']] += float(r['amount'])
for c, t in sorted(tot.items(), key=lambda kv: -kv[1]):
    print(f'{c}: {t:.2f}')
print(f'TOTAL: {sum(tot.values()):.2f}')
