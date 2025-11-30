#!/usr/bin/env python3
"""
LocalAI Embedding MCP Server for AI-to-AI Communication System
Provides embedding generation services via Model Context Protocol
"""

import sys
import json
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from datetime import datetime

class LocalAIMCPServer:
    def __init__(self):
        self.base_url = 'http://localhost:8000'
    
    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if method == 'embedding_health':
                return await self.health_check()
            elif method == 'embedding_generate':
                return await self.generate_embeddings(params.get('texts', []))
            elif method == 'embedding_generate_single':
                return await self.generate_single_embedding(params.get('text', ''))
            elif method == 'embedding_models':
                return await self.get_models()
            else:
                return {'error': f'Unknown method: {method}'}
        except Exception as e:
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/health') as response:
                    data = await response.json()
                    return {
                        'status': 'ok',
                        'service': 'localai_embedding_service',
                        'endpoint': self.base_url,
                        'health_data': data,
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Health check failed: {str(e)}'}
    
    async def generate_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        try:
            payload = {'texts': texts}
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.base_url}/embeddings', json=payload) as response:
                    data = await response.json()
                    embeddings = data.get('embeddings', [])
                    return {
                        'embeddings': embeddings,
                        'count': len(embeddings),
                        'dimension': len(embeddings[0].get('embedding', [])) if embeddings else 0,
                        'model': data.get('model', 'unknown'),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Generate embeddings failed: {str(e)}'}
    
    async def generate_single_embedding(self, text: str) -> Dict[str, Any]:
        try:
            payload = {'texts': [text]}
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.base_url}/embeddings', json=payload) as response:
                    data = await response.json()
                    embeddings = data.get('embeddings', [])
                    return {
                        'embedding': embeddings[0].get('embedding', []) if embeddings else [],
                        'text': text,
                        'dimension': len(embeddings[0].get('embedding', [])) if embeddings else 0,
                        'model': data.get('model', 'unknown'),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Generate single embedding failed: {str(e)}'}
    
    async def get_models(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/models') as response:
                    data = await response.json()
                    return {
                        'models': data.get('models', []),
                        'current_model': data.get('current_model', 'unknown'),
                        'status': 'ok',
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Get models failed: {str(e)}'}

async def main():
    server = LocalAIMCPServer()
    
    print("🚀 LocalAI Embedding MCP Server starting...", file=sys.stderr)
    
    # Simple MCP protocol handler
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            request = json.loads(line.strip())
            method = request.get('method', '')
            params = request.get('params', {})
            
            result = await server.handle_request(method, params)
            response = {
                'jsonrpc': '2.0',
                'id': request.get('id'),
                'result': result
            }
            print(json.dumps(response))
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                'jsonrpc': '2.0',
                'id': None,
                'error': {'message': str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())