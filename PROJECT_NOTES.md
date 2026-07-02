# Project Notes - Final Feature Specifications

> **Status:** Portable PC (Feature 1) — **APPLIED and TESTED OK**.
> Debug Pokemon Generator (Feature 2) — **NOT YET APPLIED**.
>
> Source of truth: ported from the pre-merge project notes of the corrupted build,
> with magic numbers / naming re-verified against this CLEAN base.

---

## 0. Compatibility Notes (verified against CLEAN base)

| Element                                                 | Old doc value        | CLEAN status                                           | Action                                            |
| ------------------------------------------------------- | -------------------- | ------------------------------------------------------ | ------------------------------------------------- |
| `FLAG_UNK_18F equ 399` (`armips/include/flags.s:413`)   | exists               | exists, identical                                      | **Rename** to `FLAG_PORTA_PC_AVAILABLE`           |
| `OVERWORLD_REQUEST_FLAGS.OpenPCCheck` bit 14            | exists               | exists at `include/map_events_internal.h:211`          | OK, no struct change                              |
| Commonscript labels `_0A18`, `_0DF0`, `_0E16`           | exist                | exist at lines 767 / 1001 / 1015                       | OK, patch in place                                |
| `scrcmd_500 90`, `scrcmd_309 90`, `_0A23`               | exist                | exist at lines 768 / 776 / 773                         | OK                                                |
| `REUSABLE_TMS` block in `include/config.h`              | exists               | exists at line 160                                     | OK, append new define after it                    |
| `APPLY_ANTIPIRACY` block in `armips/include/config.s`   | exists               | exists at line 56                                      | OK, prepend new equ before it                     |
| Hook addresses `0x021E6880`, `0x021E6982`, `0x021E6AF6` | proposed             | no collision in `hooks` / `armhooks` / `repoints`      | OK, free to use                                   |
| `arm9 Script_RunNewCmd` in `routinepointers`            | required             | exists at `routinepointers:8` (`080FB040`)             | OK, multiplexer wired                             |
| `src/script_new_cmds.c`                                 | sub-cmds 0,1,2 used  | only sub-cmd 0 (`SCRIPT_NEW_CMD_REPEL_USE`)            | **Extend** with cases 1, 2                        |
| `armips/include/scriptmacros.s` `RunNewCommand` macro   | exists               | exists at line 6755, `NEW_COMMAND_QUEUE_NEW_REPEL = 0` | OK, append new equ + macros                       |
| `std_pokecenter_pc equ 2010`                            | required             | exists at `scriptmacros.s:169`                         | OK                                                |
| `src/field/field_request.c`                             | created in old build | **does not exist**                                     | **Create**                                        |
| `asm/field/pc_anywhere.s`                               | created in old build | **does not exist**                                     | **Create**                                        |
| Sub-command IDs 1, 2                                    | claimed              | still free                                             | OK                                                |
| Digit u16 encoding `0x0121-0x012A`                      | required             | **NOT yet verified** in `charmap.txt`                  | **Verify before apply** (see Pre-Apply Checklist) |

---

## 1. Project-Specific Constants (Shadows Of Time, CLEAN)

The CLEAN base currently keeps the Shadows Of Time custom base species in the
normal base-species range:

- `MAX_CANONICAL_MON_NUM = SPECIES_PECHARUNT` (`1075`)
- `SPECIES_TERRATOPS` through `SPECIES_SINFAE` occupy `1076..1079`
- `NUM_OF_FAKEMONS = 4`, so `MAX_MON_NUM = SPECIES_SINFAE` (`1079`)
- `SPECIES_MEGA_START = MAX_MON_NUM + 1` (`1080`)
- `MAX_SPECIES_INCLUDING_FORMS = 1481`, including `SPECIES_SINFAE_SHADOW` and `SPECIES_KECLEON_ALT`

---

## 2. Naming Convention Migration (IMPORTANT)

The old build used **camelCase** macros for new script commands:
`QueueNewRepel`, `ParseNicknameAsNumber`, `RestoreNickname`.

The CLEAN base has migrated to **snake_case** macros plus uppercase
`NEW_COMMAND_*` equ constants. Current state:

```asm
.equ NEW_COMMAND_QUEUE_NEW_REPEL, 0          // scriptmacros.s:6753
.macro RunNewCommand,slot,unk                 // scriptmacros.s:6755
.macro queue_new_repel                        // scriptmacros.s:1539
    RunNewCommand NEW_COMMAND_QUEUE_NEW_REPEL, 0x800C
.endmacro
```

C-side constant in `src/script_new_cmds.c`:

```c
#define SCRIPT_NEW_CMD_REPEL_USE    0
#define SCRIPT_NEW_CMD_MAX          256
```

**All new sub-commands MUST follow this convention:**

- C-side: `SCRIPT_NEW_CMD_<UPPER_SNAKE>` value
- ASM-side equ: `.equ NEW_COMMAND_<UPPER_SNAKE>, <value>`
- ASM-side macro: lowercase snake_case wrapper that internally calls `RunNewCommand`

---

## 3. Feature 1 - Portable PC

Based on commit `4993e6b6` from BluRosie/hg-engine (by memory5ty7), adapted.
Link for reference: https://github.com/BluRosie/hg-engine/commit/4993e6b6c4addec83959f55f560005385563d541.

### 3.1 Goal / Trigger / Flag

- **Trigger:** press **L** in the overworld.
- **Gating flag:** `FLAG_PORTA_PC_AVAILABLE` (= `399` = `0x18F`). Set this flag
  via a game script when the player should gain the ability (e.g. on receiving
  a key item).
- **Transient flag:** `FLAG_PC_TRANSIENT` (= `1311` = `0x51F`). Set
  automatically by the C hook before launching the PC script, cleared by
  commonscript on PC logoff. Never set or clear this manually.
- **Master toggle:** `IMPLEMENT_PORTABLE_PC` define. Comment it out to disable
  the whole feature.

### 3.2 Files to Create

#### `src/field/field_request.c`

Three C functions:

- `ClearOverworldRequestFlags` -- replaces vanilla clear, also resets
  `OpenPCCheck`.
- `SetOverworldRequestFlags` -- sets `OpenPCCheck = TRUE` when L is pressed
  (only L, NOT R — R is reserved for a future feature).
- `CheckOverworldRequestFlags` -- if `OpenPCCheck && FLAG_PORTA_PC_AVAILABLE`
  is set, sets transient flag `0x51F` (`FLAG_PC_TRANSIENT`) and launches PC
  script `2010` (= `std_pokecenter_pc`).

> **Source for the C body:** copy from
> `<backup pre merge>/hg-engine/src/field/field_request.c`. Verify the
> bitfield access matches the current `OVERWORLD_REQUEST_FLAGS` layout
> (bit 14 = `OpenPCCheck`, confirmed in CLEAN).

#### `asm/field/pc_anywhere.s`

ARM assembly hook glue with two entry points:

- `SetOverworldRequestFlags_hook` -- hooks at `0x021E6982` (Y-button check
  area), tail-calls `SetOverworldRequestFlags`.
- `CheckOverworldRequestFlags_hook` -- hooks at `0x021E6AF6` (overworld
  request check), tail-calls `CheckOverworldRequestFlags`.

> **Source for the ASM body:** copy from
> `<backup pre merge>/hg-engine/asm/field/pc_anywhere.s`. No address
> repoint required; the three target offsets are all free in CLEAN.

### 3.3 Files to Modify

#### `armips/include/flags.s` line 413

Rename:

```
FLAG_UNK_18F                                               equ 399
```

to:

```
FLAG_PORTA_PC_AVAILABLE                                    equ 399
```

#### `include/config.h`

After the `REUSABLE_TMS` block (around line 160), before the final `#endif`:

```c
// IMPLEMENT_PORTABLE_PC enables pressing L in the overworld to open the PC
// when FLAG_PORTA_PC_AVAILABLE is set.
#define IMPLEMENT_PORTABLE_PC
#define FLAG_PORTA_PC_AVAILABLE 399
```

#### `armips/include/config.s`

Before the `APPLY_ANTIPIRACY` block (line 54-56):

```asm
// IMPLEMENT_PORTABLE_PC enables the L-button portable PC feature.
IMPLEMENT_PORTABLE_PC equ 1
```

#### `hooks` (end of file)

Add, guarded by `#ifdef IMPLEMENT_PORTABLE_PC`:

```
#ifdef IMPLEMENT_PORTABLE_PC
0001 ClearOverworldRequestFlags 021E6880 1
0001 SetOverworldRequestFlags_hook 021E6982 0
0001 CheckOverworldRequestFlags_hook 021E6AF6 3
#endif
```

#### `armips/scr_seq/scr_seq_00003_commonscript.s`

