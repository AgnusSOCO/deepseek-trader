"""
Multi-Agent System

7 specialized agents with dialectical debate workflow:
1. Technical Analyst
2. Sentiment Analyst  
3. Market Structure Analyst
4. Bull Researcher
5. Bear Researcher
6. Trader
7. Risk Manager
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .deepseek_client import DeepSeekClient
from .prompts import PromptTemplates
from .response_parser import ResponseParser, ParseResult

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from an AI agent"""
    agent_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    elapsed_seconds: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0


class BaseAgent:
    """Base class for all AI agents"""
    
    def __init__(self, name: str, model: str, client: DeepSeekClient):
        """
        Initialize agent
        
        Args:
            name: Agent name
            model: Model to use (deepseek-chat or deepseek-reasoner)
            client: DeepSeek API client
        """
        self.name = name
        self.model = model
        self.client = client
        logger.info(f"Initialized {name} with model {model}")
    
    async def execute(self, messages: List[Dict[str, str]]) -> AgentResponse:
        """
        Execute agent with given messages
        
        Args:
            messages: List of message dicts for chat completion
        
        Returns:
            AgentResponse with parsed data or error
        """
        try:
            response = await self.client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"} if "reasoner" not in self.model else None
            )
            
            parse_result = self.parse_response(response['content'])
            
            return AgentResponse(
                agent_name=self.name,
                success=parse_result.success,
                data=parse_result.data,
                error=parse_result.error,
                raw_response=response['content'],
                elapsed_seconds=response.get('elapsed_seconds', 0),
                tokens_used=response['usage']['total_tokens'],
                cost=response['cost']
            )
            
        except Exception as e:
            logger.error(f"{self.name} execution failed: {str(e)}")
            return AgentResponse(
                agent_name=self.name,
                success=False,
                error=str(e)
            )
    
    def parse_response(self, response: str) -> ParseResult:
        """Parse agent response - override in subclasses"""
        return ResponseParser.parse_json(response)


