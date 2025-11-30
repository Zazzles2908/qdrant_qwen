#!/usr/bin/env python3
"""
Qdrant MCP Server for AI-to-AI Communication System
Provides vector database operations via Model Context Protocol
"""

import sys
import json
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from datetime import datetime

class QdrantMCPServer:
    def __init__(self):
        self.base_url = 'http://localhost:6333'
        self.collection_name = 'ai_communication_vectors'
    
    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if method == 'qdrant_health':
                return await self.health_check()
            elif method == 'qdrant_collections':
                return await self.list_collections()
            elif method == 'qdrant_create_collection':
                return await self.create_collection(params.get('collection_name', self.collection_name))
            elif method == 'qdrant_insert_vectors':
                return await self.insert_vectors(params.get('vectors', []), params.get('metadata', []))
            elif method == 'qdrant_search':
                return await self.search_vectors(params.get('query_vector', []), params.get('limit', 5))
            elif method == 'qdrant_collections_info':
                return await self.get_collections_info()
            else:
                return {'error': f'Unknown method: {method}'}
        except Exception as e:
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/collections') as response:
                    data = await response.json()
                    return {
                        'status': 'ok',
                        'service': 'qdrant_vector_db',
                        'endpoint': self.base_url,
                        'collections_count': len(data.get('result', {}).get('collections', [])),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Health check failed: {str(e)}'}
    
    async def list_collections(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/collections') as response:
                    data = await response.json()
                    return {
                        'collections': data.get('result', {}).get('collections', []),
                        'count': len(data.get('result', {}).get('collections', [])),
                        'status': 'ok'
                    }
        except Exception as e:
            return {'error': f'List collections failed: {str(e)}'}
    
    async def create_collection(self, collection_name: str) -> Dict[str, Any]:
        try:
            payload = {
                'vectors': {
                    'size': 384,
                    'distance': 'Cosine'
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.put(f'{self.base_url}/collections/{collection_name}', json=payload) as response:
                    data = await response.json()
                    return {
                        'collection': collection_name,
                        'status': data.get('status', 'unknown'),
                        'result': data.get('result', {}),
                        'created_at': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Create collection failed: {str(e)}'}
    
    async def insert_vectors(self, vectors: List[List[float]], metadata: List[Dict] = None) -> Dict[str, Any]:
        try:
            if metadata is None:
                metadata = [{}] * len(vectors)
            
            points = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                points.append({
                    'id': i + 1,
                    'vector': vector,
                    'payload': meta
                })
            
            payload = {'points': points}
            async with aiohttp.ClientSession() as session:
                async with session.put(f'{self.base_url}/collections/{self.collection_name}/points', json=payload) as response:
                    data = await response.json()
                    return {
                        'inserted_count': len(vectors),
                        'collection': self.collection_name,
                        'status': data.get('status', 'unknown'),
                        'result': data.get('result', {}),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Insert vectors failed: {str(e)}'}
    
    async def search_vectors(self, query_vector: List[float], limit: int = 5) -> Dict[str, Any]:
        try:
            payload = {
                'vector': query_vector,
                'limit': limit,
                'with_payload': True
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{self.base_url}/collections/{self.collection_name}/points/search', json=payload) as response:
                    data = await response.json()
                    results = data.get('result', [])
                    return {
                        'search_results': results,
                        'found_count': len(results),
                        'query_vector_dimension': len(query_vector),
                        'limit': limit,
                        'collection': self.collection_name,
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Search vectors failed: {str(e)}'}
    
    async def get_collections_info(self) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/collections/{self.collection_name}') as response:
                    data = await response.json()
                    return {
                        'collection_info': data.get('result', {}),
                        'status': 'ok',
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {'error': f'Get collections info failed: {str(e)}'}

async def main():
    server = QdrantMCPServer()
    
    print("🚀 Qdrant MCP Server starting...", file=sys.stderr)
    
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