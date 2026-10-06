# Testing this fork

The CI workflow runs on pull requests, pushes to `master`, and manual dispatch.
It installs the checked-out source with `python -m pip install --editable ".[test]"`.
Every test job verifies the import path and records the checkout commit, Python
version, and installed dependencies alongside its JUnit report.

| Suite | Coverage | Python |
| --- | --- | --- |
| Core | All tests in `src/pyEDM/tests` | 3.10, 3.11, 3.14 |
| Custom | Literal embeddings, invalid requests, hand-calculated Simplex weights, affine S-Map coefficients, `noTime`, seeded serial/parallel CCM with both worker transports | 3.10, 3.11, 3.14 |
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

CI uses Linux CPU runners. Dependencies are resolved within the package's declared
ranges; each run's artifacts record the exact versions. A passing run therefore
certifies the recorded checkout and environment, not every platform or dependency
combination. Artifacts include test reports and environment information; package
artifacts are built for inspection and are not published to PyPI.
