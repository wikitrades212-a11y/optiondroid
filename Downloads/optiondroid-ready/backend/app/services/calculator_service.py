"""
Target Move Calculator service — v3.

Scoring model
─────────────
1. Hard-reject (avoid) only truly unusable contracts:
     spread > 50 %, OI < 10, abs(delta) < 0.03, max_premium exceeded.
   Far-OTM and low-ROI are soft-penalised inside tier scores — not hard-rejected —
   so aggressive/balanced never go empty unless nothing passes the four rules above.

2. Estimation model is move-size-aware:
     |move| ≤ 5 %   → delta + gamma Taylor (accurate for small moves)
     5 % < |move| ≤ 10% → blended Taylor + intrinsic floor
     |move| > 10 %  → intrinsic + residual time-value fraction

3. Tier assignment: relative delta thirds across the non-avoid pool.
     top-third abs(delta)    → safer
     middle-third abs(delta) → balanced
     bottom-third abs(delta) → aggressive
   Ceiling division ensures all three tiers fill for n ≥ 3.

4. Within each tier, _tier_score() ranks candidates with:
     delta, gamma (chain-normalised to 90th pct), ROI,
     spread quality, liquidity, theta efficiency (chain-normalised),
     target-distance, expiry-fit.
   All components independently normalised to [0, 1].
   Tier-specific weights reflect each tier's goal.
   Soft penalties applied for quality issues without hard-rejecting.

5. Expiry-fit scores how well DTE matches the expected move magnitude
   and is used both as a scoring component and as a surface metric.
"""
import logging
from datetime import date
from typing import List, Literal, Optional

from app.models.calculator import CalculatorResponse, StrikeAnalysis
from app.providers import provider

logger = logging.getLogger(__name__)

# ── Hard-reject thresholds (keep very permissive) ─────────────────────────────
MAX_SPREAD_AVOID = 50.0   # bid-ask > 50 % of mid → always avoid
MIN_OI_AVOID     = 10     # essentially no open interest
MIN_DELTA_HARD   = 0.03   # effectively zero delta sensitivity
TARGET_ROI_FLOOR = 1.5    # ideal_max_entry floor multiplier


# ── Estimation model ──────────────────────────────────────────────────────────

def _intrinsic_at_target(strike: float, target: float, option_type: str) -> float:
    if option_type == "call":
        return max(target - strike, 0.0)
    return max(strike - target, 0.0)


def _estimated_value_at_target(
    mid: float,
    delta: float,
    gamma: float,
    price_change: float,
    intrinsic: float,
    move_pct_abs: float,
) -> float:
    """
    Move-size-aware option value estimate at target price.

    Small (≤5%): delta+gamma Taylor expansion is reliable.
    Moderate (5–10%): blend Taylor toward intrinsic as move grows.
    Large (>10%): intrinsic dominates; add 15 % of current mid as residual.
    """
    taylor = mid + delta * price_change + 0.5 * gamma * price_change ** 2

    if move_pct_abs <= 5.0:
        estimated = taylor
    elif move_pct_abs <= 10.0:
        # Linear blend weight: 0 at 5 %, 1 at 10 %
        w = (move_pct_abs - 5.0) / 5.0
        estimated = taylor * (1.0 - w * 0.5) + intrinsic * (w * 0.5)
    else:
        # Intrinsic + small time-value residual
        estimated = intrinsic + mid * 0.15

    return round(max(estimated, intrinsic, 0.01), 4)


# ── Liquidity & quality helpers ───────────────────────────────────────────────

def _spread_pct(bid: float, ask: float, mid: float) -> float:
    if mid <= 0:
        return 100.0
    return round((ask - bid) / mid * 100, 2)


def _liquidity_score(oi: int, volume: int, spread: float) -> float:
    """0–100. OI (40 pts) + volume (30 pts) + tight spread (30 pts)."""
    oi_score     = min(oi / 500, 1.0) * 40
    vol_score    = min(volume / 200, 1.0) * 30
    spread_score = max(0.0, 1.0 - spread / 50.0) * 30
    return round(oi_score + vol_score + spread_score, 1)


def _ideal_max_entry(estimated_value: float, spread: float) -> float:
    slippage = spread / 100.0 * 0.5
    return round(max(estimated_value / TARGET_ROI_FLOOR - slippage * estimated_value, 0.01), 2)


def _contracts_for_risk(
    max_entry: float, risk_per_trade: Optional[float]
) -> Optional[int]:
    if not risk_per_trade or max_entry <= 0:
        return None
    return max(1, int(risk_per_trade / (max_entry * 100)))


# ── Expiry helpers ────────────────────────────────────────────────────────────

