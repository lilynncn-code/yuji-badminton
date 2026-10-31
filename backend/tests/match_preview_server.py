"""Temporary, local-only match UI checks. Never modifies the normal application database."""
import asyncio
import json
from datetime import datetime
from pathlib import Path
import preview_server as preview
from fastapi.responses import JSONResponse
from app.services.match_sync import sync_matches
from test_matches import snapshot

source_file = Path(preview.folder.name) / 'matches.json'
control_file = Path(preview.folder.name) / 'control.json'
control_file.write_text('{"delay": 0, "offline": false}')
fixture = snapshot()
fixture['events'][1]['name'] = '检查赛事乙（临时生成）'
fixture['events'][0]['name'] = '检查赛事甲（临时生成）'
fixture['matches'][1]['image_url'] = 'http://127.0.0.1:18004/missing-photo.jpg'
fixture['matches'].append(dict(id='e2-ms-quarter', event_id='e2', discipline='男单', round='四分之一决赛', player1='检查男单甲', player2='检查男单乙', scheduled_at='2026-10-30T10:00:00Z', status='cancelled'))
source_file.write_text(json.dumps(fixture))
last_source = source_file.stat().st_mtime_ns
with preview.Session() as db:
    sync_matches(db, fixture)

@preview.app.middleware('http')
async def match_preview(request, call_next):
    global last_source
    if request.url.path.startswith('/content/matches'):
        control = json.loads(control_file.read_text())
        if control.get('offline'):
            return JSONResponse({'detail': '临时连接失败'}, status_code=503, headers={'Access-Control-Allow-Origin': '*'})
        if control.get('delay'):
            await asyncio.sleep(control['delay'])
        revision = source_file.stat().st_mtime_ns
        if revision != last_source:
            with preview.Session() as db:
                sync_matches(db, json.loads(source_file.read_text()))
            last_source = revision
    return await call_next(request)

Path('/tmp/haoyu-match-preview-path.txt').write_text(preview.folder.name)
print('Match preview: ' + preview.folder.name, flush=True)
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(preview.app, host='127.0.0.1', port=18004, log_level='warning')
