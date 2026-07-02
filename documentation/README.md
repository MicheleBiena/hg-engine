# Shadows Of Time Documentation

This directory contains the local workflow notes for the Shadows Of Time
hg-engine fork. For chat handoff and current project state, start from
[`../LEFTOFF.md`](../LEFTOFF.md).

## Guides

- [`custom_content.md`](custom_content.md): adding or updating Pokemon, forms,
  overworlds, encounters, headbutt data, Pokedex data, and trainers in the merged
  C data layout.
- [`trainer_export.md`](trainer_export.md): generating CSV, HTML, and XLSX trainer
  documentation from `data/Trainers.c`.
- [`touched_trainers.md`](touched_trainers.md): source list and manual area order
  for trainers included in the export.
- [`../PROJECT_NOTES.md`](../PROJECT_NOTES.md): archived detailed feature notes
  and older implementation protocols. Prefer `LEFTOFF.md` and this directory for
  current handoff context.

## Current Source Layout

Use these files as the source of truth:

- Pokemon data: `data/Species.c`
- Species constants: `include/constants/species.h` and `asm/include/species.inc`
- Evolutions: `data/Evolutions.c`
- Wild encounters: `data/Encounters.c`
- Headbutt encounters: `data/Headbutt.c`
- Pokedex area data: `data/PokedexArea.c`
- Regional dex: `data/RegionalDex.c`
- Trainer data and text: `data/Trainers.c`
- Follower data: `data/FollowerProperties.c`
- Overworld table: `src/field/overworld_table.c`
- Sprite assets: `data/graphics/sprites/<species_or_form>/`
- Overworld build rules: `data/graphics/pokegra.mk`

Old `armips/data/*.s` files are no longer the place to edit most gameplay data in
this merged checkout.

## Build And Export Rules

- Michele usually runs full `make`.
- If sprite assets change, regenerate the graphics rules before building:

```sh
python scripts/reformat_sprite_data.py data/graphics/pokegra.mk
```

- Validate trainers before exporting docs:

```sh
python scripts/validate_trainers_s.py
python scripts/export_touched_trainers.py --formats csv html xlsx
```
