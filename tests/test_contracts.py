"""Independent numerical examples and execution-mode contracts for pyEDM."""
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest
import pyEDM as EDM


@pytest.mark.parametrize("tau, expected", [
    (-1, [[10, np.nan, np.nan], [20, 10, np.nan], [30, 20, 10], [40, 30, 20]]),
    (1, [[10, 20, 30], [20, 30, 40], [30, 40, np.nan], [40, np.nan, np.nan]]),
])
def test_embedding_has_literal_lag_values(tau, expected):
    data = pd.DataFrame({"Time": [1, 2, 3, 4], "x": [10, 20, 30, 40]})
    before = data.copy(deep=True)
    result = EDM.Embed(data, E=3, tau=tau, columns="x")
    np.testing.assert_allclose(result.to_numpy(), expected, rtol=0, atol=0, equal_nan=True)
    assert_frame_equal(data, before)


@pytest.mark.parametrize("kwargs", [{"E": 0}, {"tau": 0}, {"columns": "absent"}])
def test_embedding_rejects_invalid_requests(kwargs):
    options = dict(E=2, tau=-1, columns="x")
    options.update(kwargs)
    with pytest.raises(RuntimeError):
        EDM.Embed(pd.DataFrame({"Time": [1, 2, 3], "x": [1, 2, 3]}), **options)


def test_simplex_matches_hand_calculated_distance_weights():
    # Neighbors of 2.25 are 2 and 3, with distances .25 and .75.
    # Targets 7 and 9 receive weights exp(-1) and exp(-3).
    data = pd.DataFrame({"Time": [1, 2, 3, 4, 5, 6],
                         "x": [0., 1., 2., 3., 2.25, 2.75], "y": [3., 5., 7., 9., 123., 456.]})
    result = EDM.Simplex(data, columns="x", target="y", lib=[1, 4], pred=[5, 6],
                         E=1, Tp=0, knn=2, kdWorkers=1)
    assert result["Predictions"].iloc[0] == pytest.approx(7.238405844044235, rel=0, abs=1e-12)
    assert result["Observations"].iloc[0] == 123.


@pytest.mark.parametrize("theta", [0., 2.])
def test_smap_recovers_known_affine_relationship(theta):
    x = np.linspace(-2, 3, 40)
    data = pd.DataFrame({"Time": np.arange(1, 41), "x": x, "y": 2 * x + 3})
    before = data.copy(deep=True)
    result = EDM.SMap(data, columns="x", target="y", lib=[1, 30], pred=[31, 40],
                      E=1, Tp=0, theta=theta, embedded=True, kdWorkers=1)
    np.testing.assert_allclose(result["predictions"]["Predictions"], 2 * x[30:] + 3,
                               rtol=0, atol=1e-10)
    np.testing.assert_allclose(result["coefficients"]["C0"], 3., rtol=0, atol=1e-10)
    np.testing.assert_allclose(result["coefficients"]["∂y/∂x"], 2., rtol=0, atol=1e-10)
    assert_frame_equal(data, before)


@pytest.mark.parametrize("method", ["Simplex", "SMap"])
def test_no_time_preserves_predictions_and_first_data_column(method):
    t = np.arange(80)
    data = pd.DataFrame({"Time": t + 1, "x": np.sin(t / 5), "y": np.cos(t / 7)})
    values = data.drop(columns="Time")
    before = values.copy(deep=True)
    options = dict(columns="x", target="y", lib=[1, 50], pred=[55, 75], E=2, Tp=1, kdWorkers=1)
    function = getattr(EDM, method)
    if method == "SMap":
        options["theta"] = 2.
    with_time = function(data, **options)
    without_time = function(values, noTime=True, **options)
    if method == "SMap":
        with_time, without_time = with_time["predictions"], without_time["predictions"]
    assert np.isfinite(with_time["Predictions"]).sum() == 21
    assert_frame_equal(with_time, without_time, check_dtype=False, rtol=0, atol=1e-12)
    assert_frame_equal(values, before)


@pytest.mark.parametrize("shared_mb", [0., 1000.])
def test_seeded_ccm_is_identical_serial_parallel_and_repeated(shared_mb):
    # Both shared-memory and pickle worker transports must preserve the estimator.
    t = np.arange(80)
    data = pd.DataFrame({"Time": t + 1, "x": np.sin(t / 5), "y": np.cos(t / 7)})
    before = data.copy(deep=True)
    options = dict(columns="x", target="y", E=2, Tp=1, libSizes=[15, 30, 45, 60],
                   sample=8, seed=123, mpMethod="spawn", sharedMB=shared_mb)
    serial = EDM.CCM(data, parallel=False, **options)
    parallel = EDM.CCM(data, parallel=2, **options)
    repeated = EDM.CCM(data, parallel=2, **options)
    assert serial["LibSize"].tolist() == [15, 30, 45, 60]
    assert np.isfinite(serial.iloc[:, 1:].to_numpy()).all()
    assert_frame_equal(serial, parallel, rtol=0, atol=1e-12)
    assert_frame_equal(parallel, repeated, rtol=0, atol=1e-12)
    assert_frame_equal(data, before)
