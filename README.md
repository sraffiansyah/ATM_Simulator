# 🏧 ATM Simulator

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

> 💻 **Console-Based Banking Simulation** | Built with Python, OOP & Computer Vision  
> 🔗 **Frontend Companion:** [ATM Card Designer (Web)](https://atm-generator-by-vyyy.netlify.app/)

---

## 📖 About The Project

A fully functional, terminal-based ATM simulator that demonstrates advanced banking logic, dynamic account management, and real-time computer vision integration. Features a **dynamic leveling system**, **smart denomination detection**, **daily/monthly limits**, **admin fees**, and a **real-time OCR card scanner** for instant balance inquiry without login.

Built as a comprehensive coursework project focusing on **Data Structures (Stack)**, **OOP Architecture**, **State Persistence**, and **CLI UX Design**.

---

## ✨ Features

- 🔐 **Secure Login & Session Management** — Account authentication with PIN verification
- 📊 **Dynamic Account Leveling** — Auto-upgrades/downgrades (Silver → Gold → Platinum → Priority) based on real-time balance
- 💸 **Smart Withdrawal System** — Auto-detects denomination (50k/100k), enforces per-transaction limits, and applies admin fees based on tier
- 🔄 **Rate Limiting & Auto-Reset** — Daily & monthly withdrawal/transfer limits with automatic tracker reset
- 📤 **Instant Transfer** — Real-time validation, minimum amount check, daily limit enforcement, and cross-account history logging
- 📜 **LIFO Transaction History** — Stack-based history tracking, persistently saved to JSON across sessions
- 📷 **Real-Time OCR Card Scanner** — OpenCV + Tesseract integration for instant 16-digit card reading & balance display
- 🖥️ **Clean CLI UX** — Structured menus, input sanitization, formatted currency output, and graceful error handling

---

## 🛠️ Tech Stack & Architecture

| Component | Technology / Pattern |
|-----------|----------------------|
| **Language** | Python 3.8+ |
| **Architecture** | OOP, Modular Design (`ATM`, `Stack` classes) |
| **Data Structures** | `Dictionary` (O(1) account lookup), `Stack` (LIFO transaction history) |
| **Persistence** | JSON file-based storage with auto-sync |
| **Computer Vision** | OpenCV (`cv2`), `pytesseract` (OCR engine), `numpy` |
| **CLI UX** | `getpass` (hidden PIN), formatted tables, input validation loops |

---

## 🚀 Installation & Setup

### 1️⃣ Install Python (Required)
- Download the official installer: https://www.python.org/downloads/
- ⚠️ **IMPORTANT:** During installation, **check the box `Add Python to PATH`** at the bottom of the installer!
- Verify installation in terminal/cmd:
  ```bash
  python --version
  # or
  python3 --version
  ```

### 2️⃣ Create Virtual Environment (Highly Recommended)
Prevents library conflicts with other projects:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```
*(When successful, `(venv)` will appear at the start of your terminal line)*

### 3️⃣ Install Python Dependencies
Run this command in the activated `venv` terminal:
```bash
pip install opencv-python pytesseract numpy
```
> 💡 **Tip:** If you encounter `permission denied` or `externally-managed-environment` errors, ensure your virtual environment is activated, or add the `--user` flag at the end of the command.

### 4️⃣ Install Tesseract OCR (Engine for Card Scanner)

#### 🪟 Windows — Detailed Steps
1. **Download Installer**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download the latest `.exe` file (e.g., `tesseract-ocr-w64-setup-v5.x.x.exe`)

2. **Run the Installer**
   - Right-click the `.exe` file → **Run as administrator**
   - Follow the installation wizard (Next → Next)

3. **Select Additional Components (IMPORTANT!)**
   - When the **"Choose Components"** page appears, check:
     - ✅ `Additional language data` → `English`
     - ✅ `Development headers` (optional, but recommended)
   - Continue installation until complete

4. **Note the Installation Path**
   - Default path: `C:\Program Files\Tesseract-OCR`
   - Copy this path for the next step

5. **Add to Environment Variables**
   - Press `Windows + R`, type `sysdm.cpl`, press Enter
   - Go to the **Advanced** tab → click **Environment Variables...**
   - Under **System variables**, find and select `Path` → click **Edit**
   - Click **New** → paste the Tesseract path: `C:\Program Files\Tesseract-OCR`
   - Click **OK** on all windows to save

6. **Verify Installation**
   - Open a **new Command Prompt** (Ctrl + R → type `cmd` → Enter)
   - Run:
     ```bash
     tesseract --version
     ```
   - If Tesseract version info appears, installation was successful! ✅

#### 🍎 macOS
```bash
brew install tesseract
```

#### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install tesseract-ocr
```

### 5️⃣ Run the Application
```bash
python main.py
```
The main menu will appear. Type `1` to login, or `2` to test the card scanner.

---

## 📂 Project Structure

```
atm-simulator-core/
├── 🐍 main.py           # Entry point, CLI menus, input validation
├── 🧠 atm.py            # Core banking logic, Stack, Level system, Limits & Fees
├── 📷 scanner.py        # OpenCV camera interface & Tesseract OCR engine
├── 📄 accounts.json     # Persistent account data, history & level tracking
├── 📄 requirements.txt  # Python dependencies
└── 📄 README.md         # Documentation
```

---

## 👤 Demo Accounts & How to Test OCR

| Account Number | PIN    | Name                  | Initial Balance   | Level    |
|----------------|--------|-----------------------|-------------------|----------|
| `15250408`     | `654321` | Syukron Raffiansyah   | Rp 823.100.000    | Priority |
| `15250261`     | `123456` | Aditya Romadhoni      | Rp 500.950.000    | Priority |
| `15250571`     | `123456` | Yasmine Sheilana      | Rp 500.000.000    | Priority |

### 📷 How to Use the Card Scan Feature
1. Select menu `2. Check Balance (Scan Card)` from the main menu.
2. A camera window will open with a green `SCAN AREA` box.
3. **Write a 16-digit account number on white paper** (e.g., `1525040815250408`) or show a real ATM card.
4. Position it inside the green box. The balance will automatically appear on screen.
5. Press `Q` to close the camera.

> 💡 **OCR Tips:** Ensure good lighting, clear text, and camera focus. OCR works best with bold printed numbers on white paper.

---

## 🗂️ Add New Account

Edit `accounts.json` and add a new entry:

```json
"9988776655": {
    "name": "Your Name",
    "pin": "0000",
    "balance": 1000000,
    "card_number": "5816350255816350",
    "level": "Silver",
    "withdraw_count": 0,
    "last_reset_month": "",
    "tarik_harian": 0,
    "last_tarik_date": "",
    "transfer_harian": 0,
    "last_transfer_date": "",
    "history": []
}
```

> ⚠️ **Note:** Ensure valid JSON format (pay attention to commas `,` after each field except the last one).

---

## 🙏 Acknowledgments

- **OpenCV & Tesseract Teams** — For powerful, open-source computer vision tools
- **Python Community** — For extensive documentation and beginner-friendly ecosystems
- **Dicoding & Campus** — For structured learning paths that made this project possible
- **Open Source Contributors** — For CLI design patterns, OCR optimization tips, and data structure references

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

> ⚠️ **Disclaimer:** This is a **simulation project for educational purposes only**. No real banking transactions are processed. All account data is locally stored and can be modified/deleted freely.

---

<div align="center">
  <sub>Built with 💻 & 🐍 by <strong>Syukron Raffiansyah (Vyy)</strong> • 2026</sub>
</div>
```

---

### 🔧 Checklist Before Push:
- [ ] If `requirements.txt` doesn't exist, create it with:
  ```txt
  opencv-python
  pytesseract
  numpy
  ```
- [ ] Update the link `atm-generator-by-vyyy.netlify.app` if your domain is different
- [ ] Commit & push:
  ```bash
  git add README.md requirements.txt
  git commit -m "docs: update README with full English setup guide & advanced features"
  git push origin main
  ```
