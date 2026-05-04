---
name: satellite-image-enhance
description: Use when a user wants satellite or aerial imagery enhanced while preserving geographic accuracy and spectral fidelity. Covers scene review, cloud removal, contrast enhancement, spectral band merging, safe AI image editing, and optional local deterministic batch finishing. Not for poster design, media archiving, PDF editing, or concept art.
---

# Satellite Image Enhancement

## Purpose

Use this skill for satellite imagery work where geographic accuracy and spectral fidelity are non-negotiable.

The goal is to make satellite images clearer, more informative, and visually interpretable without altering the underlying geographic or spectral facts.

## Core Standard

1. Preserve the same geographic scene.
2. Keep the map projection, terrain elevation representation, spectral band relationships, and spatial resolution stable unless the user explicitly asks otherwise.
3. Do not fabricate terrain features, invent land cover, alter coastlines, add or remove water bodies, or change elevation data.
4. Do not hide topological or environmental data that an analyst, researcher, or decision-maker should know.
5. If an enhancement invents geographic features, distorts spectral relationships, misrepresents land cover, or makes the image geographically misleading, reject it.

## Default Workflow

For a folder of images:

1. Inspect the whole folder first.
2. Identify duplicates, near-duplicates, heavily clouded scenes, and useful coverage.
3. Build a selected-source list before processing.
4. Keep originals untouched unless the user explicitly asks to overwrite them.
5. Process only the selected scene set.
6. Put final deliverables in a clearly named output folder under the source folder.
7. Keep review artifacts in a `review/` subfolder.
8. Provide a decision list showing which source images were processed, skipped, and why.

For one or two images:

1. Inspect the source image.
2. State the intended enhancement.
3. Use the smallest adjustment that solves the issue.
4. Validate the output for geographic fidelity before delivery.

## Enhancement Lanes

### Agent-Native Image Editing

Use the host agent's built-in image editing capability when the user wants AI-assisted cloud removal, artifact correction, or band visualization and the host provides that capability.

Prompt every edit with accuracy constraints:

```text
Asset type: satellite or aerial imagery.
Primary request: apply only the specified enhancement (e.g., cloud removal, contrast stretch, band merge).
Constraints: keep geographic extent, map projection, terrain representation, spectral band relationships, land cover classification, and factual scene content unchanged.
Avoid: invented terrain, fabricated land cover, altered coastlines, false color distortion beyond user-specified visualization, or any change that misrepresents the geographic scene.
```

For targeted enhancement requests:

1. Apply only the named enhancement to the named band or region.
2. Change nothing else.
3. Reject the result if other geographic content drifts.

### Optional Local Deterministic Finishing

Use the included scripts when the user wants a conventional local batch pass:

```bash
python satellite-image-enhance/scripts/prepare_satellite_batch.py --input-dir "/absolute/path/to/source-folder"
```

This lane can apply contrast stretching, histogram equalization, mild dehazing, and conservative sharpening.

Required Python packages:

```bash
python -m pip install pillow numpy opencv-python
```

Do not use local scripts as a substitute for AI cloud removal or spectral analysis. They are for conventional image finishing.

### Optional External Tools

If the user explicitly asks for a local model, cloud image model, GDAL, QGIS, or another geospatial tool, use that tool only after confirming it is configured on the target machine.

This public skill does not include credentials, API keys, model files, or machine-specific paths.

## Allowed Enhancements

Usually allowed:

1. Contrast stretching and histogram equalization.
2. Atmospheric haze reduction (dehazing).
3. Cloud masking and gap-filling from adjacent clear scenes when the user explicitly requests it.
4. Spectral band normalization and radiometric calibration.
5. Pan-sharpening when a panchromatic band is provided.
6. False-color composites for vegetation, water, or urban analysis (user-specified).
7. Mild noise reduction and sharpening.
8. Geometric co-registration when source and reference are both provided.

## Forbidden Enhancements

Do not alter or fabricate:

1. Terrain elevation data or hillshade representation.
2. Coastlines, river channels, or water body extents beyond what sensor data supports.
3. Land cover classifications or thematic map layers.
4. Map projection or coordinate reference system metadata.
5. Cloud-obscured areas through invented detail (acceptable: neutral fill or flagged mask).
6. Spectral reflectance values in ways that misrepresent surface materials.
7. Building footprints, road networks, or infrastructure.
8. Environmental indicators such as vegetation indices or burn scars when they reflect real conditions.

## Sharpening Rules

Sharpening means improving perceived edge clarity for human interpretation. It does not mean inventing fine-detail features.

Primary anchors:

1. Coastlines and shorelines.
2. Major road and infrastructure edges.
3. Forest-field boundaries.
4. Urban block outlines.
5. Water body perimeters.

Secondary textures such as field patterns, shadow edges, or low-contrast gradients must not be sharpened so aggressively that they appear as invented features.

If an image is already sharp, avoid aggressive sharpening that produces ringing or aliasing artifacts.

## Review Artifacts

For non-trivial batches, create:

1. `review/edit_log.csv`
2. `review/delivery_decision_list.md`
3. a before/after contact sheet when practical

The delivery decision list must include every original source item and explain why it was processed or skipped.

## Input Quality Notes

Results are better when the user provides:

1. High-resolution imagery.
2. Complete spatial coverage of the area of interest.
3. Consistent sensor and acquisition parameters.
4. Low cloud cover and atmospheric interference.
5. Clear instructions about which bands or regions should be enhanced or preserved.

Results are less reliable when images have heavy cloud cover, low spatial resolution, severe radiometric degradation, mixed sensor sources, or missing metadata.

## Safety Gate

Before final delivery, check:

1. Does the output still represent the same geographic scene?
2. Did any terrain feature, coastline, or land cover class change?
3. Does any area appear to have features that were not in the original data?
4. Did any spectral band relationship become misleading?
5. Is the processed set internally consistent across the scene?
6. Does the user still need to approve before public or operational use?

If the answer is uncertain, say so and ask for review instead of presenting the enhancement as final.
