#!/usr/bin/env python3
"""
Export touched trainer documentation from the local trainer data.

The default output goes to documentation/generated and is intentionally
spreadsheet-friendly: one row per party Pokemon.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TOUCHED = ROOT / "documentation" / "touched_trainers.md"
DEFAULT_TRAINERS = ROOT / "armips" / "data" / "trainers" / "trainers.s"
DEFAULT_LEARNSETS = ROOT / "data" / "learnsets" / "learnsets.json"
DEFAULT_SPECIES = ROOT / "include" / "constants" / "species.h"
DEFAULT_OUTDIR = ROOT / "documentation" / "generated"

SPRITE_BASE_URL = "https://img.pokemondb.net/sprites/home/normal"

HEADERS = [
    "Trainer ID",
    "Trainer Class",
    "Trainer Class Constant",
    "Trainer Name",
    "Area",
    "Battle Type",
    "Trainer Items",
    "Party Slot",
    "Potential Ace",
    "Pokemon",
    "Species Constant",
    "Level",
    "Held Item",
    "IVs",
    "Ability Slot",
    "Move 1",
    "Move 2",
    "Move 3",
    "Move 4",
    "Moves Source",
    "Sprite URL",
    "Sheets Image Formula",
]

CARD_SLOT_COUNT = 6


SPECIAL_DISPLAY_NAMES = {
    "NIDORAN_F": "Nidoran F",
    "NIDORAN_M": "Nidoran M",
    "MR_MIME": "Mr. Mime",
    "MIME_JR": "Mime Jr.",
    "MR_RIME": "Mr. Rime",
    "HO_OH": "Ho-Oh",
    "PORYGON_Z": "Porygon-Z",
    "JANGMO_O": "Jangmo-o",
    "HAKAMO_O": "Hakamo-o",
    "KOMMO_O": "Kommo-o",
    "TYPE_NULL": "Type: Null",
    "FLABEBE": "Flabebe",
    "SIRFETCHD": "Sirfetchd",
    "FARFETCHD": "Farfetchd",
    "WO_CHIEN": "Wo-Chien",
    "CHIEN_PAO": "Chien-Pao",
    "TING_LU": "Ting-Lu",
    "CHI_YU": "Chi-Yu",
}

SPECIAL_SPRITE_SLUGS = {
    "NIDORAN_F": "nidoran-f",
    "NIDORAN_M": "nidoran-m",
    "MR_MIME": "mr-mime",
    "MIME_JR": "mime-jr",
    "MR_RIME": "mr-rime",
    "HO_OH": "ho-oh",
    "PORYGON_Z": "porygon-z",
    "JANGMO_O": "jangmo-o",
    "HAKAMO_O": "hakamo-o",
    "KOMMO_O": "kommo-o",
    "TYPE_NULL": "type-null",
    "FLABEBE": "flabebe",
    "SIRFETCHD": "sirfetchd",
    "FARFETCHD": "farfetchd",
    "WO_CHIEN": "wo-chien",
    "CHIEN_PAO": "chien-pao",
    "TING_LU": "ting-lu",
    "CHI_YU": "chi-yu",
}


@dataclass
class TouchedTrainer:
    trainer_id: int
    trainer_class: str
    name: str
    area: str


@dataclass
class Trainer:
    trainer_id: int
    name: str
    trainermontype: str = ""
    trainerclass: str = ""
    nummons: int = 0
    items: list[str] = field(default_factory=list)
    battletype: str = ""
    party: list[dict[str, object]] = field(default_factory=list)


@dataclass
class TrainerCard:
    trainer_id: object
    trainer_class: str
    trainer_name: str
    area: str
    battle_type: str
    trainer_items: str
    party: list[dict[str, object]]


def strip_comment(line: str) -> str:
    return line.split("//", 1)[0].strip()


def clean_constant(value: object, prefix: str) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text == f"{prefix}_NONE":
        return ""
    if text.startswith(prefix + "_"):
        text = text[len(prefix) + 1 :]
    return text


def title_from_constant(value: object, prefix: str = "") -> str:
    raw = clean_constant(value, prefix) if prefix else str(value or "").strip()
    if not raw:
        return ""
    if raw in SPECIAL_DISPLAY_NAMES:
        return SPECIAL_DISPLAY_NAMES[raw]
    return " ".join(part.capitalize() for part in raw.split("_"))


def trainerclass_display(value: str) -> str:
    raw = clean_constant(value, "TRAINERCLASS")
    if raw.startswith("LEADER_"):
        return "Leader " + title_from_constant(raw.removeprefix("LEADER_"))
    if raw.endswith("_M"):
        return title_from_constant(raw.removesuffix("_M")) + " M"
    if raw.endswith("_F"):
        return title_from_constant(raw.removesuffix("_F")) + " F"
    if raw.endswith("_GS"):
        return title_from_constant(raw.removesuffix("_GS"))
    return title_from_constant(raw)


def sprite_slug(species_constant: str) -> str:
    raw = clean_constant(species_constant, "SPECIES")
    if not raw:
        return ""
    if raw in SPECIAL_SPRITE_SLUGS:
        return SPECIAL_SPRITE_SLUGS[raw]
    return raw.lower().replace("_", "-")


def load_official_species(species_path: Path) -> set[str]:
    official = set()
    define_re = re.compile(r"^\s*#define\s+(SPECIES_[A-Z0-9_]+)\s+(\d+)\b")
    for line in species_path.read_text(encoding="utf-8").splitlines():
        match = define_re.match(line)
        if not match:
            continue
        constant, number = match.groups()
        if 1 <= int(number) <= 1075:
            official.add(constant)
    return official


def sprite_url(species_constant: str, official_species: set[str]) -> str:
    if species_constant not in official_species:
        return ""
    slug = sprite_slug(species_constant)
    return f"{SPRITE_BASE_URL}/{slug}.png" if slug else ""


def read_touched_trainers(path: Path) -> list[TouchedTrainer]:
    trainers = []
    line_re = re.compile(r"^\s*(\d+):\s*([^-]+?)\s*-\s*([^(]+?)\s*\((.+)\)\s*$")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = line_re.match(line)
        if not match:
            continue
        trainer_id, trainer_class, name, area = match.groups()
        trainers.append(
            TouchedTrainer(
                trainer_id=int(trainer_id),
                trainer_class=trainer_class.strip(),
                name=name.strip(),
                area=area.strip(),
            )
        )
    return trainers


def parse_key_value(line: str) -> tuple[str, str] | None:
    match = re.match(r"^([A-Za-z0-9_]+)\s+(.+)$", strip_comment(line))
    if not match:
        return None
    return match.group(1).lower(), match.group(2).strip()


def parse_party(block: str) -> list[dict[str, object]]:
    party_match = re.search(r"^\s*party\s+\d+\s*(.*?)(?=^\s*endparty\b)", block, re.M | re.S)
    if not party_match:
        return []

    party_text = party_match.group(1)
    chunks = re.split(r"^\s*//\s*mon\s+\d+\s*$", party_text, flags=re.M)
    mons = []
    for chunk in chunks:
        mon = {}
        moves = []
        for line in chunk.splitlines():
            kv = parse_key_value(line)
            if not kv:
                continue
            key, value = kv
            if key == "move":
                moves.append(value)
            else:
                mon[key] = value
        if mon:
            mon["moves"] = moves
            mons.append(mon)
    return mons


def parse_trainers(path: Path) -> dict[int, Trainer]:
    text = path.read_text(encoding="utf-8-sig")
    trainer_re = re.compile(
        r"^trainerdata\s+(\d+),\s*\"([^\"]*)\"\s*(.*?)(?=^trainerdata\s+|\Z)",
        re.M | re.S,
    )
    trainers: dict[int, Trainer] = {}

    for match in trainer_re.finditer(text):
        trainer_id = int(match.group(1))
        trainer = Trainer(trainer_id=trainer_id, name=match.group(2))
        block = match.group(3)

        in_entry = True
        for line in block.splitlines():
            stripped = strip_comment(line)
            if not stripped:
                continue
            if stripped == "endentry":
                in_entry = False
                continue
            if not in_entry:
                continue

            kv = parse_key_value(line)
            if not kv:
                continue
            key, value = kv
            if key == "trainermontype":
                trainer.trainermontype = value
            elif key == "trainerclass":
                trainer.trainerclass = value
            elif key == "nummons":
                trainer.nummons = int(value)
            elif key == "item":
                trainer.items.append(value)
            elif key == "battletype":
                trainer.battletype = value

        trainer.party = parse_party(block)
        trainers[trainer_id] = trainer

    return trainers


def load_learnsets(path: Path) -> dict[str, list[tuple[int, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    learnsets = {}
    for species, fields in data.items():
        moves = []
        for entry in fields.get("LevelMoves", []):
            try:
                level = int(entry["Level"])
                move = str(entry["Move"])
            except (KeyError, TypeError, ValueError):
                continue
            moves.append((level, move))
        learnsets[species] = moves
    return learnsets


def fallback_moves(
    species: str,
    level: int,
    learnsets: dict[str, list[tuple[int, str]]],
) -> tuple[list[str], str]:
    learned = [
        move
        for move_level, move in learnsets.get(species, [])
        if move_level <= level and move != "MOVE_NONE"
    ]
    if not learned:
        return [], "missing learnset"

    result_reversed = []
    seen = set()
    for move in reversed(learned):
        if move in seen:
            continue
        result_reversed.append(move)
        seen.add(move)
        if len(result_reversed) == 4:
            break
    return list(reversed(result_reversed)), f"learnset <= L{level}"


def trainer_items(items: Iterable[str]) -> str:
    shown = [title_from_constant(item, "ITEM") for item in items if item != "ITEM_NONE"]
    return ", ".join(shown)


def build_rows(
    touched_trainers: list[TouchedTrainer],
    trainers: dict[int, Trainer],
    learnsets: dict[str, list[tuple[int, str]]],
    official_species: set[str],
) -> tuple[list[dict[str, object]], list[str]]:
    rows = []
    warnings = []

    for touched in touched_trainers:
        trainer = trainers.get(touched.trainer_id)
        if trainer is None:
            warnings.append(f"Trainer {touched.trainer_id} is listed but was not found in trainers.s")
            continue

        levels = [int(mon.get("level", 0)) for mon in trainer.party]
        max_level = max(levels) if levels else 0

        for index, mon in enumerate(trainer.party, start=1):
            species = str(mon.get("pokemon", ""))
            level = int(mon.get("level", 0))
            explicit_moves = [str(move) for move in mon.get("moves", [])]
            if explicit_moves:
                moves = explicit_moves[:4]
                source = "explicit trainer moves"
            else:
                moves, source = fallback_moves(species, level, learnsets)

            moves = moves + [""] * (4 - len(moves))
            url = sprite_url(species, official_species)

            rows.append(
                {
                    "Trainer ID": touched.trainer_id,
                    "Trainer Class": touched.trainer_class,
                    "Trainer Class Constant": trainer.trainerclass,
                    "Trainer Name": touched.name or trainer.name,
                    "Area": touched.area,
                    "Battle Type": title_from_constant(trainer.battletype, "BATTLE"),
                    "Trainer Items": trainer_items(trainer.items),
                    "Party Slot": index,
                    "Potential Ace": "yes" if level == max_level and len(trainer.party) > 1 else "",
                    "Pokemon": title_from_constant(species, "SPECIES"),
                    "Species Constant": species,
                    "Level": level,
                    "Held Item": title_from_constant(mon.get("item", ""), "ITEM"),
                    "IVs": mon.get("ivs", ""),
                    "Ability Slot": mon.get("abilityslot", ""),
                    "Move 1": title_from_constant(moves[0], "MOVE"),
                    "Move 2": title_from_constant(moves[1], "MOVE"),
                    "Move 3": title_from_constant(moves[2], "MOVE"),
                    "Move 4": title_from_constant(moves[3], "MOVE"),
                    "Moves Source": source,
                    "Sprite URL": url,
                    "Sheets Image Formula": f'=IMAGE("{url}")' if url else "",
                }
            )

        if trainer.nummons and trainer.nummons != len(trainer.party):
            warnings.append(
                f"Trainer {trainer.trainer_id} ({trainer.name}) declares {trainer.nummons} mons "
                f"but parser found {len(trainer.party)}"
            )

    return rows, warnings


def build_trainer_cards(rows: list[dict[str, object]]) -> list[TrainerCard]:
    cards: list[TrainerCard] = []
    by_id: dict[object, TrainerCard] = {}

    for row in rows:
        trainer_id = row["Trainer ID"]
        card = by_id.get(trainer_id)
        if card is None:
            card = TrainerCard(
                trainer_id=trainer_id,
                trainer_class=str(row.get("Trainer Class", "")),
                trainer_name=str(row.get("Trainer Name", "")),
                area=str(row.get("Area", "")),
                battle_type=str(row.get("Battle Type", "")),
                trainer_items=str(row.get("Trainer Items", "")),
                party=[],
            )
            by_id[trainer_id] = card
            cards.append(card)
        card.party.append(row)

    for card in cards:
        card.party.sort(key=lambda row: int(row.get("Party Slot") or 0))

    return cards


def card_title(card: TrainerCard) -> str:
    return f"ID {card.trainer_id} | {card.trainer_class} - {card.trainer_name}"


def card_area_text(card: TrainerCard) -> str:
    return f"{card.area} | {card.battle_type}".strip(" |")


def card_items_text(card: TrainerCard) -> str:
    return f"Items: {card.trainer_items or 'None'}"


def card_team_size_text(card: TrainerCard) -> str:
    return f"Team size: {len(card.party)}"


def party_slot(card: TrainerCard, slot: int) -> dict[str, object] | None:
    for row in card.party:
        if int(row.get("Party Slot") or 0) == slot:
            return row
    return None


def party_value(
    card: TrainerCard,
    slot: int,
    field: str,
    *,
    level_prefix: bool = False,
    ace_suffix: bool = False,
) -> str:
    row = party_slot(card, slot)
    if row is None:
        return ""
    value = str(row.get(field, "") or "")
    if not value:
        return ""
    if level_prefix:
        value = f"Lv. {value}"
    if ace_suffix and str(row.get("Potential Ace", "")) == "yes":
        value = f"{value} (Ace)"
    return value


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_html(path: Path, rows: list[dict[str, object]]) -> None:
    css = """
