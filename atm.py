"""
Core ATM logic.
Struktur Data: Stack (riwayat transaksi), Dictionary (data rekening)
History transaksi disimpan ke JSON supaya persist setelah program ditutup.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent / "accounts.json"


# ─── Konstanta Level ──────────────────────────────────────────────────────────

LEVEL_CONFIG = {
    "Silver": {
        "limit_tarik_harian":    2_000_000,
        "limit_transfer_harian": 5_000_000,
        "maks_tarik_bulanan":    10,
        "free_tarik":            3,
        "biaya_admin":           6_500,
    },
    "Gold": {
        "limit_tarik_harian":    5_000_000,
        "limit_transfer_harian": 15_000_000,
        "maks_tarik_bulanan":    15,
        "free_tarik":            5,
        "biaya_admin":           5_000,
    },
    "Platinum": {
        "limit_tarik_harian":    15_000_000,
        "limit_transfer_harian": 50_000_000,
        "maks_tarik_bulanan":    20,
        "free_tarik":            10,
        "biaya_admin":           2_500,
    },
    "Priority": {
        "limit_tarik_harian":    50_000_000,
        "limit_transfer_harian": 100_000_000,
        "maks_tarik_bulanan":    None,   # unlimited
        "free_tarik":            None,   # semua free
        "biaya_admin":           0,
    },
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
            "level":                  "Silver",
            "withdraw_count":         0,
            "last_reset_month":       "",
            "tarik_harian":           0,
            "last_tarik_date":        "",
            "transfer_harian":        0,
            "last_transfer_date":     "",
            "downgrade_warning_date": None,
        }
        for key, val in defaults.items():
            if key not in acc:
                acc[key] = val
                changed = True
        if changed:
            self._save_accounts()

    # ── Auto-Leveling (Dynamic Tiering + Grace Period) ────────────────────────

    def _level_sesuai_saldo(self, saldo: int) -> str:
        """Tentukan level yang sesuai berdasarkan saldo saat ini."""
        level = "Silver"
        for lv in LEVEL_ORDER:
            if saldo >= LEVEL_THRESHOLD[lv]:
                level = lv
        return level

    def _check_and_update_level(self, no_rek: str):
        """
        Periksa dan perbarui level rekening berdasarkan saldo.
        - Naik level: instan.
        - Turun level: grace period 10 hari.
        Dipanggil saat login dan setiap transaksi yang mengurangi saldo.
        """
        acc    = self.accounts[no_rek]
        saldo  = acc["balance"]
        level_sekarang = acc.get("level", "Silver")
        level_ideal    = self._level_sesuai_saldo(saldo)

        idx_sekarang = LEVEL_ORDER.index(level_sekarang)
        idx_ideal    = LEVEL_ORDER.index(level_ideal)

        hari_ini      = datetime.now().date()
        warning_str   = acc.get("downgrade_warning_date")
        warning_date  = datetime.strptime(warning_str, "%Y-%m-%d").date() if warning_str else None

        changed = False

        if idx_ideal > idx_sekarang:
            # ── Naik level: instan ──
            acc["level"]                  = level_ideal
            acc["downgrade_warning_date"] = None
            changed = True

        elif idx_ideal < idx_sekarang:
            # ── Saldo turun di bawah threshold level saat ini ──
            if warning_date is None:
                # Pertama kali turun: catat grace period (10 hari ke depan)
                deadline = hari_ini + timedelta(days=10)
                acc["downgrade_warning_date"] = deadline.strftime("%Y-%m-%d")
                changed = True
            else:
                # Sudah ada warning — cek apakah sudah lewat grace period
                if hari_ini >= warning_date:
                    # Grace period habis: turunkan level
                    acc["level"]                  = level_ideal
                    acc["downgrade_warning_date"] = None
                    changed = True
                # Jika belum lewat: biarkan level & warning_date tetap

        else:
            # ── Level sudah sesuai saldo ──
            if warning_date is not None:
                # Saldo sudah naik kembali → hapus warning
                acc["downgrade_warning_date"] = None
                changed = True

        if changed:
            self._save_accounts()

    def get_downgrade_info(self) -> dict | None:
        """
        Kembalikan info grace period jika sedang aktif, atau None.
        Berguna untuk ditampilkan di dashboard.
        """
        if not self.logged_in:
            return None
        acc         = self.accounts[self.logged_in]
        warning_str = acc.get("downgrade_warning_date")
        if not warning_str:
            return None
        warning_date  = datetime.strptime(warning_str, "%Y-%m-%d").date()
        hari_ini      = datetime.now().date()
        sisa_hari     = (warning_date - hari_ini).days
        level_tujuan  = self._level_sesuai_saldo(acc["balance"])
        return {
            "warning_date": warning_str,
            "sisa_hari":    max(0, sisa_hari),
            "level_tujuan": level_tujuan,
        }

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
        self._check_and_update_level(no_rek)   # ← cek level saat login
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

    def tarik(self, jumlah: int, pecahan: int) -> tuple[bool, str]:
        if not self.logged_in:
            return False, "Belum login."
        if pecahan not in (50_000, 100_000):
            return False, "Pecahan tidak valid."
        if jumlah <= 0:
            return False, "Jumlah harus lebih dari 0."
        if jumlah % pecahan != 0:
            return False, f"Jumlah harus kelipatan Rp{pecahan:,.0f}."

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
                )

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
                f"Sisa limit hari ini: Rp{sisa:,.0f}."
            )

        # Cek saldo (jumlah + admin)
        if total_debit > acc["balance"]:
            if biaya_admin > 0:
                return False, (
                    f"Saldo tidak mencukupi. "
                    f"Dibutuhkan Rp{total_debit:,.0f} "
                    f"(termasuk admin Rp{biaya_admin:,.0f})."
                )
            return False, "Saldo tidak mencukupi."

        # Eksekusi
        lembar               = jumlah // pecahan
        acc["balance"]      -= total_debit
        acc["tarik_harian"] += jumlah
        acc["withdraw_count"] += 1

        keterangan = (
            f"TARIK  Rp{jumlah:,.0f}  ({lembar} lembar @Rp{pecahan:,.0f})"
        )
        if biaya_admin > 0:
            keterangan += f"  | Admin: Rp{biaya_admin:,.0f}"
        keterangan += f"  | Sisa: Rp{acc['balance']:,.0f}"

        self._record(keterangan)
        self._save_accounts()

        # ← Cek level setelah tarik (saldo berkurang)
        self._check_and_update_level(no_rek)

        pesan = f"Berhasil tarik Rp{jumlah:,.0f} ({lembar} lembar @Rp{pecahan:,.0f})."
        if biaya_admin > 0:
            pesan += f"\n  Biaya admin: Rp{biaya_admin:,.0f}."
        return True, pesan

    def transfer(self, no_rek_tujuan: str, jumlah: int) -> tuple[bool, str]:
        if not self.logged_in:
            return False, "Belum login."
        if no_rek_tujuan == self.logged_in:
            return False, "Tidak bisa transfer ke rekening sendiri."
        if no_rek_tujuan not in self.accounts:
            return False, "Nomor rekening tujuan tidak ditemukan."
        if jumlah < 10_000:
            return False, "Jumlah minimal transfer Rp10.000."

        no_rek = self.logged_in
        self._reset_daily_transfer_if_needed(no_rek)

        acc = self.accounts[no_rek]
        cfg = self.get_level_config()

        # Cek limit transfer harian
        if acc["transfer_harian"] + jumlah > cfg["limit_transfer_harian"]:
            sisa = cfg["limit_transfer_harian"] - acc["transfer_harian"]
            return False, (
                f"Melebihi limit transfer harian. "
                f"Sisa limit hari ini: Rp{sisa:,.0f}."
            )

        if jumlah > acc["balance"]:
            return False, "Saldo tidak mencukupi."

        nama_tujuan                             = self.accounts[no_rek_tujuan]["name"]
        acc["balance"]                         -= jumlah
        self.accounts[no_rek_tujuan]["balance"] += jumlah
        acc["transfer_harian"]                 += jumlah

        self._record(
            f"TRANSFER  Rp{jumlah:,.0f}  → {nama_tujuan} ({no_rek_tujuan})"
            f"  | Sisa: Rp{acc['balance']:,.0f}"
        )

        waktu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        entry_masuk = {
            "waktu": waktu,
            "keterangan": (
                f"MASUK    Rp{jumlah:,.0f}  ← {self.get_nama()} ({self.logged_in})"
                f"  | Saldo: Rp{self.accounts[no_rek_tujuan]['balance']:,.0f}"
            )
        }
        self.accounts[no_rek_tujuan].setdefault("history", []).append(entry_masuk)
        self._save_accounts()

        # ← Cek level setelah transfer (saldo berkurang)
        self._check_and_update_level(no_rek)

        return True, f"Transfer Rp{jumlah:,.0f} ke {nama_tujuan} berhasil."

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
