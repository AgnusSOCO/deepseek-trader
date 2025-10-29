"""
OpenRouter Client for DeepSeek Chat V3.1

Provides integration with OpenRouter API to access DeepSeek models:
- deepseek/deepseek-chat (for analysis and decision-making)
- deepseek/deepseek-reasoner (for complex reasoning tasks)
"""

import os
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """
    Client for OpenRouter API to access DeepSeek models
    
    Supports:
    - deepseek/deepseek-chat: Fast, efficient chat model
    - deepseek/deepseek-reasoner: Advanced reasoning model
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: OpenRouter API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided and OPENROUTER_API_KEY not set")
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.failed_requests = 0
        
        logger.info(f"OpenRouterClient initialized with base_url={base_url}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (deepseek/deepseek-chat or deepseek/deepseek-reasoner)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2 to 2)
            presence_penalty: Presence penalty (-2 to 2)
            **kwargs: Additional parameters
            
        Returns:
            Response dict from OpenRouter API
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/AgnusSOCO/deepseek-trader",
            "X-Title": "DeepSeek Trader"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            **kwargs
        }
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        self.total_requests += 1
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            if 'usage' in result:
                                usage = result['usage']
                                tokens = usage.get('total_tokens', 0)
                                self.total_tokens += tokens
                                
                                cost = (tokens / 1_000_000) * 0.21
                                self.total_cost += cost
                                
                                logger.info(
                                    f"OpenRouter request successful: "
                                    f"model={model}, tokens={tokens}, "
                                    f"cost=${cost:.6f}, total_cost=${self.total_cost:.4f}"
                                )
                            
                            return result
                        
                        elif response.status == 429:
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"Rate limited by OpenRouter, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        
                        elif response.status >= 500:
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"OpenRouter server error {response.status}, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"OpenRouter request failed with status {response.status}: {error_text}"
                            )
                            self.failed_requests += 1
                            raise Exception(f"OpenRouter API error {response.status}: {error_text}")
            
            except asyncio.TimeoutError:
                logger.warning(
                    f"OpenRouter request timeout (attempt {attempt + 1}/{self.max_retries})"
                )
                if attempt == self.max_retries - 1:
                    self.failed_requests += 1
                    raise
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                logger.error(f"OpenRouter request error: {e}")
                if attempt == self.max_retries - 1:
                    self.failed_requests += 1
                    raise
                await asyncio.sleep(2 ** attempt)
        
        self.failed_requests += 1
        raise Exception(f"OpenRouter request failed after {self.max_retries} attempts")
    
    async def verify_connection(self) -> bool:
        """
        Verify connection to OpenRouter API
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = await self.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="deepseek/deepseek-chat",
                max_tokens=10
            )
            
            if 'choices' in response and len(response['choices']) > 0:
                logger.info("✓ OpenRouter connection verified successfully")
                return True
            else:
                logger.error("✗ OpenRouter connection failed: Invalid response format")
                return False
        
        except Exception as e:
            logger.error(f"✗ OpenRouter connection failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics
        
        Returns:
            Dict with usage statistics
        """
        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.total_requests - self.failed_requests) / self.total_requests * 100 if self.total_requests > 0 else 0,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost,
            'avg_tokens_per_request': self.total_tokens / self.total_requests if self.total_requests > 0 else 0
        }
    
    def reset_statistics(self) -> None:
        """Reset usage statistics"""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.failed_requests = 0
        logger.info("OpenRouter statistics reset")


async def test_openrouter():
    """Test OpenRouter connection"""
    client = OpenRouterClient()
    
    print("Testing OpenRouter connection...")
    success = await client.verify_connection()
    
    if success:
        print("✓ Connection successful!")
        
        print("\nTesting DeepSeek Chat...")
        response = await client.chat_completion(
            messages=[
                {"role": "user", "content": "What is 2+2? Answer in one word."}
            ],
            model="deepseek/deepseek-chat",
            max_tokens=10
        )
        print(f"Response: {response['choices'][0]['message']['content']}")
        
        stats = client.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Total cost: ${stats['total_cost']:.6f}")
    else:
        print("✗ Connection failed!")
    
    return success


if __name__ == '__main__':
    asyncio.run(test_openrouter())
