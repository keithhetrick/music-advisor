from music_advisor.host.policy import Policy
from music_advisor.host.kpi import hci_v1

def test_hci_caps_at_host_only():
    policy = Policy(cap_audio=0.58)
    axes = [0.62]*6
    assert hci_v1(axes, policy) == 0.58

def test_hci_mean_when_below_cap():
    policy = Policy(cap_audio=0.58)
    axes = [0.40, 0.45, 0.50, 0.55, 0.50, 0.45]
    expected = sum(axes) / 6.0
    assert abs(hci_v1(axes, policy) - expected) < 1e-9
