"""Apollo 15 TG11B: only its 1975 data enter its equilibrium temperature.

The 1971-1974 values of the Apollo 15 probe 1 upper gradient bridge were
faulty in the original archive (Nagihara et al., 2018, p. 1131) and are
corrected in the St. Clair et al. (2020) record used here. The window rule
puts TG11B's window in 1975 anyway, 1 May to 30 June 1975, two lunations;
extract_sensor_stability guards it as a precaution.
"""
from lunar.apollo_helpers import A15_TG11_FIRST_VALID, extract_sensor_stability


def test_a15_tg11b_window_is_in_the_reprocessed_1975_data():
    o = extract_sensor_stability("a15", 80)
    s = next(s for s in o["sensors"] if s["sensor"] == "TG11B")
    tab = o["d1"][o["d1"]["sensor"] == "TG11B"]
    i0 = round(s["tail_start_frac"] * len(tab))
    first, last = str(tab["time_iso"][i0])[:10], str(tab["time_iso"][-1])[:10]
    assert first >= A15_TG11_FIRST_VALID
    assert (first, last) == ("1975-05-01", "1975-06-30")
    assert s["n_tail"] == 11579
