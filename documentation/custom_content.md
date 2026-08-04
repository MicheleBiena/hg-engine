# Custom Pokemon, Forms, Trainers, and Overworlds

This project follows hg-engine's merged C data layout. Prefer editing source
tables and regenerating generated files instead of patching generated output by
hand.

Start from [`../LEFTOFF.md`](../LEFTOFF.md) when opening a new chat or resuming
after a merge.

## Source Layout

Use these files as the current source of truth:

- Species constants: `include/constants/species.h` and `asm/include/species.inc`
- Species data: `data/Species.c`
- Evolutions: `data/Evolutions.c`
- Base experience: `data/BaseExperienceTable.c`
- Hidden abilities: `data/HiddenAbilityTable.c`
- Height table: `data/HeightTable.c`
- Sprite offsets: `data/SpriteOffsets.c`
- Icon palettes: `data/IconPaletteTable.c`
- Wild encounters: `data/Encounters.c`
- Headbutt encounters: `data/Headbutt.c`
- Pokedex area data: `data/PokedexArea.c`
- Regional dex: `data/RegionalDex.c`
- Trainers and trainer text: `data/Trainers.c`
- Follower behavior: `data/FollowerProperties.c`
- Overworld table: `src/field/overworld_table.c`
- Sprite and overworld assets: `data/graphics/sprites/<species_or_form>/`
- Overworld build rules: `data/graphics/pokegra.mk`
- Battle-only overworld padding: `data/graphics/no_overworld_forms.txt`

Old `armips/data/*.s` files are migration history, not the place to edit normal
Pokemon, trainer, encounter, Pokedex, or overworld data in this checkout.

## Add A New Pokemon Or Fakemon

For a new base species, keep these areas in sync:

1. Add the species constant in `include/constants/species.h`.
2. Add the matching constant in `asm/include/species.inc`.
3. Update max counters such as `NUM_OF_FAKEMONS`, `MAX_MON_NUM`, and related
   form starts if needed.
4. Add species data in `data/Species.c`.
5. Add evolutions in `data/Evolutions.c`.
6. Add base experience in `data/BaseExperienceTable.c`.
7. Add height, sprite offsets, and icon palette entries.
8. Add sprite/icon assets under `data/graphics/sprites/<species>/`.
9. If the species appears in the overworld or can follow the player, add
   `overworld.png`, palettes/json as needed, `data/FollowerProperties.c`, and a
   `MON_FOLLOWER_ENTRY(...)` in `src/field/overworld_table.c`.
10. Add wild placement only where intended: `data/Encounters.c`,
    `data/Headbutt.c`, `data/PokedexArea.c`, and `data/RegionalDex.c`.
11. Add or inherit learnsets in `data/learnsets/learnsets.json`.

After changing sprite or overworld assets, regenerate the graphics rules:

```sh
python scripts/reformat_sprite_data.py data/graphics/pokegra.mk
```

Michele normally runs full `make`.

## Add A New Form

First decide what kind of form it is:

- **Battle-only temporary form:** visible in battle, reverts after battle, no
  overworld. Example: `SPECIES_SINFAE_SHADOW`.
- **Persistent form:** can exist outside battle and may need party/follower
  sprites. Example: `SPECIES_KECLEON_ALT`.
- **Mega/primal/divine/shadow family form:** still use the same form-table rules;
  only the trigger and reversion rules differ.

Minimum files for a battle-visible form:

1. `include/constants/species.h`: add `SPECIES_<BASE>_<FORM>`.
2. `asm/include/species.inc`: mirror the constant.
3. `data/PokeFormDataTbl.c`: register the form under the base species.
4. `data/FormToSpeciesMapping.c`: map the form species back to the base species.
5. `data/Species.c`: add the form's species data.
6. `data/Evolutions.c`: usually `EVO_NONE` for the form.
7. `data/BaseExperienceTable.c`: add base experience.
8. `data/HiddenAbilityTable.c`: add hidden ability if it should match/inherit a
   nonzero hidden ability.
9. `data/IconPaletteTable.c`: add icon palette.
10. `data/SpriteOffsets.c`: add offsets.
11. `data/learnsets/learnsets.json`: only if the form does not inherit correctly
    or needs a different learnset.

Do not add separate `data/BabyMons.c`, `data/PokedexSort.c`,
`data/RegionalDex.c`, or `data/PokedexArea.c` entries for ordinary forms unless
the design explicitly needs separate dex behavior.

## Battle-Only Forms With No Overworld

For forms like `SPECIES_SINFAE_SHADOW`:

1. Add the form to `data/PokeFormDataTbl.c`, usually with `NEEDS_REVERSION` if it
   must revert after battle.
2. Add the reverse mapping in `data/FormToSpeciesMapping.c`.
3. Do not add a `MON_FOLLOWER_ENTRY(...)`.
4. Add the form constant to `data/graphics/no_overworld_forms.txt`.

The sprite generator uses `data/graphics/sprites/none/overworld.png` to reserve a
pokemon overworld slot. This keeps later overworld IDs aligned with
`MON_OVERWORLD_GFX_START + species` without making the form visible in DSPRE or
in the field.

