# Real Estate Photo Editing Skill

GitHub URL after publishing:

`https://github.com/yyxone/real-estate-photo-editing`

This repository packages one installable agent skill:

`real-estate-photo-editing/`

It is an agent workflow skill, not a standalone photo editor app. It teaches Codex or another compatible agent how to improve real-estate listing photos while preserving truthful property appearance.

## What It Does

- Chooses a safe editing lane for listing photos.
- Prioritizes truthful real-estate presentation over dramatic redesign.
- Defines guardrails for clutter removal, brightness, white balance, window handling, geometry, and AI image edits.
- Provides optional deterministic local batch scripts for conventional finishing.
- Requires review before broad batch work and rejects edits that invent property details.

## What It Does Not Do

- It does not include a hosted app or GUI.
- It does not include real listing photos.
- It does not include API keys, cloud credentials, or local model files.
- It does not guarantee that another computer has the same native image-editing tools.
- It does not allow fake renovations, fake staging, or hiding material property defects.

## Install In Codex

1. Clone or download this repo.
2. Copy the nested folder:

   `real-estate-photo-editing/`

3. Paste it into your Codex skills directory:

   `~/.codex/skills/real-estate-photo-editing/`

4. Restart Codex or refresh its skill index if your host requires it.
5. Ask Codex to read:

   `https://github.com/yyxone/real-estate-photo-editing`

Minimal handoff prompt for another Codex:

```text
Install and use the real-estate-photo-editing skill from:
https://github.com/yyxone/real-estate-photo-editing

The installable skill folder is:
real-estate-photo-editing/
```

## Required Setup

Required:

- A compatible agent host that can read local images and follow a `SKILL.md` workflow.
- Local source photos supplied by the user.
- Human review before using edited photos publicly.

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
- Darktable or other photo tools, if your own workflow uses them.

These are optional. The skill does not assume your machine has the author's local paths, credentials, or model setup.

## Safety Rules

- Review the folder before editing a batch.
- Do not overwrite originals unless explicitly requested.
- Do not publish generated edits without human review.
- For remove-only requests, change only the named object or clutter.
- Reject edits that alter room geometry, fixed finishes, appliances, views, lighting direction, or material property facts.
- Never use photo editing to hide defects that matter to buyers, renters, or agents.

## Accuracy And Input Quality

Editing quality depends on the source photos:

- Clear, well-lit, non-blurry photos give better results.
- Consistent angles and room coverage make batch decisions easier.
- Very dark, tilted, cluttered, low-resolution, or heavily compressed photos reduce confidence.
- The agent may use visible image content, filenames, folder names, and user instructions to understand rooms and priorities.
- External permissions, such as cloud model access or local file access, only apply after the user grants them.

## Checks

Run these before sharing changes:

```bash
python real-estate-photo-editing/scripts/privacy_scan.py --root .
python real-estate-photo-editing/scripts/capability_check.py
python -m py_compile real-estate-photo-editing/scripts/*.py
```

## License

MIT. See `LICENSE`.
