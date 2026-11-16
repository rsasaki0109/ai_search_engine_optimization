"""Manual live-network check; never part of CI. Fetches each page and robots.txt."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

URLS = ['https://example.com', 'http://example.com', 'https://www.python.org/',
        'https://www.sqlite.org/index.html', 'https://developer.mozilla.org/en-US/',
        'https://www.rfc-editor.org/rfc/rfc9309', 'https://www.w3.org/standards/',
        'https://www.iana.org/domains/reserved', 'https://www.wikipedia.org/',
        'https://www.gnu.org/software/', 'https://www.rust-lang.org/']


def main():
    rows=[]
    original=app.fetch
    for url in URLS:
        events=[]
        def tracked(target,deadline=None):
            result=original(target,deadline)
            events.append(dict(requested=target,final=result['url'],status=result['status']))
            return result
        app.fetch=tracked
        started=time.monotonic()
        row=dict(url=url)
        try:
            report=app.audit(url)
            row.update(outcome='diagnosed',score=report['score'],checks=len(report['checks']),bots=len(report['bots']),robots_note=report['robots_error'])
        except (ValueError,OSError,app.http.client.HTTPException) as error:
            row.update(outcome='failed',error_type=type(error).__name__,error=app.error_message(error))
        except Exception as error:
            row.update(outcome='unexpected_error',error_type=type(error).__name__)
        finally: app.fetch=original
        row.update(seconds=round(time.monotonic()-started,2),requests=events)
        rows.append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    result=dict(checked_at=datetime.now(timezone.utc).isoformat(),results=rows)
    out=Path(__file__).resolve().parents[1]/'docs'/'public-site-validation.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Saved',out,flush=True)

if __name__=='__main__':main()
