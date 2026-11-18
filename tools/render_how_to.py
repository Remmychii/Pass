"""Render tools/how_to.html to docs/how-to.png (1080x1080) with headless Chrome or Edge."""
import os, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'tools' / 'how_to.html'
OUT = ROOT / 'docs' / 'how-to.png'
BROWSERS = [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']

OUT.parent.mkdir(exist_ok=True)
exe = next(b for b in BROWSERS if os.path.exists(b))
subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                '--window-size=1080,1080', f'--screenshot={OUT}', SRC.as_uri()], capture_output=True)
print(OUT)
