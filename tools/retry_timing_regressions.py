"""Serial rerun of the four subprocess-sensitive failures from the full run."""
from pathlib import Path
import subprocess,sys,json
root=Path(__file__).resolve().parents[1]
records=[]
for case in ('test_open_topic_coding','test_open_topic_coding_streamlit','test_verified_coding_catalog','test_correction_verifier.py'):
    result=subprocess.run([sys.executable,'-B',str(root/'tools/evaluate_offline.py'),'--only',case],cwd=root,capture_output=True,text=True)
    print(result.stdout,flush=True)
    records.append(dict(case=case,exit_code=result.returncode,output=result.stdout,stderr=result.stderr))
(root/'data/web-regression-reruns.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
sys.exit(any(r['exit_code'] for r in records))
