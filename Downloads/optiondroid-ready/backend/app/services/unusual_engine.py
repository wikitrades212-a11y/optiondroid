"""
Unusual Options Scoring Engine

Computes an unusual_score (0–100) for each contract using a weighted
combination of six independent signals. Each signal is normalized to [0,1]
before weighting so no single raw metric dominates.

WEIGHTS (must sum to 1.0):
  vol_oi_norm        0.30   Primary signal: directional aggression today
  vol_notional_norm  0.20   Dollar flow right now (size of bets)
  oi_notional_norm   0.10   Established position size
  expiry_pct_rank    0.20   How unusual vs same-expiry peers
  global_pct_rank    0.10   How unusual vs entire chain
  atm_proximity      0.10   Prefer near-ATM unless premium is extreme

REASON TAGS (descriptive, not mutually exclusive):
  High Vol/OI          vol_oi_ratio > 5× or top 5% per expiry
  Big Premium          vol_notional > $500k or oi_notional > $5M
  Expiry Concentration expiry_pct_rank > 0.93
  Call Dominance       call with global_pct_rank > 0.90
  Put Hedge            put with oi_notional > $5M and vol_oi_ratio < 2
  Near ATM Aggression  moneyness within 2% of spot
  Far OTM Lottery      moneyness > 10% OTM with high vol_oi_ratio
"""

import math
import logging
from typing import List, Tuple

import numpy as np

from app.models.options import OptionContract

logger = logging.getLogger(__name__)

