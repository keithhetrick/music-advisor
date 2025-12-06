def build_optimization_plan_timeless(features, hci):
    return {"plan": "timeless", "actions": ["keep it human", "protect warmth"]}

def build_optimization_plan_trend_informed(features, hci, trend, creator_pulse):
    return {"plan": "trend-informed", "actions": ["align to current pulse"], "notes": ["uses snapshot", "creator ok" if creator_pulse else ""]}
