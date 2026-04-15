# 🚛 Freight Rate Calculator

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-150458?style=flat&logo=pandas&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

A web application for automated freight cost calculation based on real logistics business rules — handling multiple client rate tables, vehicle types, CIF/FOB operations, ICMS tax, and minimum weight thresholds.

> 💡 **Demo version** with anonymized data. The production version of this system is actively used at a Brazilian logistics company to replace manual spreadsheet lookups across multiple client contracts.

🔗 **[Live Demo](https://frete-calculator-marco.streamlit.app)**

---

## 📸 Overview

The app reads structured Excel rate tables and calculates freight costs by applying client-specific business rules:

- **Minimum weight enforcement** (e.g., 25-ton floor)
- **Per-ton tariff calculation** above minimum thresholds
- **ICMS tax** — either calculated separately or embedded in the rate
- **Toll fees** — either included in the rate or added separately
- **Vehicle type filtering** (truck categories)
- **Operation type filtering** (CIF vs FOB)

---

## ✨ Features

- 📂 **Multi-table support** — load and switch between different client rate tables (each with its own structure and rules)
- 🔍 **Smart origin/destination lookup** — fuzzy text matching with `difflib` handles typos and accented characters
- ⚖️ **Flexible weight input** — accepts both kg and tons (e.g., `24500`, `24.5`, `24,5`)
- 🚚 **Dynamic vehicle filtering** — dropdowns update based on available routes
- 🔄 **CIF/FOB filtering** — auto-detects operation type column per table
- 📤 **Spreadsheet upload** — users can replace the default table at runtime without touching the code
- 🧮 **Multiple pricing rules** — `tarifa_com_minimo`, `icms_embutido`, `valor_total_preferencial`
- 📊 **Detailed results** — freight base, toll, ICMS, total, applied rule, weight charged
- 💾 **Session state** — results persist across interactions

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| Streamlit | Web UI framework |
| Pandas | Data loading and filtering |
| OpenPyXL | Excel file reading |
| difflib | Fuzzy text matching |
| unicodedata | Text normalization (accents, case) |
| pathlib | File path handling |
| Streamlit Cloud | Deployment |

---

## 📁 Project Structure

```
frete-calculator-streamlit/
├── app.py              # Main application (UI + business logic)
├── planilhas/          # Rate table Excel files
│   ├── tabela_a.xlsx
│   ├── tabela_b.xlsx
│   └── tabela_c.xlsx
├── requirements.txt    # Python dependencies
└── README.md
```

---

## ⚙️ How It Works

### 1. Table Configuration
Each client rate table is defined by a config dictionary specifying column names, header rows, pricing rules, and minimum weights. The app dynamically resolves columns even when names vary across spreadsheets.

### 2. Pricing Rules
Three rule types are supported:

- **`tarifa_com_minimo`** — applies a flat rate for loads under minimum weight, then switches to per-ton tariff
- **`icms_embutido`** — ICMS already included in the rate; no separate tax calculation
- **`valor_total_preferencial`** — uses a "total value" column when available, falls back to base rate

### 3. Text Normalization
All origin/destination lookups go through normalization (lowercase, strip accents, remove extra whitespace) to avoid mismatches from formatting inconsistencies in the spreadsheets.

---

## 🚀 Running Locally

```bash
# Clone the repository
git clone https://github.com/Azevedo-073/frete-calculator-streamlit
cd frete-calculator-streamlit

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

---

## 📦 Requirements

```
streamlit
pandas
openpyxl
```

---

## 💼 Context

Freight pricing in Brazilian logistics involves multiple variables per shipment: client-specific rate tables, vehicle categories, CIF/FOB modalities, state-level ICMS tax rates, and minimum billing thresholds. Manually looking up these values across spreadsheets is slow and error-prone.

This app was built to automate that process — turning multi-column Excel tables into an interactive calculator with proper rule enforcement. The production version handles real client contracts across several major industrial accounts.

---

## 🗺️ Roadmap

- [ ] Database backend (PostgreSQL/Supabase) to store rate tables
- [ ] Authentication for multi-user access
- [ ] Export results to PDF/Excel
- [ ] Route history and audit log
- [ ] REST API for integration with TMS systems

---

## 👤 Author

**Marco Azevedo**  
[GitHub](https://github.com/Azevedo-073)

---

## 📄 License

MIT License — feel free to use and adapt.
