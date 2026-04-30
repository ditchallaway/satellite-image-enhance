---
name: real-estate-photo-editing
description: Use when a user wants real-estate or interior listing photos improved without breaking truthfulness. Covers listing-photo review, clutter removal, brightness, white balance, straighten checks, safe AI image editing, and optional local deterministic batch finishing. Not for poster design, media archiving, PDF editing, or concept art.
---

# Real Estate Photo Editing

## Purpose

Use this skill for listing photo work where realism is non-negotiable.

The goal is to make property photos clearer, cleaner, brighter, and easier to understand without changing the property facts.

## Core Standard

1. Keep the same property.
2. Keep camera angle, room geometry, fixed finishes, window framing, fixtures, appliances, and major furniture stable unless the user explicitly asks otherwise.
3. Do not fabricate renovations, luxury staging, exterior views, sunlight direction, or room size.
4. Do not hide material defects that a buyer, renter, owner, or agent should know.
5. If an edit bends architecture, melts furniture, repeats texture, changes materials, or makes the property look fake, reject it.

## Default Workflow

For a folder of photos:

1. Inspect the whole folder first.
2. Identify duplicates, near-duplicates, weak angles, and useful coverage.
3. Build a selected-source list before editing.
4. Keep originals untouched unless the user explicitly asks to overwrite them.
5. Edit only the selected still-image set.
6. Put final deliverables in a clearly named output folder under the source folder.
7. Keep review artifacts in a `review/` subfolder.
8. Provide a decision list showing which source photos were edited, skipped, and why.

For one or two photos:

1. Inspect the source image.
2. State the intended change.
3. Use the smallest edit that solves the issue.
4. Validate the output for truthfulness before delivery.

## Editing Lanes

### Agent-Native Image Editing

Use the host agent's built-in image editing capability when the user wants AI cleanup or object removal and the host provides that capability.

Prompt every edit with truth constraints:

```text
Asset type: real-estate listing photo.
Primary request: remove only the specified clutter or repair only the specified area.
Constraints: keep room geometry, finishes, window framing, fixed fixtures, appliances, furniture layout, and truthful listing appearance unchanged.
Avoid: fake staging, invented sunlight, fake exterior detail, warped lines, repeated textures, changed materials.
```

For remove-only requests:

1. Remove only the named object, person, or clutter.
2. Change nothing else.
3. Reject the result if other visible content drifts.

### Optional Local Deterministic Finishing

Use the included scripts when the user wants a conventional local batch pass:

```bash
python real-estate-photo-editing/scripts/prepare_listing_batch.py --input-dir "/absolute/path/to/source-folder"
```

This lane can adjust brightness, tone, white balance, mild color cast, and conservative straightening.

Required Python packages:

```bash
python -m pip install pillow numpy opencv-python
```

Do not use local scripts as a substitute for AI object removal. They are for conventional photo finishing.

### Optional External Tools

If the user explicitly asks for a local model, cloud image model, Darktable, Photoshop, or another tool, use that tool only after confirming it is configured on the target machine.

This public skill does not include credentials, API keys, model files, or machine-specific paths.

## Allowed Cleanup

Usually allowed:

1. Loose countertop items.
2. Trash bags.
3. Tissue boxes.
4. Loose cables.
5. Small temporary floor items.
6. Visible hangers.
7. Messy bedding.
8. Laundry baskets or storage bins when they are temporary clutter.

## Forbidden Cleanup

Do not remove or falsify:

1. Fixed lighting.
2. Switches or outlets.
3. Structural features.
4. Real window context.
5. Wall damage or floor wear that materially affects the property.
6. Permanent fixtures.
7. Cabinet doors, counters, appliances, or tile patterns.
8. Neighboring buildings or street context when it represents the real view.

## Straightening Rules

Straightening means making the built environment feel naturally upright. It does not mean forcing every visible line to agree.

Primary anchors:

1. Door frames.
2. Window jambs.
3. Cabinet sides.
4. Wall corners.
5. Tall mirror edges.
6. Countertops and window sills.

Secondary lines such as bedding, decor, floor planks, reflections, or loose objects must not override architectural anchors.

If a photo is almost straight, avoid aggressive automatic rotation.

## Review Artifacts

For non-trivial batches, create:

1. `review/edit_log.csv`
2. `review/delivery_decision_list.md`
3. a before/after contact sheet when practical

The delivery decision list must include every original source item and explain why it was edited or skipped.

## Input Quality Notes

Results are better when the user provides:

1. Sharp photos.
2. Complete room coverage.
3. Consistent angles.
4. Reasonable exposure.
5. Clear instructions about what should be removed or preserved.

Results are less reliable when photos are dark, blurry, heavily compressed, extremely cluttered, tilted, or missing key room context.

## Safety Gate

Before final delivery, check:

1. Did the output still show the same property?
2. Did any fixed feature change?
3. Did any room feel larger, newer, or more luxurious than it really is?
4. Did any exterior or window view become fake?
5. Is the edited set internally consistent?
6. Does the user still need to approve before public use?

If the answer is uncertain, say so and ask for review instead of presenting the edit as final.
