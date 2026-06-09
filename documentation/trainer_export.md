# Trainer Export

This repository can generate spreadsheet-ready documentation for the trainers
listed in `documentation/touched_trainers.md`.

Run:

```sh
python scripts/export_touched_trainers.py
```

Default outputs:

- `documentation/generated/touched_trainers.csv`
- `documentation/generated/touched_trainers.html`
- `documentation/generated/touched_trainer_cards.html`
- `documentation/generated/touched_trainers.xlsx`

The XLSX contains two sheets:

- `Trainer Cards`: user-facing trainer blocks with up to six party slots.
- `Touched Trainers`: raw spreadsheet data, one row per party Pokemon.

The export reads teams from `armips/data/trainers/trainers.s`. If a Pokemon has
explicit trainer moves, those are used. Otherwise, the tool fills the move slots
from the last four level-up moves available in `data/learnsets/learnsets.json`
at that Pokemon's level.

The CSV/XLSX include sprite URL and Google Sheets `IMAGE()` formula columns for
official species. The card HTML renders those URLs directly. Custom species are
left without sprite URLs until we add a local or hosted sprite source for them.
