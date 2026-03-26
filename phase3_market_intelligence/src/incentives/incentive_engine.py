"""
Incentive & Penalty Engine — Step 3.5
========================================
Tiered reward system for low emitters and escalating penalties
for excess emissions. Integrates with CarbonToken for bonus mints
and penalty burns.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.config import (
    INCENTIVE_TIERS, PENALTY_ESCALATION_RATE,
    MAX_PENALTY_MULTIPLIER, EARLY_ADOPTER_BONUS,
)

logger = logging.getLogger("incentives.engine")


class IncentiveEngine:
    """
    Incentive and penalty mechanism for emission behavior.

    Reward tiers (based on avg reduction %):
      - Gold:   ≥20% reduction → 1.5× bonus multiplier
      - Silver: ≥10% reduction → 1.25× bonus
      - Bronze: ≥5%  reduction → 1.1× bonus

    Penalties:
      - Escalating penalties for consecutive excess emissions
      - Non-compliance penalty burn from token balance

    Integration:
      - Bonus credits minted directly to participant via CarbonToken
      - Penalties burned from participant balance
    """

    def __init__(self, token_manager, blockchain):
        self._token = token_manager
        self._chain = blockchain

        self._participant_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_credits_earned": 0.0,
                "total_penalties": 0.0,
                "consecutive_violations": 0,
                "tier": "none",
                "readings_count": 0,
                "reduction_pcts": [],
                "bonus_total": 0.0,
                "is_early_adopter": False,
            }
        )
        self._early_adopter_count = 0
        self._total_bonuses_minted = 0.0
        self._total_penalties_burned = 0.0
        self._actions_log: List[Dict[str, Any]] = []

    def register_early_adopter(self, participant_id: str) -> Dict[str, Any]:
        """Register participant as early adopter (first 10 get bonus)."""
        stats = self._participant_stats[participant_id]
        if self._early_adopter_count < 10 and not stats["is_early_adopter"]:
            stats["is_early_adopter"] = True
            self._early_adopter_count += 1
            return {
                "status": "registered",
                "early_adopter": True,
                "bonus_multiplier": EARLY_ADOPTER_BONUS,
                "adopter_number": self._early_adopter_count,
            }
        return {"status": "registered", "early_adopter": False}

    def evaluate_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a reading and apply incentives or penalties.

        Args:
            reading: Must have facility_id, credits (dict with reduction_pct,
                     credits_earned, credits_penalty).

        Returns:
            {action, tier, bonus_credits, penalty_amount, new_balance}
        """
        fid = reading.get("facility_id", "unknown")
        credits = reading.get("credits")
        stats = self._participant_stats[fid]
        stats["readings_count"] += 1

        result = {
            "facility_id": fid,
            "action": "none",
            "tier": stats["tier"],
            "bonus_credits": 0.0,
            "penalty_amount": 0.0,
        }

        if not credits or not isinstance(credits, dict):
            return result

        reduction_pct = credits.get("reduction_pct", 0.0)
        earned = credits.get("credits_earned", 0.0)
        penalty = credits.get("credits_penalty", 0.0)

        stats["reduction_pcts"].append(reduction_pct)
        stats["total_credits_earned"] += earned

        # ── Determine tier ────────────────────────────────────────────
        recent_reductions = stats["reduction_pcts"][-20:]
        avg_reduction = sum(recent_reductions) / max(len(recent_reductions), 1)

        new_tier = "none"
        for tier_name in ["gold", "silver", "bronze"]:
            tier_cfg = INCENTIVE_TIERS[tier_name]
            if avg_reduction >= tier_cfg["min_reduction_pct"]:
                new_tier = tier_name
                break
        stats["tier"] = new_tier

        # ── Apply reward bonus ────────────────────────────────────────
        if earned > 0 and new_tier != "none":
            tier_cfg = INCENTIVE_TIERS[new_tier]
            bonus_multiplier = tier_cfg["bonus_multiplier"]

            # Early adopter extra bonus
            if stats["is_early_adopter"]:
                bonus_multiplier *= EARLY_ADOPTER_BONUS

            bonus_credits = round(earned * (bonus_multiplier - 1.0), 6)

            if bonus_credits > 0:
                # Mint bonus tokens
                try:
                    import hashlib, json, time
                    bonus_hash = hashlib.sha256(
                        json.dumps({
                            "type": "incentive_bonus",
                            "facility_id": fid,
                            "timestamp": time.time(),
                            "bonus": bonus_credits,
                        }, sort_keys=True).encode()
                    ).hexdigest()[:16]

                    self._token.mint(fid, bonus_credits, bonus_hash)
                    self._chain.add_block({
                        "type": "incentive_bonus",
                        "facility_id": fid,
                        "tier": new_tier,
                        "bonus_credits": bonus_credits,
                        "multiplier": bonus_multiplier,
                    })

                    stats["bonus_total"] += bonus_credits
                    self._total_bonuses_minted += bonus_credits
                    stats["consecutive_violations"] = 0

                    result["action"] = "reward"
                    result["tier"] = new_tier
                    result["bonus_credits"] = bonus_credits

                    self._actions_log.append({
                        "type": "reward", "facility_id": fid,
                        "tier": new_tier, "bonus": bonus_credits,
                    })
                except ValueError:
                    pass  # duplicate hash or other error

        # ── Apply penalties ───────────────────────────────────────────
        elif penalty > 0:
            stats["consecutive_violations"] += 1
            escalation = 1.0 + (
                stats["consecutive_violations"] * PENALTY_ESCALATION_RATE
            )
            escalation = min(escalation, MAX_PENALTY_MULTIPLIER)
            penalty_amount = round(penalty * escalation, 6)

            # Burn tokens if balance available
            balance = self._token.balance_of(fid)
            burn_amount = min(penalty_amount, balance)
            if burn_amount > 0:
                try:
                    self._token.burn(fid, burn_amount)
                    self._chain.add_block({
                        "type": "penalty_burn",
                        "facility_id": fid,
                        "penalty_amount": penalty_amount,
                        "burned": burn_amount,
                        "consecutive_violations": stats["consecutive_violations"],
                    })
                    self._total_penalties_burned += burn_amount
                except ValueError:
                    burn_amount = 0.0

            stats["total_penalties"] += penalty_amount
            result["action"] = "penalty"
            result["penalty_amount"] = penalty_amount

            self._actions_log.append({
                "type": "penalty", "facility_id": fid,
                "amount": penalty_amount, "burned": burn_amount,
                "consecutive": stats["consecutive_violations"],
            })
        else:
            stats["consecutive_violations"] = 0

        return result

    def get_participant_tier(self, participant_id: str) -> str:
        return self._participant_stats[participant_id]["tier"]

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Return participants ranked by tier and total bonus."""
        tier_rank = {"gold": 0, "silver": 1, "bronze": 2, "none": 3}
        entries = []
        for pid, stats in self._participant_stats.items():
            entries.append({
                "participant_id": pid,
                "tier": stats["tier"],
                "bonus_total": round(stats["bonus_total"], 4),
                "total_earned": round(stats["total_credits_earned"], 4),
                "violations": stats["consecutive_violations"],
            })
        entries.sort(key=lambda x: (tier_rank.get(x["tier"], 4), -x["bonus_total"]))
        return entries

    def get_summary(self) -> Dict[str, Any]:
        tier_counts = defaultdict(int)
        for stats in self._participant_stats.values():
            tier_counts[stats["tier"]] += 1
        return {
            "participants": len(self._participant_stats),
            "tier_distribution": dict(tier_counts),
            "total_bonuses_minted": round(self._total_bonuses_minted, 4),
            "total_penalties_burned": round(self._total_penalties_burned, 4),
            "early_adopters": self._early_adopter_count,
            "total_actions": len(self._actions_log),
        }
