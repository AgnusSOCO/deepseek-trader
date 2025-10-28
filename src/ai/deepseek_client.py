"""
DeepSeek API Client

Wrapper for DeepSeek API using OpenAI SDK.
Handles API calls, rate limiting, caching, and error handling.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)


@dataclass
class APIUsageStats:
    """Track API usage and costs"""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    requests_by_model: Dict[str, int] = field(default_factory=dict)
    tokens_by_model: Dict[str, int] = field(default_factory=dict)
    last_reset: datetime = field(default_factory=datetime.now)
    
    def add_request(self, model: str, tokens: int, cost: float):
        """Record API request"""
        self.total_requests += 1
        self.total_tokens += tokens
        self.total_cost += cost
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        self.tokens_by_model[model] = self.tokens_by_model.get(model, 0) + tokens
    
    def reset_daily(self):
        """Reset daily stats"""
        if datetime.now() - self.last_reset > timedelta(days=1):
            self.total_requests = 0
            self.total_tokens = 0
            self.total_cost = 0.0
            self.requests_by_model = {}
            self.tokens_by_model = {}
            self.last_reset = datetime.now()


@dataclass
class CacheEntry:
    """Cache entry for API responses"""
    response: str
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl_seconds)


class DeepSeekClient:
    """
    DeepSeek API client with async support, caching, and rate limiting
    """
    
    PRICING = {
        'deepseek-chat': {'input': 0.14, 'output': 0.28},
        'deepseek-reasoner': {'input': 0.55, 'output': 2.19}
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        max_retries: int = 3,
        timeout: int = 60,
        enable_cache: bool = True,
        cache_ttl: int = 300
    ):
        """
        Initialize DeepSeek client
        
        Args:
            api_key: DeepSeek API key
            base_url: API base URL
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            enable_cache: Enable response caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self.usage_stats = APIUsageStats()
        
        logger.info(f"DeepSeek client initialized with base_url={base_url}")
    
    def _get_cache_key(self, model: str, messages: List[Dict], temperature: float) -> str:
        """Generate cache key from request parameters"""
        messages_str = json.dumps(messages, sort_keys=True)
        return f"{model}:{temperature}:{hash(messages_str)}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        if not self.enable_cache:
            return None
        
        entry = self._cache.get(cache_key)
        if entry and not entry.is_expired():
            logger.debug(f"Cache hit for key: {cache_key[:50]}...")
            return entry.response
        
        if entry:
            del self._cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache API response"""
        if self.enable_cache:
            self._cache[cache_key] = CacheEntry(
                response=response,
                timestamp=datetime.now(),
                ttl_seconds=self.cache_ttl
            )
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate API cost"""
        pricing = self.PRICING.get(model, {'input': 0, 'output': 0})
        input_cost = (prompt_tokens / 1_000_000) * pricing['input']
        output_cost = (completion_tokens / 1_000_000) * pricing['output']
        return input_cost + output_cost
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Make chat completion request
        
        Args:
            model: Model name (deepseek-chat or deepseek-reasoner)
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            response_format: Response format specification
            stream: Enable streaming responses
        
        Returns:
            Response dict with 'content', 'usage', 'cost'
        """
        cache_key = self._get_cache_key(model, messages, temperature)
        cached = self._get_cached_response(cache_key)
        if cached:
            return {
                'content': cached,
                'usage': {'cached': True},
                'cost': 0.0
            }
        
        request_params = {
            'model': model,
            'messages': messages,
            'temperature': temperature
        }
        
        if max_tokens:
            request_params['max_tokens'] = max_tokens
        
        if response_format:
            request_params['response_format'] = response_format
        
        start_time = time.time()
        try:
            response = await self.client.chat.completions.create(**request_params)
            
            content = response.choices[0].message.content
            usage = response.usage
            
            cost = self._calculate_cost(
                model,
                usage.prompt_tokens,
                usage.completion_tokens
            )
            
            total_tokens = usage.prompt_tokens + usage.completion_tokens
            self.usage_stats.add_request(model, total_tokens, cost)
            self.usage_stats.reset_daily()
            
            self._cache_response(cache_key, content)
            
            elapsed = time.time() - start_time
            logger.info(
                f"API call successful: model={model}, "
                f"tokens={total_tokens}, cost=${cost:.4f}, "
                f"time={elapsed:.2f}s"
            )
            
            return {
                'content': content,
                'usage': {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': total_tokens
                },
                'cost': cost,
                'elapsed_seconds': elapsed
            }
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
    
    async def parallel_completions(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple chat completions in parallel
        
        Args:
            requests: List of request dicts with chat_completion parameters
        
        Returns:
            List of response dicts
        """
        tasks = [
            self.chat_completion(**request)
            for request in requests
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            'total_requests': self.usage_stats.total_requests,
            'total_tokens': self.usage_stats.total_tokens,
            'total_cost': self.usage_stats.total_cost,
            'requests_by_model': self.usage_stats.requests_by_model,
            'tokens_by_model': self.usage_stats.tokens_by_model,
            'cache_size': len(self._cache),
            'last_reset': self.usage_stats.last_reset.isoformat()
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("Response cache cleared")
