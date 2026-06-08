"""
╔══════════════════════════════════════╗
║        ATM SIMULATOR — main.py       ║
║  Struktur Data: Stack + Dictionary   ║
╚══════════════════════════════════════╝
"""

import os
import sys
from getpass import getpass
from atm import ATM


# ─── UI Helpers ───────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header(title: str = "ATM SIMULATOR"):
    print("=" * 44)
    print(f"  {title.center(40)}")
    print("=" * 44)

def divider():
    print("-" * 44)

def pause():
    input("\n  Tekan Enter untuk lanjut...")

def fmt_rp(amount: int) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")

def input_pilihan(opsi, reprint_fn=None) -> str:
    """Loop input sampai pilihan valid. Clear + reprint tiap salah."""
    while True:
        pilihan = input("  Pilih: ").strip()
        if pilihan in opsi:
            return pilihan
        if reprint_fn:
            clear()
            reprint_fn()
        print("  Pilihlah sesuai Pilihan")


# ─── Menu Screens ─────────────────────────────────────────────────────────────

def menu_utama(atm: ATM):
    def _reprint():
        header()
        print("  1. Login Rekening")
        print("  2. Cek Saldo (Scan Kartu)")
        print("  0. Keluar")
        divider()

    while True:
        clear()
        _reprint()
        pilihan = input_pilihan({"1", "2", "0"}, reprint_fn=_reprint)

        if pilihan == "1":   menu_login(atm)
        elif pilihan == "2": aksi_scan_saldo(atm)
        elif pilihan == "0":
            clear()
            print("\n  Terima kasih. Sampai jumpa!\n")
            sys.exit(0)


def menu_login(atm: ATM):
    while True:
        clear()
        header("LOGIN REKENING")
        no_rek = input("  No. Rekening : ").strip()
        pin    = getpass("  PIN          : ")

        ok, pesan = atm.login(no_rek, pin)

        if ok:
            print(f"\n  ✓ {pesan}")
            pause()
            menu_dashboard(atm)
            break
        else:
            print(f"\n  ✗ {pesan}")
            print("  Silakan coba lagi.")
            pause()


def menu_dashboard(atm: ATM):
    def _reprint():
        header("DASHBOARD")
        print(f"  Nama  : {atm.get_nama()}")
        print(f"  Level : {atm.get_level()}")

        # Tampilkan peringatan grace period jika aktif
        info_downgrade = atm.get_downgrade_info()
        if info_downgrade:
            print(f"  ⚠  Peringatan: Level akan turun ke {info_downgrade['level_tujuan']}")
            print(f"     dalam {info_downgrade['sisa_hari']} hari jika saldo tidak mencukupi.")

        divider()
        print("  1. Tarik Uang")
        print("  2. Cek Saldo")
        print("  3. Transfer")
        print("  4. Riwayat Transaksi")
        print("  0. Logout")
        divider()

    while True:
        clear()
        _reprint()
        pilihan = input_pilihan({"1", "2", "3", "4", "0"}, reprint_fn=_reprint)

        match pilihan:
            case "1": aksi_tarik(atm)
            case "2": aksi_cek_saldo(atm)
            case "3": aksi_transfer(atm)
            case "4": aksi_riwayat(atm)
            case "0":
                atm.logout()
                print("\n  Logout berhasil.")
                pause()
                break


# ─── Actions ──────────────────────────────────────────────────────────────────

def aksi_cek_saldo(atm: ATM):
    clear()
    header("CEK SALDO")
    divider()
    print(f"  Nama  : {atm.get_nama()}")
    print(f"  Level : {atm.get_level()}")
    print(f"  Saldo : {fmt_rp(atm.get_saldo())}")
    divider()
    pause()


def aksi_tarik(atm: ATM):
    info = atm.get_info_tarik()

    def _reprint_pecahan():
        header("TARIK UANG")
        divider()
        print(f"  Level         : {info['level']}")
        if info['maks'] is not None:
            print(f"  Tarik bulan ini: {info['count']}x / {info['maks']}x")
            sisa_free = max(0, info['free'] - info['count'])
            print(f"  Sisa gratis   : {sisa_free}x")
            if info['kena_admin']:
                print(f"  Biaya admin   : {fmt_rp(info['biaya_admin'])}/tarik")
        else:
            print("  Tarik         : Unlimited & Gratis")
        print(f"  Limit harian  : {fmt_rp(info['limit_harian'])}")
        sisa_harian = info['limit_harian'] - info['sudah_harian']
        print(f"  Sisa hari ini : {fmt_rp(sisa_harian)}")
        divider()
        print("  Pilih pecahan:")
        print("  1. Rp50.000")
        print("  2. Rp100.000")
        divider()

    clear()
    _reprint_pecahan()
    pilihan_pecahan = input_pilihan({"1", "2"}, reprint_fn=_reprint_pecahan)
    pecahan = 50_000 if pilihan_pecahan == "1" else 100_000

    def _reprint_jumlah():
        header("TARIK UANG")
        print(f"  Pecahan       : {fmt_rp(pecahan)}")
        if info['kena_admin']:
            print(f"  Biaya admin   : {fmt_rp(info['biaya_admin'])}/tarik")
        divider()
        print(f"  Masukkan kelipatan {fmt_rp(pecahan)}")
        divider()

    clear()
    _reprint_jumlah()

    while True:
        try:
            jumlah = int(input("  Jumlah tarik : Rp").replace(".", "").strip())
        except ValueError:
            clear()
            _reprint_jumlah()
            print("  Pilihlah sesuai Pilihan")
            continue

        ok, pesan = atm.tarik(jumlah, pecahan)
        if ok:
            print(f"\n  ✓ {pesan}")
            pause()
            break
        else:
            clear()
            _reprint_jumlah()
            print(f"  ✗ {pesan}")


