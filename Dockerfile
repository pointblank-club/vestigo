FROM ubuntu:22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VENV_DIR=/opt/vestigo/venv
ENV GHIDRA_INSTALL_DIR=/opt/ghidra
ENV QILING_DIR=/opt/vestigo/qiling_analysis/qiling
ENV ROOTFS_DIR=/opt/vestigo/qiling_analysis/rootfs
ENV PATH="$VENV_DIR/bin:$GHIDRA_INSTALL_DIR/support:$PATH"
ENV PYTHONPATH="/app:/app/scripts:/app/backend:$PYTHONPATH"

# 1. Install System Dependencies & Cross-Compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    build-essential \
    cmake \
    pkg-config \
    wget \
    curl \
    strace \
    file \
    binutils \
    binwalk \
    libffi-dev \
    libssl-dev \
    liblzma-dev \
    liblzo2-dev \
    zlib1g-dev \
    libsqlite3-dev \
    libreadline-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libmagic-dev \
    libbz2-dev \
    libxml2-dev \
    libxmlsec1-dev \
    xz-utils \
    tk-dev \
    yara \
    unzip \
    openjdk-17-jdk \
    # Cross-compiler toolchains
    binutils-aarch64-linux-gnu \
    binutils-arm-linux-gnueabi \
    binutils-arm-linux-gnueabihf \
    binutils-mips-linux-gnu \
    binutils-mipsel-linux-gnu \
    gcc-aarch64-linux-gnu \
    gcc-arm-linux-gnueabi \
    gcc-arm-linux-gnueabihf \
    gcc-mips-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup Directory Structure
WORKDIR /app
COPY . /app

# 3. Install Ghidra Headless
ARG GHIDRA_VERSION="11.2.1"
ARG GHIDRA_DATE="20241105"
RUN echo "Downloading Ghidra ${GHIDRA_VERSION}..." && \
    wget -q -O /tmp/ghidra.zip "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_DATE}.zip" && \
    mkdir -p "${GHIDRA_INSTALL_DIR}" && \
    unzip -q /tmp/ghidra.zip -d /tmp/ghidra_extract && \
    mv /tmp/ghidra_extract/ghidra_*/* "${GHIDRA_INSTALL_DIR}/" && \
    rm -rf /tmp/ghidra.zip /tmp/ghidra_extract && \
    chmod +x "${GHIDRA_INSTALL_DIR}/support/analyzeHeadless"

# 4. Setup Python Virtual Environment & Install Dependencies
RUN python3 -m venv "$VENV_DIR" && \
    . "$VENV_DIR/bin/activate" && \
    pip install --upgrade pip setuptools wheel && \
    # Install typing-extensions first
    pip install "typing_extensions>=4.6.0" && \
    # Install PyTorch CPU first (to save size)
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    # Install main dependencies
    pip install \
    'fastapi>=0.100.0' \
    'uvicorn>=0.23.0' \
    'python-multipart>=0.0.6' \
    'pydantic>=2.0.0' \
    'python-dotenv>=1.0.0' \
    'python-magic>=0.4.27' \
    'requests>=2.31.0' \
    'prisma>=0.11.0' \
    'scikit-learn>=1.3.0' \
    'lightgbm>=4.0.0' \
    'pandas>=2.0.0' \
    'numpy>=1.24.0' \
    'joblib>=1.3.0' \
    'pyelftools>=0.28' \
    'capstone>=4.0.0' \
    'yara-python>=4.0.0' \
    'pycryptodome>=3.15.0' \
    'z3-solver>=4.11.0' \
    'binwalk' \
    'unicorn==2.1.3' \
    'keystone-engine>=0.9.2' \
    'pefile>=2022.5.30' \
    'python-registry>=1.3.1' \
    'gevent>=20.9.0' \
    'multiprocess>=0.70.12.2' \
    'pyyaml>=6.0.1' \
    'python-fx' \
    'questionary' \
    'termcolor' \
    'openai>=1.0.0' \
    'colorama>=0.4.6' \
    'tqdm>=4.65.0' \
    'rich>=13.0.0' \
    'loguru>=0.7.0' \
    'pytest>=7.0.0' \
    'torch-geometric>=2.3.0' \
    'matplotlib>=3.7.0' \
    'seaborn>=0.12.0' \
    'networkx>=2.6.0'

# 5. Install Qiling & Rootfs
# Note: We clone to specific paths but Qiling needs editable install or standard install.
# Since we are in Docker, standard pip install of the repo is better than editable if we don't plan to change Qiling code.
# However, to match setup.sh structure:
RUN git clone https://github.com/qilingframework/qiling.git "${QILING_DIR}" && \
    . "$VENV_DIR/bin/activate" && \
    pip install "${QILING_DIR}" && \
    git clone https://github.com/qilingframework/rootfs.git "${ROOTFS_DIR}"

# 6. Generate Prisma Config
# Note: This requires DATABASE_URL to be set at runtime or build time if schema validation needs it.
# We'll skip generation here and rely on entrypoint or manual run if env vars are missing.
RUN if [ -f /app/backend/prisma/schema.prisma ]; then \
    . "$VENV_DIR/bin/activate" && \
    cd /app/backend && \
    # Attempt generation, but don't fail build if DB URL missing
    prisma generate || echo "Prisma generation skipped (needs DATABASE_URL)"; \
    fi

# 7. Finalize
EXPOSE 8000
CMD ["/bin/bash", "-c", "source $VENV_DIR/bin/activate && cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"]
