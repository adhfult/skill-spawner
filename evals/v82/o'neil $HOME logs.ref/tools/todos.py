from pathlib import Path
for p in sorted(Path('src').rglob('*.py')):
    if 'vendor' in p.parts:
        continue
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if 'TODO' in line:
            print(f'{p}:{i}')
