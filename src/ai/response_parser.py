"""
Response Parser

Parse and validate JSON responses from AI agents.
Handles malformed responses with retry logic.
"""

import json
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing operation"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class ResponseParser:
    """
    Parse and validate AI agent responses
    """
    
    @staticmethod
    def extract_json(response: str) -> Optional[str]:
        """
        Extract JSON from response text
        
        Handles cases where JSON is embedded in markdown code blocks
        or surrounded by other text.
        """
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass
        
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                potential_json = response[start:end].strip()
                try:
                    json.loads(potential_json)
                    return potential_json
                except json.JSONDecodeError:
                    pass
        
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            potential_json = response[start:end]
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def parse_json(response: str) -> ParseResult:
        """
        Parse JSON response
        
        Args:
            response: Raw response string from AI
        
        Returns:
            ParseResult with success status and parsed data or error
        """
        json_str = ResponseParser.extract_json(response)
        
        if json_str is None:
            return ParseResult(
                success=False,
                error="No valid JSON found in response",
                raw_response=response
            )
        
        try:
            data = json.loads(json_str)
            return ParseResult(
                success=True,
                data=data,
                raw_response=response
            )
        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"JSON decode error: {str(e)}",
                raw_response=response
            )
    
    @staticmethod
    def validate_schema(data: Dict[str, Any], required_fields: list) -> ParseResult:
        """
        Validate that required fields are present
        
        Args:
            data: Parsed JSON data
            required_fields: List of required field names
        
        Returns:
            ParseResult with validation status
        """
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return ParseResult(
                success=False,
                error=f"Missing required fields: {missing_fields}",
                data=data
            )
        
        return ParseResult(
            success=True,
            data=data
        )
    
    @staticmethod
    def parse_technical_analysis(response: str) -> ParseResult:
        """Parse Technical Analyst response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'trend', 'trend_strength', 'support_levels',
            'resistance_levels', 'patterns', 'key_observations', 'confidence'
        ]
        
        return ResponseParser.validate_schema(result.data, required_fields)
    
    @staticmethod
    def parse_sentiment_analysis(response: str) -> ParseResult:
        """Parse Sentiment Analyst response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'sentiment', 'sentiment_score', 'market_mood',
            'key_factors', 'warnings', 'confidence'
        ]
        
        return ResponseParser.validate_schema(result.data, required_fields)
    
    @staticmethod
    def parse_market_structure(response: str) -> ParseResult:
        """Parse Market Structure Analyst response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'liquidity_quality', 'bid_ask_spread_assessment',
            'order_book_imbalance', 'execution_recommendation',
            'slippage_estimate_pct', 'key_observations', 'confidence'
        ]
        
        return ResponseParser.validate_schema(result.data, required_fields)
    
    @staticmethod
    def parse_bull_thesis(response: str) -> ParseResult:
        """Parse Bull Researcher response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'thesis', 'supporting_evidence', 'price_targets',
            'timeframe', 'conviction', 'risks_acknowledged'
        ]
        
        return ResponseParser.validate_schema(result.data, required_fields)
    
    @staticmethod
    def parse_bear_thesis(response: str) -> ParseResult:
        """Parse Bear Researcher response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'thesis', 'risk_factors', 'price_targets',
            'timeframe', 'conviction', 'bull_counterarguments'
        ]
        
        return ResponseParser.validate_schema(result.data, required_fields)
    
    @staticmethod
    def parse_trading_decision(response: str) -> ParseResult:
        """Parse Trader Agent response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'action', 'rationale', 'confidence', 'position_size_pct',
            'entry_price', 'stop_loss', 'take_profit', 'timeframe',
            'risk_reward_ratio', 'key_decision_factors'
        ]
        
        validation = ResponseParser.validate_schema(result.data, required_fields)
        
        if not validation.success:
            return validation
        
        valid_actions = ['BUY', 'SELL', 'HOLD']
        if result.data['action'] not in valid_actions:
            return ParseResult(
                success=False,
                error=f"Invalid action: {result.data['action']}. Must be one of {valid_actions}",
                data=result.data
            )
        
        return ParseResult(
            success=True,
            data=result.data
        )
    
    @staticmethod
    def parse_risk_approval(response: str) -> ParseResult:
        """Parse Risk Manager response"""
        result = ResponseParser.parse_json(response)
        if not result.success:
            return result
        
        required_fields = [
            'approved', 'rationale', 'risk_score',
            'concerns', 'confidence'
        ]
        
        validation = ResponseParser.validate_schema(result.data, required_fields)
        
        if not validation.success:
            return validation
        
        if not isinstance(result.data['approved'], bool):
            return ParseResult(
                success=False,
                error=f"'approved' must be boolean, got {type(result.data['approved'])}",
                data=result.data
            )
        
        return ParseResult(
            success=True,
            data=result.data
        )
    
    @staticmethod
    def safe_parse(response: str, parser_func, max_retries: int = 3) -> ParseResult:
        """
        Safely parse response with retry logic
        
        Args:
            response: Raw response string
            parser_func: Parser function to use
            max_retries: Maximum retry attempts
        
        Returns:
            ParseResult
        """
        for attempt in range(max_retries):
            try:
                result = parser_func(response)
                if result.success:
                    return result
                
                logger.warning(
                    f"Parse attempt {attempt + 1}/{max_retries} failed: {result.error}"
                )
                
            except Exception as e:
                logger.error(f"Parse exception on attempt {attempt + 1}: {str(e)}")
        
        return ParseResult(
            success=False,
            error=f"Failed to parse after {max_retries} attempts",
            raw_response=response
        )
