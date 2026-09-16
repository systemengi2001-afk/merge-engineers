from __future__ import annotations

# Product invariants learned from regression/correction sessions.  These are executable
# requirements, not strategy labels: future versions must preserve them or update tests
# with an explicit migration note.
EDUCATION_CONTRACT = {
    "version": "v6.10",
    "principles": [
        "final_ranking_uses_points_ev_not_ukeire_alone",
        "ordinary_dora_and_aka_dora_are_carried_through_future_states",
        "actual_dora_input_must_be_converted_to_indicator_before_scoring",
        "future_winability_and_tenpai_shape_matter_beyond_current_ukeire",
        "never_claim_uncomputed_or_unverified_accuracy",
        "math_engine_handles_calculable_values_ai_handles_hidden_information_and_strategy",
        "third_party_ai_and_gpl_outputs_obey_commercial_license_boundaries",
    ],
    "regressions": {
        "future_shape": "23567p123456678s / sanma_all_fives / actual dora 8p",
        "red_vs_plain_discard": "2446789p2335678s / sanma_all_fives / actual dora 9p",
        "bad_shanten_regression": "22455578p123577s / sanma_all_fives / actual dora 3p",
        "dora_ev": "234566789p57779s / sanma_all_fives / actual dora 9s",
    },
}

def education_contract() -> dict:
    return {"version": EDUCATION_CONTRACT["version"], "principles": list(EDUCATION_CONTRACT["principles"]), "regressions": dict(EDUCATION_CONTRACT["regressions"])}