body { font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #17202a; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { border: 1px solid #d5dce3; padding: 6px 8px; vertical-align: middle; }
th { background: #eef3f7; position: sticky; top: 0; text-align: left; }
tr:nth-child(even) { background: #fbfcfd; }
img { width: 44px; height: 44px; object-fit: contain; }
.num { text-align: right; }
"""
    visible_headers = ["Sprite"] + [h for h in HEADERS if h != "Sheets Image Formula"]
    lines = [
        "<!doctype html>",
        "<meta charset=\"utf-8\">",
        "<title>Touched Trainers</title>",
        f"<style>{css}</style>",
        "<h1>Touched Trainers</h1>",
        "<table>",
        "<thead><tr>",
    ]
    lines.extend(f"<th>{html.escape(header)}</th>" for header in visible_headers)
    lines.append("</tr></thead><tbody>")

    for row in rows:
        lines.append("<tr>")
        url = str(row.get("Sprite URL", ""))
        if url:
            alt = html.escape(str(row.get("Pokemon", "")))
            lines.append(f"<td><img src=\"{html.escape(url)}\" alt=\"{alt}\"></td>")
        else:
            lines.append("<td></td>")
        for header in visible_headers[1:]:
            value = html.escape(str(row.get(header, "")))
            klass = " class=\"num\"" if header in {"Trainer ID", "Party Slot", "Level", "IVs", "Ability Slot"} else ""
            lines.append(f"<td{klass}>{value}</td>")
        lines.append("</tr>")

    lines.extend(["</tbody></table>", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_cards_html(path: Path, cards: list[TrainerCard]) -> None:
    css = """
body {
  background: #f4f8f5;
  color: #17201c;
  font-family: Segoe UI, Arial, sans-serif;
  margin: 24px;
}
h1 { margin: 0 0 4px; font-size: 28px; }
.note { margin: 0 0 24px; color: #51635a; }
.cards {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fit, minmax(760px, 1fr));
}
.card {
  background: #ffffff;
  border: 2px solid #1e4439;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(18, 43, 36, 0.08);
}
.card-header {
  align-items: center;
  background: #2e5e50;
  color: #ffffff;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding: 10px 12px;
}
.card-title { font-weight: 700; }
.card-area { color: #dbeee6; font-size: 13px; text-align: right; }
.card-meta {
  background: #e9f4ee;
  display: flex;
  gap: 18px;
  padding: 7px 12px;
  color: #33483f;
  font-size: 13px;
}
table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 12px; }
th, td { border: 1px solid #d4e0d8; padding: 5px 6px; text-align: center; vertical-align: middle; }
th { background: #edf5f0; color: #29443a; }
td.label { background: #edf5f0; color: #29443a; font-weight: 700; text-align: left; width: 92px; }
td.sprite { height: 72px; }
td.sprite img { height: 64px; max-width: 80px; object-fit: contain; }
tr.source-row td { background: #f2f2f2; color: #666; font-size: 11px; }
"""
    lines = [
        "<!doctype html>",
        "<meta charset=\"utf-8\">",
        "<title>Trainer Cards</title>",
        f"<style>{css}</style>",
        "<h1>Trainer Cards</h1>",
        "<p class=\"note\">Generated from touched trainer data. Each card has up to six party slots.</p>",
        "<div class=\"cards\">",
    ]

    for card in cards:
        lines.extend(
            [
                "<section class=\"card\">",
                "<div class=\"card-header\">",
                f"<div class=\"card-title\">{html.escape(card_title(card))}</div>",
                f"<div class=\"card-area\">{html.escape(card_area_text(card))}</div>",
                "</div>",
                "<div class=\"card-meta\">",
                f"<span>{html.escape(card_items_text(card))}</span>",
                f"<span>{html.escape(card_team_size_text(card))}</span>",
                "</div>",
                "<table>",
                "<thead><tr><th></th>",
            ]
        )
        lines.extend(f"<th>Pokemon {slot}</th>" for slot in range(1, CARD_SLOT_COUNT + 1))
        lines.append("</tr></thead><tbody>")

        lines.append("<tr><td class=\"label\"></td>")
        for slot in range(1, CARD_SLOT_COUNT + 1):
            url = party_value(card, slot, "Sprite URL")
            name = party_value(card, slot, "Pokemon")
            if url:
                lines.append(
                    f"<td class=\"sprite\"><img src=\"{html.escape(url)}\" alt=\"{html.escape(name)}\"></td>"
                )
            else:
                lines.append("<td class=\"sprite\"></td>")
        lines.append("</tr>")

        row_specs = [
            ("Pokemon", "Pokemon", {"ace_suffix": True}),
            ("Level", "Level", {"level_prefix": True}),
            ("Held Item", "Held Item", {}),
            ("Move One", "Move 1", {}),
            ("Move Two", "Move 2", {}),
            ("Move Three", "Move 3", {}),
            ("Move Four", "Move 4", {}),
            ("Source", "Moves Source", {}),
        ]
        for label, field, options in row_specs:
            source_class = " class=\"source-row\"" if label == "Source" else ""
            lines.append(f"<tr{source_class}><td class=\"label\">{html.escape(label)}</td>")
            for slot in range(1, CARD_SLOT_COUNT + 1):
                value = party_value(card, slot, field, **options)
                lines.append(f"<td>{html.escape(value)}</td>")
            lines.append("</tr>")

        lines.extend(["</tbody></table>", "</section>"])

    lines.extend(["</div>", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xlsx_cell(row_index: int, column_index: int, value: object, style: int = 0) -> str:
    ref = f"{column_name(column_index)}{row_index}"
    style_attr = f' s="{style}"' if style else ""
    text = "" if value is None else str(value)
    if text.startswith("="):
        return f'<c r="{ref}"{style_attr}><f>{xml_escape(text[1:])}</f></c>'
    return (
        f'<c r="{ref}" t="inlineStr"{style_attr}>'
        f"<is><t>{xml_escape(text)}</t></is></c>"
    )


def xlsx_row(
    row_index: int,
    values: list[object],
    styles: list[int] | None = None,
    *,
    height: int | None = None,
) -> str:
    styles = styles or []
    cells = []
    for column_index, value in enumerate(values, start=1):
        style = styles[column_index - 1] if column_index <= len(styles) else 0
        cells.append(xlsx_cell(row_index, column_index, value, style))
    height_attr = f' ht="{height}" customHeight="1"' if height else ""
    return f'<row r="{row_index}"{height_attr}>{"".join(cells)}</row>'


def xlsx_cols(widths: list[int]) -> str:
    return "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, width in enumerate(widths, start=1)
    )


def worksheet_xml(
    rows_xml: list[str],
    dimension: str,
    cols_xml: str,
    *,
    merges: list[str] | None = None,
    auto_filter: str = "",
) -> str:
    merge_xml = ""
    if merges:
        merge_refs = "".join(f'<mergeCell ref="{xml_escape(ref)}"/>' for ref in merges)
        merge_xml = f'<mergeCells count="{len(merges)}">{merge_refs}</mergeCells>'
    auto_filter_xml = f'<autoFilter ref="{xml_escape(auto_filter)}"/>' if auto_filter else ""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="{xml_escape(dimension)}"/>
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <cols>{cols_xml}</cols>
  <sheetData>{''.join(rows_xml)}</sheetData>
  {merge_xml}
  {auto_filter_xml}
</worksheet>"""


def raw_worksheet_xml(rows: list[dict[str, object]]) -> str:
    sheet_rows = []
    header_cells = [xlsx_cell(1, index, header, style=1) for index, header in enumerate(HEADERS, start=1)]
    sheet_rows.append(f'<row r="1">{"".join(header_cells)}</row>')

    for row_index, row in enumerate(rows, start=2):
        cells = [xlsx_cell(row_index, index, row.get(header, "")) for index, header in enumerate(HEADERS, start=1)]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    widths = [11, 18, 28, 18, 34, 13, 18, 10, 12, 16, 24, 8, 16, 8, 12, 18, 18, 18, 18, 20, 48, 36]
    dimension = f"A1:{column_name(len(HEADERS))}{max(len(rows) + 1, 1)}"
    return worksheet_xml(
        sheet_rows,
        dimension,
        xlsx_cols(widths),
        auto_filter=dimension,
    )


def cards_worksheet_xml(cards: list[TrainerCard]) -> str:
    sheet_rows: list[str] = []
    row_index = 1
    blank_8 = [""] * 8

    sheet_rows.append(
        xlsx_row(
            row_index,
            ["Shadows of Time - Trainer Cards", *blank_8[1:]],
            [2] * 8,
            height=28,
        )
    )
    row_index += 1
    sheet_rows.append(
        xlsx_row(
            row_index,
            ["Generated from touched trainer data. Each card has up to six party slots.", *blank_8[1:]],
            [3] * 8,
            height=24,
        )
    )
    row_index += 1

    for card in cards:
        sheet_rows.append(
            xlsx_row(
                row_index,
                [
                    card_title(card),
                    "Pokemon 1",
                    "Pokemon 2",
                    "Pokemon 3",
                    "Pokemon 4",
                    "Pokemon 5",
                    "Pokemon 6",
                    card_area_text(card),
                ],
                [4] * 8,
                height=24,
            )
        )
        row_index += 1

        image_values = [""]
        for slot in range(1, CARD_SLOT_COUNT + 1):
            url = party_value(card, slot, "Sprite URL")
            image_values.append(f'=IMAGE("{url}")' if url else "")
        image_values.append("")
        sheet_rows.append(xlsx_row(row_index, image_values, [6] * 8, height=64))
        row_index += 1

        row_specs = [
            ("Pokemon", "Pokemon", {"ace_suffix": True}, card_items_text(card)),
            ("Level", "Level", {"level_prefix": True}, card_team_size_text(card)),
            ("Held Item", "Held Item", {}, ""),
            ("Move One", "Move 1", {}, ""),
            ("Move Two", "Move 2", {}, ""),
            ("Move Three", "Move 3", {}, ""),
            ("Move Four", "Move 4", {}, ""),
            ("Source", "Moves Source", {}, ""),
        ]
        for label, field, options, side_text in row_specs:
            values = [label]
            values.extend(party_value(card, slot, field, **options) for slot in range(1, CARD_SLOT_COUNT + 1))
            values.append(side_text)
            style = 7 if label == "Source" else 6
            sheet_rows.append(xlsx_row(row_index, values, [5, *([style] * CARD_SLOT_COUNT), style]))
            row_index += 1

        sheet_rows.append(xlsx_row(row_index, blank_8))
        row_index += 1

    dimension = f"A1:H{max(row_index - 1, 1)}"
    return worksheet_xml(
        sheet_rows,
        dimension,
        xlsx_cols([26, 18, 18, 18, 18, 18, 18, 34]),
        merges=["A1:H1", "A2:H2"],
    )


def write_xlsx(path: Path, rows: list[dict[str, object]], cards: list[TrainerCard]) -> None:
    cards_sheet_xml = cards_worksheet_xml(cards)
    raw_sheet_xml = raw_worksheet_xml(rows)

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Trainer Cards" sheetId="1" r:id="rId1"/>
    <sheet name="Touched Trainers" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""

    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><sz val="9"/><color rgb="FF666666"/><name val="Calibri"/></font>
  </fonts>
  <fills count="6">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF2E5E50"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE9F4EE"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFBFDFB"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border/>
    <border>
      <left style="thin"><color rgb="FFD4E0D8"/></left>
      <right style="thin"><color rgb="FFD4E0D8"/></right>
      <top style="thin"><color rgb="FFD4E0D8"/></top>
      <bottom style="thin"><color rgb="FFD4E0D8"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="8">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>
    <xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1">
      <alignment horizontal="left" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="3" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", cards_sheet_xml)
        archive.writestr("xl/worksheets/sheet2.xml", raw_sheet_xml)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--touched", type=Path, default=DEFAULT_TOUCHED)
    parser.add_argument("--trainers", type=Path, default=DEFAULT_TRAINERS)
    parser.add_argument("--learnsets", type=Path, default=DEFAULT_LEARNSETS)
    parser.add_argument("--species", type=Path, default=DEFAULT_SPECIES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["csv", "html", "xlsx"],
        choices=["csv", "html", "xlsx"],
        help="Output formats to write.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    touched = read_touched_trainers(args.touched)
    trainers = parse_trainers(args.trainers)
    learnsets = load_learnsets(args.learnsets)
    official_species = load_official_species(args.species)
    rows, warnings = build_rows(touched, trainers, learnsets, official_species)
    cards = build_trainer_cards(rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    if "csv" in args.formats:
        path = args.output_dir / "touched_trainers.csv"
        write_csv(path, rows)
        written.append(path)
    if "html" in args.formats:
        path = args.output_dir / "touched_trainers.html"
        write_html(path, rows)
        written.append(path)
        path = args.output_dir / "touched_trainer_cards.html"
        write_cards_html(path, cards)
        written.append(path)
    if "xlsx" in args.formats:
        path = args.output_dir / "touched_trainers.xlsx"
        write_xlsx(path, rows, cards)
        written.append(path)

    print(f"Exported {len(rows)} party rows from {len(cards)} trainer cards.")
    for path in written:
        print(path.relative_to(ROOT))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    return 0 if not warnings else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
