# Testing this fork

The CI workflow runs on pull requests, pushes to `master`, and manual dispatch.
It installs the checked-out source with `python -m pip install --editable ".[test]"`.
Every test job verifies the import path and records the checkout commit, Python
version, and installed dependencies alongside its JUnit report.

| Suite | Coverage | Python |
| --- | --- | --- |
| Core | All 55 tests in `src/pyEDM/tests` | 3.10, 3.11, 3.14 |
| Custom | 14 cases: literal embeddings, invalid requests, hand-calculated Simplex weights, explicit tie/exclusion results, affine S-Map coefficients, `noTime`, seeded serial/parallel CCM with both worker transports | 3.10, 3.11, 3.14 |
| Applications | All tests in `src/pyEDM/apps/tests`, with the three complete CCM matrix regressions in separate jobs | 3.11 |
| Package | Build wheel and sdist, check metadata, install the wheel, and forecast using bundled data outside the checkout | 3.11 |

Core and application tests run in separate processes from their own directories:
their `conftest.py` modules share a name and some fixtures use relative paths.
The CCM matrix jobs retain the full upstream datasets, sample counts, and assertions.
All numerical execution and its datasets remain on GitHub runners.

To reproduce the suites in an environment with a complete checkout and dependencies:

```sh
python -m pip install --editable ".[test]"
python -m pytest -q tests
(cd src/pyEDM/tests && python -m pytest -q .)
(cd src/pyEDM/apps/tests && python -m pytest -q .)
```

The extended validation workflow runs on `master`, `ci/**` branches, weekly, and
manual dispatch. It checks out `pao-unit/EDM_MDE_validation` at
`bae270e568dd52830f57ab661380e700097aa58d` and runs its 31 Simplex, S-Map, CCM,
and embedding-dimension tests against this fork. It does not install a different
pyEDM release in place of the checkout.

## External reference compatibility

The external suite predates the neighbor changes in
[9ea97212](https://github.com/SugiharaLab/pyEDM/commit/9ea97212c064fab529e53a9ca30b1a251b0c4bec)
and [4ad6b049](https://github.com/SugiharaLab/pyEDM/commit/4ad6b049951af5052b00af21985acc74902d9bf8).
The former selects equal-distance Simplex neighbors by temporal proximity, then
original row; the latter prevents excluded/self neighbors from being reinstated.
These changes affect `EmbedDimension`, which calls Simplex for each E.

`ci/external_fixtures.py` provides fresh sample-data copies for each test because
`test_simplex7` inserts NaNs into the shared Lorenz frame. For EDim cases 1, 3, 4,
6, and 7 only, it supplies frozen pyEDM 2.5.8 curves from `ci/edim_reference.py`.
The original pinned CSVs remain untouched. The adapter preserves their E values
and schema, retains the tests' exact equality, and rejects other pyEDM versions
until their expectations are reviewed. There are no skips or expected failures.

Before accepting those curves, [this diagnostic run](https://github.com/wangseann/pyEDM/actions/runs/37404974853)
verified all 50 case/E combinations with exhaustive distance sorting and weighted
predictions, independent observation alignment, and Pearson correlation. Its
diagnostic step passed; its original external tests still reported the five
historical-curve failures. The maximum raw prediction difference was
1.37e-12 (floating-point accumulation); all rounded correlations agreed exactly.

The diagnostic remains a required CI step and compares its independently computed
correlations to the frozen curves. It shares the package's embedding and library
row domain, so it independently checks neighbor selection, projection, alignment,
and correlation rather than claiming an independent implementation of the whole
API. Literal embedding tests and the upstream suite cover those other stages.
A pinned historical neighbor implementation is loaded only by the diagnostic to
attribute the old/new differences; application tests always use the current fork.
The diagnostic JSON is retained with the environment and test reports.

[The historical comparison](https://github.com/wangseann/pyEDM/actions/runs/37405189665)
reproduced all 50 original correlations exactly using the pre-change neighbor
function. Case 3 at E=1 included two prediction rows where that old function
reintroduced excluded neighbors. The diagnostic also continues to verify those
historical correlations against the untouched CSVs, separately from the current
fork's exhaustive-reference checks.

CI uses Linux CPU runners. Dependencies are resolved within the package's declared
ranges; each run's artifacts record the exact versions. A passing run therefore
certifies the recorded checkout and environment, not every platform or dependency
combination. Artifacts include test reports and environment information; package
artifacts are built for inspection and are not published to PyPI.
