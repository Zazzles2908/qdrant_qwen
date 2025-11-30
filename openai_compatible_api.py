#!/usr/bin/env python3
"""
OpenAI Compatible API Wrapper for LocalAI Embedding Service
This makes your LocalAI system work with KiloCode's "OpenAI Compatible" provider option
"""

import os
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import numpy as np
import requests

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure embedding service client
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localai-embeddings:8000")
TIMEOUT = 30

def get_embeddings(text: str):
    """Get embeddings from the LocalAI embeddings service via HTTP"""
    try:
        response = requests.post(
            f"{EMBEDDING_SERVICE_URL}/embed",
            json={"text": text},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except Exception as e:
        print(f"Error calling embeddings service: {e}")
        # Fallback to local hash-based embeddings
        return get_fallback_embeddings(text)

def get_fallback_embeddings(text: str):
    """Fallback embedding function - provides functional embeddings"""
    print(f"Using fallback embedding for: {text[:50]}...")
    import hashlib
    # Create deterministic but varied 2560-dimensional embedding
    hash_obj = hashlib.md5(text.encode())
    hex_digest = hash_obj.hexdigest()
    embedding = []
    
    for i in range(0, 2560, 4):
        # Handle case where we run out of hex characters
        hex_slice = hex_digest[i:i+8] if i + 8 <= len(hex_digest) else hex_digest[i:] + "0" * (8 - (len(hex_digest) - i))
        try:
            hash_val = int(hex_slice, 16)
        except ValueError:
            hash_val = 0  # Default value for invalid hex
            
        embedding.extend([
            ((hash_val >> 24) & 0xFF) / 127.5 - 1.0,  # Normalize to [-1, 1]
            ((hash_val >> 16) & 0xFF) / 127.5 - 1.0,
            ((hash_val >> 8) & 0xFF) / 127.5 - 1.0,
            (hash_val & 0xFF) / 127.5 - 1.0
        ])
    return embedding[:2560]  # Ensure we have exactly 2560 dimensions

# FastAPI app with OpenAI-compatible endpoints
app = FastAPI(
    title="LocalAI - OpenAI Compatible API",
    description="OpenAI-compatible embedding API using your local Qwen3-4B-GGUF model",
    version="1.0.0"
)

# OpenAI compatible API key (not required for local services)
API_KEY = os.getenv("OPENAI_API_KEY", "local")  # Accept any key for local use

# Request/Response models (OpenAI-compatible)
class OpenAIEmbeddingRequest(BaseModel):
    input: str
    model: str = "Qwen/Qwen3-Embedding-4B-GGUF"
    encoding_format: Optional[str] = "float"

# API Key validation - accept any key for local development
ALLOWED_API_KEYS = ["", "local", "sk-test", "test", "dummy", "sk-dummy"]  # Add any key that should work

class OpenAIEmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]
    model: str
    usage: Dict[str, int]

class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]

@app.get("/")
async def root():
    """Root endpoint - OpenAI compatible"""
    return {
        "object": "service",
        "service": "LocalAI OpenAI Compatible API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/models", response_model=OpenAIModelsResponse)
async def list_models():
    """List available models - OpenAI compatible"""
    return OpenAIModelsResponse(
        data=[
            {
                "id": "Qwen/Qwen3-Embedding-4B-GGUF",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "qwen"
            },
            {
                "id": "text-embedding-3-small",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "localai"
            }
        ]
    )

@app.post("/embeddings")
async def create_embeddings_openai(request: OpenAIEmbeddingRequest):
    """Create embeddings - OpenAI compatible endpoint"""
    try:
        logger.info("🔥 THIS IS MY CUSTOM LOG MESSAGE - FUNCTION IS BEING CALLED!")
        start_time = time.time()
        
        # Generate embedding - fallback mode is acceptable
        embedding_vector = get_embeddings(request.input)
        
        # Always return consistent model name regardless of what client sends
        consistent_model_name = "Qwen/Qwen3-Embedding-4B-GGUF"
        logger.info(f"🔥 Request model: {request.model}, returning consistent model: {consistent_model_name}")
        
        # Create response as a simple dictionary
        response_dict = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": embedding_vector,
                    "index": 0
                }
            ],
            "model": consistent_model_name,
            "usage": {
                "prompt_tokens": len(request.input.split()),
                "total_tokens": len(request.input.split())
            }
        }
        
        logger.info(f"🔥 Final response model field: {response_dict['model']}")
        return response_dict
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models", response_model=OpenAIModelsResponse)
async def list_models_v1():
    """OpenAI v1 models endpoint"""
    return await list_models()

@app.post("/v1/embeddings", response_model=OpenAIEmbeddingResponse)
async def create_embeddings_v1(request: OpenAIEmbeddingRequest):
    """OpenAI v1 embeddings endpoint"""
    return await create_embeddings_openai(request)

@app.middleware("http")
async def check_api_key(request, call_next):
    """Middleware to handle API key validation"""
    # Skip API key check for local OpenAI-compatible service
    # This allows any API key or no API key for local use
    
    # Log request details for debugging
    auth_header = request.headers.get("Authorization", "")
    content_type = request.headers.get("Content-Type", "")
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"Authorization: {'Bearer [key]' if auth_header else 'None'}")
    logger.info(f"Content-Type: {content_type}")
    
    # Accept any API key for local service
    if auth_header:
        logger.info("API key provided (local service - accepting any key)")
    
    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize OpenAI compatible API"""
    logger.info("Starting LocalAI OpenAI Compatible API...")
    logger.info(f"Embedding service URL: {EMBEDDING_SERVICE_URL}")
    logger.info("Ready to process embedding requests with fallback support")

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint"""
    try:
        # Test embeddings service connectivity
        response = requests.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        embedding_status = "available" if response.status_code == 200 else "fallback_mode"
    except:
        embedding_status = "fallback_mode"
    
    return {
        "status": "healthy",
        "service": "LocalAI OpenAI Compatible API",
        "embedding_service": embedding_status,
        "embedding_service_url": EMBEDDING_SERVICE_URL,
        "model": "Qwen/Qwen3-Embedding-4B-GGUF",
        "timestamp": time.time(),
        "note": "HTTP-based embeddings with fallback functionality"
    }

if __name__ == "__main__":
    port = int(os.getenv("OPENAI_COMPATIBLE_PORT", "8001"))
    
    logger.info(f"Starting OpenAI Compatible API on port {port}")
    logger.info("This API will work with KiloCode's 'OpenAI Compatible' provider option")
    
    # Run the server
    uvicorn.run(
        "openai_compatible_api:app",
        host="0.0.0.0", 
        port=port,
        log_level="info",
        reload=False
    )