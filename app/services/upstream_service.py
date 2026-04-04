"""
upstream_service.py — Stub/driver layer for upstream financial data systems.

Each upstream system has:
  - A descriptor (name, type, available endpoints)
  - A request handler that returns realistic mock responses
  - A hook point for real API calls when credentials are configured

Registered upstream systems:
  - retirement       : Retirement & Pension team
  - mutual_fund      : Mutual Fund team
  - alt_investment   : Alternative Investments team
  - finra_mail       : FINRA mailing address registry
  - stocks           : Stocks & equities platform
  - etrade           : eTrade brokerage platform
  - program_banks    : Program Banks / sweep accounts
"""
import json
import random
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── System Registry ────────────────────────────────────────────────────────────

UPSTREAM_SYSTEMS: dict[str, dict] = {
    "retirement": {
        "name": "Retirement & Pension Platform",
        "description": "401(k), IRA, and pension account data",
        "team": "Retirement Team",
        "base_url_env": "RETIREMENT_API_URL",
        "auth_env": "RETIREMENT_API_KEY",
        "endpoints": [
            "GET /accounts/{account_id}",
            "GET /accounts/{account_id}/holdings",
            "GET /accounts/{account_id}/transactions",
            "POST /accounts/{account_id}/statement-request",
            "GET /plans/{plan_id}/participants",
        ],
        "stub_mode": True,
    },
    "mutual_fund": {
        "name": "Mutual Fund Platform",
        "description": "Mutual fund positions, NAV, and transaction history",
        "team": "Mutual Fund Team",
        "base_url_env": "MUTUAL_FUND_API_URL",
        "auth_env": "MUTUAL_FUND_API_KEY",
        "endpoints": [
            "GET /funds/{fund_id}",
            "GET /accounts/{account_id}/fund-positions",
            "GET /funds/{fund_id}/nav-history",
            "POST /orders",
            "GET /orders/{order_id}",
        ],
        "stub_mode": True,
    },
    "alt_investment": {
        "name": "Alternative Investments Platform",
        "description": "Hedge funds, private equity, REITs, and structured products",
        "team": "Alternative Investment Team",
        "base_url_env": "ALT_INVEST_API_URL",
        "auth_env": "ALT_INVEST_API_KEY",
        "endpoints": [
            "GET /instruments/{instrument_id}",
            "GET /accounts/{account_id}/alt-positions",
            "GET /accounts/{account_id}/capital-calls",
            "GET /accounts/{account_id}/distributions",
        ],
        "stub_mode": True,
    },
    "finra_mail": {
        "name": "FINRA Mailing Address Registry",
        "description": "Regulatory mailing address validation and FINRA Rule 2231 compliance",
        "team": "FINRA Compliance Team",
        "base_url_env": "FINRA_MAIL_API_URL",
        "auth_env": "FINRA_MAIL_API_KEY",
        "endpoints": [
            "GET /addresses/{client_id}",
            "POST /addresses/validate",
            "PUT /addresses/{client_id}",
            "GET /mailings/{mailing_id}/status",
            "GET /undeliverable-mail",
        ],
        "stub_mode": True,
    },
    "stocks": {
        "name": "Stocks & Equities Platform",
        "description": "Real-time and historical equity positions, corporate actions, dividends",
        "team": "Equities Team",
        "base_url_env": "STOCKS_API_URL",
        "auth_env": "STOCKS_API_KEY",
        "endpoints": [
            "GET /equities/{symbol}/price",
            "GET /accounts/{account_id}/equity-positions",
            "GET /corporate-actions/{symbol}",
            "GET /dividends/{symbol}/history",
            "POST /accounts/{account_id}/confirm-trade",
        ],
        "stub_mode": True,
    },
    "etrade": {
        "name": "eTrade Brokerage Platform",
        "description": "Brokerage account data, order management, and trade confirmations",
        "team": "eTrade Integration Team",
        "base_url_env": "ETRADE_API_URL",
        "auth_env": "ETRADE_API_KEY",
        "endpoints": [
            "GET /accounts/{account_id}/summary",
            "GET /accounts/{account_id}/orders",
            "POST /orders",
            "DELETE /orders/{order_id}",
            "GET /accounts/{account_id}/brokerage-statement",
        ],
        "stub_mode": True,
    },
    "program_banks": {
        "name": "Program Banks / Sweep Accounts",
        "description": "Cash sweep, FDIC coverage, and program bank interest data",
        "team": "Program Banks Team",
        "base_url_env": "PROGRAM_BANKS_API_URL",
        "auth_env": "PROGRAM_BANKS_API_KEY",
        "endpoints": [
            "GET /sweep-accounts/{account_id}/balance",
            "GET /banks",
            "GET /banks/{bank_id}/rates",
            "GET /accounts/{account_id}/fdic-coverage",
            "POST /sweep-accounts/{account_id}/transfer",
        ],
        "stub_mode": True,
    },
}

