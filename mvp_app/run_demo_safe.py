import runpy
import traceback
import os
from datetime import datetime

LOG = os.path.join(os.path.dirname(__file__), 'demo_run.log')

with open(LOG, 'a', encoding='utf-8') as f:
    f.write('\n----- run at ' + datetime.now().isoformat() + ' -----\n')
    try:
        runpy.run_path(os.path.join(os.path.dirname(__file__), 'demo_run.py'), run_name='__main__')
        f.write('demo_run executed successfully.\n')
    except Exception as e:
        f.write('Exception during demo_run:\n')
        f.write(traceback.format_exc())
        f.write('\n')

print('done (check demo_run.log)')
