import csv
from collections import defaultdict
tot = defaultdict(float)
for r in csv.DictReader(open('invoices.csv')):
    if r['paid'] != 'yes':
        tot[r['client']] += float(r['amount'])
for c, t in sorted(tot.items(), key=lambda kv: -kv[1]):
    print(f'{c}: {t:.2f}')
