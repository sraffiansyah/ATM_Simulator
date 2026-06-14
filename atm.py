"""
Core ATM logic.
Struktur Data: Stack (riwayat transaksi), Dictionary (data rekening)
History transaksi disimpan ke JSON supaya persist setelah program ditutup.
"""

import json
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "accounts.json"


# ─── Konstanta Level ──────────────────────────────────────────────────────────

LEVEL_CONFIG = {
    "Silver": {
        "limit_tarik_harian":    5_000_000,
        "limit_transfer_harian": 5_000_000,
        "maks_tarik_bulanan":    10,
        "free_tarik":            3,
        "biaya_admin":           6_500,
    },
    "Gold": {
        "limit_tarik_harian":    7_000_000,
        "limit_transfer_harian": 15_000_000,
        "maks_tarik_bulanan":    15,
        "free_tarik":            5,
        "biaya_admin":           5_000,
    },
    "Platinum": {
        "limit_tarik_harian":    10_000_000,
        "limit_transfer_harian": 50_000_000,
        "maks_tarik_bulanan":    20,
        "free_tarik":            10,
        "biaya_admin":           2_500,
    },
    "Priority": {
        "limit_tarik_harian":    15_000_000,
        "limit_transfer_harian": 100_000_000,
        "maks_tarik_bulanan":    None,   # unlimited
        "free_tarik":            None,   # semua free
        "biaya_admin":           0,
    },
}

# Batas maksimal sekali tarik per jenis pecahan (berlaku semua level)
MAKS_TARIK_PER_TRANSAKSI = {
    50_000:  1_000_000,   # pecahan 50k → maks Rp1.000.000 per tarik
    100_000: 2_000_000,   # pecahan 100k → maks Rp2.000.000 per tarik
}

# Threshold saldo untuk level (batas bawah)
LEVEL_THRESHOLD = {
    "Silver":   0,
    "Gold":     5_000_000,
    "Platinum": 25_000_000,
    "Priority": 100_000_000,
}

LEVEL_ORDER = ["Silver", "Gold", "Platinum", "Priority"]


# ─── Stack Implementation ─────────────────────────────────────────────────────

class Stack:
    def __init__(self, initial: list | None = None):
        self._data: list = list(initial) if initial else []

    def push(self, item):       self._data.append(item)
    def pop(self):              return self._data.pop() if self._data else None
    def peek(self):             return self._data[-1] if self._data else None
    def is_empty(self) -> bool: return len(self._data) == 0
    def size(self) -> int:      return len(self._data)
    def to_list(self) -> list:  return list(reversed(self._data))


# ─── ATM Core ─────────────────────────────────────────────────────────────────