class TechnicalAnalystAgent(BaseAgent):
    """Technical Analyst Agent - analyzes price action and indicators"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Technical Analyst", "deepseek-chat", client)
    
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict],
        indicators: Dict[str, Any],
        current_price: float
    ) -> AgentResponse:
        """Perform technical analysis"""
        messages = PromptTemplates.technical_analyst(
            symbol, timeframe, ohlcv_data, indicators, current_price
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_technical_analysis(response)


class SentimentAnalystAgent(BaseAgent):
    """Sentiment Analyst Agent - analyzes market sentiment from derivatives"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Sentiment Analyst", "deepseek-chat", client)
    
    async def analyze(
        self,
        symbol: str,
        funding_rate: float,
        open_interest: float,
        liquidations_24h: Dict[str, float],
        volume_24h: float
    ) -> AgentResponse:
        """Perform sentiment analysis"""
        messages = PromptTemplates.sentiment_analyst(
            symbol, funding_rate, open_interest, liquidations_24h, volume_24h
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_sentiment_analysis(response)


class MarketStructureAgent(BaseAgent):
    """Market Structure Agent - analyzes order book and liquidity"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Market Structure Analyst", "deepseek-chat", client)
    
    async def analyze(
        self,
        symbol: str,
        order_book: Dict[str, List],
        bid_ask_spread: float,
        volume_profile: Dict[str, float]
    ) -> AgentResponse:
        """Perform market structure analysis"""
        messages = PromptTemplates.market_structure(
            symbol, order_book, bid_ask_spread, volume_profile
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_market_structure(response)


class BullResearcherAgent(BaseAgent):
    """Bull Researcher Agent - builds bullish thesis"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Bull Researcher", "deepseek-reasoner", client)
    
    async def research(
        self,
        symbol: str,
        technical_analysis: Dict,
        sentiment_analysis: Dict,
        market_structure: Dict,
        portfolio_state: Dict
    ) -> AgentResponse:
        """Build bullish thesis"""
        messages = PromptTemplates.bull_researcher(
            symbol, technical_analysis, sentiment_analysis,
            market_structure, portfolio_state
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_bull_thesis(response)


class BearResearcherAgent(BaseAgent):
    """Bear Researcher Agent - builds bearish thesis"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Bear Researcher", "deepseek-reasoner", client)
    
    async def research(
        self,
        symbol: str,
        technical_analysis: Dict,
        sentiment_analysis: Dict,
        market_structure: Dict,
        portfolio_state: Dict
    ) -> AgentResponse:
        """Build bearish thesis"""
        messages = PromptTemplates.bear_researcher(
            symbol, technical_analysis, sentiment_analysis,
            market_structure, portfolio_state
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_bear_thesis(response)


class TraderAgent(BaseAgent):
    """Trader Agent - makes final trading decision"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Trader", "deepseek-reasoner", client)
    
    async def decide(
        self,
        symbol: str,
        current_price: float,
        bull_thesis: Dict,
        bear_thesis: Dict,
        portfolio_state: Dict,
        account_balance: float
    ) -> AgentResponse:
        """Make trading decision"""
        messages = PromptTemplates.trader(
            symbol, current_price, bull_thesis, bear_thesis,
            portfolio_state, account_balance
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_trading_decision(response)


class RiskManagerAgent(BaseAgent):
    """Risk Manager Agent - approves/rejects trades"""
    
    def __init__(self, client: DeepSeekClient):
        super().__init__("Risk Manager", "deepseek-chat", client)
    
    async def review(
        self,
        symbol: str,
        proposed_trade: Dict,
        portfolio_metrics: Dict,
        account_balance: float,
        current_positions: List[Dict]
    ) -> AgentResponse:
        """Review and approve/reject trade"""
        messages = PromptTemplates.risk_manager(
            symbol, proposed_trade, portfolio_metrics,
            account_balance, current_positions
        )
        return await self.execute(messages)
    
    def parse_response(self, response: str) -> ParseResult:
        return ResponseParser.parse_risk_approval(response)


@dataclass
class MultiAgentResult:
    """Result from multi-agent workflow"""
    success: bool
    final_decision: Optional[Dict[str, Any]] = None
    technical_analysis: Optional[Dict[str, Any]] = None
    sentiment_analysis: Optional[Dict[str, Any]] = None
    market_structure: Optional[Dict[str, Any]] = None
    bull_thesis: Optional[Dict[str, Any]] = None
    bear_thesis: Optional[Dict[str, Any]] = None
    trader_decision: Optional[Dict[str, Any]] = None
    risk_approval: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0


class MultiAgentSystem:
    """
    Multi-agent system orchestrator
    
    Coordinates 7 agents through dialectical debate workflow:
    Phase 1: Parallel Analysis (Technical, Sentiment, Market Structure)
    Phase 2: Dialectical Debate (Bull vs Bear Researchers)
    Phase 3: Decision Synthesis (Trader)
    Phase 4: Risk Review (Risk Manager)
    """
    
    def __init__(self, client: DeepSeekClient):
        """
        Initialize multi-agent system
        
        Args:
            client: DeepSeek API client
        """
        self.client = client
        
        self.technical_analyst = TechnicalAnalystAgent(client)
        self.sentiment_analyst = SentimentAnalystAgent(client)
        self.market_structure = MarketStructureAgent(client)
        self.bull_researcher = BullResearcherAgent(client)
        self.bear_researcher = BearResearcherAgent(client)
        self.trader = TraderAgent(client)
        self.risk_manager = RiskManagerAgent(client)
        
        logger.info("Multi-agent system initialized with 7 agents")
    
    async def execute_workflow(
        self,
        symbol: str,
        timeframe: str,
        market_data: Dict[str, Any],
        portfolio_state: Dict[str, Any],
        account_balance: float,
        current_positions: List[Dict]
    ) -> MultiAgentResult:
        """
        Execute complete multi-agent workflow
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            market_data: Market data including OHLCV, indicators, order book, etc.
            portfolio_state: Current portfolio state
            account_balance: Account balance
            current_positions: List of current positions
        
        Returns:
            MultiAgentResult with final decision and all intermediate results
        """
        start_time = datetime.now()
        result = MultiAgentResult(success=False)
        
        try:
            logger.info(f"Phase 1: Parallel Analysis for {symbol}")
            analysis_results = await self._phase1_parallel_analysis(
                symbol, timeframe, market_data
            )
            
            if not all(r.success for r in analysis_results):
                errors = [r.error for r in analysis_results if not r.success]
                result.errors.extend(errors)
                logger.error(f"Phase 1 failed: {errors}")
                return result
            
            result.technical_analysis = analysis_results[0].data
            result.sentiment_analysis = analysis_results[1].data
            result.market_structure = analysis_results[2].data
            
            for r in analysis_results:
                result.total_cost += r.cost
                result.total_tokens += r.tokens_used
            
            logger.info(f"Phase 2: Dialectical Debate for {symbol}")
            debate_results = await self._phase2_dialectical_debate(
                symbol,
                result.technical_analysis,
                result.sentiment_analysis,
                result.market_structure,
                portfolio_state
            )
            
            if not all(r.success for r in debate_results):
                errors = [r.error for r in debate_results if not r.success]
                result.errors.extend(errors)
                logger.error(f"Phase 2 failed: {errors}")
                return result
            
            result.bull_thesis = debate_results[0].data
            result.bear_thesis = debate_results[1].data
            
            for r in debate_results:
                result.total_cost += r.cost
                result.total_tokens += r.tokens_used
            
            logger.info(f"Phase 3: Decision Synthesis for {symbol}")
            trader_response = await self.trader.decide(
                symbol,
                market_data['current_price'],
                result.bull_thesis,
                result.bear_thesis,
                portfolio_state,
                account_balance
            )
            
            if not trader_response.success:
                result.errors.append(trader_response.error)
                logger.error(f"Phase 3 failed: {trader_response.error}")
                return result
            
            result.trader_decision = trader_response.data
            result.total_cost += trader_response.cost
            result.total_tokens += trader_response.tokens_used
            
            logger.info(f"Phase 4: Risk Review for {symbol}")
            risk_response = await self.risk_manager.review(
                symbol,
                result.trader_decision,
                portfolio_state,
                account_balance,
                current_positions
            )
            
            if not risk_response.success:
                result.errors.append(risk_response.error)
                logger.error(f"Phase 4 failed: {risk_response.error}")
                return result
            
            result.risk_approval = risk_response.data
            result.total_cost += risk_response.cost
            result.total_tokens += risk_response.tokens_used
            
            if result.risk_approval['approved']:
                result.final_decision = {
                    'action': result.trader_decision['action'],
                    'confidence': result.trader_decision['confidence'],
                    'position_size_pct': result.trader_decision['position_size_pct'],
                    'entry_price': result.trader_decision['entry_price'],
                    'stop_loss': result.trader_decision['stop_loss'],
                    'take_profit': result.trader_decision['take_profit'],
                    'timeframe': result.trader_decision['timeframe'],
                    'risk_reward_ratio': result.trader_decision['risk_reward_ratio'],
                    'rationale': result.trader_decision['rationale'],
                    'risk_approved': True,
                    'risk_score': result.risk_approval['risk_score']
                }
                result.success = True
            else:
                result.final_decision = {
                    'action': 'HOLD',
                    'confidence': 0,
                    'rationale': f"Trade rejected by Risk Manager: {result.risk_approval['rationale']}",
                    'risk_approved': False,
                    'risk_concerns': result.risk_approval['concerns']
                }
                result.success = True  # Workflow succeeded, just rejected trade
            
            result.elapsed_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Multi-agent workflow completed: "
                f"decision={result.final_decision['action']}, "
                f"cost=${result.total_cost:.4f}, "
                f"tokens={result.total_tokens}, "
                f"time={result.elapsed_seconds:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Multi-agent workflow failed: {str(e)}")
            result.errors.append(str(e))
            result.elapsed_seconds = (datetime.now() - start_time).total_seconds()
            return result
    
    async def _phase1_parallel_analysis(
        self,
        symbol: str,
        timeframe: str,
        market_data: Dict[str, Any]
    ) -> List[AgentResponse]:
        """Execute Phase 1: Parallel Analysis"""
        tasks = [
            self.technical_analyst.analyze(
                symbol,
                timeframe,
                market_data['ohlcv'],
                market_data['indicators'],
                market_data['current_price']
            ),
            self.sentiment_analyst.analyze(
                symbol,
                market_data.get('funding_rate', 0.0),
                market_data.get('open_interest', 0.0),
                market_data.get('liquidations_24h', {'longs': 0, 'shorts': 0}),
                market_data.get('volume_24h', 0.0)
            ),
            self.market_structure.analyze(
                symbol,
                market_data.get('order_book', {'bids': [], 'asks': []}),
                market_data.get('bid_ask_spread', 0.0),
                market_data.get('volume_profile', {})
            )
        ]
        
        return await asyncio.gather(*tasks)
    
    async def _phase2_dialectical_debate(
        self,
        symbol: str,
        technical_analysis: Dict,
        sentiment_analysis: Dict,
        market_structure: Dict,
        portfolio_state: Dict
    ) -> List[AgentResponse]:
        """Execute Phase 2: Dialectical Debate"""
        tasks = [
            self.bull_researcher.research(
                symbol,
                technical_analysis,
                sentiment_analysis,
                market_structure,
                portfolio_state
            ),
            self.bear_researcher.research(
                symbol,
                technical_analysis,
                sentiment_analysis,
                market_structure,
                portfolio_state
            )
        ]
        
        return await asyncio.gather(*tasks)
