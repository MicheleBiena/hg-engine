# Shadows Of Time hg-engine Leftoff

Last updated: 2026-08-31

This file is the handoff entry point for future chats and local work on this
checkout. Start here, then follow the linked guides for details.

## Current State

- Repository: `C:\Users\Michele\Documents\hg-engine\Shadows Of Time\rework\CLEAN\hg-engine`
- Branch: `main`
- Latest local commit: 2026-08-31 upstream merge commit; use `git log -1` for
  the exact hash.
- Upstream merged: `BluRosie/hg-engine` `upstream/main` at `dacca858e`.
- Merge status: completed locally; no Git conflicts remain.
- Build status: not run by Codex for the 2026-08-31 merge. Michele should run
  `make clean`/`make -j12`.
- Runtime smoke tests: pending for the 2026-08-31 merge. Previous smoke tests
  confirmed boot, DSPRE event entries, Vivillon Garden overworld, Kecleon Alt
  party/follower behavior, and matrix 0 outdoor maps after restoring
  `MON_OVERWORLD_TAG_START` to `1050`.

## Important Local Decisions

- The project now follows hg-engine's post-merge C data flow. Prefer editing
  `data/*.c`, `include/constants/*.h`, and `data/graphics/sprites/*` over old
  `armips/data/*.s` files.
- Old overworld IDs in DSPRE event files were converted to the new merged
  overworld table order. The edited extracted DSPRE files live outside tracked
  source history and should be treated as ROM-editing artifacts, not source code.
- Custom follower overworlds use species-folder assets and
  `MON_FOLLOWER_ENTRY(...)` in `src/field/overworld_table.c`.
- Keep `MON_OVERWORLD_TAG_START` at `1050`. Upstream changed it to `2500`, but
  that black-screened on entry to matrix 0/outdoor maps in this project, likely
  because existing DSPRE overworld references still depend on the old follower
  tag range.
- During the 2026-08-31 upstream merge, conflicts in `hooks`,
  `include/constants/pokemon.h`, `include/constants/species.h`, and
  `src/field/overworld_table.c` were resolved by keeping the local follower tag
  base, keeping all custom species/forms, accepting upstream's roamer guard
  closure, and reinserting custom follower entries before the overworld table
  terminator.
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
- `SPECIES_MEOWSTIC_SHADOW`: persistent male Meowstic shadow form with copied
  Meowstic battle/OW assets. It is form 4 under `SPECIES_MEOWSTIC`; keep it
  after female and mega forms so older form ids do not shift. Its
  `meowstic_shadow/female/*.png` battle slots intentionally duplicate the male
  sprites so summary/battle loaders cannot hit the empty vanilla Meowstic female
  placeholders.

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

Merge caution: trainer text generation must keep one raw message entry per
`TrainerMessageEntry`. `data/Trainers.c` C strings may contain real control
characters, so `tools/source/trainerdatagen/trainer_data_gen.c` must write them
escaped as `\n`, `\r`, and `\f` into `build/rawtext/728/*.txt`. If a merge
regresses this, `msg_cat.py` splits one trainer text into several message-bank
entries, all later trainer text ids shift, and pre-battle/post-battle/last-Pokemon
dialogue appears to come from unrelated trainers. Quick sanity check after
trainer text pipeline merges: `build/rawtext/728` file count should match
`build/trainer_text_map/7_0` size divided by 4, and `build/rawtext/728.txt`
should not gain extra physical lines from unescaped trainer text.

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

Meowstic Shadow is intentionally form 4:

```c
GivePokemon SPECIES_MEOWSTIC 30 ITEM_NONE 4 0 32780
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
