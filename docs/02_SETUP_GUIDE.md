# Setup Guide - Complete Deployment Instructions

**Date**: December 9, 2025  
**Target System**: Windows 11 + WSL2 + RTX 5070 Ti  
**Estimated Time**: 30-45 minutes

## 🎯 Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA RTX 5070 Ti (16GB VRAM minimum)
- **RAM**: 16GB+ system memory
- **Storage**: 50GB+ free space for models and data
- **OS**: Windows 11 with WSL2 enabled

### Software Requirements
- **Windows 11**: Latest version with WSL2
- **Docker in WSL2**: Native Linux Docker (not Docker Desktop)
- **NVIDIA Drivers**: Latest Game Ready or Studio drivers
- **NVIDIA Container Toolkit**: For GPU passthrough
- **Ollama**: Windows native application

## 🏗️ Architecture Approach

**Why This Hybrid Setup?**
This guide implements a **Windows Native + WSL2 Docker** architecture to avoid Docker Desktop issues:

- **Ollama (Windows Native)**: Direct GPU access, no Docker networking overhead
- **Qdrant (WSL2 Docker)**: Native Linux containers with proper GPU passthrough
- **Benefits**: Reliable performance, simplified networking, avoid Docker Desktop complications

**Alternative to Docker Desktop**: We use native Docker in WSL2 instead of Docker Desktop for better stability and performance.

## 📋 Step 1: Windows Environment Setup

### Enable WSL2
```powershell
# Run as Administrator
wsl --install
wsl --set-default-version 2

# Restart Windows after this
```

### Install Ubuntu in WSL2
```powershell
# Install Ubuntu 22.04 LTS
wsl --install -d Ubuntu-22.04

# Set Ubuntu as default
wsl --setdefault Ubuntu-22.04
```

### Update Ubuntu
```bash
# In WSL2 Ubuntu terminal
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git
```

## 📋 Step 2: NVIDIA GPU Setup

### Install NVIDIA Drivers (Windows)
1. Download latest **NVIDIA GeForce Game Ready Driver**
2. Install with **Custom Installation**
3. Enable **NVIDIA Container Toolkit** option
4. Restart Windows

### Configure NVIDIA Container Toolkit (WSL2)
```bash
# In WSL2 Ubuntu terminal
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo service docker restart
```

### Verify GPU Access
```bash
# Check NVIDIA drivers
nvidia-smi

# Should show RTX 5070 Ti with 16GB VRAM
```

## 📋 Step 3: Docker Setup in WSL2

### Install Docker (WSL2)
```bash
# In WSL2 Ubuntu terminal
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Restart Docker service
sudo service docker restart

# Verify Docker works
docker --version
docker run hello-world
```

### Test GPU Passthrough
```bash
# Test NVIDIA container support
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi

# Should show GPU information without errors
```

## 📋 Step 4: Ollama Installation (Windows)

### Download and Install Ollama
1. Visit https://ollama.ai/download/windows
2. Download **Ollama Windows installer**
3. Run installer as Administrator
4. Ollama will install to `C:\Program Files\Ollama\`

### Verify Ollama Installation
```powershell
# In Windows PowerShell
ollama --version

# Should show version number
ollama ps

# Should show running models (if any)
```

## 📋 Step 5: Model Setup

### Create Custom Model Directory
```powershell
# In PowerShell, create directory structure
mkdir C:\AI\Models\Qwen3-Embedding
cd C:\AI\Models\Qwen3-Embedding
```

### Download Embedding Model
```powershell
# Download qwen3-4b-embedding model
# Note: This will be handled by Ollama automatically when creating model

# Create modelfile for custom quantization
@"
FROM qwen3-4b-embedding-q4_k_m.gguf
"@ | Out-File -FilePath "rtx5070ti-custom-quant.modelfile" -Encoding utf8
```

### Create Custom Model
```powershell
# Create the custom model with optimal quantization
ollama create qwen3-rtx5070ti:q4_k_m_custom -f rtx5070ti-custom-quant.modelfile

# Verify model was created
ollama list
```

## 📋 Step 6: Qdrant Deployment

### Create Data Volume
```bash
# In WSL2 Ubuntu terminal
docker volume create qdrant_data
```

### Deploy Qdrant Container
```bash
# Run Qdrant with GPU passthrough
docker run -d \
  --name qdrant-vector-db \
  --gpus all \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  --restart unless-stopped \
  qdrant/qdrant:latest

# Verify container is running
docker ps | grep qdrant
```

### Test Qdrant API
```bash
# Test basic connectivity
curl http://localhost:6333/collections

