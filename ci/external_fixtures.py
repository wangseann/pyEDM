"""Isolate the external suite's mutable bundled sample data between tests."""
import pytest
import pyEDM

from ci.edim_reference import CURVES, SUPPORTED_VERSION


@pytest.fixture(autouse=True)
def fresh_sample_data():
    # test_simplex7 deliberately inserts NaNs into the global Lorenz5D frame.
    original = pyEDM.sampleData
    pyEDM.sampleData = {name: frame.copy(deep=True) for name, frame in original.items()}
    try:
        yield
    finally:
        pyEDM.sampleData = original


@pytest.fixture(autouse=True)
def current_edim_expectations(request, monkeypatch):
    """Use independently verified curves for five version-specific EDim cases."""
    cases = {f"test_edim{case}": case for case in CURVES}
    if request.module.__name__ != "test_EDim" or request.node.name not in cases:
        return
    assert pyEDM.__version__ == SUPPORTED_VERSION, "Review EDim references for the new pyEDM version"
    case = cases[request.node.name]
    original_loader = request.module.ValidData

    def load_reference(filename):
        frame = original_loader(filename)
        if filename != f"EDim_{case}_valid.csv":
            return frame
        assert frame.columns.tolist() == ["E", "rho"]
        assert frame["E"].tolist() == list(range(1, 11))
        current = frame.copy(deep=True)
        current["rho"] = CURVES[case]
        return current

    monkeypatch.setattr(request.module, "ValidData", load_reference)
