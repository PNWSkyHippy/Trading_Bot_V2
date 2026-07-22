"""Fail-closed Tradovate execution adapter for the EMT strategy.

The adapter deliberately uses Tradovate's server-side multi-bracket strategy.
Once accepted, the protective stop and profit target live at the broker rather
than depending on the Python process continuing to run.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional


class TradovateExecutionError(RuntimeError):
    """Raised when an order cannot be proven accepted by Tradovate."""


@dataclass(frozen=True)
class BrokerOrder:
    strategy_id: int
    entry_order_id: Optional[int]
    symbol: str
    direction: str
    quantity: int


class TradovateExecutor:
    """Small synchronous REST client used only by the EMT receiver thread."""

    def __init__(self, *, access_token: str, account_id: int,
                 account_spec: str, environment: str = "demo",
                 timeout_seconds: float = 8.0,
                 credentials: Optional[dict] = None):
        environment = str(environment).strip().lower()
        if environment not in ("demo", "live"):
            raise ValueError("Tradovate environment must be 'demo' or 'live'")
        credentials = dict(credentials or {})
        if not str(access_token).strip() and not credentials:
            raise ValueError("Tradovate access token or API credentials are required")
        if int(account_id) <= 0 or not str(account_spec).strip():
            raise ValueError("Tradovate account id and account spec are required")
        self.access_token = str(access_token).strip()
        self.account_id = int(account_id)
        self.account_spec = str(account_spec).strip()
        self.environment = environment
        self.timeout_seconds = float(timeout_seconds)
        self.credentials = credentials
        self.base_url = (
            "https://live.tradovateapi.com/v1"
            if environment == "live"
            else "https://demo.tradovateapi.com/v1"
        )
        self._lock = threading.RLock()
        if not self.access_token:
            self.authenticate()

    @classmethod
    def from_env(cls, settings: dict) -> "TradovateExecutor":
        environment = os.getenv(
            "TRADOVATE_ENVIRONMENT",
            str(settings.get("broker_environment", "demo")),
        ).strip().lower()
        if environment == "live" and os.getenv("EMT_LIVE_TRADING") != "I_UNDERSTAND_LIVE_ORDERS":
            raise ValueError(
                "live Tradovate execution requires "
                "EMT_LIVE_TRADING=I_UNDERSTAND_LIVE_ORDERS"
            )
        credential_names = {
            "name": "TRADOVATE_USERNAME",
            "password": "TRADOVATE_PASSWORD",
            "appId": "TRADOVATE_APP_ID",
            "appVersion": "TRADOVATE_APP_VERSION",
            "cid": "TRADOVATE_CID",
            "sec": "TRADOVATE_SEC",
            "deviceId": "TRADOVATE_DEVICE_ID",
        }
        credentials = {
            field: os.getenv(env_name, "").strip()
            for field, env_name in credential_names.items()
        }
        required = ("name", "password", "cid", "sec", "deviceId")
        if any(credentials.values()) and any(not credentials[name] for name in required):
            raise ValueError(
                "Tradovate API credentials are partial; username, password, "
                "cid, sec, and device id are all required"
            )
        credentials["appId"] = credentials["appId"] or "EMT Hostinger"
        credentials["appVersion"] = credentials["appVersion"] or "1.0"
        if not all(credentials[name] for name in required):
            credentials = {}
        return cls(
            access_token=os.getenv("TRADOVATE_ACCESS_TOKEN", ""),
            account_id=int(os.getenv("TRADOVATE_ACCOUNT_ID", "0")),
            account_spec=os.getenv("TRADOVATE_ACCOUNT_SPEC", ""),
            environment=environment,
            timeout_seconds=float(settings.get("broker_timeout_seconds", 8.0)),
            credentials=credentials,
        )

    def authenticate(self) -> None:
        """Acquire a fresh token from official Tradovate API credentials."""
        if not self.credentials:
            raise TradovateExecutionError(
                "access token expired and no Tradovate API credentials are configured"
            )
        data = json.dumps(self.credentials).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/auth/accesstokenrequest",
            data=data,
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, json.JSONDecodeError) as exc:
            raise TradovateExecutionError(f"Tradovate authentication failed: {exc}") from exc
        error = result.get("errorText")
        token = str(result.get("accessToken") or "").strip()
        if error or not token:
            raise TradovateExecutionError(
                f"Tradovate authentication rejected: {error or 'missing access token'}"
            )
        self.access_token = token

    def _request(self, path: str, body: Optional[dict] = None,
                 query: Optional[dict] = None, _allow_reauth: bool = True):
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="GET" if body is None else "POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code == 401 and _allow_reauth and self.credentials:
                # A 401 proves the request was not authorized/accepted, so one
                # credential refresh and retry cannot duplicate an order.
                with self._lock:
                    self.authenticate()
                return self._request(
                    path, body=body, query=query, _allow_reauth=False
                )
            raise TradovateExecutionError(
                f"Tradovate HTTP {exc.code} for {path}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # A timeout is ambiguous: the broker may have accepted the order.
            # Never retry automatically because that could double the position.
            raise TradovateExecutionError(
                f"Tradovate request outcome unknown for {path}: {exc}"
            ) from exc
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise TradovateExecutionError(
                f"Tradovate returned invalid JSON for {path}"
            ) from exc

    def verify_account(self) -> dict:
        """Prove the token can see exactly the configured active account."""
        accounts = self._request("/account/list")
        match = next(
            (
                item for item in accounts
                if int(item.get("id", 0)) == self.account_id
                and str(item.get("name", "")) == self.account_spec
            ),
            None,
        )
        if match is None:
            raise TradovateExecutionError(
                "configured Tradovate account is not visible to this token"
            )
        if not bool(match.get("active", True)):
            raise TradovateExecutionError("configured Tradovate account is inactive")
        return match

    def assert_can_enter(self, symbol: str) -> None:
        """Fail if this account already has exposure or a working strategy."""
        contract = self._request("/contract/find", query={"name": str(symbol)})
        contract_id = int(contract.get("id") or 0)
        if contract_id <= 0:
            raise TradovateExecutionError(
                f"Tradovate contract not found: {symbol}"
            )
        positions = self._request("/position/list")
        for position in positions:
            if (int(position.get("accountId") or 0) == self.account_id
                    and int(position.get("contractId") or 0) == contract_id
                    and int(position.get("netPos") or 0) != 0):
                raise TradovateExecutionError(
                    f"refusing EMT entry: existing {symbol} position"
                )
        strategies = self._request("/orderStrategy/list")
        inactive = {"completed", "terminated", "inactive", "stopped", "failed"}
        for strategy in strategies:
            status = str(strategy.get("status", "")).lower()
            if (int(strategy.get("accountId") or 0) == self.account_id
                    and int(strategy.get("contractId") or 0) == contract_id
                    and status not in inactive):
                raise TradovateExecutionError(
                    f"refusing EMT entry: working {symbol} order strategy"
                )

    def place_bracket(self, *, symbol: str, direction: str, quantity: int,
                      stop_points: float, target_points: float,
                      tick_size: float, client_id: str) -> BrokerOrder:
        """Submit one market entry with broker-hosted 2-sided protection."""
        direction = str(direction).lower()
        if direction not in ("long", "short"):
            raise ValueError("direction must be long or short")
        if int(quantity) != 1:
            raise ValueError("EMT live execution is locked to exactly one contract")
        stop_ticks = int(round(float(stop_points) / float(tick_size)))
        target_ticks = int(round(float(target_points) / float(tick_size)))
        if stop_ticks <= 0 or target_ticks <= 0:
            raise ValueError("stop and target must be positive whole tick distances")
        if abs(stop_ticks * tick_size - float(stop_points)) > 1e-9:
            raise ValueError("stop distance does not align to the contract tick size")
        if abs(target_ticks * tick_size - float(target_points)) > 1e-9:
            raise ValueError("target distance does not align to the contract tick size")

        action = "Buy" if direction == "long" else "Sell"
        sign = 1 if direction == "long" else -1
        params = {
            "entryVersion": {"orderQty": 1, "orderType": "Market"},
            "brackets": [{
                "qty": 1,
                "profitTarget": sign * target_ticks,
                "stopLoss": -sign * stop_ticks,
                "trailingStop": False,
            }],
        }
        body = {
            "accountId": self.account_id,
            "accountSpec": self.account_spec,
            "symbol": str(symbol),
            "action": action,
            "orderStrategyTypeId": 2,
            "params": json.dumps(params, separators=(",", ":")),
            "uuid": str(client_id)[:64],
            "customTag50": "EMT_AUTO",
        }
        with self._lock:
            self.assert_can_enter(symbol)
            result = self._request("/orderStrategy/startorderstrategy", body=body)
        error = result.get("errorText") or result.get("failureText")
        strategy = result.get("orderStrategy") or {}
        strategy_id = int(strategy.get("id") or 0)
        if error or strategy_id <= 0:
            raise TradovateExecutionError(
                f"Tradovate rejected EMT bracket: {error or 'missing strategy id'}"
            )
        return BrokerOrder(
            strategy_id=strategy_id,
            entry_order_id=None,
            symbol=str(symbol),
            direction=direction,
            quantity=1,
        )

    def strategy_status(self, strategy_id: int) -> str:
        """Return pending/open/closed/rejected for a submitted bracket."""
        item = self._request("/orderStrategy/item", query={"id": int(strategy_id)})
        status = str(item.get("status", "")).lower()
        failure = str(item.get("failureMessage", "")).strip()
        if failure or "fail" in status or "reject" in status:
            return "rejected"
        if status in ("completed", "terminated", "inactive", "stopped"):
            return "closed"
        if status in ("activeorder", "activestrategy", "working"):
            return "open"
        return "pending"

    def interrupt(self, strategy_id: int) -> None:
        result = self._request(
            "/orderStrategy/interruptorderstrategy",
            body={"orderStrategyId": int(strategy_id)},
        )
        if result.get("errorText"):
            raise TradovateExecutionError(str(result["errorText"]))
