"""Pass (パス): move files between the PC and a phone over home Wi-Fi with a QR code.
Made by Rem (レム). MIT license.

    Pass.exe / pythonw pass_app.py [file ...]      app window (files open on Send)
    pythonw pass_app.py --receive                  app window on Receive
    python  pass_app.py --no-gui <file ...>        headless send, prints the URL (tests)
    python  pass_app.py --no-gui --receive [dir]   headless receive

Files go byte for byte (no re-encoding). Each share has a random link, only the
chosen files are served, and a share stops when the window closes or after
IDLE_MIN minutes with no transfers. Received files never overwrite: a clash gets
" (1)", " (2)" ... added.
"""
import html, json, mimetypes, os, re, secrets, socket, sys, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = 'Pass'
IDLE_MIN = 20
CHUNK = 1 << 20
CREDIT_URL = 'https://github.com/Remmychii/Pass'
ACCENT = '#e05a70'                               # Rem pink (same as ループ Loop)


def downloads_dir():
    """The Windows Downloads folder (follows a moved one, e.g. D:\\Downloads)."""
    try:
        import ctypes, uuid
        guid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('{374DE290-123F-4565-9164-39C4925E467B}').bytes_le)
        p = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, 0, ctypes.byref(p)) == 0:
            path = p.value
            ctypes.windll.ole32.CoTaskMemFree(p)
            return path
    except Exception:
        pass
    return os.path.join(os.path.expanduser('~'), 'Downloads')


RECEIVE_DIR = os.path.join(downloads_dir(), 'From Phone')


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))       # no packet is sent; just picks the Wi-Fi/LAN interface
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


def free_port(start=3000):
    for p in range(start, start + 100):
        with socket.socket() as c:              # Windows lets 0.0.0.0 bind over a 127.0.0.1-only server: skip those
            c.settimeout(0.2)
            if c.connect_ex(('127.0.0.1', p)) == 0:
                continue
        with socket.socket() as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    raise SystemExit('no free port from 3000')