# ── Stub Response Generators ───────────────────────────────────────────────────

def _random_account_id() -> str:
    return f"ACC{random.randint(1000000, 9999999)}"

def _random_amount(low=1000, high=500000) -> float:
    return round(random.uniform(low, high), 2)

def _random_date(days_ago=365) -> str:
    delta = random.randint(1, days_ago)
    return (date.today() - timedelta(days=delta)).isoformat()


def _stub_retirement(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    return {
        "system": "retirement",
        "endpoint": endpoint,
        "account_id": account_id,
        "account_type": random.choice(["401k", "IRA", "Roth IRA", "Pension"]),
        "plan_id": f"PLAN{random.randint(100, 999)}",
        "participant_name": "John A. Doe",
        "total_balance": _random_amount(50000, 800000),
        "vested_balance": _random_amount(40000, 750000),
        "employer_match_ytd": _random_amount(1000, 15000),
        "contributions_ytd": _random_amount(5000, 22500),
        "holdings": [
            {"fund": "SP500 Index Fund", "shares": random.randint(10, 500), "nav": round(random.uniform(50, 250), 2)},
            {"fund": "Bond Index Fund",  "shares": random.randint(5, 200),  "nav": round(random.uniform(10, 50), 2)},
            {"fund": "Money Market",     "balance": _random_amount(1000, 20000)},
        ],
        "last_contribution_date": _random_date(90),
        "plan_entry_date": _random_date(3650),
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_mutual_fund(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    funds = [
        {"fund_id": "MF001", "name": "Growth & Income Fund",    "ticker": "GRINX", "nav": 42.17},
        {"fund_id": "MF002", "name": "International Equity Fund","ticker": "INTLX", "nav": 18.94},
        {"fund_id": "MF003", "name": "Tax-Exempt Bond Fund",     "ticker": "TXBDX", "nav": 11.32},
    ]
    selected = random.choice(funds)
    return {
        "system": "mutual_fund",
        "endpoint": endpoint,
        "account_id": account_id,
        "fund": selected,
        "shares": round(random.uniform(10, 2000), 3),
        "total_market_value": _random_amount(10000, 200000),
        "unrealized_gain_loss": round(random.uniform(-5000, 50000), 2),
        "dividends_ytd": round(random.uniform(0, 5000), 2),
        "last_trade_date": _random_date(30),
        "nav_history": [
            {"date": _random_date(i * 5), "nav": round(selected["nav"] + random.uniform(-2, 2), 2)}
            for i in range(1, 6)
        ],
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_alt_investment(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    instrument_types = [
        {"type": "Hedge Fund",     "name": "Macro Opportunities Fund LP"},
        {"type": "Private Equity", "name": "Buyout Partners III"},
        {"type": "REIT",           "name": "Commercial Property Income REIT"},
        {"type": "Structured Note","name": "7yr USD LIBOR-linked Note"},
    ]
    inst = random.choice(instrument_types)
    return {
        "system": "alt_investment",
        "endpoint": endpoint,
        "account_id": account_id,
        "instrument": inst,
        "commitment": _random_amount(50000, 500000),
        "contributed_capital": _random_amount(30000, 400000),
        "distributed_capital": _random_amount(0, 100000),
        "net_asset_value": _random_amount(50000, 600000),
        "irr_pct": round(random.uniform(-5, 25), 2),
        "moic": round(random.uniform(0.8, 3.5), 2),
        "vintage_year": random.randint(2015, 2023),
        "capital_calls": [
            {"date": _random_date(180), "amount": _random_amount(10000, 50000), "status": "settled"}
        ],
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_finra_mail(endpoint: str, params: dict) -> dict:
    client_id = params.get("client_id", f"CL{random.randint(10000, 99999)}")
    return {
        "system": "finra_mail",
        "endpoint": endpoint,
        "client_id": client_id,
        "client_name": "Jane B. Smith",
        "mailing_address": {
            "line1": f"{random.randint(100,9999)} Oak Street",
            "line2": f"Suite {random.randint(1,500)}",
            "city": random.choice(["New York", "Chicago", "San Francisco", "Boston"]),
            "state": random.choice(["NY", "IL", "CA", "MA"]),
            "zip": f"{random.randint(10000, 99999)}",
            "country": "US",
        },
        "address_validated": random.choice([True, True, True, False]),
        "last_validated_date": _random_date(90),
        "delivery_preference": random.choice(["postal", "electronic", "both"]),
        "undeliverable_flag": False,
        "finra_rule_2231_compliant": True,
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_stocks(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    symbols = ["AAPL", "MSFT", "GOOGL", "JPM", "BAC", "GS", "MS", "BLK"]
    holdings = [
        {
            "symbol": s,
            "shares": random.randint(1, 500),
            "avg_cost": round(random.uniform(50, 400), 2),
            "current_price": round(random.uniform(50, 450), 2),
            "unrealized_pnl": round(random.uniform(-5000, 20000), 2),
        }
        for s in random.sample(symbols, k=min(4, len(symbols)))
    ]
    return {
        "system": "stocks",
        "endpoint": endpoint,
        "account_id": account_id,
        "equity_positions": holdings,
        "total_equity_value": sum(h["shares"] * h["current_price"] for h in holdings),
        "total_unrealized_pnl": sum(h["unrealized_pnl"] for h in holdings),
        "dividends_received_ytd": round(random.uniform(0, 8000), 2),
        "last_trade_date": _random_date(10),
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_etrade(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    return {
        "system": "etrade",
        "endpoint": endpoint,
        "account_id": account_id,
        "account_type": random.choice(["Individual Brokerage", "Joint Account", "Margin Account"]),
        "net_account_value": _random_amount(10000, 500000),
        "cash_balance": _random_amount(1000, 50000),
        "margin_available": _random_amount(0, 100000),
        "open_orders": random.randint(0, 5),
        "orders": [
            {
                "order_id": f"ORD{random.randint(100000, 999999)}",
                "symbol": random.choice(["AAPL", "MSFT", "TSLA"]),
                "order_type": random.choice(["LIMIT", "MARKET", "STOP"]),
                "side": random.choice(["BUY", "SELL"]),
                "quantity": random.randint(1, 100),
                "limit_price": round(random.uniform(100, 400), 2),
                "status": random.choice(["PENDING", "FILLED", "PARTIALLY_FILLED"]),
                "placed_at": _random_date(5),
            }
        ],
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _stub_program_banks(endpoint: str, params: dict) -> dict:
    account_id = params.get("account_id", _random_account_id())
    banks = [
        {"bank_id": "BK001", "name": "First National Trust",    "rate_apy_pct": 4.75},
        {"bank_id": "BK002", "name": "Pacific Savings Bank",    "rate_apy_pct": 4.50},
        {"bank_id": "BK003", "name": "Heritage Federal Credit", "rate_apy_pct": 4.80},
    ]
    return {
        "system": "program_banks",
        "endpoint": endpoint,
        "account_id": account_id,
        "sweep_balance": _random_amount(5000, 250000),
        "fdic_insured_amount": min(250000, _random_amount(5000, 250000)),
        "fdic_coverage_pct": round(random.uniform(80, 100), 1),
        "allocated_banks": random.sample(banks, k=random.randint(1, 3)),
        "total_interest_ytd": round(random.uniform(50, 8000), 2),
        "program_rate_apy_pct": round(random.uniform(4.25, 5.00), 2),
        "last_sweep_date": _random_date(1),
        "stub": True,
        "request_id": str(uuid.uuid4()),
        "generated_at": datetime.utcnow().isoformat(),
    }


_STUB_HANDLERS = {
    "retirement":   _stub_retirement,
    "mutual_fund":  _stub_mutual_fund,
    "alt_investment": _stub_alt_investment,
    "finra_mail":   _stub_finra_mail,
    "stocks":       _stub_stocks,
    "etrade":       _stub_etrade,
    "program_banks": _stub_program_banks,
}


class UpstreamService:
    def list_systems(self) -> list[dict]:
        result = []
        for sys_id, meta in UPSTREAM_SYSTEMS.items():
            result.append({
                "system_id": sys_id,
                "name": meta["name"],
                "description": meta["description"],
                "team": meta["team"],
                "endpoints": meta["endpoints"],
                "mode": "stub" if meta["stub_mode"] else "live",
            })
        return result

    def call_upstream(self, system_id: str, endpoint: str, params: dict) -> dict:
        if system_id not in UPSTREAM_SYSTEMS:
            return {"error": f"Unknown upstream system: {system_id}"}

        system = UPSTREAM_SYSTEMS[system_id]
        logger.info(f"Upstream call → {system_id} : {endpoint}")

        if system["stub_mode"]:
            handler = _STUB_HANDLERS.get(system_id)
            if handler:
                response = handler(endpoint, params)
                logger.info(f"Stub response generated for {system_id}")
                return response
            return {"error": f"No stub handler for {system_id}"}

        # Real API call (when not in stub mode — not yet implemented)
        return {"error": "Live upstream calls not yet configured — set stub_mode=False and configure the API credentials"}

    def discover_test_data(self, system_id: str, data_type: str, filters: dict) -> dict:
        """
        Discover existing test data from an upstream system matching filters.
        Returns matching records or a suggestion to create new data.
        """
        if system_id not in UPSTREAM_SYSTEMS:
            return {"error": f"Unknown system: {system_id}"}

        # In stub mode, we generate representative data that "matches" the filters
        endpoint = f"GET /accounts/search"
        base = self.call_upstream(system_id, endpoint, filters)
        base["discovery_filters"] = filters
        base["data_type"] = data_type
        base["match_count"] = random.randint(0, 5)
        base["recommendation"] = (
            "Use existing test account ACC1234567 — matches all filter criteria."
            if base["match_count"] > 0
            else "No existing data matches. Recommend creating synthetic test data with the /create-test-data endpoint."
        )
        return base

    def create_test_data(self, system_id: str, data_spec: dict) -> dict:
        """
        Request upstream system to create / provision test data.
        Stub: returns a simulated creation response.
        """
        logger.info(f"Create test data → {system_id}")
        return {
            "system_id": system_id,
            "action": "create_test_data",
            "created": True,
            "account_id": _random_account_id(),
            "spec_applied": data_spec,
            "confirmation_id": str(uuid.uuid4()),
            "ready_at": (datetime.utcnow() + timedelta(minutes=2)).isoformat(),
            "stub": UPSTREAM_SYSTEMS.get(system_id, {}).get("stub_mode", True),
            "note": "Test data provisioned in stub environment. Configure upstream API credentials for live provisioning.",
        }


upstream_service = UpstreamService()
