# Implementation Plan: 6 High-Priority nof1.ai Features

**Date**: October 27, 2025  
**Estimated Duration**: 6-8 hours total  
**Status**: Awaiting Approval

## Overview

This document outlines a phased approach to implementing 6 high-priority features identified from the nof1.ai comparison:

1. Contract Spec Enforcement
2. Funding Rate Tracking
3. Per-Symbol Cooldown
4. AI Decision Database
5. WebSocket Market Data (optional)
6. Health Endpoint

## Phase Breakdown

### Phase 1: Risk Management Enhancements (2-3 hours)

**Features:**
- Contract Spec Enforcement
- Per-Symbol Cooldown

**Rationale**: These two features work together to prevent order rejections and over-trading. They're foundational for production stability.

**Deliverables:**

1. **Contract Spec Enforcement**
   - `src/execution/contract_specs.py` - ContractSpec dataclass and ContractSpecManager
   - Fetch contract specs from exchange (tick_size, step_size, min_notional, lot_size, contract_multiplier)
   - Price/quantity rounding functions
   - Order validation before submission
   - Integration with ExchangeInterface
   - 10+ unit tests

2. **Per-Symbol Cooldown**
   - Add `last_trade_time: Dict[str, datetime]` to EnhancedRiskManager
   - Add `MIN_TRADE_INTERVAL_SEC` to .env
   - Implement `can_trade_symbol()` check
   - Integration with AutonomousDecisionEngine
   - 5+ unit tests

**Testing:**
- Unit tests for rounding logic
- Unit tests for cooldown logic
- Integration tests with mock exchange specs
- Integration tests with rapid signals

**Success Criteria:**
- All tests passing
- No order rejections due to invalid sizes
- Cooldown prevents rapid-fire trading on same symbol

---

### Phase 2: Perpetual Contract Support (1-2 hours)

**Features:**
- Funding Rate Tracking

**Rationale**: Essential for accurate P&L on perpetual contracts. Builds on Phase 1's contract spec foundation.

**Deliverables:**

1. **Funding Rate Tracking**
   - Database schema: `funding_events` table (timestamp, symbol, rate, notional, amount)
   - `src/execution/funding_tracker.py` - FundingTracker class
   - `fetch_funding_rate()` - Get current funding rate from exchange
   - `calculate_funding_payment()` - Calculate funding payment for position
   - `record_funding_event()` - Store funding event in database
   - Integration with PaperTradingEngine and live trading
   - Add `FUNDING_ENABLED` flag to .env
   - 8+ unit tests

**Testing:**
- Unit tests for funding calculation
- Integration tests with mock funding events
- Backtest validation with historical funding rates
- Paper trading validation

**Success Criteria:**
- All tests passing
- Funding payments correctly calculated and recorded
- P&L includes funding payments
- Dashboard shows funding payments

---

### Phase 3: AI Audit Trail (1-2 hours)

**Features:**
- AI Decision Database

**Rationale**: Complete audit trail for AI decisions. Critical for debugging, optimization, and regulatory compliance.

**Deliverables:**

1. **AI Decision Database**
   - Database schema: `ai_decisions` table (id, timestamp, symbol, action, size, sl, tp, confidence, reasoning, market_context, executed, execution_id)
   - Update SingleAgentStrategy to persist decisions
   - Dashboard view: `/api/decisions` endpoint
   - Dashboard UI: AI decisions table with filtering
   - 6+ unit tests

**Testing:**
- Unit tests for decision storage
- Integration tests with SingleAgentStrategy
- Dashboard view tests
- Query performance tests

**Success Criteria:**
- All tests passing
- All AI decisions persisted to database
- Dashboard shows AI decisions with full reasoning
- Can filter by symbol, date, action

---

### Phase 4: Monitoring & Real-Time Data (2-3 hours)

**Features:**
- Health Endpoint
- WebSocket Market Data (optional)

**Rationale**: Production monitoring and optional real-time data. These are independent features that enhance observability.

**Deliverables:**

1. **Health Endpoint**
   - `/api/health` endpoint in dashboard
   - Returns: status, uptime, trading_enabled, error_count_24h, last_trade_time, open_positions, account_health
   - System health checks (Redis, database, exchange connectivity)
   - 4+ unit tests

2. **WebSocket Market Data (Optional)**
   - `src/data/websocket_feed.py` - WebSocketFeed class
   - Add `MARKET_DATA_WS_ENABLED` flag to .env (default: false)
   - Subscribe to ticker and orderbook updates
   - Fallback to REST if WebSocket fails
   - Integration with PriceFeed
   - 6+ unit tests
   - **Note**: Requires CCXT Pro ($1000/year) - implement as optional feature

**Testing:**
- Unit tests for health endpoint
- Integration tests for health checks
- Unit tests for WebSocket feed
- Integration tests with WebSocket connection
- Fallback tests (WebSocket → REST)

**Success Criteria:**
- All tests passing
- Health endpoint returns accurate system status
- WebSocket feed works when enabled (with CCXT Pro)
- System falls back to REST when WebSocket disabled or fails

---

## Implementation Strategy

### Code Quality Standards

- **No comments unless requested** - Clean, self-documenting code
- **Follow existing conventions** - Match codebase style
- **Comprehensive tests** - 100% test coverage for new code
- **Type hints** - Full type annotations
- **Error handling** - Graceful error handling with logging
- **Documentation** - Update README and docs

### Testing Strategy

For each phase:
1. Write unit tests first (TDD approach)
2. Implement feature
3. Run unit tests
4. Write integration tests
5. Run integration tests
6. Manual testing in paper trading mode
7. Update documentation

### Git Workflow

- One commit per phase
- Descriptive commit messages
- Push to branch after each phase
- Update PR description after all phases complete

## Timeline

| Phase | Duration | Features |
|-------|----------|----------|
| Phase 1 | 2-3 hours | Contract Spec Enforcement + Per-Symbol Cooldown |
| Phase 2 | 1-2 hours | Funding Rate Tracking |
| Phase 3 | 1-2 hours | AI Decision Database |
| Phase 4 | 2-3 hours | Health Endpoint + WebSocket Market Data |
| **Total** | **6-10 hours** | **6 features** |

## Dependencies

- **CCXT**: Already installed (for contract specs, funding rates)
- **CCXT Pro**: Optional (for WebSocket, $1000/year license)
- **SQLAlchemy**: Already installed (for database schema)
- **FastAPI**: Already installed (for health endpoint)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CCXT Pro not available | Implement WebSocket as optional, fallback to REST |
| Exchange API rate limits | Add rate limiting and caching |
| Database schema changes | Use Alembic migrations |
| Breaking changes | Comprehensive tests before deployment |

## Success Criteria (Overall)

- ✅ All 6 features implemented
- ✅ 40+ new tests, all passing
- ✅ No breaking changes to existing functionality
- ✅ Documentation updated
- ✅ Paper trading validation successful
- ✅ Ready for production deployment

## Next Steps

1. **Get approval on this phase plan**
2. **Begin Phase 1**: Contract Spec Enforcement + Per-Symbol Cooldown
3. **Complete each phase sequentially**
4. **Test comprehensively after each phase**
5. **Update PR with all changes**
6. **Message user with completion report**

---

**Awaiting user approval to proceed with Phase 1...**
