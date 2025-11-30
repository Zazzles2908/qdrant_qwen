#!/usr/bin/env python3
# Enhanced GPU Health Check for RTX 5070Ti - Supports Embeddings and LLM Services
import torch
import sys
import os
import argparse

def check_basic_gpu():
    """Basic GPU check for embedding service"""
    if not torch.cuda.is_available():
        print('GPU not available')
        return False
    
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    if gpu_mem < 3.5:  # Minimum for embeddings
        print('Insufficient GPU memory: {:.1f}GB'.format(gpu_mem))
        return False
    
    print('GPU OK: {:.1f}GB detected'.format(gpu_mem))
    return True

def check_llm_service():
    """Enhanced check for LLM service"""
    try:
        import requests
        import time
        
        # Check if LLM service is running
        max_retries = 3
        for i in range(max_retries):
            try:
                response = requests.get('http://localhost:8001/health', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"LLM Service OK: {data.get('status', 'unknown')}")
                    print(f"Model: {data.get('model_name', 'not loaded')}")
                    print(f"GPU Memory: {data.get('gpu_usage_percent', 0):.1f}%")
                    return True
            except requests.exceptions.RequestException:
                if i < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    print('LLM service not responding')
                    return False
                    
    except ImportError:
        print('Requests library not available for LLM check')
        
    # Fallback to basic GPU check
    return check_basic_gpu()

def main():
    parser = argparse.ArgumentParser(description='Enhanced GPU Health Check')
    parser.add_argument('--service', choices=['embedding', 'llm'], default='embedding',
                       help='Service type to check')
    args = parser.parse_args()
    
    print(f'Running health check for {args.service} service...')
    
    if args.service == 'embedding':
        if check_basic_gpu():
            print('✅ Embedding service health check passed')
            sys.exit(0)
        else:
            print('❌ Embedding service health check failed')
            sys.exit(1)
            
    elif args.service == 'llm':
        if check_llm_service():
            print('✅ LLM service health check passed')
            sys.exit(0)
        else:
            print('❌ LLM service health check failed')
            sys.exit(1)
    else:
        print(f'Unknown service type: {args.service}')
        sys.exit(1)

if __name__ == '__main__':
    main()