Sinfae Shadow follows the same broad pattern as Aegislash-style form changes:
the battle controller checks the trigger, updates `form_no`, calls
`BattleFormChange`, and the form table/reverse mapping handles reversion.

## Forms With Overworlds Or Followers

For forms like `SPECIES_KECLEON_ALT`:

1. Add form sprite and overworld assets under
   `data/graphics/sprites/<form_folder>/`.
2. Regenerate `data/graphics/pokegra.mk`.
3. Add `data/FollowerProperties.c` if follower behavior differs or needs an
   explicit entry.
4. Add a `MON_FOLLOWER_ENTRY(SPECIES_<FORM>, ...)` in
   `src/field/overworld_table.c`.
5. Use `data/SpeciesToOWFormFemale.c` only for gender/special OW mappings that
   the engine must resolve automatically.

If the base species already has special `SpeciesToOWFormFemale.c` handling,
verify `src/pokemon.c::get_mon_ow_tag` still resolves the new form to its real
species overworld slot. `SPECIES_MEOWSTIC_SHADOW` has a narrow guard there
because Meowstic already uses special female/form OW logic.

For single-sex technical forms cloned from a species with gendered sprite
handling, keep both `male/*.png` and `female/*.png` battle slots valid even if
the form is conceptually male-only or female-only. Some menu/summary paths can
still touch the alternate slot from the original species/PID flow; empty PNG
placeholders can freeze the summary screen.

`data/SpeciesToOWGfx.c` is no longer used by the build.

## Encounters, Headbutt, And Pokedex Area Data

Wild and dex placement are separate tasks:

- `data/Encounters.c`: grass, water, fishing, swarms, and other wild tables.
- `data/Headbutt.c`: headbutt encounters. Tree coordinates depend on the actual
  edited map layout, so keep the hack's route-specific coordinates instead of
  blindly importing upstream coordinates.
- `data/PokedexArea.c`: Pokedex area display data. Preserve the expected bank/list
  structure even when a species has no area data.
- `data/RegionalDex.c`: regional dex ordering.

When adding a new Pokemon, do not assume that encounter placement automatically
updates the Pokedex. Keep encounter tables and Pokedex area tables in sync on
purpose.

## Trainers And Trainer Text

Trainer source data now lives in `data/Trainers.c`. Trainer teams, metadata,
items, moves, and text are all in the same C initializer.

Every trainer included in the exported documentation must:

- be listed in `documentation/touched_trainers.md`;
- have a compact area comment on the initializer line, for example
  `[24] = { // Route4`;
- use an area id present in the manual area order in
  `documentation/touched_trainers.md`.

Before exporting:

```sh
python scripts/validate_trainers_s.py
python scripts/export_touched_trainers.py --formats csv html xlsx
```

For XLSX-only updates:

```sh
python scripts/export_touched_trainers.py --formats xlsx
```

Merge caution: trainer text ids depend on `tools/source/trainerdatagen` writing
exactly one `build/rawtext/728/NNNN.txt` file per trainer text map entry. Because
`data/Trainers.c` stores C strings, real `\n`, `\r`, and `\f` characters must be
escaped back to text before `msg_cat.py` concatenates bank 728. If this breaks,
the map/offset tables can look correct while in-game pre-battle, post-battle,
defeated, and last-Pokemon text reads from shifted message-bank entries.

For a single trainer that starts a double battle without a second overworld
trainer, such as a custom Gym Leader, use `NO_PARTNER_DOUBLE_BATTLE`. Its
in-battle defeat line is still looked up as `TRMSG_DBL_LOSE_1`, not
`TRMSG_LOSE`; last-Pokemon lines stay `TRMSG_LAST_POKE` and
`TRMSG_LAST_POKE_HALF`.

See [`trainer_export.md`](trainer_export.md) for the full export rules.

## DSPRE And Script Notes

Use `test_DSPRE_contents\unpacked\eventFiles` for the current extracted event
files when working with this merge's DSPRE output. Older extracted folders should
not be treated as current unless intentionally refreshed.

Normal `GivePokemon` scripts use a base species plus a separate form argument:

```c
GivePokemon SPECIES_KECLEON 5 ITEM_NONE 1 0 32780
```

Meowstic Shadow is form 4 of `SPECIES_MEOWSTIC` because the existing slots are
female, mega male, and mega female:

```c
GivePokemon SPECIES_MEOWSTIC 30 ITEM_NONE 4 0 32780
```

Do not encode forms in the first argument for normal `GivePokemon`:

```c
GivePokemon 2400 5 ITEM_NONE 0 0 32780
```

The `species + 2048 * form` convention only works in contexts that explicitly
decode it, such as specific trainer, starter, or macro paths. If a command has a
separate form parameter, use that parameter.

After the upstream overworld migration, old DSPRE overworld entry IDs are not
stable. Prefer checking the current dropdown/table and the species/form mappings
instead of reusing pre-merge numeric OW IDs from memory.