def _dte(expiration: str) -> int:
    """Days to expiration from today (floor 0)."""
    try:
        return max(0, (date.fromisoformat(expiration) - date.today()).days)
    except Exception:
        return 30


def _expiry_fit_score(dte: int, move_pct_abs: float) -> float:
    """
    [0, 1] score for how well DTE matches the expected move magnitude.

    Larger moves need more runway; smaller moves favour shorter DTE
    (higher gamma, less theta drag before the move materialises).
    """
    if dte <= 0:
        return 0.0
    if move_pct_abs < 3:    ideal = 10
    elif move_pct_abs < 6:  ideal = 21
    elif move_pct_abs < 10: ideal = 42
    else:                   ideal = 60

    ratio = dte / ideal
    if ratio < 0.5:
        return ratio * 1.6                          # too little time
    elif ratio <= 1.5:
        return 1.0 - abs(ratio - 1.0) * 0.25       # sweet spot
    else:
        return max(0.2, 1.0 - (ratio - 1.5) * 0.12)  # too much time


# ── Chain-level statistics ────────────────────────────────────────────────────

def _chain_stats(contracts: List[StrikeAnalysis]) -> dict:
    """
    Compute 90th-percentile gamma and theta across all non-avoid contracts
    for chain-relative normalisation in _tier_score.
    """
    gammas = sorted([abs(s.gamma or 0) for s in contracts if s.gamma])
    thetas = sorted([abs(s.theta or 0) for s in contracts if s.theta])

    def pct90(lst):
        if not lst:
            return None
        return lst[min(int(len(lst) * 0.90), len(lst) - 1)]

    return {
        "gamma_ceil": max(pct90(gammas) or 0.0, 0.001),
        "theta_ceil": max(pct90(thetas) or 0.0, 0.001),
    }


# ── Tier scoring ──────────────────────────────────────────────────────────────

def _tier_score(
    s: StrikeAnalysis,
    target_price: float,
    tier: str,
    dte: int,
    gamma_ceil: float,
    theta_ceil: float,
    expiry_fit: float,
) -> float:
    """
    Composite [0, 1] score for a contract within its assigned tier.

    All components are independently normalised before weighting so no
    raw metric dominates by scale. Weights are tier-specific.
    Soft penalties are multiplicative (reduce score, never zero it).

    Tier goals
    ----------
    aggressive : maximum ROI leverage, fast gamma, strike near target
    balanced   : solid delta + good ROI with manageable theta decay
    safer      : high delta responsiveness, liquid fills, tight spreads
    """
    abs_delta = abs(s.delta or 0)
    gamma     = s.gamma or 0
    theta     = s.theta or 0
    roi       = s.estimated_roi_pct
    spread    = s.spread_pct
    liq       = s.liquidity_score
    strike    = s.strike

    # ── Normalise components to [0, 1] ───────────────────────────────────────
    delta_n   = min(abs_delta, 1.0)
    gamma_n   = min(gamma / gamma_ceil, 1.0)                  # chain-relative
    roi_n     = max(0.0, min(roi, 300.0)) / 300.0
    spread_n  = max(0.0, 1.0 - spread / 50.0)
    liq_n     = liq / 100.0

    # Target distance: how close is the strike to where price will land
    window        = max(target_price * 0.08, 1.0)
    target_dist_n = max(0.0, 1.0 - abs(strike - target_price) / window)

    # Theta efficiency: theta-per-delta-unit, chain-normalised
    # theta_ceil is the 90th-pct raw theta; convert to per-delta scale
    theta_eff_raw  = abs(theta) / max(abs_delta, 0.01)
    theta_eff_ceil = theta_ceil / 0.10   # typical delta is ~0.1 at the tails
    theta_n        = max(0.0, 1.0 - theta_eff_raw / max(theta_eff_ceil, 0.001))

    # Expiry fit: constant per chain but still enters tier weights
    fit_n = expiry_fit

    # DTE-adaptive theta weight for balanced:
    # short DTE → theta drags more → weight it higher
    theta_w = max(0.08, min(0.20, 12.0 / max(dte, 1)))

    # ── Weighted sum per tier ─────────────────────────────────────────────────
    if tier == "aggressive":
        raw = (
            roi_n         * 0.34
            + gamma_n     * 0.26
            + target_dist_n * 0.18
            + spread_n    * 0.12
            + liq_n       * 0.06
            + fit_n       * 0.04
        )
        # Soft penalties (multiplicative — never zeroes the score)
        if abs_delta < 0.10 and target_dist_n < 0.25:
            raw *= 0.60   # lottery-ticket OTM
        if roi < 40.0:
            raw *= 0.80   # poor payoff even for aggressive

    elif tier == "balanced":
        # Remaining weight after theta share
        base = 1.0 - theta_w
        raw = (
            roi_n         * (base * 0.26)
            + delta_n     * (base * 0.24)
            + liq_n       * (base * 0.22)
            + target_dist_n * (base * 0.19)
            + fit_n       * (base * 0.09)
            + theta_n     * theta_w
        )

    else:  # safer
        raw = (
            delta_n       * 0.30
            + liq_n       * 0.28
            + spread_n    * 0.22
            + roi_n       * 0.12
            + target_dist_n * 0.08
        )
        if roi < 12.0:
            raw *= 0.65   # deep ITM with negligible upside is capital-inefficient

    return max(0.0, raw)