Three patches to skip NPC PC animations when the portable PC is in use.
Transient flag `0x51F` (`FLAG_PC_TRANSIENT`) is set by the C hook and
cleared on logoff. Restructured to match the original BluRosie layout:
shared common code runs for both NPC PC and Portable PC; only NPC-specific
calls (`call _0A23` at `_0DF0`, `scrcmd_309 90` at `_0E16`) are gated.

1. **At `_0A18`** (PC open animation, line 767): insert before
   `scrcmd_500 90`:

   ```
       goto_if_set 0x51F, _skipPCOnOff
   ```

   Add label `_skipPCOnOff:` before the existing `return`.

2. **At `_0DF0`** (PC logoff, line 1001): `closemsg` runs before the
   branch (shared). Insert before `call _0A23`:

   ```
       goto_if_set 0x51F, _skipPCOff
   ```

   After the `call _0A23`, ensure `_skipPCOff:` is followed by
   `clearflag 0x51F` then the shared cleanup (`touchscreen_menu_show`,
   `releaseall`, `end`). This avoids duplicating the menu-show and end
   logic, and does **not** clear the persistent gate flag `FLAG_PORTA_PC_AVAILABLE`.

3. **At `_0E16`** (fade transition, line 1015): insert before
   `scrcmd_309 90`:
   ```
       goto_if_set 0x51F, _skipPCTransition
   ```
   Add label `_skipPCTransition:` before the existing `return`.

### 3.4 How It Works

1. Player presses L in the overworld.
2. `SetOverworldRequestFlags_hook` fires -> `SetOverworldRequestFlags()`
   sets `OpenPCCheck = TRUE`.
3. `CheckOverworldRequestFlags_hook` fires -> `CheckOverworldRequestFlags()`
   checks `OpenPCCheck && FLAG_PORTA_PC_AVAILABLE`.
4. If both true: sets transient flag `0x51F` (`FLAG_PC_TRANSIENT`),
   triggers PC script `2010` (`std_pokecenter_pc`).
5. Commonscript checks `0x51F` to skip the NPC PC animations (open, close,
   transition).
6. On PC exit, `0x51F` is cleared; `FLAG_PORTA_PC_AVAILABLE` (399) persists.

### 3.5 How to Revert

To fully remove:

1. Delete `src/field/field_request.c`
2. Delete `asm/field/pc_anywhere.s`
3. In `include/config.h`: remove `IMPLEMENT_PORTABLE_PC` and
   `FLAG_PORTA_PC_AVAILABLE` defines.
4. In `armips/include/config.s`: remove `IMPLEMENT_PORTABLE_PC equ 1`.
5. In `hooks`: remove the `#ifdef IMPLEMENT_PORTABLE_PC` ... `#endif` block.
6. In `armips/include/flags.s` lines 413-414: rename
   `FLAG_PORTA_PC_AVAILABLE` back to `FLAG_UNK_18F` and
   `FLAG_PC_TRANSIENT` back to `FLAG_UNK_51F`.
7. In `armips/scr_seq/scr_seq_00003_commonscript.s`: revert the 3 patches
   (remove `goto_if_set` lines, labels, and the `clearflag 0x51F`).

To disable without removing: comment out `#define IMPLEMENT_PORTABLE_PC`.
The hooks won't be installed; the commonscript patches stay harmless because
flag `0x51F` will never be set.

---

## 4. Feature 2 - Debug Pokemon Generator

A debug tool that lets you generate any Pokemon at any level by typing numbers
on the naming screen.

**No ASM hooks required.** Uses the existing `Script_RunNewCmd` (script command 208) multiplexer, which is already wired via `routinepointers`.

**Script must be built in DSPRE** (not in commonscript) to avoid overlay /
touchscreen restore issues with the naming screen.

### 4.1 Sub-command IDs (claimed)

```c
#define SCRIPT_NEW_CMD_PARSE_NICKNAME_NUM    1
#define SCRIPT_NEW_CMD_RESTORE_NICKNAME      2
```

(Sub-command 0 is `SCRIPT_NEW_CMD_REPEL_USE`. 3..255 remain free.)

### 4.2 How It Works

1. Talk to the NPC carrying script 21 (DSPRE).
2. Naming screen opens -- type the **species number** as digits (e.g. `152`
   for Chikorita).
3. Naming screen reopens -- type the **level**.
4. The Pokemon is added to the party with a Poke Ball, no held item.
5. Slot 0 nickname is restored after each input.
6. Empty species (= 0) cancels the script.
7. Level is clamped to `1..100`.

### 4.3 Files to Modify

#### `src/script_new_cmds.c`

Extend the existing switch:

- Add includes for `config.h`, `pokemon.h`, `save.h`.
- Add `#define SCRIPT_NEW_CMD_PARSE_NICKNAME_NUM 1`
- Add `#define SCRIPT_NEW_CMD_RESTORE_NICKNAME   2`
- Add a static helper `ParseNicknameAsNumber(...)` that reads the nickname of
  the party mon at the slot stored in `VAR_SPECIAL_x8004` (`32772`), parses
  the u16 digit characters as an integer, and returns the result.
- Add `case SCRIPT_NEW_CMD_PARSE_NICKNAME_NUM`: calls the helper, stores
  result in `arg0`.
- Add `case SCRIPT_NEW_CMD_RESTORE_NICKNAME`: restores the default species
  name as nickname for the party slot stored in the variable referenced by
  `arg0`. Clears the "has nickname" flag.

> **Source for function bodies:** copy from
> `<backup pre merge>/hg-engine/src/script_new_cmds.c`, then **rename
> identifiers to the new convention** (uppercase `SCRIPT_NEW_CMD_*` already
> matches; double-check nothing inside still uses the old camelCase).

#### `armips/include/scriptmacros.s`

Append after the `queue_new_repel` block (around line 1541):

```asm
.macro parse_nickname_as_number,retvar
    RunNewCommand NEW_COMMAND_PARSE_NICKNAME_NUM, retvar
.endmacro

.macro restore_nickname,slotvar
    RunNewCommand NEW_COMMAND_RESTORE_NICKNAME, slotvar
.endmacro
```

And in the `NEW_COMMAND_*` equ block (around line 6753), append:

```asm
.equ NEW_COMMAND_PARSE_NICKNAME_NUM, 1
.equ NEW_COMMAND_RESTORE_NICKNAME,   2
```

> The macros use snake_case to match the existing `queue_new_repel` style.
> Do NOT name them `ParseNicknameAsNumber` / `RestoreNickname` (old
> camelCase).

### 4.4 DSPRE Script 21 (assign to any debug NPC)

Pattern: Name Rater (`ChoosePokemonNickname` on slot 0, then parse).

```
Script 21:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    SetVar 32772 0                       // VAR_SPECIAL_x8004 = 0 (party slot 0)
    SetVar 32774 0                       // VAR_SPECIAL_x8006 = 0 (party slot 0)

    // -- species input --
    FadeScreen 6 1 0 0
    WaitFadeScreen
    ChoosePokemonNickname 0 32780        // result in VAR_SPECIAL_RESULT
    FadeScreen 6 1 1 0
    WaitFadeScreen
    DummyTextTrap 1 32772                // ParseNicknameAsNumber -> x8004
    DummyTextTrap 2 32774                // RestoreNickname slot from x8006

    CompareVarValue 32772 0
    JumpIf EQUAL Function#20             // cancel

    // -- level input --
    SetVarFromVariable 32775 32772       // x8007 = species (save)
    SetVar 32772 0                       // reset slot for parse
    FadeScreen 6 1 0 0
    WaitFadeScreen
    ChoosePokemonNickname 0 32780
    FadeScreen 6 1 1 0
    WaitFadeScreen
    DummyTextTrap 1 32773                // ParseNicknameAsNumber -> x8005
    DummyTextTrap 2 32774                // RestoreNickname
    SetVarFromVariable 32772 32775       // restore species into x8004

    CompareVarValue 32773 0
    JumpIf EQUAL Function#19             // level=0 -> set 1
    CompareVarValue 32773 100
    JumpIf GREATER Function#21           // level>100 -> cap 100

    GivePokemon 32772 32773 ITEM_NONE 0 0 32780
    ReleaseAll
End

Function 19:                             // level was 0 -> 1
    SetVar 32773 1
    GivePokemon 32772 32773 ITEM_NONE 0 0 32780
    ReleaseAll
End

Function 20:                             // cancel (species 0)
    ReleaseAll
End

Function 21:                             // level capped at 100
    SetVar 32773 100
    GivePokemon 32772 32773 ITEM_NONE 0 0 32780
    ReleaseAll
End
```

**Variable reference:**

