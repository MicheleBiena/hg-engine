# Trainer Export

This repository can generate spreadsheet-ready documentation for the trainers
listed in `documentation/touched_trainers.md`. The exporter reads from the merged
C trainer table, `data/Trainers.c`.

Run:

```sh
python scripts/export_touched_trainers.py
```

Before exporting, validate the trainer source table:

```sh
python scripts/validate_trainers_s.py
```

The script name is historical; it now validates `data/Trainers.c`.

To export only selected formats, pass them after `--formats`:

```sh
python scripts/export_touched_trainers.py --formats xlsx
```

Default outputs, all ignored by Git:

- `documentation/generated/touched_trainers.csv`
- `documentation/generated/touched_trainers.html`
- `documentation/generated/touched_trainer_cards.html`
- `documentation/generated/touched_trainers.xlsx`

The XLSX contains two sheets:

- `Trainer Cards`: user-facing trainer blocks with up to six party slots.
- `Touched Trainers`: raw spreadsheet data, one row per party Pokemon.

## Area ordering rules

The final CSV/XLSX/HTML must group trainers by area in manual exploration
order, not by trainer id.

`documentation/touched_trainers.md` is the source of truth for which trainers
are exported and for the manual area order. `data/Trainers.c` is the source of
truth for each trainer's team, items, class, battle type, text, and export area.
Every exported trainer must carry a compact area comment on the C initializer
line:

```c
[24] = { // Route4
[256] = { // Gym1
[19] = { // HeritagePark
```

Area ids should be compact and stable, for example `Route4`, `Gym1`, and
`HeritagePark`. The user provides the canonical area order manually. The
exporter preserves that order and exits with warnings if a listed trainer has
no area comment or references an area missing from the manual order.

Within the same area, keep the order from `documentation/touched_trainers.md`
unless the user asks for a different secondary order.

The CSV writes a visible area separator row before each area. The XLSX and HTML
use colored separator rows/headers.

The export reads teams, trainer classes, battle types, items, moves, and text
from `data/Trainers.c`. If a Pokemon has explicit `.moves = { ... }`, those
moves are used. Otherwise, the tool fills the move slots from the last four
level-up moves available in `data/learnsets/learnsets.json` at that Pokemon's
level.

The CSV/XLSX include sprite URL and Google Sheets `IMAGE()` formula columns for
official species. The card HTML renders those URLs directly. Custom species are
left without sprite URLs until we add a local or hosted sprite source for them.

Do not edit generated CSV/HTML/XLSX files by hand. Update `data/Trainers.c`,
`documentation/touched_trainers.md`, or the exporter, then regenerate.
