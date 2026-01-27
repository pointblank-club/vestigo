# Vestigo: Firmware analysis & crypto-detection pipeline

Vestigo is a collection of tools, scripts and services to automate
the process of (1) producing cross-compiled test binaries, (2)
statically and dynamically analyzing firmware/binaries, (3)
extracting ML-ready features, and (4)
producing datasets and inference results for cryptographic-function detection. The repo
combines headless Ghidra-based extraction, Qiling-based dynamic
tracing, a dataset generation pipeline (including optional LLM
assisted labeling), and a small backend + frontend for web access.

This README gives a concise, practical overview and quickstart so
you can get the pipeline running and contribute.

## Key project goals

- Extract function-level and trace-level features suitable for ML
- Provide utilities for static (Ghidra) and dynamic (Qiling) analysis
- Offer scripts to build training CSVs and run inference
- Provide a backend API and frontend for file upload and analysis

## Quick facts / highlights

- Languages: Python (main tooling & backend), TypeScript/React frontend
- Major folders: `ghidra_scripts`, `qiling_analysis`, `ml`, `backend`, `frontend`
- Important entry points:
  - `generate_dataset.py` — create ML CSVs from Ghidra JSONs
    - `analyzer.py`, `bare_metal.py`, `main.py` — orchestrate analysis flows
    - `factory/builder.py` — cross-compile sources across arch/opt matrix
    - `qiling_analysis/` — dynamic tracing & batch extraction pipeline
    - `backend/` — FastAPI backend with analysis endpoints

## Quick Setup

### 1. Automated Installation

```bash
./setup.sh
source activate_vestigo.sh
```

**What gets installed:**
- Python environment with all dependencies (FastAPI, Qiling, ML libraries)
- Ghidra headless analyzer (/opt/ghidra)
- Qiling framework + rootfs
- Cross-compiler toolchains (ARM, MIPS, AArch64)
- Container runtime (Podman/Docker)

**Options:** `--minimal` | `--skip-ghidra` | `--skip-ml` | `--help`

### 2. Manual Steps Required

**Frontend (Node.js 18+):**
```bash
# Install Node.js for your OS, then:
cd frontend && npm install && cd ..
```

**Database (PostgreSQL):**
```bash
# Option A: Local
sudo apt install postgresql && sudo -u postgres createdb vestigo

# Option B: Cloud (https://neon.tech - recommended)
# Get connection string and add to .env
```

**Configure .env:**
```bash
DATABASE_URL=postgresql://user:pass@host:5432/vestigo
OPENAI_API_KEY=sk-your-key-here  # Get from platform.openai.com
```

**Initialize Database:**
```bash
cd backend && prisma db push && prisma generate && cd ..
```

## Usage

**Always activate environment first:** `source activate_vestigo.sh`

### Static Analysis (Ghidra)
```bash
python3 scripts/analyzer.py <binary>
```

### Dynamic Analysis (Qiling)
```bash
python3 qiling_analysis/tests/verify_crypto.py <binary>
```

### Generate ML Dataset
```bash
python3 scripts/generate_dataset.py --input-dir ghidra_output --output dataset.csv
```

### Batch Processing
```bash
python3 qiling_analysis/batch_extract_features.py \
    --dataset-dir ./dataset_binaries --output-dir ./results --parallel 4
```

### Cross-Compile Binaries
```bash
python3 factory/builder.py --source algorithm.c
```

### LLM Crypto Analysis
```bash
python3 qiling_analysis/tests/llm/crypto_deep_analyzer.py --strace trace.log --output analysis.json
```

### Run Web Interface
```bash
# Backend (terminal 1)
cd backend && uvicorn main:app --reload

# Frontend (terminal 2)
cd frontend && npm run dev
```

## Project Structure

```
vestigo-data/
├── setup.sh                 # Automated installation
├── activate_vestigo.sh      # Environment activation
├── backend/                 # FastAPI server
├── frontend/                # React UI
├── factory/                 # Cross-compilation tools
├── ghidra_scripts/          # Ghidra analysis scripts
├── qiling_analysis/         # Dynamic tracing pipeline
├── ml/                      # ML models and training
├── scripts/                 # Analysis orchestration
└── dataset_binaries/        # Sample binaries
```

**Key Scripts:**
- `scripts/analyzer.py` - Ghidra static analysis
- `scripts/generate_dataset.py` - Create ML datasets
- `qiling_analysis/tests/verify_crypto.py` - Dynamic analysis
- `factory/builder.py` - Cross-compilation

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Virtual environment not found | Run `./setup.sh` |
| Import errors | `pip install -r requirements.txt -r backend/requirements.txt` |
| Qiling rootfs missing | `git clone --depth 1 https://github.com/qilingframework/rootfs.git qiling_analysis/rootfs` |
| Ghidra not found | Set `export GHIDRA_HOME=/opt/ghidra` |
| Database errors | Check `DATABASE_URL` in `.env`, run `prisma generate` |
| OpenAI quota exceeded | Check billing at platform.openai.com |
| Frontend won't start | `cd frontend && rm -rf node_modules && npm install` |

## System Requirements

- **OS**: Ubuntu/Debian, Fedora/RHEL, Arch, macOS
- **RAM**: 8GB min, 16GB recommended
- **Disk**: ~10GB
- **Python**: 3.9+ (3.11 recommended)
- **Node.js**: 18+ (for frontend)

## Documentation

- `qiling_analysis/QUICKSTART_GUIDE.md` - Dynamic analysis guide
- `CONTRIBUTING.md` - Contribution guidelines

## License

Apache-2.0 - See `LICENSE`
