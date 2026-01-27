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

## Minimum prerequisites

- Python 3.9+ (3.11 recommended)
- pip and virtual env
- Ghidra (for static feature extraction using headless analyzer)
- Qiling (for dynamic tracing features)

See `setup.sh` for an automated environment setup script and path hints.

## Environment Setup

Before running the pipeline, you need to configure environment variables. Create a `.env` file in the project root:

1. Copy the example environment file:

     ```bash
     cp .env.example .env
     ```

2. Edit `.env` and fill in your actual values:

     ```bash
     # OpenAI API Configuration (optional)
     OPENAI_API_KEY=your_openai_api_key_here

     # Ghidra Installation Path
     GHIDRA_HOME=/path/to/ghidra

     # Python Virtual Environment Directory
     VENV_DIR=/path/to/vestigo-data/.venv

     # Database Configuration
     DATABASE_URL=postgresql://user:password@localhost:5432/vestigo

     # Perplexity API Configuration
     PERPLEXITY_API_KEY=your_perplexity_api_key_here
     ```

## Quickstart (recommended test flow)

1. Create and activate a virtualenv and install Python deps:

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```

2. Set up your environment variables (see "Environment Setup" section above).

3. If you want to generate the ML dataset from existing Ghidra JSONs:

     ```bash
     python3 generate_dataset.py --input-dir ghidra_output --output dataset_output.csv --limit 10
     ```

4. To run the dynamic trace batch extractor (Qiling pipeline) on a small sample:

     ```bash
     python3 qiling_analysis/batch_extract_features.py \
         --dataset-dir ./dataset_binaries --output-dir ./batch_results --limit 5 --parallel 2
     ```

5. To run the backend API locally (development):

     ```bash
     cd backend
     pip install -r requirements.txt
     # run with uvicorn
     uvicorn main:app --reload --host 127.0.0.1 --port 8000
     ```

6. Frontend: `frontend/` contains a React app — see its own package.json and scripts.

## Common workflows and commands

- Cross-compile many algorithm sources (factory):
  - `python3 factory/builder.py --source <file.c>` (see options in the script)
- Run static Ghidra analysis for a binary:
  - `python3 analyzer.py <binary>` (scripts call `ghidra_headless` internally)
- Generate ML dataset from Ghidra JSONs:
  - `python3 generate_dataset.py --input-dir ghidra_output --output dataset.csv`
- Run the Qiling-based full pipeline (traces → windowed features → inference):
  - see `qiling_analysis/FULL_PIPELINE_README.md` and `qiling_analysis/QUICKSTART_GUIDE.md`

## Repo layout (high level)

- `factory/` — tools to cross-compile C source set across architectures and options
- `ghidra_scripts/` — Ghidra helper scripts used by headless analysis
- `qiling_analysis/` — dynamic tracing and batch extraction pipeline
- `ml/` — dataset processing, labels, model helpers and evaluation scripts
- `backend/` — FastAPI backend and supporting services
- `frontend/` — React UI for uploads and results (if present)
- `dataset_binaries/`, `test_dataset_binaries/` — sample compiled binaries
- `ghidra_json/`, `ghidra_output/` — expected outputs from Ghidra headless runs
- `features.csv`, `features.txt` — canonical feature columns used by dataset scripts

## Notes, assumptions and safety

- Some scripts expect environment configuration (Ghidra path, OpenAI API key, rootfs for Qiling).
- Not all components are required to run every workflow; you can use only the static path (Ghidra → generate_dataset) or the dynamic path (Qiling tracing) independently.
- Several scripts are designed to be run inside CI or Docker with specific mounts; review `setup.sh` and `Containerfile` for reproducible environments.

## Contributing

Please see `CONTRIBUTING.md` for the contribution process, coding style and testing guidelines.

## License

This repository is licensed under the Apache-2.0 License — see `LICENSE`.

## Where to go next

- `qiling_analysis/QUICKSTART_GUIDE.md` — dynamic tracing quick start
- `README_DATASET.md` — dataset generation details and column descriptions
- `IMPLEMENTATION_SUMMARY.md` — helpers for converting JSON → CSV and matching columns

If anything is missing or you want a feature explained or automated, open an issue or follow the contribution guide.

## Features

- **Cross-Compilation Matrix**: Automatically builds C code for multiple architectures (x86_64, ARM, MIPS, RISC-V, AVR, Z80) and optimization levels using Docker.
- **Headless Ghidra Analysis**: Automates Ghidra to analyze binaries and export P-Code/instruction data to JSON.
- **Feature Extraction**: Extracts cryptographic indicators (S-Boxes, constants) and structural features (entropy, instruction histograms) from binaries and analysis results.

## Prerequisites

- **Docker**: Required for the cross-compilation environment.
- **Python 3.x**: For running the orchestration scripts.
- **Ghidra**: Required for `analyzer.py` to perform binary analysis.

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/pointblank-club/vestigo.git
    cd cross-compiler
    ```

