# Custom Pokemon, Forms, Trainers, and Overworlds

This project follows hg-engine's C data layout. Prefer editing the source data
files and regenerating generated files instead of patching generated output by
hand.

## New Pokemon or Fakemon

For a new species, keep these areas in sync:

- `include/constants/species.h` for the species constant and max counters.
- `data/Species.c` for stats, typing, abilities, items, egg data, and flags.
- `data/Evolutions.c` for evolution methods.
- `data/graphics/sprites/<species>/` for battle sprites, icon, palettes, and
  `overworld.png` if the species appears outside battle.
- `data/FollowerProperties.c` and `src/field/overworld_table.c` for follower
  behavior and the overworld tag entry.
- `data/Encounters.c`, `data/Headbutt.c`, `data/PokedexArea.c`, and
  `data/RegionalDex.c` when the species should be found, seen in the dex, or
  placed in the regional dex.
- `data/SpriteOffsets.c`, `data/HeightTable.c`, and icon palette tables when
  the sprite presentation needs custom offsets or palettes.

After changing sprite assets, run:

```sh
python scripts/reformat_sprite_data.py data/graphics/pokegra.mk
```

## New Forms

Use hg-engine's form tables for battle-visible forms:

- Add the form constant in `include/constants/species.h`.
- Register the form in `data/PokeFormDataTbl.c`.
- Map it back to the base species in `data/FormToSpeciesMapping.c`.
- Add species/form data in `data/Species.c` and any evolution, dex, sprite,
  offset, palette, and follower entries the form needs.

If the form should be visible outside battle, add its `overworld.png`, regenerate
`data/graphics/pokegra.mk`, and add a `MON_FOLLOWER_ENTRY` in
`src/field/overworld_table.c`.

If the form is battle-only and must not appear as a follower, do not add a
`MON_FOLLOWER_ENTRY`. Add the form constant to
`data/graphics/no_overworld_forms.txt` instead. The sprite generator will reserve
a pokemonow padding slot with `data/graphics/sprites/none/overworld.png`, keeping
later overworld IDs aligned with `MON_OVERWORLD_GFX_START + species`.

## Trainers and Documentation Export

Trainer source data lives in `data/Trainers.c`. Every trainer exported to the
spreadsheet docs must also be listed in `documentation/touched_trainers.md`, and
the trainer initializer must carry a compact area comment such as `// Route4`.

Validate before exporting:

```sh
python scripts/validate_trainers_s.py
python scripts/export_touched_trainers.py --formats csv html xlsx
```