- `32772` = `VAR_SPECIAL_x8004` (species number)
- `32773` = `VAR_SPECIAL_x8005` (level)
- `32774` = `VAR_SPECIAL_x8006` (slot for restore = 0)
- `32775` = `VAR_SPECIAL_x8007` (temp: saves species while parsing level)
- `32780` = `VAR_SPECIAL_RESULT`

### 4.5 Character Encoding (verify before apply!)

DS Pokemon games use a custom u16 character encoding. The expected mapping
for digits is:

- `'0'` = `0x0121`, `'1'` = `0x0122`, ... `'9'` = `0x012A`

> **NOT yet verified in CLEAN.** Before applying, grep `charmap.txt` (and/or
> the assembled string tables) to confirm. If the values differ, update the
> `ParseNicknameAsNumber` helper accordingly.

Non-digit characters must be silently ignored during parsing.

### 4.6 How to Revert

1. In `src/script_new_cmds.c`:
   - Remove the new `#include` lines (`config.h`, `pokemon.h`, `save.h`).
   - Remove the two `#define`s.
   - Remove the static helper.
   - Remove the two new `case` blocks.
2. In `armips/include/scriptmacros.s`:
   - Remove the two new `.equ` lines.
   - Remove `parse_nickname_as_number` and `restore_nickname` macros.
3. Delete or unassign DSPRE script 21.

### 4.7 Notes

- The `RunNewCommand` multiplexer supports up to 256 sub-commands.
  Currently 0..2 will be used; 3..255 free.
- Species range: see Section 1. Test only against species that exist in the
  current build.
- Level is u16 in the variables but only `1..100` is meaningful in vanilla
  mechanics.
- The script lives in DSPRE because the naming-screen overlay has
  touchscreen / state-restore issues when called from commonscript.
  Map-specific scripts compiled by DSPRE handle overlay transitions
  correctly.

---

## 5. Reusable Patterns

These patterns are extracted from the two features above and from existing
CLEAN code. They are documented here as a reference for future maintenance
work in this project.

### 5.1 Config double-guard pattern

For any feature that needs **both** C code and ARMIPS assembly:

- C-side (`include/config.h`): `#define IMPLEMENT_<FEATURE>` (and any
  associated numeric constants).
- ASM-side (`armips/include/config.s`): `IMPLEMENT_<FEATURE> equ 1`.
- Hook entries in `hooks` / `armhooks` / `repoints`: wrap with
  `#ifdef IMPLEMENT_<FEATURE>` ... `#endif`.

Commenting out the C `#define` automatically disables hook installation;
ASM patches that rely solely on labels or transient flags become harmless
no-ops.

### 5.2 Transient flag commonscript pattern

To skip a branch of an existing commonscript only when triggered by a new
custom path:

1. Pick an unused flag (here `0x18F`).
2. The custom C entry point sets the flag right before triggering the
   shared script.
3. The shared commonscript's branches that should be skipped get a
   `goto_if_set <flag>, _skipLabel` injected before the unwanted command.
4. `_skipLabel:` either jumps to `return` or runs cleanup (e.g.
   `clearflag <flag>` on logoff).

> **Implementation note (Portable PC):** the transient flag must be
> **distinct** from the persistent gate flag. The original BluRosie commit
> used the same flag (`0x18F` = `FLAG_PORTA_PC_AVAILABLE` = 399) for both
> roles, causing `clearflag` on PC logoff to destroy the persistent gate.
> The CLEAN implementation uses a separate flag `0x51F` (`FLAG_PC_TRANSIENT`)
> to avoid this collision.
5. Any vanilla path leaves the flag clear, so the new gating is a no-op
   for them.

### 5.3 `RunNewCommand` multiplexer pattern (script command 208)

To add a new script command **without** carving an ASM hook:

- The vanilla command 208 (`scrcmd_208`, formerly DummyTextTrap) is
  repointed to `Script_RunNewCmd` via `routinepointers`.
- `Script_RunNewCmd` is a `switch (sub_command_id)` in
  `src/script_new_cmds.c`.
- New behaviour = new `case`. New ID must:
  - Get a `SCRIPT_NEW_CMD_<NAME>` define on the C side.
  - Get a `.equ NEW_COMMAND_<NAME>, <id>` on the ASM side.
  - Get a snake*case macro wrapper in `scriptmacros.s` that calls
    `RunNewCommand NEW_COMMAND*<NAME>, <halfword arg>`.

The halfword arg is typically a script variable id; the helper reads /
writes that variable as needed.

### 5.4 Name Rater input pattern

To accept arbitrary numeric input from the player without a custom UI:

1. Open the naming screen on a party mon (Name Rater style:
   `ChoosePokemonNickname`).
2. After the screen closes, parse the mon's nickname as digits via
   `parse_nickname_as_number`.
3. Restore the original species name with `restore_nickname` so the mon
   isn't permanently renamed.
4. Repeat as needed for additional inputs (saving intermediate values
   into spare `VAR_SPECIAL_x800x` slots).

### 5.5 DSPRE vs commonscript decision rule

- Use **commonscript** (`armips/scr_seq/scr_seq_00003_commonscript.s`) for
  generic, map-agnostic behaviour that is shared across the game.
- Use **DSPRE map scripts** when the script invokes overlays whose
  state-restore is fragile (naming screen, summary screen, certain
  menus). DSPRE compiles these into the map's native script bank, which
  the engine restores correctly on overlay return.
- When in doubt, prototype in DSPRE first; promote to commonscript only
  if the script is genuinely shared across many maps and uses no
  fragile overlay.

---

## 6. Pre-Apply Checklist

Run through these before starting Feature 1 or Feature 2:

- [ ] **Backup the CLEAN tree** (or commit a clean baseline) so the
      revert procedures in Sections 3.5 / 4.6 are trivially available.
- [ ] Confirm the ROM base used here matches the offsets in this doc
      (HG/SS U is the assumed base; offsets `0x021E68xx` / `0x021E69xx` /
      `0x021E6Axx` should fall inside the field/overworld code).
- [ ] **Feature 1 only:** verify that flag `0x18F` (399) is not used
      anywhere else in the project (rg `0x18F\b|FLAG_UNK_18F|\b399\b`
      across `armips/`, `src/`, `include/`).
- [ ] **Feature 2 only:** verify the digit u16 encoding in `charmap.txt`
      matches `0x0121..0x012A`. If not, update the parser.
- [ ] **Feature 2 only:** confirm that `Script_RunNewCmd` is still
      hooked at `routinepointers` line 8 (`arm9 Script_RunNewCmd 080FB040`).
- [ ] After applying, run a clean `make` and resolve any new warnings
      before testing in-game.
- [ ] Test on hardware (or a strict emulator) -- naming-screen overlay
      issues are flaky on some emulators.

---

## 7. Out of Scope (notes for the user)

- **Custom fakemon (Terratops, Ignisoar, Dipplash, Sinfae):** are now ported
  into the CLEAN C data files. Future Debug Generator work should test against
  the current `MAX_MON_NUM` and `MAX_SPECIES_INCLUDING_FORMS` values in
  `include/constants/species.h`.
- **Species `1079` and Mega start `1080`:** are current again after the merge
  resolution. `1079` is `SPECIES_SINFAE`; `1080` is `SPECIES_MEGA_START`.

---

## 8. In-Game Flags & Currently-Enabled Config Features

This section documents **which flags must be set via game scripts** for the
features above to actually trigger, and **which `config.h` / `config.s`
features are currently enabled** in this CLEAN base. Use it as a quick
reference when wiring scripts in DSPRE or when toggling features.

### 8.1 In-Game Flags to Enable

These flags are **NOT auto-set** by the engine. They must be set with a
`setflag` script command (e.g. on receiving a key item, finishing an event,
etc.) for the corresponding feature to activate.

| Flag                             | Value  | Purpose                                                              | When to set                                                      |
| -------------------------------- | ------ | -------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `FLAG_PORTA_PC_AVAILABLE`        | `399`  | Gates the Portable PC. While clear, pressing L does nothing.         | Once the player should be able to use the L-button PC anywhere.  |
| `HIDDEN_ABILITIES_FLAG`          | `2600` | Wild Pokemon spawn with their hidden ability while this flag is set. | Toggle on/off as a debug or post-game feature.                   |
| `HIDDEN_ABILITIES_STARTERS_FLAG` | `2601` | Starter Pokemon receive their hidden ability while this flag is set. | Set before the starter selection event (debug / special routes). |
| `FLAG_MEGA_EVOLUTION_ENABLED`    | `2518` | Required for Mega Evolution to be usable in battle.                  | After receiving the Mega Bracelet / equivalent key item.         |
| `FLAG_Z_MOVE_ENABLED`            | `2519` | Required for Z-Moves to be usable in battle.                         | After receiving the Z-Ring / equivalent.                         |
| `FLAG_DYNAMAX_ENABLED`           | `2520` | Required for Dynamax to be usable.                                   | After receiving the Dynamax Band / equivalent.                   |
| `FLAG_TERASTALIZATION_ENABLED`   | `2521` | Required for Terastallization to be usable.                          | After receiving the Tera Orb / equivalent.                       |

