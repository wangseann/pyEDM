"""Audit changed EDim goldens with an exhaustive neighbor calculation on CI."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyEDM


CASES = {
    1: ("Lorenz5D", dict(columns="V1", target="V1", lib=[1, 1000], pred=[1, 1000], Tp=5, tau=-5)),
    3: ("SumFlow_1980-2005", dict(columns="S12.C.D.S333", target="S12.C.D.S333", lib=[1, 1379], pred=[1, 1379], exclusionRadius=5)),
    4: ("SumFlow_1980-2005", dict(columns="S12.C.D.S333", target="S12.C.D.S333", lib=[1, 800], pred=[801, 1379], exclusionRadius=5)),
    6: ("Lorenz5D", dict(columns="V1", target="V1", lib=[1, 1000], pred=[1, 1000], Tp=-5, tau=5)),
    7: ("Lorenz5D", dict(columns="V1", target="V4", lib=[1, 1000], pred=[1, 1000], Tp=5, tau=-5, exclusionRadius=20)),
}


def exhaustive_projection(obj):
    """Check neighbor selection/projection, using the API's embedding and row domain.

    This deliberately shares no KDTree, selection helper, or projection code.
    It does not independently validate embedding or library-range construction.
    """
    embedding = obj.Embedding.to_numpy()
    library = np.asarray(obj.lib_i)
    target = obj.targetVec[:, 0]
    predictions = []
    ties = deficient = 0
    for row in obj.pred_i:
        candidates = library[np.abs(library - row) > obj.exclusionRadius]
        distances = np.sqrt(np.sum((embedding[candidates] - embedding[row]) ** 2, axis=1))
        order = sorted(range(len(candidates)),
                       key=lambda i: (distances[i], abs(int(candidates[i]) - row), candidates[i]))
        chosen = np.asarray(order[:obj.knn], dtype=int)
        deficient += len(chosen) < obj.knn
        if len(order) > obj.knn:
            ties += distances[order[obj.knn - 1]] == distances[order[obj.knn]]
        if not len(chosen):
            predictions.append(np.nan)
            continue
        distance = distances[chosen]
        weights = np.exp(-distance / max(float(distance.min()), 1e-6))
        predictions.append(np.dot(weights, target[candidates[chosen] + obj.Tp]) / weights.sum())
    return np.asarray(predictions), int(ties), int(deficient)


def diagnose(root):
    records = []
    for case, (dataset, kwargs) in CASES.items():
        golden = pd.read_csv(root / f"external/EDM_MDE_validation/ValidOutput/EDim_{case}_valid.csv")
        for dimension in range(1, 11):
            obj = pyEDM.Simplex(pyEDM.sampleData[dataset].copy(deep=True), E=dimension,
                                kdWorkers=1, returnObject=True, **kwargs)
            reference, ties, deficient = exhaustive_projection(obj)
            # dot() and the production multiply/sum accumulate in different orders.
            np.testing.assert_allclose(obj.projection, reference,
                                       rtol=32 * np.finfo(float).eps, atol=1e-12, equal_nan=True)
            max_error = float(np.nanmax(np.abs(reference - obj.projection)))
            current = pyEDM.ComputeError(obj.Projection.Observations, obj.Projection.Predictions)["rho"]
            observation_rows = np.asarray(obj.pred_i) + obj.Tp
            paired = (observation_rows >= 0) & (observation_rows < len(obj.targetVec))
            observations = obj.targetVec[observation_rows[paired], 0]
            predictions = reference[paired]
            finite = np.isfinite(observations) & np.isfinite(predictions)
            assert finite.sum() > 5
            reference_rho = float(np.round(np.corrcoef(observations[finite], predictions[finite])[0, 1], 6))
            assert current == reference_rho, (case, dimension, current, reference_rho)
            # Isolate the tie-policy change; retain current exclusion safeguards.
            obj.tieBreak = False
            obj.FindNeighbors()
            obj.Project()
            obj.FormatProjection()
            legacy = pyEDM.ComputeError(obj.Projection.Observations, obj.Projection.Predictions)["rho"]
            record = dict(case=case, E=dimension, golden=float(golden.rho.iloc[dimension - 1]),
                          current=float(current), reference_rho=reference_rho,
                          without_tie_policy=float(legacy),
                          boundary_tie_rows=ties, deficient_rows=deficient,
                          exhaustive_max_error=max_error)
            records.append(record)
            print(json.dumps(record), flush=True)
    (root / "test-results/edim-diagnostics.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    diagnose(Path(__file__).resolve().parents[1])