class ATM:
    def __init__(self):
        self.accounts: dict        = self._load_accounts()
        self.logged_in: str | None = None
        self.history:   Stack      = Stack()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_accounts(self) -> dict:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _save_accounts(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, indent=4, ensure_ascii=False)

    # ── Backward Compatibility & Default Fields ───────────────────────────────

    def _ensure_fields(self, no_rek: str):
        """Pastikan semua field baru ada. Default ke Silver jika tidak ada."""
        acc = self.accounts[no_rek]
        changed = False
        defaults = {
            "level":              "Silver",
            "withdraw_count":     0,
            "last_reset_month":   "",
            "tarik_harian":       0,
            "last_tarik_date":    "",
            "transfer_harian":    0,
            "last_transfer_date": "",
        }
        for key, val in defaults.items():
            if key not in acc:
                acc[key] = val
                changed = True
        # Hapus field grace period lama jika masih ada
        if "downgrade_warning_date" in acc:
            del acc["downgrade_warning_date"]
            changed = True
        if changed:
            self._save_accounts()

    # ── Auto-Leveling Realtime (tanpa grace period) ───────────────────────────

    def _level_sesuai_saldo(self, saldo: int) -> str:
        """Tentukan level yang sesuai berdasarkan saldo saat ini."""
        level = "Silver"
        for lv in LEVEL_ORDER:
            if saldo >= LEVEL_THRESHOLD[lv]:
                level = lv
        return level

    def _check_and_update_level(self, no_rek: str) -> str | None:
        """
        Periksa dan perbarui level rekening berdasarkan saldo secara realtime.
        Naik maupun turun level sama-sama instan.
        Mengembalikan pesan notifikasi jika level berubah, atau None jika tidak.
        """
        acc            = self.accounts[no_rek]
        level_lama     = acc.get("level", "Silver")
        level_baru     = self._level_sesuai_saldo(acc["balance"])

        if level_baru != level_lama:
            acc["level"] = level_baru
            self._save_accounts()
            arah = "naik" if LEVEL_ORDER.index(level_baru) > LEVEL_ORDER.index(level_lama) else "turun"
            return f"Level rekening {arah} dari {level_lama} → {level_baru}."
        return None

    # ── Reset Tracker ─────────────────────────────────────────────────────────

    def _reset_monthly_if_needed(self, no_rek: str):
        """Reset withdraw_count jika bulan sudah berganti."""
        acc       = self.accounts[no_rek]
        bulan_ini = datetime.now().strftime("%Y-%m")
        if acc.get("last_reset_month") != bulan_ini:
            acc["withdraw_count"]   = 0
            acc["last_reset_month"] = bulan_ini
            self._save_accounts()

    def _reset_daily_tarik_if_needed(self, no_rek: str):
        """Reset tarik_harian jika hari sudah berganti."""
        acc      = self.accounts[no_rek]
        hari_ini = datetime.now().strftime("%Y-%m-%d")
        if acc.get("last_tarik_date") != hari_ini:
            acc["tarik_harian"]    = 0
            acc["last_tarik_date"] = hari_ini
            self._save_accounts()

    def _reset_daily_transfer_if_needed(self, no_rek: str):
        """Reset transfer_harian jika hari sudah berganti."""
        acc      = self.accounts[no_rek]
        hari_ini = datetime.now().strftime("%Y-%m-%d")
        if acc.get("last_transfer_date") != hari_ini:
            acc["transfer_harian"]    = 0
            acc["last_transfer_date"] = hari_ini
            self._save_accounts()

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_card(no_kartu: str) -> str:
        return no_kartu.replace(" ", "").replace("-", "").strip()

    def get_level_config(self, no_rek: str | None = None) -> dict:
        key   = no_rek or self.logged_in
        level = self.accounts.get(key, {}).get("level", "Silver")
        return LEVEL_CONFIG.get(level, LEVEL_CONFIG["Silver"])

    @staticmethod
    def deteksi_pecahan(jumlah: int):
        """
        Auto-deteksi pecahan berdasarkan nominal.
        Return value:
        50_000   → pasti pecahan 50k (ada komponen 50k, misal 50k/150k/250k/...)
        100_000  → pasti pecahan 100k (nominal > 1jt, kelipatan 100k)
        "tanya"  → nominal kelipatan 100k DAN <= 1jt → bisa dua-duanya, tanya user
        None     → tidak valid (bukan kelipatan 50k, atau > 1jt tapi tidak kelipatan 100k)
        """
        if jumlah <= 0:
            return None
        if jumlah % 50_000 != 0:
            return None
        # Nominal > 1jt → wajib kelipatan 100k, pakai pecahan 100k
        if jumlah > 1_000_000:
            if jumlah % 100_000 != 0:
                return None  # Ada komponen 50k tapi melebihi maks pecahan 50k
            return 100_000
        # Nominal <= 1jt, ada komponen 50k (bukan kelipatan 100k) → pasti 50k
        if jumlah % 100_000 != 0:
            return 50_000
        # Nominal <= 1jt dan kelipatan bersih 100k → dua pecahan sama-sama bisa
        return "tanya"

    # ── Lookup ───────────────────────────────────────────────────────────────

    def find_by_card(self, no_kartu: str) -> str | None:
        target = self._normalize_card(no_kartu)
        for no_rek, data in self.accounts.items():
            if self._normalize_card(data.get("card_number", "")) == target:
                return no_rek
        return None

    def account_exists(self, no_rek: str) -> bool:
        return no_rek in self.accounts

    def card_exists(self, no_kartu: str) -> bool:
        return self.find_by_card(no_kartu) is not None

    # ── Auth ─────────────────────────────────────────────────────────────────

    def login(self, no_rek: str, pin: str) -> tuple[bool, str]:
        if no_rek not in self.accounts:
            return False, "Nomor rekening tidak ditemukan."
        if self.accounts[no_rek]["pin"] != pin:
            return False, "PIN salah."
        self._ensure_fields(no_rek)
        self._check_and_update_level(no_rek)
        self.logged_in = no_rek
        saved = self.accounts[no_rek].get("history", [])
        self.history = Stack(saved)
        self._record(f"LOGIN berhasil — rekening {no_rek}")
        return True, "Login berhasil."

    def logout(self):
        self._record(f"LOGOUT — rekening {self.logged_in}")
        self.logged_in = None
        self.history   = Stack()

    # ── Account Info ─────────────────────────────────────────────────────────

    def get_saldo(self, no_rek: str | None = None) -> int | None:
        key = no_rek or self.logged_in
        return self.accounts.get(key, {}).get("balance")

    def get_nama(self, no_rek: str | None = None) -> str | None:
        key = no_rek or self.logged_in
        return self.accounts.get(key, {}).get("name")

    def get_level(self, no_rek: str | None = None) -> str:
        key = no_rek or self.logged_in
        return self.accounts.get(key, {}).get("level", "Silver")

    def get_no_kartu(self, no_rek: str | None = None) -> str | None:
        key = no_rek or self.logged_in
        raw = self._normalize_card(self.accounts.get(key, {}).get("card_number", ""))
        return " ".join(raw[i:i+4] for i in range(0, len(raw), 4)) if raw else None

    def get_info_tarik(self) -> dict:
        """Info kuota tarik untuk ditampilkan ke user."""
        no_rek = self.logged_in
        self._reset_monthly_if_needed(no_rek)
        self._reset_daily_tarik_if_needed(no_rek)
        acc   = self.accounts[no_rek]
        cfg   = self.get_level_config()
        count = acc["withdraw_count"]
        free  = cfg["free_tarik"]
        maks  = cfg["maks_tarik_bulanan"]
        return {
            "level":        self.get_level(),
            "count":        count,
            "free":         free,
            "maks":         maks,
            "biaya_admin":  cfg["biaya_admin"],
            "limit_harian": cfg["limit_tarik_harian"],
            "sudah_harian": acc["tarik_harian"],
            "kena_admin":   False if free is None else count >= free,
        }

    # ── Transactions ─────────────────────────────────────────────────────────

    def tarik(self, jumlah: int, pecahan: int) -> tuple[bool, str, str | None]:
        """
        Kembalikan (ok, pesan, notif_level).
        notif_level berisi pesan perubahan level jika ada, atau None.
        """
        if not self.logged_in:
            return False, "Belum login.", None
        if pecahan not in (50_000, 100_000):
            return False, "Pecahan tidak valid.", None
        if jumlah <= 0:
            return False, "Jumlah harus lebih dari 0.", None
        if jumlah % pecahan != 0:
            return False, f"Jumlah harus kelipatan {fmt_rp(pecahan)}.", None

        # Validasi batas per-transaksi berdasarkan pecahan
        maks_per_tx = MAKS_TARIK_PER_TRANSAKSI[pecahan]
        if jumlah > maks_per_tx:
            return False, (
                f"Maksimal sekali tarik pecahan {fmt_rp(pecahan)} "
                f"adalah {fmt_rp(maks_per_tx)}."
            ), None

        no_rek = self.logged_in
        self._reset_monthly_if_needed(no_rek)
        self._reset_daily_tarik_if_needed(no_rek)

        acc = self.accounts[no_rek]
        cfg = self.get_level_config()

        # Cek maks tarik bulanan
        if cfg["maks_tarik_bulanan"] is not None:
            if acc["withdraw_count"] >= cfg["maks_tarik_bulanan"]:
                return False, (
                    f"Batas tarik bulanan ({cfg['maks_tarik_bulanan']}x) "
                    f"sudah tercapai."
                ), None

        # Hitung biaya admin
        biaya_admin = 0
        if cfg["free_tarik"] is not None and acc["withdraw_count"] >= cfg["free_tarik"]:
            biaya_admin = cfg["biaya_admin"]

        total_debit = jumlah + biaya_admin

        # Cek limit harian
        if acc["tarik_harian"] + jumlah > cfg["limit_tarik_harian"]:
            sisa = cfg["limit_tarik_harian"] - acc["tarik_harian"]
            return False, (
                f"Melebihi limit tarik harian. "
                f"Sisa limit hari ini: {fmt_rp(sisa)}."
            ), None

        # Cek saldo (jumlah + admin)
        if total_debit > acc["balance"]:
            if biaya_admin > 0:
                return False, (
                    f"Saldo tidak mencukupi. "
                    f"Dibutuhkan {fmt_rp(total_debit)} "
                    f"(termasuk admin {fmt_rp(biaya_admin)})."
                ), None
            return False, "Saldo tidak mencukupi.", None

        # Eksekusi
        lembar                = jumlah // pecahan
        acc["balance"]       -= total_debit
        acc["tarik_harian"]  += jumlah
        acc["withdraw_count"] += 1

        keterangan = f"TARIK  {fmt_rp(jumlah)}  ({lembar} lembar @{fmt_rp(pecahan)})"
        if biaya_admin > 0:
            keterangan += f"  | Admin: {fmt_rp(biaya_admin)}"
        keterangan += f"  | Sisa: {fmt_rp(acc['balance'])}"

        self._record(keterangan)
        self._save_accounts()

        # Cek level realtime setelah saldo berkurang
        notif_level = self._check_and_update_level(no_rek)

        pesan = f"Berhasil tarik {fmt_rp(jumlah)} ({lembar} lembar @{fmt_rp(pecahan)})."
        if biaya_admin > 0:
            pesan += f"\n  Biaya admin: {fmt_rp(biaya_admin)}."
        return True, pesan, notif_level

    def transfer(self, no_rek_tujuan: str, jumlah: int) -> tuple[bool, str, str | None]:
        """
        Kembalikan (ok, pesan, notif_level).
        notif_level berisi pesan perubahan level jika ada, atau None.
        """
        if not self.logged_in:
            return False, "Belum login.", None
        if no_rek_tujuan == self.logged_in:
            return False, "Tidak bisa transfer ke rekening sendiri.", None
        if no_rek_tujuan not in self.accounts:
            return False, "Nomor rekening tujuan tidak ditemukan.", None
        if jumlah < 10_000:
            return False, "Jumlah minimal transfer Rp10.000.", None

        no_rek = self.logged_in
        self._reset_daily_transfer_if_needed(no_rek)

        acc = self.accounts[no_rek]
        cfg = self.get_level_config()

        # Cek limit transfer harian
        if acc["transfer_harian"] + jumlah > cfg["limit_transfer_harian"]:
            sisa = cfg["limit_transfer_harian"] - acc["transfer_harian"]
            return False, (
                f"Melebihi limit transfer harian. "
                f"Sisa limit hari ini: {fmt_rp(sisa)}."
            ), None

        if jumlah > acc["balance"]:
            return False, "Saldo tidak mencukupi.", None

        nama_tujuan                              = self.accounts[no_rek_tujuan]["name"]
        acc["balance"]                          -= jumlah
        self.accounts[no_rek_tujuan]["balance"] += jumlah
        acc["transfer_harian"]                  += jumlah

        self._record(
            f"TRANSFER  {fmt_rp(jumlah)}  → {nama_tujuan} ({no_rek_tujuan})"
            f"  | Sisa: {fmt_rp(acc['balance'])}"
        )

        waktu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        entry_masuk = {
            "waktu": waktu,
            "keterangan": (
                f"MASUK    {fmt_rp(jumlah)}  ← {self.get_nama()} ({self.logged_in})"
                f"  | Saldo: {fmt_rp(self.accounts[no_rek_tujuan]['balance'])}"
            )
        }
        self.accounts[no_rek_tujuan].setdefault("history", []).append(entry_masuk)
        self._save_accounts()

        # Cek level realtime setelah saldo berkurang
        notif_level = self._check_and_update_level(no_rek)

        return True, f"Transfer {fmt_rp(jumlah)} ke {nama_tujuan} berhasil.", notif_level

    # ── History (Stack + JSON) ────────────────────────────────────────────────

    def _record(self, keterangan: str):
        waktu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        entry = {"waktu": waktu, "keterangan": keterangan}
        self.history.push(entry)
        if self.logged_in:
            self.accounts[self.logged_in]["history"] = self.history._data
            self._save_accounts()

    def get_history(self) -> list[dict]:
        return self.history.to_list()


# ── Helper format (dipakai internal atm.py juga) ──────────────────────────────

def fmt_rp(amount: int) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")