def aksi_transfer(atm: ATM):
    W = 42

    def _box_line(label: str, value: str) -> str:
        content = f"  {label}: {value}"
        return f"  │{content:<{W}}│"

    def _reprint_norek():
        header("TRANSFER")
        cfg = atm.get_level_config()
        print(f"  Level         : {atm.get_level()}")
        print(f"  Limit harian  : {fmt_rp(cfg['limit_transfer_harian'])}")
        divider()

    def _reprint_jumlah(nama_tujuan, no_tujuan):
        header("TRANSFER")
        print(f"  No. Rek Tujuan   : {no_tujuan}")
        print(f"  Nama Penerima    : {nama_tujuan}")
        print("  (Minimal Rp10.000)")
        divider()

    # ── Input no. rekening tujuan ──
    clear()
    _reprint_norek()
    while True:
        no_tujuan = input("  No. Rekening Tujuan : ").strip()
        if not atm.account_exists(no_tujuan):
            clear()
            _reprint_norek()
            print("  ✗ Nomor rekening tidak ditemukan. Coba lagi.")
        elif no_tujuan == atm.logged_in:
            clear()
            _reprint_norek()
            print("  ✗ Tidak bisa transfer ke rekening sendiri.")
        else:
            break

    nama_tujuan = atm.get_nama(no_tujuan)

    # ── Input jumlah ──
    clear()
    _reprint_jumlah(nama_tujuan, no_tujuan)
    while True:
        try:
            jumlah = int(input("  Jumlah transfer : Rp").replace(".", "").strip())
        except ValueError:
            clear()
            _reprint_jumlah(nama_tujuan, no_tujuan)
            print("  ✗ Input tidak valid. Masukkan angka.")
            continue

        if jumlah < 10_000:
            clear()
            _reprint_jumlah(nama_tujuan, no_tujuan)
            print("  ✗ Jumlah minimal transfer Rp10.000.")
            continue

        if jumlah > atm.get_saldo():
            clear()
            _reprint_jumlah(nama_tujuan, no_tujuan)
            print("  ✗ Saldo tidak mencukupi.")
            continue

        break

    # ── Konfirmasi ──
    def _reprint_konfirmasi():
        header("TRANSFER")
        print()
        print(f"  ┌{'─' * W}┐")
        print(f"  │{'  Konfirmasi Transfer':^{W}}│")
        print(f"  ├{'─' * W}┤")
        print(_box_line("  Ke    ", f"{nama_tujuan} ({no_tujuan})"))
        print(_box_line("  Jumlah", fmt_rp(jumlah)))
        print(f"  └{'─' * W}┘")
        print()
        print("  Konfirmasi transfer (y = lanjutkan, n = batal)")

    clear()
    _reprint_konfirmasi()
    konfirmasi = input_pilihan({"y", "n"}, reprint_fn=_reprint_konfirmasi)

    if konfirmasi != "y":
        print("  Transfer dibatalkan.")
        pause()
        return

    ok, pesan = atm.transfer(no_tujuan, jumlah)
    print(f"\n  {'✓' if ok else '✗'} {pesan}")
    pause()


def aksi_riwayat(atm: ATM):
    clear()
    header("RIWAYAT TRANSAKSI")
    history = atm.get_history()

    if not history:
        print("  Belum ada transaksi.")
    else:
        for i, item in enumerate(history, 1):
            print(f"  {i:>2}. [{item['waktu']}]")
            print(f"      {item['keterangan']}")
            if i < len(history):
                divider()
    pause()


def aksi_scan_saldo(atm: ATM):
    clear()
    header("CEK SALDO — SCAN KARTU")
    print("  Kamera akan terbuka.")
    print("  Arahkan kartu ATM ke area scan.")
    print("  Saldo akan ditampilkan di layar kamera.")
    print("  Tekan Q di jendela kamera untuk keluar.")
    divider()
    input("  Tekan Enter untuk membuka kamera...")

    try:
        from scanner import scan_card
    except ImportError as e:
        print(f"\n  [ERROR] Library tidak lengkap: {e}")
        print("  Jalankan: pip install opencv-python pytesseract")
        pause()
        return

    scan_card(atm)
    pause()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    atm = ATM()
    menu_utama(atm)
