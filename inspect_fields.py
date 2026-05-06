#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from etl.client import ServiceNowClient

c = ServiceNowClient()
resp = c.get('sn_customerservice_case', params={'sysparm_limit': 1})
record = resp.json().get('result', [{}])[0]

print('Time/Update fields that could support incremental extraction:')
time_fields = [k for k in record.keys() if any(x in k.lower() for x in ['time', 'date', 'on', 'created', 'updated', 'sys_'])]
for key in sorted(time_fields):
    val = record[key]
    if isinstance(val, dict):
        print(f'  {key}: {val.get("display_value", val.get("value", "?"))}')
    else:
        print(f'  {key}: {val}')

print('\nSample record structure (first 5 fields):')
for key in list(record.keys())[:5]:
    val = record[key]
    if isinstance(val, dict):
        print(f'  {key}: {val}')
    else:
        print(f'  {key}: {str(val)[:60]}...')
