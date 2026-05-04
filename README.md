# Satellite Image Enhancement Skill

GitHub URL after publishing:

`https://github.com/ditchallaway/satellite-image-enhance`

This repository packages one installable agent skill:

`satellite-image-enhance/`

It is an agent workflow skill, not a standalone image processing app. It teaches Codex or another compatible agent how to enhance satellite and aerial imagery while preserving geographic accuracy and spectral fidelity.

## What It Does

- Chooses a safe enhancement lane for satellite imagery.
- Prioritizes geographic accuracy and spectral fidelity over dramatic visual effect.
- Defines guardrails for cloud removal, contrast enhancement, spectral band merging, and AI image edits.
- Provides optional deterministic local batch scripts for conventional finishing.
- Requires review before broad batch work and rejects edits that invent geographic features.

## What It Does Not Do

- It does not include a hosted app or GUI.
- It does not include real satellite imagery.
- It does not include API keys, cloud credentials, or local model files.
- It does not guarantee that another computer has the same native image-editing tools.
- It does not allow fabricating terrain, inventing geographic features, or hiding crucial topological data.

## Install In Codex

1. Clone or download this repo.
2. Copy the nested folder:

   `satellite-image-enhance/`

3. Paste it into your Codex skills directory:

   `~/.codex/skills/satellite-image-enhance/`

4. Restart Codex or refresh its skill index if your host requires it.
5. Ask Codex to read:

   `https://github.com/ditchallaway/satellite-image-enhance`

Minimal handoff prompt for another Codex:

```text
Install and use the satellite-image-enhance skill from:
https://github.com/ditchallaway/satellite-image-enhance

The installable skill folder is:
satellite-image-enhance/
```

## Required Setup

Required:

- A compatible agent host that can read local images and follow a `SKILL.md` workflow.
- Local source imagery supplied by the user.
- Human review before using enhanced imagery publicly.

Required for the optional local batch scripts:

- Python 3.10+
- `Pillow`
- `numpy`
- `opencv-python`

Install example:

```bash
python -m pip install pillow numpy opencv-python
```

## Optional Enhancements

Optional:

- A native image-editing tool inside the agent host.
- A local deterministic finishing workflow.
- A local or cloud image model configured by the user.
- GDAL, QGIS, or other geospatial tools, if your own workflow uses them.

These are optional. The skill does not assume your machine has the author's local paths, credentials, or model setup.

## Safety Rules

- Review the folder before processing a batch.
- Do not overwrite originals unless explicitly requested.
- Do not publish generated enhancements without human review.
- For targeted enhancement requests, change only the named band or region.
- Reject edits that invent geographic features, alter terrain elevation data, distort map projections, or hide crucial topological information.
- Never use image processing to conceal geographic or environmental data that matters to analysts, researchers, or decision-makers.

## Accuracy And Input Quality

Enhancement quality depends on the source imagery:

- High-resolution, low-noise, cloud-free scenes give better results.
- Consistent acquisition parameters and scene coverage make batch decisions easier.
- Very cloudy, low-resolution, heavily compressed, or radiometrically degraded imagery reduces confidence.
- The agent may use visible image content, filenames, folder names, and user instructions to understand scene types and priorities.
- External permissions, such as cloud model access or local file access, only apply after the user grants them.

## Checks

Run these before sharing changes:

```bash
python satellite-image-enhance/scripts/privacy_scan.py --root .
python satellite-image-enhance/scripts/capability_check.py
python -m py_compile satellite-image-enhance/scripts/*.py
```

## License

MIT. See `LICENSE`.
