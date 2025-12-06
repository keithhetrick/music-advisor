def map_era_timeless(features, hci):
    return {"era": "timeless", "lineage": ["classic"], "notes": []}

def map_era_trend_aware(features, hci, trend):
    return {"era": "trend-aware", "lineage": ["classic","current"], "notes": ["uses snapshot"]}