2. Build the Docker image (required for `builder.py`):

    ```bash
    python3 builder.py --source aes_128.c --build-image
    ```

    _Note: You only need to run with `--build-image` once._

## Usage

### 1. Cross-Compilation (`builder.py`)

Compiles a source C file across all defined architectures and optimization levels.

```bash
python3 builder.py --source <source_file.c> [--output <output_dir>]
```

**Example:**

```bash
python3 builder.py --source aes_128.c --output bin
```

This will generate ELF/IHX binaries in the `bin/` directory for x86_64, ARM, MIPS, RISC-V, AVR, and Z80.

### 2. Binary Analysis (`analyzer.py`)

Uses Ghidra's `analyzeHeadless` to process all binaries in the `bin/` directory and export intermediate data.

**Configuration:**
Update the `GHIDRA_HOME` variable in `analyzer.py` to point to your Ghidra installation.

```bash
python3 analyzer.py
```

This produces `ghidra_output.json` (or individual JSONs depending on script configuration) containing function and instruction data.

### 3. Feature Extraction (`extract_features.py`)

Extracts ML-ready features from a binary and its corresponding Ghidra analysis JSON.

### **`4.features.json`**

Final feature vector for **Machine Learning** or **rule-based crypto detection**.

```bash
python3 extract_features.py
```

_Note: Currently configured to run on a specific example in `__main__`. Modify the script to iterate over your dataset as needed._

### 4. Dynamic Analysis (`dynamic_analysis/`)

Automates the emulation and instrumentation of firmware binaries to extract runtime secrets and detect security vulnerabilities.

**Components:**

- `emulator.py`: Runs binaries using QEMU User Mode.
- `instrumentation.py`: Injects Frida hooks to capture crypto keys.
- `log_monitor.py`: Scans logs for Secure Boot failures and other leaks.

**Usage:**

```bash
python3 dynamic_analysis/dynamic_main.py <binary_path> <arch> <sysroot_path>
```

_Example:_

```bash
python3 dynamic_analysis/dynamic_main.py ./busybox arm /tmp/extracted_fs
```

## Supported Architectures

The `builder.py` script supports the following architectures via the provided Dockerfile:

- **x86_64** (GCC, Clang)
- **ARM** (arm-linux-gnueabihf)
- **MIPS** (mips-linux-gnu)
- **RISC-V** (riscv64-linux-gnu)
- **AVR** (avr-gcc)
- **Z80** (sdcc)

## Project Structure

- `builder.py`: Orchestrates the Docker-based cross-compilation.
- `Dockerfile`: Defines the build environment with all cross-compilers.
- `analyzer.py`: Wrapper for Ghidra headless analysis.
- `ghidra_script.py`: The Ghidra Python script executed by `analyzeHeadless`.
- `extract_features.py`: Extracts static and structural features from binaries.
- `aes_*.c`: Example cryptographic source files.

---

## Firmware Extraction

### Prerequisites

- **Python 3**
- **Podman** (Docker can be used with script modification, but Podman is default)
- **Binwalk** (`sudo apt install binwalk`)
- **System Tools:** `objcopy` (usually part of binutils)

### Step 1: Build the Sasquatch Container

1. Build the image:

    ```bash
    podman build -t sasquatch_tool .
    ```

### Step 2: Run the Analyzer

Run the Python script on your firmware file. The script handles conversion, Binwalk extraction, container mounting, and crypto scanning automatically.

```bash
python3 unpacker.py <firmware_filename>
```
