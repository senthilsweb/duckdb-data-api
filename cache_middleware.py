"""
cache_middleware.py

Implements caching for FastAPI requests to enhance performance and response times.
The middleware utilizes Upstash Redis due to limitations encountered with vercel-kv
in the Python environment. Vercel-kv offers native support for JavaScript but not for Python.

Caching is particularly important for this application as it uses MotherDuck, a serverless
version of DuckDB. While DuckDB is performant, deploying it at the edge with Vercel's hobby
plan introduces constraints such as memory and RAM limitations, and a function timeout of 10 seconds.
To mitigate these limitations and improve response times, a Redis cache was implemented.
Upstash Redis was chosen for its ease of integration with Vercel, offering 500 MB of free cache
storage under the hobby plan.

Cache keys are consistently lowercased and prefixed with 'duckdb-data-api:' to ensure
uniformity and to avoid case-sensitive cache misses. Only GET requests and a specific POST
request for executing SQL are cached.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from upstash_redis.asyncio import Redis

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Upstash Redis using environment variables
redis = Redis.from_env()

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache GET and specific POST request responses using Upstash Redis.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process an incoming request by checking if it's cached. If not, call the next
        request handler and cache the response if applicable.
        
        Args:
            request: The incoming HTTP request.
            call_next: The next request handler to call if the cache misses.

        Returns:
            The cached response or the response from the next request handler.
        """
        
        # Apply caching only for GET requests or the specific POST method
        if request.method == "GET" or (request.method == "POST" and request.url.path == "/execute/sql"):
            # Normalize and construct the cache key
            cache_key = f"duckdb-data-api:{request.method.lower()}-{request.url.path.lower()}?{request.query_params}".lower()
            
            # Attempt to retrieve the cached response
            cached_response = await redis.get(cache_key)
            if cached_response:
                print(f"Cache hit for key: {cache_key}")
                return Response(content=cached_response, status_code=200, media_type='application/json')
            print(f"Cache miss for key: {cache_key}")
        else:
            # For non-cachable methods, bypass the cache and proceed with the request
            cache_key = None

        # Process the request
        response = await call_next(request)

        # Cache the response if the status code is 200
        if response.status_code == 200 and cache_key:
            body = b''.join([chunk async for chunk in response.body_iterator])
            cache_content = body.decode()
            headers = {"Content-Length": str(len(cache_content))}
            await redis.set(cache_key, cache_content)
            print(f"Cached response for key: {cache_key}")
            return Response(content=cache_content, status_code=200, media_type='application/json', headers=headers)

        return response
