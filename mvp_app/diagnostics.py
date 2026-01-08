import sys
import platform
import shutil
import pkgutil
import subprocess
import traceback
import os
from datetime import datetime

LOG = os.path.join(os.path.dirname(__file__), 'diagnostics.log')
with open(LOG, 'a', encoding='utf-8') as f:
    f.write('\n----- DIAGNOSTICS RUN at ' + datetime.now().isoformat() + ' -----\n')
    try:
        f.write('Python executable: ' + sys.executable + '\n')
        f.write('Python version: ' + sys.version.replace('\n',' ') + '\n')
        f.write('Platform: ' + platform.platform() + '\n')

        # pip list
        try:
            import pkg_resources
            pkgs = sorted([p.project_name + '==' + p.version for p in pkg_resources.working_set])
            f.write('Installed packages (sample 100):\n')
            for p in pkgs[:200]:
                f.write('  ' + p + '\n')
        except Exception as e:
            f.write('pkg_resources failed: ' + repr(e) + '\n')

        # check tesseract
        tesseract_path = shutil.which('tesseract')
        f.write('tesseract in PATH: ' + str(tesseract_path) + '\n')
        try:
            import pytesseract
            try:
                v = pytesseract.get_tesseract_version()
                f.write('pytesseract.get_tesseract_version: ' + str(v) + '\n')
            except Exception as e:
                f.write('pytesseract present but get_tesseract_version failed: ' + repr(e) + '\n')
        except Exception as e:
            f.write('pytesseract import failed: ' + repr(e) + '\n')

        # check PIL
        try:
            from PIL import Image
            f.write('Pillow imported OK.\n')
        except Exception as e:
            f.write('Pillow import failed: ' + repr(e) + '\n')

        # Report environment variables of interest
        f.write('ENV OPENAI_API_KEY set: ' + str(bool(os.getenv('OPENAI_API_KEY'))) + '\n')
        f.write('ENV USE_GOOGLE_VISION: ' + str(os.getenv('USE_GOOGLE_VISION')) + '\n')

        # Run demo_run.py and capture stdout/stderr
        demo = os.path.join(os.path.dirname(__file__), 'demo_run.py')
        f.write('\n--- Running demo_run.py ---\n')
        try:
            proc = subprocess.run([sys.executable, demo], capture_output=True, text=True, timeout=30)
            f.write('demo stdout:\n' + proc.stdout + '\n')
            f.write('demo stderr:\n' + proc.stderr + '\n')
            f.write('demo returncode: ' + str(proc.returncode) + '\n')
        except subprocess.TimeoutExpired as e:
            f.write('demo_run.py timed out: ' + repr(e) + '\n')
        except Exception as e:
            f.write('demo_run.py failed to run: ' + repr(e) + '\n')

    except Exception as e:
        f.write('DIAGNOSTICS INTERNAL EXCEPTION:\n')
        f.write(traceback.format_exc())

print('Diagnostics written to', LOG)