> **Flag separation note:** The original BluRosie commit used flag `0x18F`
> (`399` = `FLAG_PORTA_PC_AVAILABLE`) for **both** the persistent gate and
> the commonscript transient signal. This caused `clearflag` on PC logoff
> to destroy the persistent gate. The CLEAN implementation uses a
> **separate transient flag** `0x51F` (`1311` = `FLAG_PC_TRANSIENT`) to
> avoid this collision. The transient flag is managed automatically by the
> C code and commonscript patches; it must never be manually set or cleared.

### 8.2 Currently-Enabled `include/config.h` Features

Active `#define`s in CLEAN (defaults shipped with this base):

- `FAIRY_TYPE_IMPLEMENTED 1` -- Fairy type as type 9.
- `TYPE_EFFECTIVENESS_GEN GEN_LATEST` -- modern type chart.
- `ALLOW_SAVE_CHANGES` -- expanded save fields (breaks PKHeX compatibility).
- `EXPERIENCE_FORMULA_GEN GEN_LATEST` -- gen-9 scaled exp formula.
- `HIDDEN_ABILITIES` (with flag `2600` / starters flag `2601`).
- `MEGA_EVOLUTIONS`.
- `PRIMAL_REVERSION`.
- `ITEM_POCKET_EXPANSION`.
- `IMPLEMENT_BDHCAM_ROUTINE`.
- `IMPLEMENT_CAPTURE_EXPERIENCE`.
- `IMPLEMENT_CRITICAL_CAPTURE` (gen-latest formula).
- `IMPLEMENT_NEW_EV_IV_VIEWER`.
- `UPDATE_OVERWORLD_POISON`.
- `IMPLEMENT_SEASONS`.
- `IMPLEMENT_DEXIT_FORMS_MECHANICS`.
- `EXPAND_PC_BOXES` (max 30 boxes).
- `SHINY_ODDS 8` (vanilla 1/8192).
- `FRIENDSHIP_EVOLUTION_THRESHOLD 160` + `FRIENDSHIP_EFFECTS`.
- `RESTORE_ITEMS_AT_BATTLE_END`.
- `AI_CAN_GRAB_ITEMS`.
- `PROTEAN_GENERATION GEN_LATEST` (changes type once per appearance).
- `CORROSIVE_GAS_IMPLIED_BEHAVIOUR TRUE`.
- `SNOW_WARNING_GENERATION GEN_LATEST` (Snow, not Hail).
- `IMPLEMENT_REUSABLE_REPELS` -- prompt to reuse repels.
- `UPDATE_VITAMIN_EV_CAPS` -- vitamins cap at 252.
- `REUSABLE_TMS` -- TMs are infinite, quantity hidden.
- `MART_EXPANSION`.
- `IMPLEMENT_PORTABLE_PC` -- press L in the overworld to open the PC
  (gated by flag 399).
- `STATIC_HP_BAR` -- gen-latest fixed-rate HP bar.
- `UPDATE_MACHINE_MOVE_LABELS`.
- Ball generations: `NEST/NET/REPEAT/TIMER/DUSK/QUICK/MOON/FRIEND_BALL_GENERATION = GEN_LATEST`;
  `SAFARI/LURE/SPORT_BALL_GENERATION = 4`.
- `NATURAL_GIFT_POWER_GEN GEN_LATEST`.
- `BLOCK_LEARNING_UNIMPLEMENTED_MOVES`.
- `VANILLA_PARADOX_BOOSTER_ENERGY_BEHAVIOUR`.
- `VANILLA_MYTHICALS`.
- `DISABLE_CRITICAL_HP_WARNING`.

Currently **disabled** (commented out) -- relevant to remember when a
feature looks broken:

- `IMPLEMENT_TRANSPARENT_TEXTBOXES`
- `IMPLEMENT_WILD_DOUBLE_BATTLES` (broken upstream)
- `IMPLEMENT_LEVEL_CAP` (and the related sub-defines)
- `DISABLE_END_OF_TURN_WEATHER_MESSAGE`
- `IMPLEMENT_DYNAMIC_WILD_SPECIES_FORMS`
- `DISABLE_ITEMS_IN_TRAINER_BATTLE`
- `DELETABLE_HMS`
- `POKEATHLON_SHOP_EXPANSION`
- `THUNDER_STORM_WEATHER_ELECTRIC_TERRAIN`
- `FOG_WEATHER_MISTY_TERRAIN`

### 8.3 Currently-Enabled `armips/include/config.s` Features

Active equ values (mirrors of the C side, plus ASM-only knobs):

- `GEN_LATEST equ 9`
- `START_ADDRESS equ 0x10`
- `DISALLOW_DEXIT_GEN equ 0` -- disable any unimplemented moves entirely.
- `FAIRY_TYPE_IMPLEMENTED equ 1`
- `TYPE_EFFECTIVENESS_GEN equ GEN_LATEST`
- `SNOW_WARNING_GENERATION equ GEN_LATEST`
- `ALLOW_SAVE_CHANGES = 0` (defined via `.definelabel`; matches `ALLOW_SAVE_CHANGES` on the C side).
- `CRY_PSEUDOBANK_START equ 778`
- `BATTLE_MODE_FORCE_SET equ 0` -- player can switch out (no forced "set" mode).
- **`ALWAYS_HAVE_NATIONAL_DEX equ 1`** -- player has the national dex from the start (debug-friendly).
- `ALWAYS_UNCAPPED_FRAME_RATE equ 0`
- `BATTLES_UNCAPPED_FRAME_RATE equ 0`
- **`FAST_TEXT_PRINTING equ 1`** -- text prints almost instantly.
- `NO_PARTNER_DOUBLE_BATTLES equ 1` -- doubles can be set without a partner trainer (use `.type = TRMSG_DBL_LOSE_1` in `data/Trainers.c`).
- `APPLY_ANTIPIRACY = 0` (defined via `.definelabel`).
- `IMPLEMENT_PORTABLE_PC equ 1` -- press L in the overworld to open the PC (gated by flag 399).

### 8.4 Cross-reference summary

To get the Portable PC working in a saved game you must:

1. Apply Feature 1 (Portable PC) — **done**.
2. Build the ROM.
3. In a game script (DSPRE or commonscript), at the appropriate story
   beat, run `setflag FLAG_PORTA_PC_AVAILABLE` (= flag `399`).
4. From then on, pressing L in the overworld opens the PC.

For all other gameplay flags (Mega, Z-Move, Dynamax, Tera, Hidden
Abilities) the same pattern applies: `setflag <value>` from a script when
the player should gain access; `clearflag` to revoke it.

---

## 10. Fakemon Implementation Protocol

This section documents the **complete strategy** for adding a new custom fakemon
to the CLEAN base, including the information-gathering protocol used by the
previous implementation notes
to collect all required parameters from the user.

### 10.1 Files Modified Per Fakemon

The upstream merge moved most species data out of the old ASM data files and into C
initializer files under `data/`. New fakemon work should update the C files
first; the old `.s` files are migration references only while this merge is
open.

| #   | File                              | What to insert                                                        |
| --- | --------------------------------- | --------------------------------------------------------------------- |
| 1   | `include/constants/species.h`     | `#define SPECIES_<NAME> (SPECIES_LAST_FAKEMON + 1)` and count updates |
| 2   | `asm/include/species.inc`         | Matching `.equ SPECIES_<NAME>, ...` and count updates                 |
| 3   | `data/Species.c`                  | `SpeciesData` entry: stats, types, abilities, dex text, metrics       |
| 4   | `data/Evolutions.c`               | Evolution list, or only `EVO_NONE` entries if no evolution            |
| 5   | `data/BabyMons.c`                 | Baby species mapping, usually self for a standalone fakemon           |
| 6   | `data/IconPaletteTable.c`         | Icon palette byte                                                     |
| 7   | `data/PokedexArea.c`              | Area data blocks; keep empty per-bank lists even if no area data      |
| 8   | `data/PokedexSort.c`              | National/sort list references                                         |
| 9   | `data/RegionalDex.c`              | Regional dex number                                                   |
| 10  | `data/SpriteOffsets.c`            | Front/back sprite offset and shadow data                              |
| 11  | `src/field/overworld_table.c`     | OW table entry `{ .tag, .gfx, OVERWORLD_SIZE_* }`                     |
| 12  | `data/SpeciesToOWFormFemale.c`    | Female/special OW form mapping only when needed                       |
| 13  | `data/learnsets/base/custom.json` | Custom learnset source                                                |
| 14  | `data/learnsets/learnsets.json`   | Generated/merged learnset output                                      |

