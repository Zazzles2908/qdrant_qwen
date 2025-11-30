# Enhanced Dockerfile with Blackwell RTX 5070 Ti support
FROM nvidia/cuda:12.9.1-cudnn-devel-ubuntu24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VERSION=12.9.1
# RTX 5070 Ti Blackwell compute capability 12.0 (sm_120)
# Updated: November 30, 2025 - CUDA 12.9.1 recommended over 12.8 for better stability
ENV TORCH_CUDA_ARCH_LIST="12.0"

WORKDIR /app

# Install system dependencies (CUDA already included in base image)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    build-essential \
    cmake \
    curl \
    git \
    wget \
    pkg-config \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up CUDA environment
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"

# Create symlink for python
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Install PyTorch with CUDA 12.9.1 support for Blackwell RTX 5070 Ti
# Skip pip upgrade to avoid conflicts with Ubuntu packages
# Updated: November 30, 2025 - CUDA 12.9.1 with cu129 for Blackwell RTX 5070 Ti
# Available cu129 versions: torch 2.9.1, torchvision 0.24.1, torchaudio 2.9.1
# Reference: https://docs.nvidia.com/deeplearning/frameworks/support-matrix/index.html
RUN python3 -m pip install --break-system-packages --no-cache-dir torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu129

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# Install additional Blackwell optimizations
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    cupy-cuda12x \
    optuna \
    tensorboardX \
    && python3 -m pip cache purge

# Blackwell Architecture Notes:
# - RTX 5070 Ti uses compute capability 12.0 (sm_120)
# - CUDA 12.8 PyTorch binaries officially support Blackwell GPUs
# - Updated: November 30, 2025 based on MiniMax research
# - Reference: https://discuss.pytorch.org/t/nvidia-geforce-rtx-5070-ti-with-cuda-capability-sm-120/221509

# Set Blackwell-specific environment variables
ENV CUDA_DEVICE_MAX_CONNECTIONS=1
ENV CUDA_CACHE_PATH=/tmp/cuda_cache
ENV TORCH_BF16_LINEAR=1
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Copy the embedding services
COPY embedding_service.py .
COPY openai_compatible_api.py .
COPY healthcheck.py .

# Create models directory with proper permissions
RUN mkdir -p /app/models && chmod 755 /app/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 healthcheck.py || exit 1

# Run the service
CMD ["python", "embedding_service.py"]