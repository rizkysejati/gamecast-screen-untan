"""GameCast (SCREEN UNTAN) v0.1 - mirroring HP Android ringan untuk lomba esport.
Membungkus scrcpy + adb. HP pemain tidak perlu instal apa-apa."""
import json, os, random, re, shutil, socket, subprocess, sys, threading, time
import tkinter as tk
from tkinter import ttk, messagebox
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import qrcode
    from PIL import Image, ImageTk
except ImportError:
    qrcode = None

APP = "GameCast (SCREEN UNTAN)"
HERE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "hasil")
os.makedirs(OUT, exist_ok=True)
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NAVY, AMBER, PAPER = "#0F2A4A", "#F2B01E", "#F4F6FA"

QUALITY = {  # nama: (max-size, fps, bitrate)
    "720p / 30 fps (hemat)": (1280, 30, "6M"),
    "1080p / 30 fps": (1920, 30, "10M"),
    "1080p / 60 fps (terbaik)": (1920, 60, "16M"),
}
MODES = ["Tampilan saja", "Tampilan + kontrol", "Tampilan + rekam"]

registrations = []  # nama pemain dari halaman web


def find_tool(name):
    exe = name + (".exe" if os.name == "nt" else "")
    for folder in (os.path.join(HERE, "scrcpy"), HERE):
        p = os.path.join(folder, exe)
        if os.path.exists(p):
            return p
    return shutil.which(name)


ADB, SCRCPY = find_tool("adb"), find_tool("scrcpy")