`data/PokedexArea.c` uses eight area banks. Its list stride is the number of
base species slots, not the last species id: `MAX_MON_NUM + 1`. In ASM terms,
`NUM_OF_MONS` mirrors the highest base species id, so dump/export tooling uses
`NUM_OF_MONS + 1`. With `SPECIES_SINFAE = 1079`, the stride is `1080`.

**Not touched automatically** (user-managed unless explicitly requested):

- `data/Encounters.c` -- encounter slots and wild placement
- `data/graphics/pokegra.mk` -- graphics build rules, preferably regenerated
- `data/graphics/sprites/<id>/` -- sprite assets
- `data/graphics/sprites/<id>/overworld.*` -- overworld assets
### 10.2 Placeholder Strategy

Where values depend on graphics not yet created, use **Terratops placeholders**:

- Sprite offsets: `2, 5, -16, 5, SHADOW_SIZE_SMALL`
- Pokedex Y pos / scale: copy from `SPECIES_TERRATOPS` entries
- Icon palette: `0x1`
- Overworld tag/gfx: incremental after last fakemon
- Overworld bounce: `OVERWORLD_BOUNCE_MED`

These must be updated when graphics are inserted (see Section 10.4).

### 10.3 Information-Gathering Protocol

When the user requests a new fakemon, ask the following questions
**sequentially** (one at a time, in order):

1. **Dex classification** (e.g. "Skull Pokémon")
2. **Base stats** (HP / Atk / Def / SpA / SpD / Spe) — or "copy [species]"
3. **Types** (primary + secondary; pure = `TYPE_X, TYPE_X`)
4. **Abilities** (slot 1, slot 2 or `ABILITY_NONE`, hidden ability)
5. **Catch rate** (0–255)
6. **EXP yield** (or "0" if managed externally)
7. **EV yield** (which stat, how many EVs)
8. **Gender ratio** (87.5% M = 31 for starters, or 50/50)
9. **Egg groups** (primary, secondary)
10. **Egg cycles**
11. **Growth rate** (e.g. `GROWTH_MEDIUM_SLOW`)
12. **Base friendship**
13. **Body color** (`BODY_COLOR_*` constant)
14. **Wild held items** (`ITEM_NONE, ITEM_NONE` default)
15. **Run chance** (0 default)
16. **Pokedex height** (DS format: `X'YY"`)
17. **Pokedex weight** (DS format: `XX.X lbs.`)
18. **Pokedex description** (max 3 lines, `\n` separated)
19. **Dex numbers** (national + regional; usually incremental)
20. **Evolution data** (none = `EVO_NONE` x7, or specific evolutions)

Once all info is collected, present the **complete implementation
plan** with all values resolved, then waits for user confirmation before
making any edits.

### 10.4 Post-Implementation Steps (user action)

After the fakemon data is applied:

1. User creates sprite assets in `data/graphics/sprites/<id>/`
2. User regenerates or updates `data/graphics/pokegra.mk` with graphics build rules
3. User updates **all placeholder values** that depend on graphics:
   - `data/SpriteOffsets.c` (actual sprite dimensions/offsets)
   - `data/Species.c` (height, weight, dex text, classification, metrics)
   - `data/PokedexArea.c` (replace empty area lists with actual data if any; do not remove the empty bank entries)
   - `src/field/overworld_table.c` (actual tag and gfx IDs)
   - `data/SpeciesToOWFormFemale.c` (female/special OW form mapping only if needed)
4. User adds encounter slots in `data/Encounters.c` as needed
5. User tests in-game, resolves any build warnings
6. Fakemon entry appended to Fakemon Tracker (Section 9)
### 10.5 Dex Numbering Convention

Fakemon dex numbers are **incremental** (no gaps) to avoid potential issues
with sort lists, dex lookups, and array bounds. Start from `258` (next after
Terratops at 257) and increment by 1 for each new species:

| Species   | Dex # | Notes         |
| --------- | ----- | ------------- |
| Terratops | 257   | First fakemon |
| Ignisoar  | 258   | Incremental   |
| Dipplash  | 259   | Incremental   |
| ...       | +1    | And so on     |

National and regional dex numbers should match for custom fakemon
(unless a specific regional ordering is desired).

---

## 9. Custom Fakemon Tracker

This section logs the fakemon that have been re-imported into the CLEAN
base, in the order the user adds them. Each entry is appended manually
after the corresponding fakemon's data (species entry, sprites, learnset,
encounter slots, etc.) has been brought across.

| #   | Internal name | Display name | Status      | Notes                                             |
| --- | ------------- | ------------ | ----------- | ------------------------------------------------- |
| 1   | TERRATOPS     | Terratops    | Implemented | First custom fakemon ported into the CLEAN base.  |
| 2   | IGNISOAR      | Ignisoar     | Implemented | Fire-type, incremental dex 258.                   |
| 3   | DIPPLASH      | Dipplash     | Implemented | Water-type, incremental dex 259.                  |
| 4   | SINFAE        | Sinfae       | Implemented | Psychic-type legendary, dex 260, copy of Mesprit. |

- FLAG 2600 can be used to enable wild mons to have their hidden abilities,
  2601 for starters.

---

## 11. Fakemon Species ID Notation (STRICT)

The **only** valid pattern for defining new fakemon species IDs:

**`include/constants/species.h`:**

```c
#define SPECIES_<NAME> (MAX_CANONICAL_MON_NUM + <N>)  // N = 1, 2, 3... sequential
```

**`asm/include/species.inc`:**

```asm
.equ SPECIES_<NAME>, (MAX_CANONICAL_MON_NUM + <N>)
```

Increment `NUM_OF_FAKEMONS` accordingly. The `MAX_CANONICAL_MON_NUM` is defined
as `(SPECIES_PECHARUNT)` — the last official species.

**NEVER** use `(SPECIES_LAST_FAKEMON + 1)` — that pattern is obsolete.

After changing base fakemon counts, keep the Pokedex area archive dense through
`MAX_MON_NUM + 1` slots per bank. `data/PokedexArea.c` and
`tools/source/dumptools/dump_scripts/pokedex_data.py` must agree on that stride.

---

## 12. Build Rule (ABSOLUTE)

**NEVER** run `make` or any build/compile command. After completing file edits,
stop immediately and say:

> maestro, ora può buildare il suo capolavoro

The user will handle the build. No exceptions.

---

## 13. Fakemon Alternative Form Protocol

### 13.1 When to Use Forms vs New Species

| Scenario                                                      | Nuova specie | Forma alternativa |
| ------------------------------------------------------------- | ------------ | ----------------- |
| Pokémon completamente nuovo, dex # unico                      | ✅           | ❌                |
| Variante di specie esistente (tipo/stats/abilità diversa)     | ❌           | ✅                |
| Forma reversibile solo in battaglia (es. mega, battle-only)   | ❌           | ✅                |
| Forma estetica permanente (es. Vivillon, Alolan, Kecleon_alt) | ❌           | ✅                |

### 13.2 Species ID Notation (FORMS)

**`include/constants/species.h`**, dopo il blocco `MAX_SPECIES_CANONICAL_FORM_NUM`:

```c
#define SPECIES_<NAME>_<FORM> (MAX_SPECIES_CANONICAL_FORM_NUM + <N>)   // N = 1, 2, 3...
#define NUM_OF_FAKEMONS_FORM <N>
```

**`asm/include/species.inc`**, speculare **ma con N-1** perché
`MAX_CANONICAL_SPECIES_INCLUDING_FORMS` è già 1 avanti rispetto al C:

```asm
.equ SPECIES_<NAME>_<FORM>, (MAX_CANONICAL_SPECIES_INCLUDING_FORMS + (<N> - 1))   // N = 1, 2, 3...
.equ NUM_OF_FAKEMON_FORMS, <N>
```

Esempio concreto (Sinfae Shadow = N=1, Kecleon Alt = N=2):

```c
// species.h
#define SPECIES_SINFAE_SHADOW (MAX_SPECIES_CANONICAL_FORM_NUM + 1)   // = 1393
#define SPECIES_KECLEON_ALT (MAX_SPECIES_CANONICAL_FORM_NUM + 2)     // = 1394
```

```asm
; species.inc
.equ SPECIES_SINFAE_SHADOW, (MAX_CANONICAL_SPECIES_INCLUDING_FORMS)      // = 1393 (N-1 = 0)
.equ SPECIES_KECLEON_ALT, (MAX_CANONICAL_SPECIES_INCLUDING_FORMS + 1)    // = 1394 (N-1 = 1)
```

