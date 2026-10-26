# GameCast (SCREEN UNTAN) v0.1

## Cara pasang (Windows / Mac)
1. Pasang Python 3.10+ lalu jalankan: `pip install -r requirements.txt`
2. Unduh scrcpy (github.com/Genymobile/scrcpy/releases), ekstrak ke folder `scrcpy` di sebelah gamecast.py (sudah termasuk adb). Gunakan scrcpy 3.x.
3. Taruh logo di sebelah gamecast.py dengan nama `logo.png`.
4. Jalankan: `python gamecast.py`

## Cara pakai
- Colok HP lewat USB, atau klik "Sambung WiFi (QR)" lalu pemain scan lewat Debugging nirkabel.
- Isi nama pemain, pilih mode dan kualitas, klik MULAI TAMPILKAN. Satu HP = satu jendela.
- Di OBS: Sources > Window Capture, pilih jendela dengan nama pemain. Lalu pakai Start Virtual Camera bila perlu.
- "Halaman panduan pemain" menampilkan QR ke halaman web bantu (panduan per merk + kirim nama).
- iPhone: taruh UxPlay di folder aplikasi, klik "Mode iPhone".

## Syarat pemain
Android 11+, Opsi pengembang aktif, USB/Wireless debugging aktif (Xiaomi: tambah USB debugging Security settings).
Rekaman dan screenshot masuk ke folder `hasil`.
