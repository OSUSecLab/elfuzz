import json

with open('sqlite3_1_100_results.json') as f:
    results = json.load(f)

items = list(results.items())
items.sort(key=lambda x: x[1])
for k, v in items:
    print(f'{k}: {v}')
