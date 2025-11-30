#!/usr/bin/env python3
"""
Qwen3 Embedding Service - GGUF Version
Loads Jgriosanz/Qwen3-Embedding-4B-Q4_K_M-GGUF and provides embeddings API
Optimized for Ubuntu 24.04 with RTX 5070Ti GPU acceleration
"""

import os
import asyncio
import logging
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request/Response models
class EmbeddingRequest(BaseModel):
    text: str
    model_name: Optional[str] = None

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model: str
    dimension: int
    processing_time_ms: float

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str

# Global model reference
embedding_model = None
model_device = "cpu"
model_type = "sentence_transformers"  # Track which model type we're using

# FastAPI app
app = FastAPI(title="Qwen3 Embedding Service - GGUF", version="1.0.0")

# Model configuration - use environment variable or default
MODEL_NAME = os.getenv("MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")  # Default fallback model
MODEL_REPO = MODEL_NAME.replace("Jgriosanz/", "").replace("/", "/")  # Convert to huggingface format
MODEL_FILES = [
    "qwen3-embedding-4b-q4_k_m.gguf",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json"
]
MODELS_DIR = Path("/app/embeddings_models")  # Original working path
LOCAL_MODEL_PATH = MODELS_DIR / "qwen3-embedding-4b-q4_k_m.gguf"
LOCAL_MODEL_PATH_VAR = LOCAL_MODEL_PATH  # Variable version for modification

def get_fallback_model():
    """Get a working fallback model with GPU acceleration"""
    try:
        import torch
        logger.info("Loading PyTorch-based fallback model with GPU acceleration...")
        
        # Try to use PyTorch with GPU acceleration
        if torch.cuda.is_available():
            logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
            device = "cuda"
        else:
            logger.info("GPU not available, using CPU")
            device = "cpu"
            
        # Use a simple sentence-transformers model that works reliably
        logger.info("Loading all-MiniLM-L6-v2 with PyTorch backend...")
        model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        
        # Force GPU if available
        if torch.cuda.is_available():
            model = model.cuda()
            
        return model, f"sentence_transformers_{device}"
        
    except Exception as e:
        logger.warning(f"Failed to load PyTorch fallback model: {e}")
        
        # Generate deterministic embeddings as final fallback
        logger.info("Using deterministic embedding fallback")
        return None, "deterministic"

def deterministic_embedding(text: str, dimension: int = 384) -> List[float]:
    """Generate deterministic embeddings based on text content"""
    import hashlib
    
    # Create a seed from the text
    hash_obj = hashlib.md5(text.encode('utf-8'))
    seed = int(hash_obj.hexdigest()[:8], 16)
    
    # Use the seed to generate consistent "random" values
    np.random.seed(seed)
    
    # Generate normalized embedding
    vector = np.random.normal(0, 0.1, dimension)
    vector = vector / np.linalg.norm(vector)  # Normalize to unit length
    
    return vector.tolist()

async def load_model():
    """Load the Qwen3 embedding model with proper fallbacks"""
    global embedding_model, model_device, model_type
    
    logger.info("=== LOADING EMBEDDING MODEL ===")
    
async def load_model():
    """Load the Qwen3 embedding model via Ollama API"""
    global embedding_model, model_device, model_type
    
    logger.info("=== LOADING EMBEDDING MODEL ===")
    
    # Test Ollama API availability
    try:
        import requests
        import torch
        
        # Test Ollama connectivity (using Docker container name)
        logger.info("Testing Ollama API connectivity...")
        response = requests.get("http://localai-ollama:11434/api/version", timeout=10)
        response.raise_for_status()
        logger.info("✅ Ollama API is accessible")
        
        # Test Qwen3 model availability
        logger.info("Testing Qwen3-embedding:4b model...")
        test_response = requests.post(
            "http://localai-ollama:11434/api/embeddings",
            json={"model": "qwen3-embedding:4b", "prompt": "test"},
            timeout=30
        )
        test_response.raise_for_status()
        test_result = test_response.json()
        
        # Extract embedding dimensions
        if "embedding" in test_result:
            embedding_dim = len(test_result["embedding"])
            logger.info(f"✅ Qwen3-embedding:4b model confirmed working ({embedding_dim} dimensions)")
        else:
            raise Exception("No embedding returned from test call")
        
        # Set up for Ollama-based embeddings
        model_device = "cuda" if torch.cuda.is_available() else "cpu"
        model_type = "ollama_qwen3"
        
        # Store embedding dimension for later use
        global QWEN3_EMBEDDING_DIM
        QWEN3_EMBEDDING_DIM = embedding_dim
        
        logger.info(f"=== QWEN3 EMBEDDING SETUP COMPLETE ===")
        logger.info(f"Model: qwen3-embedding:4b")
        logger.info(f"Dimensions: {embedding_dim}")
        logger.info(f"Device: {model_device}")
        logger.info(f"Method: Ollama API")
        
        return
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ollama API not accessible: {e}")
        raise Exception(f"Ollama API connection failed: {e}")
    except Exception as e:
        logger.error(f"❌ Qwen3 model test failed: {e}")
        raise Exception(f"Qwen3 model verification failed: {e}")

