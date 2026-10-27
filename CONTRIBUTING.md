# Contributing

```sh
pip install -r requirements_test.txt pre-commit
pre-commit install  # runs ruff and mypy before each commit
pytest --cov=custom_components.solar_illuminance
python script/translations.py  # after changing strings.json
pytest --snapshot-update  # after changing the sensor; review the diff
```

CI requires 100% test coverage, and also runs the tests against the oldest
Home Assistant version in `hacs.json`.

`translations/en.json` is generated from `strings.json`, so change the
latter. The other translations are edited by hand: if you add or change a
string, leave them as they are unless you can translate it.

For a release, bump `version` in `manifest.json`, add the changes to
`CHANGELOG.md`, and publish a GitHub release tagged and titled with the
version and a leading `v`, e.g. `v6.0.0`, with the version's changes as its
description. A workflow attaches the zip HACS installs.
