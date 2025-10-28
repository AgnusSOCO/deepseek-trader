"""
AI Module

DeepSeek-powered multi-agent system for autonomous trading decisions.
Implements 7 specialized agents with dialectical debate workflow.
"""

from .deepseek_client import DeepSeekClient
from .agents import (
    TechnicalAnalystAgent,
    SentimentAnalystAgent,
    MarketStructureAgent,
    BullResearcherAgent,
    BearResearcherAgent,
    TraderAgent,
    RiskManagerAgent,
    MultiAgentSystem
)
from .prompts import PromptTemplates
from .response_parser import ResponseParser

__all__ = [
    'DeepSeekClient',
    'TechnicalAnalystAgent',
    'SentimentAnalystAgent',
    'MarketStructureAgent',
    'BullResearcherAgent',
    'BearResearcherAgent',
    'TraderAgent',
    'RiskManagerAgent',
    'MultiAgentSystem',
    'PromptTemplates',
    'ResponseParser'
]
