def emotion_scan_timeless(features, hci):
    return {"mode": "timeless", "vectors": {"heart": 0.9}, "notes": []}

def emotion_scan_trend_aware(features, hci, trend):
    return {"mode": "trend-aware", "vectors": {"heart": 0.9}, "notes": ["uses snapshot"]}