> **Nota:** `MAX_CANONICAL_SPECIES_INCLUDING_FORMS = SPECIES_PALDEAN_FORMS_START + NUM_OF_PALDEAN_FORMS = 1393`,
> mentre `MAX_SPECIES_CANONICAL_FORM_NUM = SPECIES_TERAPAGOS_STELLAR = 1392`. La differenza di 1 tra le due basi
> è intenzionale: l'ASM conta "uno dopo l'ultimo", il C conta "l'ultimo numero".
> Quindi l'ASM usa `+0` dove il C usa `+1`, `+1` dove il C usa `+2`, ecc.

Differenza chiave dai fakemon base: le forme usano
`MAX_SPECIES_CANONICAL_FORM_NUM` (= dopo `SPECIES_TERAPAGOS_STELLAR`), non
`MAX_CANONICAL_MON_NUM`. Contatore separato `NUM_OF_FAKEMONS_FORM`.

Non dimenticare di incrementare `NUM_OF_FAKEMON_FORMS` nell'ASM quando aggiungi
una nuova forma, in modo che `NUM_OF_TOTAL_MONS_PLUS_FORMS` sia corretto.

### 13.3 NEEDS_REVERSION Logic

Usa `NEEDS_REVERSION \| SPECIES_<FORM>` in `PokeFormDataTbl.c` quando la forma
esiste **solo durante la battaglia** e deve **revertire alla forma base** al
termine della lotta.

**SI usa NEEDS_REVERSION:** Mega evoluzioni, Primal, Castform/Cherrim/Minior,
Darmanitan Zen, Aegislash Blade, Greninja Ash, Zygarde Complete, Palafin Hero,
Ogerpon Terastal, Terapagos Terastal/Stellar, battle-only custom (es.
SINFAE_SHADOW).

**NON si usa NEEDS_REVERSION:** Forme cosmetiche permanenti, forme regionali
(Alolan/Galarian/Hisuian/Paldean), Vivillon, Furfrou, Pumpkaboo, forme
decorative (es. KECLEON_ALT).

> Se l'utente non specifica il tipo di forma, chiedere esplicitamente: "Questa
> forma è **battle-only** (reversibile) o **permanente** (cosmetica)?"

### 13.4 Files to Modify

**Inserimento SEMPRE in fondo alle liste/array dedicati** (a differenza dei
fakemon base che vanno subito dopo gli ultimi fakemon base):

| #   | File                              | Cosa inserire                                                     | Obbligatorio? |
| --- | --------------------------------- | ----------------------------------------------------------------- | ------------- |
| 1   | `include/constants/species.h`     | `#define SPECIES_<NAME>_<FORM>` + `NUM_OF_FAKEMONS_FORM`          | Yes           |
| 2   | `asm/include/species.inc`         | `.equ` speculare                                                  | Yes           |
| 3   | `data/PokeFormDataTbl.c`          | Entry sotto `[SPECIES_<BASE>]` con eventuale `NEEDS_REVERSION |` | Yes           |
| 4   | `data/FormToSpeciesMapping.c`     | `[SPECIES_<FORM> - SPECIES_MEGA_START] = SPECIES_<BASE>`          | Yes           |
| 5   | `data/Species.c`                  | Species data completo per la forma                                | Yes           |
| 6   | `data/Evolutions.c`               | Evoluzioni della forma, di solito solo `EVO_NONE`                 | Yes           |
| 7   | `data/IconPaletteTable.c`         | Icon palette                                                      | Yes           |
| 8   | `data/SpriteOffsets.c`            | Placeholder sprite offsets                                        | Yes           |
| 9   | `data/learnsets/base/custom.json` | Learnset solo se diverso dal base                                 | No            |
| 10  | `data/learnsets/learnsets.json`   | Learnset solo se diverso dal base                                 | No            |
| 11  | `src/field/overworld_table.c`     | OW table entry solo se ha OW gfx proprio                          | No            |
| 12  | `data/SpeciesToOWFormFemale.c`    | Female/special OW mapping solo quando serve                        | No            |

**NON toccare** (le forme NON hanno questi dati base):

- `data/BabyMons.c`
- `data/PokedexSort.c`
- `data/RegionalDex.c`
- `data/PokedexArea.c`

