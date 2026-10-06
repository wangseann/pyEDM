"""Isolate the external suite's mutable bundled sample data between tests."""
import pytest
import pyEDM


@pytest.fixture(autouse=True)
def fresh_sample_data():
    # test_simplex7 deliberately inserts NaNs into the global Lorenz5D frame.
    original = pyEDM.sampleData
    pyEDM.sampleData = {name: frame.copy(deep=True) for name, frame in original.items()}
    try:
        yield
    finally:
        pyEDM.sampleData = original