# ── Classification ────────────────────────────────────────────────────────────

def _avoid_reasons(
    mid: float,
    max_premium: Optional[float],
    spread: float,
    oi: int,
    delta: float,
) -> List[str]:
    """
    Hard-reject rules only. Four simple gates.
    OTM distance and ROI are intentionally excluded — they are handled as
    soft penalties in _tier_score so tiers never go empty.
    """
    reasons = []
    if max_premium and mid > max_premium:
        reasons.append(f"Premium ${mid:.2f} exceeds max ${max_premium:.2f}")
    if spread > MAX_SPREAD_AVOID:
        reasons.append("Spread > 50 %")
    if oi < MIN_OI_AVOID:
        reasons.append("OI near zero")
    if abs(delta or 0) < MIN_DELTA_HARD:
        reasons.append(f"Delta negligible ({abs(delta or 0):.3f})")
    return reasons


def _assign_tiers_relative(
    contracts: List[StrikeAnalysis],
    target_price: float,
    dte: int,
    gamma_ceil: float,
    theta_ceil: float,
    expiry_fit: float,
) -> None:
    """
    Phase 1 — Delta anchor:
      Sort by abs(delta) desc; split into equal thirds.
        top third    → safer
        middle third → balanced
        bottom third → aggressive
      Ceiling division guarantees all three tiers fill for n ≥ 3.

    Phase 2 — Intra-tier refinement:
      Score each contract with _tier_score() using tier-specific weights.
      Score stored as s._score for _best() to consume.
    """
    if not contracts:
        return

    contracts.sort(key=lambda s: abs(s.delta or 0), reverse=True)
    n = len(contracts)
    safer_end    = max(1, -(-n // 3))                      # ceiling div
    balanced_end = max(safer_end + 1, n - (n // 3))

    for i, s in enumerate(contracts):
        if i < safer_end:
            s.tier = "safer"
        elif i < balanced_end:
            s.tier = "balanced"
        else:
            s.tier = "aggressive"

    for s in contracts:
        s._score = _tier_score(  # type: ignore[attr-defined]
            s, target_price, s.tier, dte, gamma_ceil, theta_ceil, expiry_fit
        )


# ── Badges ────────────────────────────────────────────────────────────────────

def _badges(
    delta: float, gamma: float, spread: float, oi: int,
    volume: int, iv: float, tier: str,
) -> List[str]:
    tags = []
    ad = abs(delta or 0)
    if ad >= 0.60:              tags.append("High Delta")
    elif ad >= 0.40:            tags.append("Responsive")
    if gamma and gamma >= 0.01: tags.append("Fast Gamma")
    if spread <= 5.0:           tags.append("Tight Spread")
    elif spread > 25.0:         tags.append("Wide Spread")
    if oi >= 500:               tags.append("Liquid")
    elif oi < 100:              tags.append("Illiquid")
    if iv > 0.60:               tags.append("IV Rich")
    elif 0 < iv < 0.30:         tags.append("IV Reasonable")
    if tier == "avoid":         tags.append("Avoid")
    return tags


# ── Main entry point ──────────────────────────────────────────────────────────

async def analyze_target_move(
    ticker: str,
    current_price: float,
    target_price: float,
    option_type: Literal["call", "put"],
    expiration: str,
    max_premium: Optional[float] = None,
    preferred_strike: Optional[float] = None,
    account_size: Optional[float] = None,
    risk_per_trade: Optional[float] = None,
) -> CalculatorResponse:

    ticker       = ticker.upper()
    price_change = target_price - current_price
    move_pct     = round(price_change / current_price * 100, 3)
    move_pct_abs = abs(move_pct)

    # Expiry metadata
    dte        = _dte(expiration)
    expiry_fit = _expiry_fit_score(dte, move_pct_abs)

    # Fetch chain for the selected expiration
    raw = await provider.get_option_chain_bulk(ticker, [expiration])

    # Filter: right type, non-zero mid, within ±15 % of current price
    relevant = [
        c for c in raw
        if c.get("option_type") == option_type
        and c.get("mid", 0) > 0
        and abs((c.get("strike", 0) - current_price) / current_price) <= 0.15
    ]

    if not relevant:
        return CalculatorResponse(
            ticker=ticker, current_price=current_price,
            target_price=target_price, move_pct=move_pct,
            option_type=option_type, expiration=expiration,
            dte=dte, expiry_fit_score=round(expiry_fit, 3),
            recommended_aggressive=None, recommended_balanced=None,
            recommended_safer=None, avoid_list=[], all_strikes=[],
        )

    relevant.sort(key=lambda c: c["strike"])
    analyzed: List[StrikeAnalysis] = []

    for c in relevant:
        strike = c["strike"]
        bid    = c.get("bid", 0.0)
        ask    = c.get("ask", 0.0)
        mid    = c.get("mid", 0.0)
        mark   = c.get("mark", mid)
        volume = c.get("volume", 0)
        oi     = c.get("open_interest", 0)
        iv     = c.get("implied_volatility", 0.0) or 0.0
        delta  = c.get("delta") or 0.0
        gamma  = c.get("gamma") or 0.0
        theta  = c.get("theta") or 0.0
        vega   = c.get("vega") or 0.0

        moneyness = round((strike - current_price) / current_price * 100, 3)
        intrinsic = _intrinsic_at_target(strike, target_price, option_type)
        est_val   = _estimated_value_at_target(
            mid, delta, gamma, price_change, intrinsic, move_pct_abs
        )
        roi = round((est_val - mid) / mid * 100, 2) if mid > 0 else 0.0

        if option_type == "call":
            breakeven      = round(strike + mid, 2)
            breakeven_move = round((breakeven - current_price) / current_price * 100, 3)
        else:
            breakeven      = round(strike - mid, 2)
            breakeven_move = round((current_price - breakeven) / current_price * 100, 3)

        spread  = _spread_pct(bid, ask, mid)
        liq     = _liquidity_score(oi, volume, spread)
        reasons = _avoid_reasons(mid, max_premium, spread, oi, delta)
        tier    = "avoid" if reasons else "balanced"   # placeholder; overwritten below
        badges  = _badges(delta, gamma, spread, oi, volume, iv, tier)
        max_ent = _ideal_max_entry(est_val, spread)
        ctrs    = _contracts_for_risk(max_ent, risk_per_trade)

        analyzed.append(StrikeAnalysis(
            strike=strike, expiration=expiration, option_type=option_type,
            bid=bid, ask=ask, mid=mid, mark=mark,
            volume=volume, open_interest=oi, implied_volatility=iv,
            delta=delta, gamma=gamma, theta=theta, vega=vega,
            moneyness_pct=moneyness, intrinsic_at_target=intrinsic,
            estimated_value_at_target=est_val, estimated_roi_pct=roi,
            breakeven=breakeven, breakeven_move_pct=breakeven_move,
            liquidity_score=liq, spread_pct=spread,
            tier=tier, avoid_reasons=reasons, badges=badges,
            ideal_max_entry=max_ent, contracts_for_risk=ctrs,
        ))

    # ── Relative classification ───────────────────────────────────────────────
    non_avoid  = [s for s in analyzed if s.tier != "avoid"]
    avoid_list = [s for s in analyzed if s.tier == "avoid"]

    stats = _chain_stats(non_avoid)
    _assign_tiers_relative(
        non_avoid, target_price, dte,
        stats["gamma_ceil"], stats["theta_ceil"], expiry_fit,
    )

    # Refresh badges now tiers are final
    for s in non_avoid:
        s.badges = _badges(
            s.delta or 0, s.gamma or 0, s.spread_pct,
            s.open_interest, s.volume, s.implied_volatility, s.tier,
        )

    # Preferred-strike annotation
    if preferred_strike:
        for s in analyzed:
            if abs(s.strike - preferred_strike) < 0.5:
                s.badges.append("Preferred")

    def _best(tier_name: str) -> Optional[StrikeAnalysis]:
        candidates = [s for s in non_avoid if s.tier == tier_name]
        if not candidates:
            return None
        return max(candidates, key=lambda s: getattr(s, "_score", 0.0))

    return CalculatorResponse(
        ticker=ticker,
        current_price=current_price,
        target_price=target_price,
        move_pct=move_pct,
        option_type=option_type,
        expiration=expiration,
        dte=dte,
        expiry_fit_score=round(expiry_fit, 3),
        recommended_aggressive=_best("aggressive"),
        recommended_balanced=_best("balanced"),
        recommended_safer=_best("safer"),
        avoid_list=sorted(avoid_list, key=lambda s: abs(s.moneyness_pct))[:8],
        all_strikes=sorted(analyzed, key=lambda s: s.estimated_roi_pct, reverse=True),
    )
