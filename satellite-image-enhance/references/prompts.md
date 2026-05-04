# Prompt Patterns

## General Satellite Enhancement

```text
Enhance this satellite image lightly and truthfully. Improve contrast, brightness, and color balance while preserving the same geographic scene, map projection, terrain representation, spectral band relationships, and land cover. Do not invent terrain features, alter coastlines, fabricate land cover, or hide environmental data.
```

## Targeted Enhancement Only

```text
Apply only the specified enhancement. Change nothing else. Preserve geographic extent, map projection, spectral band relationships, land cover classification, and all factual scene content. Do not redesign, invent features, or alter fixed geographic properties.
```

## Vegetation Enhancement

```text
Boost vegetation contrast and green saturation lightly for visual clarity. Keep forest and field boundaries truthful and unchanged. Do not inflate vegetation indices beyond what the spectral data supports.
```

## Coastal and Water Scene

```text
Improve clarity of the coastal or water scene. Preserve shoreline position, water body extent, and true color relationships. Do not alter coastlines, invent islands, or change water body boundaries beyond what the source data shows.
```

## Cloud Region Handling

```text
Attenuate or mask the cloud-covered area neutrally. Do not invent terrain, land cover, or features beneath the clouds. If the original data does not show what is under the cloud, leave the area masked or filled with a neutral placeholder.
```