def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=NOWIN)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return str(e)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ---------- halaman web bantu untuk pemain ----------
GUIDE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>GameCast SCREEN UNTAN</title>
<style>
:root{--navy:#0F2A4A;--amber:#F2B01E;--bg:#F4F6FA;--ink:#14213A}
@media(prefers-color-scheme:dark){:root{--bg:#0B1B30;--ink:#E8EEF8}}
body{margin:0;font:16px/1.55 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--navy);color:#fff;padding:22px 18px;border-bottom:5px solid var(--amber)}
h1{margin:0;font-size:1.5rem}header p{margin:4px 0 0;opacity:.85}
main{max-width:620px;margin:auto;padding:16px}
details{border:1px solid #8aa;border-radius:10px;margin:10px 0;padding:10px 14px}
summary{font-weight:600;cursor:pointer}
input,button{font:inherit;padding:12px;border-radius:8px;border:1px solid #789;width:100%;box-sizing:border-box;margin-top:8px}
button{background:var(--amber);border:0;font-weight:700;color:#14213A}
.ok{color:#1a8a4a;font-weight:600}
</style></head><body>
<header><h1>GameCast SCREEN UNTAN</h1><p>Siapkan HP kamu untuk tampil di layar lomba</p></header><main>
<h2>1. Isi nama</h2>
<input id="n" placeholder="Nama pemain / tim"><button onclick="d()">Kirim nama</button><p id="s"></p>
<h2>2. Aktifkan mode pengembang</h2>
<p>Syarat: Android 11 atau lebih baru. Buka Pengaturan, Tentang ponsel, lalu ketuk Nomor build 7 kali.</p>
<details><summary>Xiaomi / Redmi / Poco</summary><p>Pengaturan tambahan &gt; Opsi pengembang. Aktifkan Debugging USB, Debugging nirkabel, dan Debugging USB (Pengaturan keamanan).</p></details>
<details><summary>Samsung</summary><p>Pengaturan &gt; Opsi pengembang. Aktifkan Debugging USB dan Debugging nirkabel.</p></details>
<details><summary>Oppo / Realme / Vivo</summary><p>Pengaturan &gt; Pengelolaan tambahan (atau Sistem) &gt; Opsi pengembang. Aktifkan Debugging USB dan Debugging nirkabel. Matikan penghemat baterai.</p></details>
<details><summary>Merk lain</summary><p>Cari "Opsi pengembang" di Pengaturan, lalu aktifkan Debugging USB dan Debugging nirkabel.</p></details>
<h2>3. Sambung ke panitia</h2>
<p><b>Lewat kabel:</b> colok USB ke komputer panitia, lalu tekan Izinkan pada layar HP.</p>
<p><b>Lewat WiFi:</b> sambungkan HP ke WiFi lomba. Di Debugging nirkabel pilih "Sambungkan perangkat dengan kode QR", lalu pindai QR dari petugas.</p>
<p>Sebelum main, matikan notifikasi dan aktifkan mode jangan ganggu supaya chat pribadi tidak tampil di siaran.</p>
</main><script>
async function d(){let n=document.getElementById('n').value.trim();if(!n)return;
try{await fetch('/daftar',{method:'POST',body:JSON.stringify({nama:n})});
document.getElementById('s').innerHTML='<span class="ok">Nama terkirim. Tunggu petugas.</span>'}catch(e){document.getElementById('s').textContent='Gagal kirim, panggil petugas.'}}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = GUIDE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            nama = json.loads(self.rfile.read(n))["nama"][:40]
            if nama not in registrations:
                registrations.append(nama)
        except Exception:
            pass
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


# ---------- aplikasi ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("680x640")
        self.configure(bg=PAPER)
        self.procs = {}
        self.server = None
        self.build()
        self.refresh()
        self.after(1500, self.poll_names)
        if not ADB or not SCRCPY:
            messagebox.showwarning(APP, "adb / scrcpy belum ditemukan.\nTaruh isi folder scrcpy ke folder 'scrcpy' di sebelah aplikasi ini (lihat README).")

    def build(self):
        head = tk.Frame(self, bg=NAVY)
        head.pack(fill="x")
        logo = os.path.join(HERE, "logo.png")
        if qrcode and os.path.exists(logo):
            im = Image.open(logo)
            im.thumbnail((56, 56))
            self.logo = ImageTk.PhotoImage(im)
            tk.Label(head, image=self.logo, bg=NAVY).pack(side="left", padx=12, pady=8)
        tk.Label(head, text="GameCast", font=("Segoe UI", 20, "bold"), fg="white", bg=NAVY).pack(side="left", pady=10)
        tk.Label(head, text=" (SCREEN UNTAN)", font=("Segoe UI", 12), fg=AMBER, bg=NAVY).pack(side="left", pady=10)
        tk.Frame(self, bg=AMBER, height=4).pack(fill="x")

        box = ttk.LabelFrame(self, text="Perangkat tersambung")
        box.pack(fill="both", padx=12, pady=8)
        self.lst = tk.Listbox(box, height=6, font=("Segoe UI", 11), exportselection=False)
        self.lst.pack(fill="both", padx=8, pady=6)
        row = tk.Frame(box)
        row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(row, text="Segarkan", command=self.refresh).pack(side="left")
        ttk.Button(row, text="Sambung WiFi (QR)", command=self.wifi_qr).pack(side="left", padx=6)
        ttk.Button(row, text="Sambung IP manual", command=self.manual_ip).pack(side="left")

        opt = ttk.LabelFrame(self, text="Pengaturan layar")
        opt.pack(fill="x", padx=12, pady=4)
        self.mode = tk.StringVar(value=MODES[0])
        self.qual = tk.StringVar(value=list(QUALITY)[1])
        self.name = tk.StringVar()
        self.audio = tk.BooleanVar(value=True)
        for i, (lab, w) in enumerate([
            ("Mode", ttk.Combobox(opt, textvariable=self.mode, values=MODES, state="readonly")),
            ("Kualitas", ttk.Combobox(opt, textvariable=self.qual, values=list(QUALITY), state="readonly")),
            ("Nama pemain / tim", None)]):
            ttk.Label(opt, text=lab).grid(row=i, column=0, sticky="w", padx=8, pady=5)
            if w is None:
                w = self.namebox = ttk.Combobox(opt, textvariable=self.name)
            w.grid(row=i, column=1, sticky="ew", padx=8, pady=5)
        opt.columnconfigure(1, weight=1)
        ttk.Checkbutton(opt, text="Suara game ikut (Android 11+)", variable=self.audio).grid(row=3, column=1, sticky="w", padx=8, pady=5)

        act = tk.Frame(self, bg=PAPER)
        act.pack(fill="x", padx=12, pady=8)
        ttk.Button(act, text="MULAI TAMPILKAN", command=self.start).pack(side="left", ipadx=10, ipady=6)
        ttk.Button(act, text="Hentikan", command=self.stop).pack(side="left", padx=6, ipady=6)
        ttk.Button(act, text="Screenshot", command=self.shot).pack(side="left", ipady=6)

        more = ttk.LabelFrame(self, text="Lainnya")
        more.pack(fill="x", padx=12, pady=4)
        ttk.Button(more, text="Halaman panduan pemain (QR)", command=self.guide).pack(side="left", padx=8, pady=8)
        ttk.Button(more, text="Mode iPhone (AirPlay)", command=self.iphone).pack(side="left")
        self.status = tk.StringVar(value="Siap.")
        tk.Label(self, textvariable=self.status, bg=PAPER, anchor="w", wraplength=640, justify="left").pack(fill="x", padx=14, pady=6)

    # --- perangkat ---
    def refresh(self):
        self.lst.delete(0, "end")
        self.devs = []
        if not ADB:
            return
        for line in run([ADB, "devices", "-l"]).splitlines()[1:]:
            p = line.split()
            if len(p) >= 2 and p[1] == "device":
                model = next((x[6:] for x in p if x.startswith("model:")), "")
                self.devs.append(p[0])
                self.lst.insert("end", f"{model}   [{p[0]}]")
            elif len(p) >= 2 and p[1] == "unauthorized":
                self.lst.insert("end", f"{p[0]}  (belum diizinkan, cek layar HP)")
                self.devs.append(None)
        self.say(f"{sum(1 for d in self.devs if d)} perangkat siap.")

    def say(self, t):
        self.status.set(t)

    def selected(self):
        s = self.lst.curselection()
        if not s or self.devs[s[0]] is None:
            messagebox.showinfo(APP, "Pilih perangkat yang sudah diizinkan dari daftar.")
            return None
        return self.devs[s[0]]

    # --- mirroring ---
    def start(self):
        dev = self.selected()
        if not dev or not SCRCPY:
            return
        size, fps, br = QUALITY[self.qual.get()]
        title = self.name.get().strip() or dev
        cmd = [SCRCPY, "-s", dev, "--window-title", title, "--max-size", str(size),
               "--max-fps", str(fps), "--video-bit-rate", br, "--no-power-on"]
        m = self.mode.get()
        if m == MODES[0]:
            cmd.append("--no-control")
        if m == MODES[2]:
            cmd += ["--no-control", "--record", os.path.join(OUT, f"{re.sub(r'[^A-Za-z0-9_-]', '_', title)}_{int(time.time())}.mp4")]
        if not self.audio.get():
            cmd.append("--no-audio")
        if dev in self.procs and self.procs[dev].poll() is None:
            self.procs[dev].terminate()
        self.procs[dev] = subprocess.Popen(cmd, creationflags=NOWIN)
        self.say(f"Menampilkan '{title}'. Di OBS pakai Window Capture dengan judul jendela itu.")

    def stop(self):
        for p in self.procs.values():
            if p.poll() is None:
                p.terminate()
        self.say("Semua tampilan dihentikan.")

    def shot(self):
        dev = self.selected()
        if not dev:
            return
        path = os.path.join(OUT, f"shot_{int(time.time())}.png")
        with open(path, "wb") as f:
            subprocess.run([ADB, "-s", dev, "exec-out", "screencap", "-p"], stdout=f, creationflags=NOWIN)
        self.say(f"Screenshot tersimpan: {path}")

    # --- WiFi ---
    def manual_ip(self):
        win = tk.Toplevel(self)
        win.title("Sambung IP")
        ttk.Label(win, text="IP:port dari layar Debugging nirkabel").pack(padx=14, pady=(14, 4))
        e = ttk.Entry(win, width=30)
        e.pack(padx=14)

        def go():
            self.say(run([ADB, "connect", e.get().strip()]).strip())
            win.destroy()
            self.refresh()
        ttk.Button(win, text="Sambung", command=go).pack(pady=14)

    def show_qr(self, text, title, note):
        if not qrcode:
            messagebox.showinfo(APP, "Pasang dulu: pip install qrcode pillow")
            return None
        win = tk.Toplevel(self)
        win.title(title)
        img = ImageTk.PhotoImage(qrcode.make(text).get_image().resize((280, 280)))
        lab = tk.Label(win, image=img)
        lab.image = img
        lab.pack(padx=16, pady=12)
        tk.Label(win, text=note, wraplength=300, justify="center").pack(padx=16, pady=(0, 14))
        return win

    def wifi_qr(self):
        if not ADB:
            return
        nm, pw = "GC" + str(random.randint(1000, 9999)), str(random.randint(100000, 999999))
        win = self.show_qr(f"WIFI:T:ADB;S:{nm};P:{pw};;", "Sambung WiFi",
                           "Pemain: Opsi pengembang > Debugging nirkabel > 'Sambungkan dengan kode QR', lalu pindai.")
        if win:
            threading.Thread(target=self.pair_worker, args=(nm, pw, win), daemon=True).start()

    def pair_worker(self, nm, pw, win):
        pair_addr = None
        for _ in range(90):  # tunggu sampai 3 menit
            out = run([ADB, "mdns", "services"])
            for line in out.splitlines():
                if nm in line and "_adb-tls-pairing" in line:
                    pair_addr = line.split()[-1]
            if pair_addr:
                break
            time.sleep(2)
        if not pair_addr:
            self.after(0, lambda: self.say("QR kedaluwarsa. Coba lagi."))
            return
        res = run([ADB, "pair", pair_addr, pw])
        ip = pair_addr.split(":")[0]
        for _ in range(30):
            for line in run([ADB, "mdns", "services"]).splitlines():
                if "_adb-tls-connect" in line and line.split()[-1].startswith(ip + ":"):
                    run([ADB, "connect", line.split()[-1]])
                    self.after(0, lambda: (win.destroy(), self.refresh(), self.say("HP tersambung lewat WiFi.")))
                    return
            time.sleep(1)
        self.after(0, lambda: self.say("Pairing: " + res.strip() + " (sambung manual jika perlu)"))

    # --- web & iPhone ---
    def guide(self):
        if not self.server:
            self.server = HTTPServer(("0.0.0.0", 8080), Handler)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
        url = f"http://{lan_ip()}:8080"
        self.show_qr(url, "Panduan pemain", f"Pemain pindai QR ini (HP harus di WiFi yang sama).\n{url}")
        self.say("Server panduan menyala. Nama yang dikirim pemain muncul di kolom nama.")

    def poll_names(self):
        self.namebox["values"] = registrations
        self.after(1500, self.poll_names)

    def iphone(self):
        ux = find_tool("uxplay")
        if not ux:
            messagebox.showinfo(APP, "UxPlay belum ditemukan. Taruh uxplay di folder aplikasi ini.\nPemain iPhone pilih 'Screen Mirroring' lalu nama komputer ini.")
            return
        self.procs["iphone"] = subprocess.Popen([ux, "-n", self.name.get().strip() or "GameCast"], creationflags=NOWIN)
        self.say("Mode iPhone menyala. Di iPhone: Pusat Kontrol > Screen Mirroring.")


if __name__ == "__main__":
    App().mainloop()