# ── Weights ──────────────────────────────────────────────────────────────────
WEIGHTS = {
    "vol_oi_norm":       0.30,
    "vol_notional_norm": 0.20,
    "oi_notional_norm":  0.10,
    "expiry_pct_rank":   0.20,
    "global_pct_rank":   0.10,
    "atm_proximity":     0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

# ── Thresholds ────────────────────────────────────────────────────────────────
VOL_OI_HIGH         = 5.0        # flag "High Vol/OI" above this ratio
BIG_PREMIUM_VOL     = 500_000    # $500k vol_notional
BIG_PREMIUM_OI      = 5_000_000  # $5M oi_notional
EXPIRY_CONC_RANK    = 0.93       # top 7% within expiry = Expiry Concentration
CALL_DOM_RANK       = 0.90       # top 10% globally = Call Dominance
PUT_HEDGE_OI        = 5_000_000  # $5M oi_notional
PUT_HEDGE_VOL_OI    = 2.0        # low vol/oi = defensive positioning
ATM_PCT             = 0.02       # within 2% of spot
OTM_PCT             = 0.10       # more than 10% OTM


# ── Helpers ───────────────────────────────────────────────────────────────────

def _percentile_rank(value: float, arr: np.ndarray) -> float:
    """Fraction of arr that is <= value. Returns [0, 1]."""
    if len(arr) == 0:
        return 0.0
    return float(np.mean(arr <= value))


def _minmax_norm(arr: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1]. Returns zeros if range is zero."""
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-9:
        return np.zeros_like(arr, dtype=float)
    return (arr - lo) / (hi - lo)


def _atm_score(moneyness: float) -> float:
    """
    Return [0, 1] based on proximity to ATM.
    1.0 = exactly ATM, decays to 0 at >20% OTM.
    Uses a Gaussian-ish decay so near-ATM gets most credit.
    """
    distance = abs(moneyness - 1.0)
    return math.exp(-((distance / 0.07) ** 2))


# ── Main entry point ──────────────────────────────────────────────────────────

def score_contracts(
    contracts: List[OptionContract],
    underlying_price: float,
) -> List[OptionContract]:
    """
    Annotate each contract with unusual_score, unusual_rank, reason_tags.
    Modifies contracts in-place and returns them sorted by unusual_score desc.
    """
    if not contracts:
        return contracts

    # Build per-expiry groups for relative ranking
    expiry_groups: dict[str, List[int]] = {}
    for i, c in enumerate(contracts):
        expiry_groups.setdefault(c.expiration, []).append(i)

    # Raw signal arrays (global)
    vol_oi_arr   = np.array([c.vol_oi_ratio    for c in contracts], dtype=float)
    vol_not_arr  = np.array([c.vol_notional    for c in contracts], dtype=float)
    oi_not_arr   = np.array([c.oi_notional     for c in contracts], dtype=float)

    # Global min-max normalization
    vol_oi_norm  = _minmax_norm(vol_oi_arr)
    vol_not_norm = _minmax_norm(vol_not_arr)
    oi_not_norm  = _minmax_norm(oi_not_arr)

    scores: List[float] = []

    for i, contract in enumerate(contracts):
        # ── Signal 1: vol/oi normalized ──────────────────────────────────────
        s_vol_oi = vol_oi_norm[i]

        # ── Signal 2: vol notional normalized ────────────────────────────────
        s_vol_not = vol_not_norm[i]

        # ── Signal 3: oi notional normalized ─────────────────────────────────
        s_oi_not = oi_not_norm[i]

        # ── Signal 4: percentile rank within same expiry ──────────────────────
        expiry_idxs = expiry_groups[contract.expiration]
        expiry_vol_oi = vol_oi_arr[expiry_idxs]
        s_expiry = _percentile_rank(contract.vol_oi_ratio, expiry_vol_oi)

        # ── Signal 5: global percentile rank ──────────────────────────────────
        s_global = _percentile_rank(contract.vol_oi_ratio, vol_oi_arr)

        # ── Signal 6: ATM proximity ───────────────────────────────────────────
        moneyness = (contract.strike / underlying_price) if underlying_price > 0 else 1.0
        contract.moneyness = round(moneyness, 4)
        contract.underlying_price = underlying_price
        s_atm = _atm_score(moneyness)

        # ── Weighted sum → 0–100 ──────────────────────────────────────────────
        raw = (
            WEIGHTS["vol_oi_norm"]       * s_vol_oi   +
            WEIGHTS["vol_notional_norm"] * s_vol_not  +
            WEIGHTS["oi_notional_norm"]  * s_oi_not   +
            WEIGHTS["expiry_pct_rank"]   * s_expiry   +
            WEIGHTS["global_pct_rank"]   * s_global   +
            WEIGHTS["atm_proximity"]     * s_atm
        )
        scores.append(raw)

        # ── Reason tags ───────────────────────────────────────────────────────
        tags: List[str] = []
        distance_pct = abs(moneyness - 1.0)

        if contract.vol_oi_ratio >= VOL_OI_HIGH or s_expiry >= EXPIRY_CONC_RANK:
            tags.append("High Vol/OI")

        if (contract.vol_notional >= BIG_PREMIUM_VOL or
                contract.oi_notional >= BIG_PREMIUM_OI):
            tags.append("Big Premium")

        if s_expiry >= EXPIRY_CONC_RANK:
            tags.append("Expiry Concentration")

        if contract.option_type == "call" and s_global >= CALL_DOM_RANK:
            tags.append("Call Dominance")

        if (contract.option_type == "put" and
                contract.oi_notional >= PUT_HEDGE_OI and
                contract.vol_oi_ratio < PUT_HEDGE_VOL_OI):
            tags.append("Put Hedge")

        if distance_pct <= ATM_PCT and contract.volume > 0:
            tags.append("Near ATM Aggression")

        if (distance_pct >= OTM_PCT and
                contract.vol_oi_ratio >= VOL_OI_HIGH and
                contract.option_type == "call"):
            tags.append("Far OTM Lottery")

        if not tags and raw > 0.4:
            tags.append("Unusual Activity")

        contract.reason_tags = tags

    # Normalize scores to 0–100
    max_score = max(scores) if scores else 1.0
    for i, contract in enumerate(contracts):
        contract.unusual_score = round((scores[i] / max_score) * 100, 2)

    # Rank (1 = highest)
    ranked = sorted(range(len(contracts)), key=lambda i: contracts[i].unusual_score, reverse=True)
    for rank, idx in enumerate(ranked, start=1):
        contracts[idx].unusual_rank = rank

    return sorted(contracts, key=lambda c: c.unusual_score, reverse=True)