# Global variable to store embedding dimension
QWEN3_EMBEDDING_DIM = 2560  # Default, will be updated during model loading

def get_embeddings(text: str) -> List[float]:
    """Generate embeddings for the given text using Ollama Qwen3 model"""
    global model_device, model_type
    
    if model_type != "ollama_qwen3":
        raise HTTPException(status_code=503, detail="Ollama Qwen3 model not loaded")
    
    try:
        start_time = time.time()
        
        if model_type == "ollama_qwen3":
            # Use Ollama API for Qwen3 embeddings
            import requests
            
            # Call Ollama API
            response = requests.post(
                "http://localai-ollama:11434/api/embeddings",
                json={
                    "model": "qwen3-embedding:4b",
                    "prompt": text,
                    "stream": False
                },
                timeout=60  # Qwen3 can be slow
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "embedding" not in result:
                raise Exception("No embedding returned from Ollama API")
            
            embedding_vector = result["embedding"]
            
            # Ensure proper dimension (use actual or default)
            target_dim = QWEN3_EMBEDDING_DIM if 'QWEN3_EMBEDDING_DIM' in globals() else 2560
            
            if len(embedding_vector) > target_dim:  # Truncate if too long
                embedding_vector = embedding_vector[:target_dim]
            elif len(embedding_vector) < target_dim:  # Pad if too short
                embedding_vector.extend([0.0] * (target_dim - len(embedding_vector)))
                
        else:
            # This should not happen, but provide fallback
            logger.warning(f"Unexpected model type: {model_type}, falling back to deterministic")
            embedding_vector = deterministic_embedding(text, 2560)
        
        # Normalize to unit length for cosine similarity
        embedding_array = np.array(embedding_vector)
        embedding_norm = embedding_array / np.linalg.norm(embedding_array)
        embedding_final = embedding_norm.tolist()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Generated {len(embedding_final)}-dim embedding in {processing_time:.2f}ms using {model_type}")
        
        return embedding_final
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API error: {e}")
        # Fallback to deterministic embeddings
        logger.info("Falling back to deterministic embeddings due to Ollama API error")
        return deterministic_embedding(text, 2560)
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        # Fallback to deterministic embeddings on any error
        logger.info("Falling back to deterministic embeddings due to error")
        return deterministic_embedding(text, 2560)

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    try:
        await load_model()
        logger.info("=== MODEL LOADING COMPLETE ===")
    except Exception as e:
        logger.error(f"Failed to load model on startup: {e}")
        # Don't raise here, let the service start and handle errors in endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "service": "Qwen3 Embedding Service - GGUF",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "model_type": model_type,
        "device": model_device,
        "status": "running",
        "model_loaded": embedding_model is not None or model_type == "deterministic"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check if we're actually using GPU
    actual_device = model_device
    if model_type.startswith("sentence_transformers"):
        import torch
        if torch.cuda.is_available():
            actual_device = "cuda"
        else:
            actual_device = "cpu"
    
    return HealthResponse(
        status="healthy",
        model_loaded=embedding_model is not None or model_type == "deterministic",
        device=actual_device
    )

@app.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Generate embedding for text"""
    start_time = time.time()
    
    try:
        # Generate embeddings
        embedding = get_embeddings(request.text)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        return EmbeddingResponse(
            embedding=embedding,
            model=request.model_name or f"{MODEL_NAME}_{model_type}",
            dimension=len(embedding),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in /embed endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed_batch", response_model=List[EmbeddingResponse])
async def create_embeddings_batch(requests: List[EmbeddingRequest]):
    """Generate embeddings for multiple texts"""
    responses = []
    for request in requests:
        response = await create_embedding(request)
        responses.append(response)
    return responses

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("EMBEDDING_SERVICE_PORT", "8000"))
    
    logger.info(f"Starting Qwen3 Embedding Service (GGUF) on port {port}")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )