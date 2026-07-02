# Shadows Of Time hg-engine Leftoff

Last updated: 2026-07-02

This file is the handoff entry point for future chats and local work on this
checkout. Start here, then follow the linked guides for details.

## Current State

- Repository: `C:\Users\Michele\Documents\hg-engine\Shadows Of Time\rework\CLEAN\hg-engine`
- Branch: `main`
- Latest local commit: `59f50475a Merge upstream hg-engine updates`
- Upstream merged: `BluRosie/hg-engine` `upstream/main` at `3eb5838b6`
- Merge status: completed; no Git conflicts remain.
- Build status: Michele ran `make` successfully after the merge.
- Runtime smoke tests: game boots, converted overworld event entries open in DSPRE,
  Vivillon Garden overworld is visible, and Kecleon Alt party/follower behavior was
  confirmed in game.

## Important Local Decisions

- The project now follows hg-engine's post-merge C data flow. Prefer editing
  `data/*.c`, `include/constants/*.h`, and `data/graphics/sprites/*` over old
  `armips/data/*.s` files.
- Old overworld IDs in DSPRE event files were converted to the new merged
  overworld table order. The edited extracted DSPRE files live outside tracked
  source history and should be treated as ROM-editing artifacts, not source code.
- Custom follower overworlds use species-folder assets and
  `MON_FOLLOWER_ENTRY(...)` in `src/field/overworld_table.c`.
- Battle-only forms with no overworld must be listed in
  `data/graphics/no_overworld_forms.txt` so generated pokemon overworld IDs stay
  aligned.
- `GivePokemon` uses base species plus a separate form argument. Do not encode
  forms as `species + 2048 * form` in normal `GivePokemon` script commands.

## Custom Pokemon And Forms

Current custom base species:

- `SPECIES_TERRATOPS`
- `SPECIES_IGNISOAR`
- `SPECIES_DIPPLASH`
- `SPECIES_SINFAE`

Current custom forms:

- `SPECIES_SINFAE_SHADOW`: battle-only, no overworld, uses `NEEDS_REVERSION`.
- `SPECIES_KECLEON_ALT`: persistent alternate form with overworld/follower.

Main guide:

- [documentation/custom_content.md](documentation/custom_content.md)

## Trainer Documentation

Trainer data now lives in `data/Trainers.c`. The export list and manual area
order live in:

- [documentation/touched_trainers.md](documentation/touched_trainers.md)

Exporter guide:

- [documentation/trainer_export.md](documentation/trainer_export.md)

Useful commands:

```sh
python scripts/validate_trainers_s.py
python scripts/export_touched_trainers.py --formats csv html xlsx
python scripts/export_touched_trainers.py --formats xlsx
```

## DSPRE Notes

- Use `test_DSPRE_contents\unpacked\eventFiles` for the current extracted event
  files.
- `rom_DSPRE_contents` was an older extraction during the merge investigation and
  should not be treated as current unless it is intentionally refreshed.
- Headbutt tree coordinates depend on the actual edited map layout. Keep Michele's
  map-specific coordinates; do not blindly import upstream coordinates.
- For `GivePokemon`, spawn alternate forms like this:

```c
GivePokemon SPECIES_KECLEON 5 ITEM_NONE 1 0 32780
```

Do not use this pattern for normal `GivePokemon`:

```c
GivePokemon 2400 5 ITEM_NONE 0 0 32780
```

That encoded species form is valid only in contexts that explicitly decode the
`species + 2048 * form` convention, such as specific trainer/starters/form macros.

## Documentation Map

- [documentation/README.md](documentation/README.md): local documentation index.
- [documentation/custom_content.md](documentation/custom_content.md): how to add
  Pokemon, forms, overworlds, encounters, headbutt data, Pokedex data, and trainer
  content in this merged C layout.
- [documentation/trainer_export.md](documentation/trainer_export.md): exporter
  workflow and output formats.
- [documentation/touched_trainers.md](documentation/touched_trainers.md): current
  touched trainer list and manual area order.
- [PROJECT_NOTES.md](PROJECT_NOTES.md): archived detailed feature notes and local implementation
  patterns. Use it for historical details, but prefer this file and the
  `documentation/` guides as current handoff context.

## Safe Workflow Reminder

- Ask before destructive operations, broad cleanups, resets, or mass generated-file
  rewrites.
- Michele runs full `make` unless explicitly asking Codex to run it.
- For risky merge/update work, start with read-only Git status and conflict
  reconnaissance.
- Validate only the relevant files for focused fixes; this repository can have very
  large merge diffs.