**Mai toccati dal protocollo** (gestiti dall'utente):

- `data/graphics/sprites/<id>/` -- asset PNG
- `data/graphics/pokegra.mk` -- regole di build, preferibilmente rigenerate
- `data/Encounters.c` -- spawn selvatici
### 13.5 Information-Gathering Protocol

Quando l'utente richiede una nuova forma alternativa, chiedere
**sequenzialmente**:

1. **Nome specie base** (es. SINFAE, KECLEON)
2. **Nome forma** (es. SHADOW, ALT)
3. **Tipo di forma**: battle-only (`NEEDS_REVERSION`) o permanente?
4. **Base stats** — o "copy [species]" (default: copia base)
5. **Tipi** (se diversi dal base)
6. **Abilità** (slot 1, slot 2, hidden; default: copia base)
7. **Catch rate** (0 se uncatchable; default: copia base)
8. **EV yield** (default: copia base)
9. **Gender ratio** (default: copia base)
10. **Egg groups** (default: copia base)
11. **Growth rate** (default: copia base)
12. **Body color** (se diverso dal base)
13. **Peso** (formato `XX.X lbs.`)
14. **Sprite offsets** (placeholder dal base)
15. **Icon palette** (valore esadecimale)
16. **Ha overworld graphics?** Se sì: tag/gfx/OW size/bounce incrementale
17. **Ha learnset diverso dal base?** Se sì: elenco mosse level-up
18. **Base exp** (default: 0)

### 13.6 Post-Implementation Steps (user action)

1. Creare sprite in `data/graphics/sprites/<id>/`
2. Creare OW graphics accanto alla cartella sprite (se applicabile)
3. Rigenerare o aggiornare `data/graphics/pokegra.mk`
4. Aggiungere spawn in `data/Encounters.c` (se applicabile)
5. Testare in-game
### 13.7 Overworld Form Insertion (esistenti)

**Quando serve:** una forma alternativa di un Pokemon **esistente** (es. KECLEON_ALT per Kecleon) DEVE avere il proprio sprite overworld.

Se l'utente non specifica se la forma ha un OW proprio, CHIEDERE esplicitamente: "Questa forma ha bisogno di un proprio sprite overworld?"

#### Come funziona

Il chiamante di `grab_overworld_a081_index` risolve le forme alternative in
(specie_base, form_index). Quindi KECLEON_ALT -> (KECLEON, 1). Il tag calcolato
e basato sulla species risolta (`MON_OVERWORLD_TAG_START + resolvedSpecies`).
Per una forma con OW proprio, aggiungere una entry esplicita in `gOWTagToFileNum`.

#### Operazioni sui file C (shift coordinato)

1. **`src/field/overworld_table.c` (`gOWTagToFileNum`):** inserire la nuova entry con tag = tag_base + form_index e la gfx corrispondente. Shiftare tutte le entry successive di +1. Rimuovere eventuali entry leftover della vecchia implementazione.

2. **`data/SpeciesToOWFormFemale.c` (solo se applicabile):** aggiornare la mappa delle forme female/speciali se la forma ha una variante OW separata che il motore deve risolvere tramite mask o form id.

**Importante:** `data/SpeciesToOWGfx.c` non e piu usato dal build.
`GetPokemonOwNum()` ritorna la species e `get_mon_ow_tag()` risolve forme/gender
tramite `GetSpeciesBasedOnForm()` e `SpeciesToOWFormFemale.c`.

---
## 14. Battle Transformation Pattern (Sinfae → Sinfae Shadow)

Protocollo per implementare una trasformazione battle-only che cambia tipo/stats
di un Pokémon durante la battaglia e **revertisce automaticamente** al termine.

### 14.1 How It Works (Sinfae)

- **Gatillante:** Sinfae usa **Tail Whip** (mossa 39) in battaglia
- **Toggle:** ogni uso di Tail Whip alterna tra forma base e Shadow
- **Battle-only:** `NEEDS_REVERSION` fa revertire a Sinfae base al termine
- **Stat-identical:** 80/105/105/105/105/105 in entrambe le forme
- **Tipo cambia:** Psychic → Dark/Psychic
- **Ability identica:** LEVITATE in entrambe

### 14.2 File da Modificare

| #  | File                     | Cosa                                             |
|----|--------------------------|--------------------------------------------------|
| 1  | `include/constants/species.h` | `#define SPECIES_<NAME>_<FORM>`              |
| 2  | `asm/include/species.inc`    | `.equ` speculare                              |
| 3  | `data/PokeFormDataTbl.c`  | `NEEDS_REVERSION \| SPECIES_<FORM>` sotto base |
| 4  | `data/FormToSpeciesMapping.c` | `[SPECIES_<FORM> - SPECIES_MEGA_START] = SPECIES_<BASE>` |
| 5  | `include/battle.h`        | `BEFORE_MOVE_STATE_<NAME>_CHANGE` enum        |
| 6  | `src/individual/BattleController_BeforeMove.c` | Forward decl, switch case, funzione transform |
| 7  | `data/Species.c`          | Species data per la forma                     |
| 8  | `data/Evolutions.c`       | Evoluzioni della forma, di solito `EVO_NONE`  |
| 9  | `data/IconPaletteTable.c` | Icon palette                                  |
| 10 | `data/SpriteOffsets.c`    | Placeholder sprite offsets                    |

### 14.3 Codice Trasformazione

**`include/battle.h`** -- enum entry subito dopo Stance Change:

```c
BEFORE_MOVE_STATE_STANCE_CHANGE,
BEFORE_MOVE_STATE_SINFAE_CHANGE,
```

**`src/individual/BattleController_BeforeMove.c`** -- forward declaration:

```c
void BattleController_CheckSinfaeChange(struct BattleSystem *bsys, struct BattleStruct *ctx);
```

**Dispatch nello switch `wb_seq_no`:**

```c
case BEFORE_MOVE_STATE_SINFAE_CHANGE: {
    BattleController_CheckSinfaeChange(bsys, ctx);
    ctx->wb_seq_no++;
    return;
}
```

**Helper condiviso con Aegislash/Stance Change:**

```c
static void BattleController_StartFormChange(
    int battlerId,
    int formNo,
    struct BattleSystem *bsys,
    struct BattleStruct *ctx)
{
    ctx->battlerIdTemp = battlerId;
    ctx->battlemon[battlerId].form_no = formNo;
    BattleFormChange(battlerId, formNo, bsys, ctx, 0);
    LoadBattleSubSeqScript(ctx, ARC_BATTLE_SUB_SEQ, SUB_SEQ_FORM_CHANGE);
    ctx->next_server_seq_no = ctx->server_seq_no;
    ctx->server_seq_no = CONTROLLER_COMMAND_RUN_SCRIPT;
}
```

**Logica SINFAE:**

```c
void BattleController_CheckSinfaeChange(struct BattleSystem *bsys, struct BattleStruct *ctx)
{
    int attacker = ctx->attack_client;

    if (ctx->battlemon[attacker].species != SPECIES_SINFAE
        || ctx->current_move_index != MOVE_TAIL_WHIP) {
        return;
    }

    if (ctx->battlemon[attacker].form_no == 0) {
        BattleController_StartFormChange(attacker, 1, bsys, ctx);
    } else if (ctx->battlemon[attacker].form_no == 1) {
        BattleController_StartFormChange(attacker, 0, bsys, ctx);
    }
}
```

**Pattern chiave:**

1. Il controllo resta move-gated su `MOVE_TAIL_WHIP`, senza ability requirement.
2. Il cambio forma usa lo stesso percorso di Aegislash: aggiorna `form_no`, chiama `BattleFormChange`, poi lancia `SUB_SEQ_FORM_CHANGE`.
3. Se le ability delle due forme diventano diverse, aggiornare il quinto argomento di `BattleFormChange` nel helper da `0` a `1` o specializzare il helper.
### 14.4 Form Data & Reversion

**`data/PokeFormDataTbl.c:716-718`:**
```c
[SPECIES_SINFAE] = {
    NEEDS_REVERSION | SPECIES_SINFAE_SHADOW,
},
```

L'array è indicizzato per specie base. Ogni entry lista le forme (form 1, form 2, ...). Il flag `NEEDS_REVERSION` dice al motore di **revertire obbligatoriamente** a fine battaglia.

**`data/FormToSpeciesMapping.c:323`:**
```c
[SPECIES_SINFAE_SHADOW - SPECIES_MEGA_START] = SPECIES_SINFAE,
```

Array usato da `BattleEndRevertFormChange()` → `RevertFormChange()` per mappare la specie forma (`1394`) alla specie base (`1079`) quando `NEEDS_REVERSION` è attivo. La form_no viene azzerata e stats/ability ricalcolati.

### 14.5 Flusso Completo

```
Player seleziona Tail Whip
  → BattleController_BeforeMove() macchina a stati (wb_seq_no)
    → BEFORE_MOVE_STATE_SINFAE_CHANGE
      → BattleController_CheckSinfaeChange()
        → species == SPECIES_SINFAE, move == MOVE_TAIL_WHIP, form == 0
          → form_no = 1
          → BattleFormChange() aggiorna tipi a Dark/Psychic
          → SUB_SEQ_FORM_CHANGE animazione
        → (oppure form == 1 → revert a Psychic)
    → stati successivi (Move Type Changes, PP decrement, etc.)
    → Tail Whip esegue col nuovo tipo

Battaglia termina
  → BattleEndRevertFormChange() (battle_pokemon.c:885)
    → RevertFormChange() (pokemon.c:1813)
      → Legge form table: NEEDS_REVERSION | SPECIES_SINFAE_SHADOW
      → Legge mapping: SPECIES_SINFAE_SHADOW → SPECIES_SINFAE
      → form_no = 0, ricalcola stats
```

### 14.6 Parametri Modificabili

| Parametro          | Dove cambiare                                              | Esempio Sinfae             |
|--------------------|------------------------------------------------------------|----------------------------|
| **Mossa trigger**  | `ctx->current_move_index == MOVE_<X>` in `CheckSinfaeChange` | `MOVE_TAIL_WHIP` (39)      |
| **Ability check**  | `ctx->battlemon[...].ability == ABILITY_<X>` nel `if`      | Non usato (nessun check)   |
| **SwitchAbility**  | Ultimo argomento di `BattleFormChange(..., ..., ..., ..., 0/1)` | `0` (stessa ability)    |
| **Form data**      | `data/PokeFormDataTbl.c` sotto `[SPECIES_<BASE>]`           | `NEEDS_REVERSION \| SPECIES_SINFAE_SHADOW` |
| **NEEDS_REVERSION** | Rimuovere = forma permanente anche fuori battaglia        | Attivo (battle-only)       |

### 14.7 Aggiungere Nuova Trasformazione (Checklist)

Per copiare il pattern per un altro Pokémon:

1. Definire specie forma in `species.h` / `species.inc`
2. Aggiungere `NEEDS_REVERSION` in `PokeFormDataTbl.c`
3. Aggiungere mapping in `FormToSpeciesMapping.c`
4. Aggiungere `BEFORE_MOVE_STATE_<NAME>_CHANGE` in `battle.h` (dopo `BEFORE_MOVE_STATE_STANCE_CHANGE`)
5. In `BattleController_BeforeMove.c`:
   - Forward declaration
   - `case BEFORE_MOVE_STATE_<NAME>_CHANGE:` dispatcher
   - Funzione `BattleController_Check<Name>Change()` copiata da `CheckSinfaeChange`
6. Modificare: specie, mossa trigger, eventuale ability check, `SwitchAbility` flag
7. Aggiungere i dati forma in `data/Species.c`, `data/Evolutions.c`, `data/IconPaletteTable.c` e `data/SpriteOffsets.c`

---

## 15. Double Battle Trainer Patterns

### 15.1 Overview

Two ways to make a trainer fight a double battle:

| Battle type | Value | Partner NPC needed? | Overworld entries | Walk animation | Text entries |
|---|---|---|---|---|---|
| `SINGLE_BATTLE` | 0 | No | 1 | Normal | 3 (single pattern) |
| `DOUBLE_BATTLE` | 2 | **Yes** (2 NPCs) | 2 | Side-by-side walk | **6-8** (full double pattern) |
| `NO_PARTNER_DOUBLE_BATTLE` | 3 | **No** (1 NPC) | 1 | Normal | **3** (reduced double pattern) |

### 15.2 Prerequisites

- `NO_PARTNER_DOUBLE_BATTLES equ 1` in `armips/include/config.s` -- enabled in CLEAN.
- Battle type constants are defined in `include/trainer_data.h` and mirrored in `armips/include/constants.s`:
  ```c
  #define SINGLE_BATTLE            0
  #define DOUBLE_BATTLE            2
  #define NO_PARTNER_DOUBLE_BATTLE 3
  ```
- Trainer teams and trainer text now live together in `data/Trainers.c`.

### 15.3 All Text Types for Battles

| Constant | Value | Used by |
|---|---:|---|
| `TRMSG_INTRO` | 0 | Single battle -- pre-battle |
| `TRMSG_LOSE` | 1 | Single battle -- defeat in battle |
| `TRMSG_AFTER` | 2 | Single battle -- post-battle in overworld |
| `TRMSG_DBL_INTRO_1` | 3 | Any double -- pre-battle (trainer 1) |
| `TRMSG_DBL_LOSE_1` | 4 | Any double -- defeat in battle (trainer 1) |
| `TRMSG_DBL_AFTER_1` | 5 | Any double -- post-battle (trainer 1) |
| `TRMSG_DBL_1POKE_1` | 6 | Any double -- player has 1 mon (trainer 1) |
| `TRMSG_DBL_INTRO_2` | 7 | Any double -- pre-battle (trainer 2) |
| `TRMSG_DBL_LOSE_2` | 8 | Any double -- defeat in battle (trainer 2) |
| `TRMSG_DBL_AFTER_2` | 9 | Any double -- post-battle (trainer 2) |
| `TRMSG_DBL_1POKE_2` | 10 | Any double -- player has 1 mon (trainer 2) |
| `TRMSG_LAST_POKE` | 15 | Battle-engine last Pokemon line |
| `TRMSG_LAST_POKE_HALF` | 16 | Battle-engine last Pokemon half-HP line |
| `TRMSG_WIN` | 20 | Battle-engine win text |

### 15.4 Trainer Text Location

`data/Trainers.c` stores each trainer as one C initializer. Text is in the same
trainer block under `.text = { ... }`:

```c
[4] = { // Route2
    .name = "Alex",
    .data = {
        .trainerType = TRAINER_DATA_TYPE_NOTHING,
        .trainerClass = TRAINERCLASS_SCHOOL_KID_M,
        .items = { ITEM_NONE, ITEM_NONE, ITEM_NONE, ITEM_NONE },
        .aiFlags = F_PRIORITIZE_SUPER_EFFECTIVE,
        .battleType = DOUBLE_BATTLE,
    },
    .party = {
        {
            .ivs = 0,
            .abilitySlot = TRAINER_POKEMON_ABILITY_1,
            .level = 3,
            .species = SPECIES_HOOTHOOT,
            .ballSeal = 0,
        },
        {
            .ivs = 0,
            .abilitySlot = TRAINER_POKEMON_ABILITY_1,
            .level = 4,
            .species = SPECIES_POOCHYENA,
            .ballSeal = 0,
        },
    },
    .text = {
        {
            .type = TRMSG_DBL_INTRO_1,
            .text = "Whoa! Are you a real Pokemon Trainer?!\\nLet's battle!\\r",
        },
        {
            .type = TRMSG_DBL_INTRO_2,
            .text = "Pooch! Yena!\\r",
        },
        {
            .type = TRMSG_DBL_LOSE_1,
            .text = "Awwwww...\\n",
        },
        {
            .type = TRMSG_DBL_AFTER_1,
            .text = "You can catch Pokemon even if you have\\nsix with you.\\rIf you catch one, it'll go to your Box\\nautomatically.\\n",
        },
        {
            .type = TRMSG_DBL_AFTER_2,
            .text = "Pooch! Yena!\\r",
        },
    },
},
```

When adding text to a trainer that previously had none, add or extend that
trainer's `.text` array. There is no separate trainer text offset table to edit
in the new C data flow.

### 15.5 Pattern A: Classic `DOUBLE_BATTLE` (2 NPCs)

`data/Trainers.c` -- set `.battleType = DOUBLE_BATTLE`. Place **two** NPCs on
the overworld map, both with the same trainer ID.

Use the full double text pattern when both NPCs should speak:

```c
.text = {
    { .type = TRMSG_DBL_INTRO_1, .text = "..." },
    { .type = TRMSG_DBL_LOSE_1, .text = "..." },
    { .type = TRMSG_DBL_AFTER_1, .text = "..." },
    { .type = TRMSG_DBL_INTRO_2, .text = "..." },
    { .type = TRMSG_DBL_LOSE_2, .text = "..." },
    { .type = TRMSG_DBL_AFTER_2, .text = "..." },
},
```

`TRMSG_DBL_1POKE_*` lines are optional and should be added only when the design
needs a custom one-Pokemon warning.

### 15.6 Pattern B: No-Partner `NO_PARTNER_DOUBLE_BATTLE` (1 NPC)

`data/Trainers.c` -- set `.battleType = NO_PARTNER_DOUBLE_BATTLE`. Place
**one** NPC on the overworld. No partner needed.

Use only the `_1` suffixed double text types because trainer 1 is the single
speaking NPC:

```c
.text = {
    { .type = TRMSG_DBL_INTRO_1, .text = "..." },
    { .type = TRMSG_DBL_LOSE_1, .text = "..." },
    { .type = TRMSG_DBL_AFTER_1, .text = "..." },
},
```

For regular double battles, do not use `TRMSG_INTRO`, `TRMSG_LOSE`, or
`TRMSG_AFTER`. The game reads the `TRMSG_DBL_*` variants instead. Gym Leaders
are an exception; see 15.7.

### 15.7 Gym Leader Exception

Gym Leaders use map scripts for pre-battle and post-battle dialogue. Their
`data/Trainers.c` `.text` entries should therefore include only in-battle
battle-engine text:

- `TRMSG_LAST_POKE`
- `TRMSG_LAST_POKE_HALF`
- `TRMSG_LOSE`
- Any other special in-battle leader text the battle engine supports

Do **not** add these for Gym Leaders unless a specific script needs them:

- `TRMSG_INTRO`
- `TRMSG_AFTER`
- `TRMSG_DBL_INTRO_*`
- `TRMSG_DBL_AFTER_*`
- `TRMSG_DBL_1POKE_*`

Gym Leaders must have explicit movesets:

- Use `TRAINER_DATA_TYPE_ITEMS | TRAINER_DATA_TYPE_MOVES`.
- Each party member needs `.item = ITEM_NONE` if no held item and a `.moves = { ... }` list.
- Held items are allowed. Usually only the ace should hold an item early-game.
- The ace can be first or last, but Gym Leader aces are usually in the back.
- The first Gym Leader should have one trainer healing item, currently
  `ITEM_POTION`; later Gym Leaders can have more/better healing items.

Example: first Gym Leader Erika uses `DOUBLE_BATTLE`, two Carnivine lv12, ace in
the back with `ITEM_ORAN_BERRY`, and one trainer `ITEM_POTION`.

### 15.8 Concrete Example: Trainer 4 "Alex" (Classic DOUBLE_BATTLE)

Desired shape after porting the local trainer over the upstream C format:

- Trainer block: `[4] = { // Route2` in `data/Trainers.c`
- `.name = "Alex"`
- `.trainerClass = TRAINERCLASS_SCHOOL_KID_M`
- `.battleType = DOUBLE_BATTLE`
- Party: Hoothoot lv3 and Poochyena lv4
- Text: `TRMSG_DBL_INTRO_1`, `TRMSG_DBL_INTRO_2`, `TRMSG_DBL_LOSE_1`,
  `TRMSG_DBL_AFTER_1`, and `TRMSG_DBL_AFTER_2`
### 15.9 Which Pattern to Use

| Scenario | Use |
|---|---|
| Two NPCs standing side-by-side on the map | `DOUBLE_BATTLE` |
| A single NPC who should start a 2v2 fight | `NO_PARTNER_DOUBLE_BATTLE` |
| Both NPCs need their own pre/post-battle dialogue | `DOUBLE_BATTLE` |
| Minimal overworld setup, one NPC talks for all | `NO_PARTNER_DOUBLE_BATTLE` |

## 16. Trainer Team Documentation Export Rules

The trainer team export tool is `scripts/export_touched_trainers.py`.
Documentation source list and manual area order live in
`documentation/touched_trainers.md`.

The exporter reads trainer teams from `data/Trainers.c`, not the removed old ASM trainer source. It parses each trainer initializer,
including `.data`, `.party`, `.items`, `.moves`, and the compact area comment.

Final CSV/XLSX/HTML must group trainers by area in the user's manual exploration
order, not by trainer id.

Every exported trainer must carry a compact area comment on its initializer line
in `data/Trainers.c`:

```c
[24] = { // Route4
[256] = { // Gym1
[19] = { // HeritagePark
```

Area id rules:

- Use compact route/gym/place ids.
- Examples: `Route4`, `Gym1`, `HeritagePark`.
- Do not infer area order from trainer ids.
- Ask the user for canonical area order and trainer-to-area placement.
- Exporter warns if a trainer has no area comment or an area not present in the
  manual area order.
- Within the same area, preserve row order from `documentation/touched_trainers.md`
  unless user gives a different secondary order.
- Current manual area order: `Route2`, `Route3`, `Gym1`, `RavagedPath`,
  `R3PostCave`, `HeritagePark`, `Gym2`, `Route4`.
- CSV includes visible area separator rows. XLSX/HTML use colored area separator
  rows/headers.

Useful commands:

```sh
python scripts/export_touched_trainers.py
python scripts/export_touched_trainers.py --formats xlsx
```
