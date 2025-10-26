#!/usr/bin/env python3
import requests
import json

response = requests.post(
    'http://localhost:5000/api/chat',
    json={'player_id': 'Debug3', 'npc_name': 'elira', 'area': 'Forest', 'message': 'notecard please'}
)

data = response.json()
resp = data.get('npc_response', '')

idx = resp.find('[notecard=')
if idx != -1:
    print(f'Found [notecard= at position {idx}')
    print('Next 600 chars:')
    print(repr(resp[idx:idx+600]))

    # Check for pipe
    pipe_idx = resp.find('|', idx)
    print(f'\nPipe | at position {pipe_idx} (relative: {pipe_idx - idx})')

    # Check for closing bracket
    close_idx = resp.find(']', idx)
    print(f'Closing ] at position {close_idx} (relative: {close_idx - idx})')

    if close_idx != -1:
        full_notecard = resp[idx:close_idx+1]
        print(f'\nFull notecard length: {len(full_notecard)}')
else:
    print('No [notecard= found')
    print('Response length:', len(resp))
    print('First 500:', resp[:500])