# Should return: {"collections":[],"timestamp":...}
```

## 📋 Step 7: Service Integration

### Test Ollama API
```powershell
# In Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:11434/api/tags"

# Should show your qwen3-rtx5070ti:q4_k_m_custom model
```

### Test Embedding Generation
```powershell
# Test embedding API
$embeddingRequest = @{
    model = "qwen3-rtx5070ti:q4_k_m_custom"
    prompt = "test embedding generation"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:11434/api/embeddings" -Method Post -Body $embeddingRequest -ContentType "application/json"

# Should return 2560-dimensional embedding
```

### Test Qdrant-Write Access
```powershell
# Create test collection
$collectionRequest = @{
    vectors = @{
        size = 2560
        distance = "Cosine"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:6333/collections/test_collection" -Method Put -Body $collectionRequest -ContentType "application/json"

# Verify collection was created
Invoke-RestMethod -Uri "http://localhost:6333/collections"
```

## 📋 Step 8: Kilocode Configuration

### Install Kilocode Extension
1. Install **Kilocode** from browser extension store
2. Open Kilocode settings
3. Configure endpoints:

```yaml
# Embedder Provider: Ollama
Ollama Base URL: http://localhost:11434
Model: qwen3-rtx5070ti:q4_k_m_custom
Model Dimension: 2560

# Vector Store Provider: Qdrant
Qdrant URL: http://localhost:6333
Qdrant API Key: (leave empty)
```

### Alternative Endpoints (if localhost fails)
```yaml
# Try these if localhost doesn't work:
Ollama Base URL: http://127.0.0.1:11434
Qdrant URL: http://127.0.0.1:6333
```

## 📋 Step 9: Initial Data Population

### Create Production Collection
```powershell
# Create main collection for repository indexing
$mainCollection = @{
    vectors = @{
        size = 2560
        distance = "Cosine"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:6333/collections/repository-index" -Method Put -Body $mainCollection -ContentType "application/json"
```

### Start Repository Indexing
1. Open your project in VSCode
2. Activate Kilocode extension
3. Start indexing process
4. Monitor progress in Kilocode dashboard

## 🔧 Verification Checklist

### Services Running
- [ ] **Ollama**: `ollama ps` shows model running
- [ ] **Qdrant**: `docker ps` shows container running
- [ ] **Kilocode**: Extension shows "Connected" status

### API Endpoints Responding
- [ ] **Ollama**: `curl http://localhost:11434/api/tags`
- [ ] **Qdrant**: `curl http://localhost:6333/collections`
- [ ] **Embedding Test**: API returns 2560-dimensional vector

### GPU Functionality
- [ ] **Ollama GPU**: Model loads in GPU VRAM
- [ ] **Qdrant GPU**: Container shows GPU passthrough
- [ ] **Performance**: Embedding generation < 50ms

### Data Flow
- [ ] **File → Embedding**: Text files processed successfully
- [ ] **Embedding → Storage**: Vectors stored in Qdrant
- [ ] **Search**: Semantic search returns relevant results

## 🚨 Troubleshooting Common Issues

### GPU Not Available in Docker
```bash
# Reconfigure NVIDIA toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo service docker restart

# Test again
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu20.04 nvidia-smi
```

### Ollama Model Not Loading
```powershell
# Check model files
ollama list
ollama show qwen3-rtx5070ti:q4_k_m_custom

# Re-create model if needed
ollama rm qwen3-rtx5070ti:q4_k_m_custom
ollama create qwen3-rtx5070ti:q4_k_m_custom -f rtx5070ti-custom-quant.modelfile
```

### Qdrant Connection Refused
```bash
# Check container status
docker ps -a | grep qdrant

# Check logs
docker logs qdrant-vector-db --tail 20

# Restart container
docker restart qdrant-vector-db
```

### Kilocode "Fetch Failed"
1. Try alternative endpoints (127.0.0.1 instead of localhost)
2. Check Windows Firewall settings
3. Verify services are running in correct order
4. Restart Kilocode extension

## 🎯 Success Criteria

**System is fully operational when:**
- All services running without errors
- API endpoints responding quickly
- GPU utilization confirmed
- Vector storage and retrieval working
- Kilocode shows "Connected" status
- Repository indexing completes successfully

**Expected Performance:**
- Embedding generation: 29ms per vector
- Indexing rate: 3,000+ vectors/minute
- Search latency: <10ms for queries
- GPU VRAM usage: 4-6GB steady state

---

**Next**: See [03_MAINTENANCE.md](03_MAINTENANCE.md) for ongoing operational procedures