def human(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB':
            return f'{n:.0f} {u}' if u == 'B' else f'{n:.1f} {u}'
        n /= 1024


def serve(handler):
    port = free_port()
    srv = ThreadingHTTPServer(('0.0.0.0', port), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


# ---------------------------------------------------------------- phone pages (shared look)

PHONE_CSS = """
:root{--bg:#120e10;--card:#1d1719;--ink:#f0eae6;--mute:#968c8c;--line:#2f2729;--acc:__ACC__;--ok:#5fbf8a;--bad:#ff8a8a}
*{box-sizing:border-box;touch-action:manipulation}
html{-webkit-tap-highlight-color:transparent;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,sans-serif;padding:22px 16px 28px;overflow-x:hidden}
.top{display:flex;align-items:baseline;gap:8px;margin:0 0 4px}
.top b{font:900 19px "Hiragino Mincho ProN","Yu Mincho",serif;letter-spacing:.06em}.top span{color:var(--mute);font-size:13px}
.foot b{color:var(--acc);font:900 12px "Hiragino Mincho ProN","Yu Mincho",serif;letter-spacing:.04em}
.lbl{font-size:10.5px;font-weight:600;letter-spacing:.24em;text-transform:uppercase;color:var(--mute);margin:18px 0 8px}
.f{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px;margin:0 0 8px}
.n{word-break:break-all;font-weight:600}.s{color:var(--mute);font-size:13px;margin:2px 0 10px}
.b,label.pick{display:block;width:100%;text-align:center;font:inherit;font-weight:700;padding:12px;border-radius:4px;border:1px solid var(--acc);background:var(--acc);color:var(--bg);text-decoration:none}
label.pick{background:none;color:var(--ink);border:1px dashed var(--line)}
button.b:disabled{opacity:.4}
input[type=file]{display:none}
.bar{height:4px;background:var(--line);border-radius:2px;overflow:hidden}.bar i{display:block;height:100%;width:0;background:var(--acc)}
.f.ok .bar i{background:var(--ok)}.f.bad .s{color:var(--bad)}
.h{color:var(--mute);font-size:13px;margin-top:18px;overflow-wrap:anywhere}.h b{color:var(--ink);font-weight:600}
.foot{color:var(--mute);font-size:11px;margin-top:26px;letter-spacing:.04em}
:focus{outline:none}
@media (hover:hover){label.pick:hover{border-color:var(--mute)}.b:hover{filter:brightness(1.08)}}
"""

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#120e10"><title>Pass</title><style>__CSS__</style></head><body>
<div class="top"><b>パス</b><span>pass</span></div>"""

PAGE_FOOT = '<p class="foot">Pass · made by <b>レム</b></p></body></html>'


def phone_page(body):
    return (PAGE_HEAD.replace('__CSS__', PHONE_CSS.replace('__ACC__', ACCENT)) + body + PAGE_FOOT).encode()


# ---------------------------------------------------------------- PC -> phone

class State:
    def __init__(self, files):
        self.files = []                          # absolute paths
        self.sent, self.done = [], []
        self.token = secrets.token_urlsafe(9)
        self.last = time.time()
        self.active = 0
        self.lock = threading.Lock()
        self.add(files)

    def add(self, files):
        with self.lock:
            for f in files:
                f = os.path.abspath(f)
                if os.path.isfile(f) and f not in self.files:
                    self.files.append(f); self.sent.append(0); self.done.append(False)
        self.last = time.time()


def make_handler(st):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            parts = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).strip('/').split('/')
            if not parts or parts[0] != st.token:
                return self.send_error(404)
            st.last = time.time()
            if len(parts) == 1:
                return self.page()
            try:
                i = int(parts[1])
                path = st.files[i]
            except (ValueError, IndexError):
                return self.send_error(404)
            self.send_file(i, path)

        do_HEAD = do_GET

        def page(self):
            items = ''.join(
                f'<div class="f"><div class="n">{html.escape(os.path.basename(p))}</div>'
                f'<div class="s">{human(os.path.getsize(p))}</div>'
                f'<a class="b" href="/{st.token}/{i}/{urllib.parse.quote(os.path.basename(p))}" download>Download</a></div>'
                for i, p in enumerate(list(st.files)) if os.path.isfile(p))
            body = phone_page(
                '<div class="lbl">From your PC</div>' + (items or '<p class="h">No files yet.</p>') +
                '<p class="h">Tap <b>Download</b>, then <b>Files › Downloads</b> → tap the file → '
                '<b>Share</b> → <b>Save Video</b> (or Save Image) to put it in Photos.<br><br>'
                'Keep Safari open until it finishes.</p>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def send_file(self, i, path):
            size = os.path.getsize(path)
            start, end = 0, size - 1
            rng = self.headers.get('Range', '')
            if rng.startswith('bytes='):                       # lets Safari resume or seek
                a, _, b = rng[6:].split(',')[0].partition('-')
                try:
                    if a:
                        start = int(a); end = int(b) if b else size - 1
                    else:
                        start = size - int(b)
                except ValueError:
                    return self.send_error(416)
                if start < 0 or start >= size or end < start:
                    self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers()
                    return
                end = min(end, size - 1)
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            else:
                self.send_response(200)
            name = os.path.basename(path)
            ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Disposition',
                             "attachment; filename*=UTF-8''" + urllib.parse.quote(name))
            self.end_headers()
            if self.command == 'HEAD':
                return
            with st.lock:
                st.active += 1
            try:
                with open(path, 'rb') as f:
                    f.seek(start)
                    left = end - start + 1
                    pos = start
                    while left > 0:
                        buf = f.read(min(CHUNK, left))
                        if not buf:
                            break
                        self.wfile.write(buf)
                        left -= len(buf); pos += len(buf)
                        st.last = time.time()
                        with st.lock:
                            st.sent[i] = max(st.sent[i], pos)
                    if pos >= size:
                        st.done[i] = True
            except (ConnectionError, OSError):
                pass                                            # phone left; it can resume with Range
            finally:
                with st.lock:
                    st.active -= 1

    return H


def start_server(files):
    st = State(files)
    srv, port = serve(make_handler(st))
    return st, srv, f'http://{lan_ip()}:{port}/{st.token}/'


# ---------------------------------------------------------------- phone -> PC

class RecvState:
    def __init__(self, folder):
        self.folder = folder
        self.token = secrets.token_urlsafe(9)
        self.items = []                         # [name, size, got, status]  status: up / done / failed
        self.last = time.time()
        self.active = 0
        self.lock = threading.Lock()


BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def safe_name(name):
    name = BAD_CHARS.sub('_', name.replace('\\', '/').rsplit('/', 1)[-1]).strip(' .')
    if not name or os.path.splitext(name)[0].upper() in RESERVED:
        name = 'file_' + (name or 'upload')
    stem, ext = os.path.splitext(name)
    return stem[:150] + ext[:20]


def claim_path(folder, name):
    """Reserve a free name in folder (never overwrite): name, name (1), name (2) ..."""
    stem, ext = os.path.splitext(name)
    n = 0
    while True:
        cand = os.path.join(folder, name if n == 0 else f'{stem} ({n}){ext}')
        try:
            open(cand, 'xb').close()            # atomic create; fails if it already exists
            return cand
        except FileExistsError:
            n += 1


RECV_BODY = """<div class="lbl">Send to your PC</div>
<label class="pick" for="f">Choose photos, videos or files</label>
<input id="f" type="file" multiple>
<div id="list" style="margin-top:8px"></div>
<button class="b" id="go" disabled style="margin-top:8px">Upload</button>
<p class="h">Saved full size on the PC in <b>__FOLDER__</b>.<br><br>Keep Safari open and the screen on until every file says <b>Done</b>.</p>
<script>
var T='__TOKEN__',inp=document.getElementById('f'),list=document.getElementById('list'),go=document.getElementById('go'),rows=[],busy=false;
function human(n){var u=['B','KB','MB','GB'],i=0;while(n>=1024&&i<3){n/=1024;i++}return (i?n.toFixed(1):n)+' '+u[i]}
inp.onchange=function(){if(busy)return;rows=[];list.innerHTML='';
 Array.prototype.forEach.call(inp.files,function(f){var d=document.createElement('div');d.className='f';
  d.innerHTML='<div class="n"></div><div class="s"></div><div class="bar"><i></i></div>';
  d.querySelector('.n').textContent=f.name;d.querySelector('.s').textContent=human(f.size)+' \\u00b7 ready';
  list.appendChild(d);rows.push({f:f,d:d,ok:false});});
 go.textContent='Upload';go.disabled=!rows.length;};
function send(q,i){if(i>=q.length){busy=false;var left=rows.filter(function(r){return !r.ok}).length;
  go.textContent=left?'Retry failed ('+left+')':'All done';go.disabled=!left;return}
 var r=q[i],s=r.d.querySelector('.s'),bar=r.d.querySelector('.bar i'),x=new XMLHttpRequest();
 r.d.className='f';bar.style.width='0';
 x.open('POST','/'+T+'/up?name='+encodeURIComponent(r.f.name));
 x.upload.onprogress=function(e){if(e.lengthComputable){var p=Math.floor(e.loaded*100/e.total);bar.style.width=p+'%';s.textContent=human(r.f.size)+' \\u00b7 '+p+'%'}};
 x.onload=function(){if(x.status==200){r.ok=true;r.d.className='f ok';bar.style.width='100%';s.textContent=human(r.f.size)+' \\u00b7 Done \\u00b7 saved as '+x.responseText}
  else{r.d.className='f bad';s.textContent='Failed ('+x.status+')'}send(q,i+1)};
 x.onerror=function(){r.d.className='f bad';s.textContent='Failed: connection lost';send(q,i+1)};
 x.send(r.f);}
go.onclick=function(){if(busy)return;busy=true;go.disabled=true;go.textContent='Uploading\\u2026';
 send(rows.filter(function(r){return !r.ok}),0)};
</script>"""


def make_recv_handler(st):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def route(self):
            parts = urllib.parse.urlsplit(self.path).path.strip('/').split('/')
            if not parts or parts[0] != st.token:
                self.send_error(404)
                return None
            st.last = time.time()
            return parts[1:]

        def do_GET(self):
            rest = self.route()
            if rest is None:
                return
            if rest:
                return self.send_error(404)
            body = phone_page(RECV_BODY.replace('__TOKEN__', st.token)
                              .replace('__FOLDER__', html.escape(st.folder)))
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            rest = self.route()
            if rest is None:
                return
            if rest != ['up']:
                return self.send_error(404)
            try:
                size = int(self.headers.get('Content-Length', ''))
            except ValueError:
                return self.send_error(411)
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            os.makedirs(st.folder, exist_ok=True)
            final = claim_path(st.folder, safe_name(q.get('name', ['upload'])[0]))
            part = final + '.part'
            item = [os.path.basename(final), size, 0, 'up']
            with st.lock:
                st.items.append(item); st.active += 1
            got = 0
            try:
                with open(part, 'wb') as f:
                    while got < size:
                        buf = self.rfile.read(min(CHUNK, size - got))
                        if not buf:
                            break
                        f.write(buf); got += len(buf)
                        item[2] = got; st.last = time.time()
                if got == size:
                    os.replace(part, final)
                    item[3] = 'done'
                    msg = item[0].encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.send_header('Content-Length', str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
            except (ConnectionError, OSError):
                pass
            finally:
                with st.lock:
                    st.active -= 1
            item[3] = 'failed'                          # cut off: drop the half file and its reserved name
            for p in (part, final):
                try:
                    os.remove(p)
                except OSError:
                    pass
            try:
                self.send_error(400)
            except OSError:
                pass

    return H


def start_receiver(folder):
    st = RecvState(os.path.abspath(folder))
    os.makedirs(st.folder, exist_ok=True)
    srv, port = serve(make_recv_handler(st))
    return st, srv, f'http://{lan_ip()}:{port}/{st.token}/'


# ---------------------------------------------------------------- app window (pywebview)

def resource(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def font_faces():
    """Bundled fonts as inline @font-face (works offline): Inter Tight + Zen Old Mincho (kana subset)."""
    import base64
    css = ''
    for fam, file, wt in (('Inter Tight', 'InterTight.woff2', '100 900'), ('Zen Old Mincho', 'ZenOldMincho-kana.woff2', '900')):
        try:
            with open(resource(os.path.join('fonts', file)), 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            css += f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,{b64}) format('woff2')}}" + '\n'
        except OSError:
            pass
    return css


def qr_svg(url):
    import segno
    return segno.make(url, error='m').svg_data_uri(dark='#120e10', light='#f0eae6', border=2, scale=6)


class Share:
    """One running server (send or receive) with its QR, stopped on idle."""

    def __init__(self, st, srv, url):
        self.st, self.srv, self.url, self.qr = st, srv, url, qr_svg(url)
        self.port = srv.server_address[1]

    def stop(self):
        threading.Thread(target=self.srv.shutdown, daemon=True).start()

    def idle(self):
        return not self.st.active and time.time() - self.st.last > IDLE_MIN * 60


class Api:
    def __init__(self, files, receive):
        self.lock = threading.Lock()
        self.send = None
        self.recv = None
        self._window = None
        self.start_tab = 'recv' if receive else 'send'
        if files:
            self.add_files(files)

    # -- send
    def add_files(self, paths):
        paths = [p for p in paths if p and os.path.isfile(p)]
        if not paths:
            return
        with self.lock:
            if self.send:
                self.send.st.add(paths)
            else:
                self.send = Share(*start_server(paths))

    def pick(self):
        import webview
        got = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True)
        if got:
            self.add_files(list(got))
        return True

    def clear(self):
        with self.lock:
            if self.send:
                self.send.stop(); self.send = None
        return True

    # -- receive
    def start_receive(self):
        with self.lock:
            if not self.recv:
                self.recv = Share(*start_receiver(RECEIVE_DIR))
        return True

    def stop_receive(self):
        with self.lock:
            if self.recv:
                self.recv.stop(); self.recv = None
        return True

    def open_folder(self):
        os.makedirs(RECEIVE_DIR, exist_ok=True)
        os.startfile(RECEIVE_DIR)

    # -- window
    def minimize(self):
        self._window.minimize()

    def close(self):
        self.clear(); self.stop_receive()
        self._window.destroy()

    def credit(self):
        import webbrowser
        webbrowser.open(CREDIT_URL)

    def boot(self):
        return {'tab': self.start_tab, 'folder': RECEIVE_DIR, 'idle': IDLE_MIN}

    def status(self):
        with self.lock:
            for name in ('send', 'recv'):
                sh = getattr(self, name)
                if sh and sh.idle():
                    sh.stop(); setattr(self, name, None)
            out = {'send': None, 'recv': None}
            if self.send:
                st = self.send.st
                with st.lock:
                    files = [{'name': os.path.basename(p), 'size': human(os.path.getsize(p)) if os.path.isfile(p) else '?',
                              'pct': 100 if d else (n * 100 // max(os.path.getsize(p), 1) if os.path.isfile(p) else 0),
                              'state': 'done' if d else ('up' if n else 'wait')}
                             for p, n, d in zip(st.files, st.sent, st.done)]
                out['send'] = {'port': self.send.port, 'url': self.send.url, 'qr': self.send.qr, 'files': files, 'active': st.active}
            if self.recv:
                st = self.recv.st
                with st.lock:
                    items = [{'name': n, 'size': human(s), 'pct': 100 if stt == 'done' else g * 100 // max(s, 1),
                              'state': stt} for n, s, g, stt in st.items]
                out['recv'] = {'port': self.recv.port, 'url': self.recv.url, 'qr': self.recv.qr, 'files': items[::-1], 'active': st.active}
            return out


def gui(files, receive=False):
    import webview
    try:                                         # own taskbar entry and icon instead of Python's
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('rem.pass')
    except Exception:
        pass
    api = Api(files, receive)
    with open(resource('ui.html'), encoding='utf-8') as f:
        page = f.read().replace('__ACC__', ACCENT).replace('__FONTS__', font_faces())
    pos = {}
    if os.environ.get('PASS_TEST_POS'):          # tests: open at x,y without taking focus
        x, y = map(int, os.environ['PASS_TEST_POS'].split(','))
        pos = dict(x=x, y=y, focus=False)
    win = webview.create_window(APP, html=page, js_api=api, width=400, height=600, resizable=False,
                                frameless=True, easy_drag=False, background_color='#120e10', **pos)
    api._window = win

    def on_drop(e):
        paths = [f.get('pywebviewFullPath') for f in e.get('dataTransfer', {}).get('files', [])]
        api.add_files([p for p in paths if p])
        win.evaluate_js('window.dropped && window.dropped()')

    def wire():
        from webview.dom import DOMEventHandler
        win.dom.document.events.drop += DOMEventHandler(on_drop, True, True)

    win.events.loaded += wire
    webview.start(icon=resource('icon.ico'))
    api.clear(); api.stop_receive()


def headless(files, receive=False):
    if receive:
        st, srv, url = start_receiver(files[0] if files else RECEIVE_DIR)
    else:
        st, srv, url = start_server(files)
    print(url, flush=True)
    try:
        while time.time() - st.last < IDLE_MIN * 60 or st.active:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    srv.shutdown()


if __name__ == '__main__':
    args = sys.argv[1:]
    receive = '--receive' in args
    args = [a for a in args if a != '--receive']
    if args and args[0] == '--no-gui':
        headless(args[1:], receive)
    else:
        gui([a for a in args if os.path.isfile(a)], receive)
