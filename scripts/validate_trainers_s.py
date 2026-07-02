import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from export_touched_trainers import CARD_SLOT_COUNT, DEFAULT_TRAINERS, parse_trainers as parse_c_trainers


def parse_trainers(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    trainers = {}
    trainer_id = None
    trainer = {}
    in_trainerdata = False
    in_party = False
    current_mon = []
    mon_list = []
    key_counts = None

    for line in lines:
        stripped = line.split("//")[0].strip().lower()

        if not stripped:
            continue

        if stripped.startswith("trainerdata"):
            match = re.match(r'trainerdata\s+(\d+),\s*"([^"]+)"', stripped)
            if match:
                trainer_id = int(match.group(1))
                trainer = {
                    "id": trainer_id,
                    "name": match.group(2),
                    "trainermontype": "",
                    "trainerclass": "",
                    "nummons": 0,
                    "party": []
                }
                in_trainerdata = True
                key_counts = {}
            continue

        if in_trainerdata:
            key = stripped.split()[0]
            key_counts[key] = key_counts.get(key, 0) + 1
            if key == "item":
                if key_counts[key] > 4:
                    print(f"ERROR: trainerdata id {trainer_id} ({trainer['name']}): too many '{key}' entries (max 4)")
                    sys.exit(1)
            elif key_counts[key] > 1:
                print(f"ERROR: trainerdata id {trainer_id} ({trainer['name']}): duplicate '{key}' not allowed")
                sys.exit(1)

            if stripped.startswith("trainermontype"):
                trainer["trainermontype"] = stripped.split("trainermontype")[1].strip().upper()
                trainer["trainermontype"] = trainer["trainermontype"].split()
                if len(trainer["trainermontype"]) % 2 == 0:
                    print(f"ERROR: Incorrect number or formating of 'trainermontype' for trainer id {trainer_id} ({trainer['name']})")
                    sys.exit(1)
                if(len(trainer["trainermontype"]) > 1):
                    for i in range(0,len(trainer["trainermontype"])):
                        if i % 2 == 1 and trainer["trainermontype"][i] != "|":
                            print(f"ERROR: Incorrect number or formating of 'trainermontype' from trainer id {trainer_id} ({trainer['name']})")
                            sys.exit(1)

            elif stripped.startswith("trainerclass"):
                trainer["trainerclass"] = stripped.split()
                if len(trainer["trainerclass"]) != 2:
                    print(f"ERROR: Incorrect number or formating of 'trainerclass' for trainer id {trainer_id} ({trainer['name']})")
                    sys.exit(1)
                trainer["trainerclass"] = trainer["trainerclass"][1].strip().upper()

            elif stripped.startswith("nummons"):
                match = re.search(r'nummons\s+.*?(\b[0-6]\b)', stripped)
                if match:
                    trainer["nummons"] = int(match.group(1))
                else:
                    print(f"encountered unexpected 'nummons' value for trainer {trainer_id}")
                    sys.exit(1)

            elif stripped == "endentry":
                if key_counts["item"] < 4:
                    print(f"ERROR: only {key_counts['item']} 'item' entries were in trainer id {trainer_id} ({trainer['name']})")
                    sys.exit(1)

                trainers[trainer_id] = trainer
                trainer = {}
                in_trainerdata = False
                key_counts = None
            continue

        if stripped.startswith("party"):
            if in_party:
                print(f"encountered unexpected 'party' tag before closure with 'endparty'. inspect your trainers.s file before trainer {trainer_id}")
                sys.exit(1)

            match = re.match(r'party\s+(\d+)', stripped)
            if match:
                party_trainer_id = int(match.group(1))
                if party_trainer_id in trainers:
                    in_party = True
                    mon_list = []
                    current_mon = []
            continue

        if in_party:
            if stripped.startswith("ivs"):
                if current_mon:
                    mon_list.append(current_mon)
                current_mon = [stripped]
                continue
            elif stripped == "endparty":
                if current_mon:
                    mon_list.append(current_mon)

                parsed_mons = []
                for mon in mon_list:
                    mon_dict = {}
                    move_count = 1
                    for line in mon:
                        kv = re.match(r'(\w+)\s+(.+)', line)
                        if kv:
                            key, value = kv.groups()
                            if key == "move":
                                if " " in value or "move_" not in value:
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has an invalid constant specified for {key}: {value}")
                                    sys.exit(1)
                                mon_dict[f"move{move_count}"] = value
                                move_count += 1
                            else:
                                if (key in mon_dict):
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has a duplicate {key} field in one of its mons.")
                                    sys.exit(1)
                                elif (key == "pokemon") and (("species_" not in value) or (" " in value)):
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has an invalid constant specified for {key}: {value}")
                                    sys.exit(1)
                                elif (key == "item") and (("item_" not in value) or (" " in value)):
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has an invalid constant specified for {key}: {value}")
                                    sys.exit(1)
                                elif (key == "ability") and (("ability_" not in value) or (" " in value)):
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has an invalid constant specified for {key}: {value}")
                                    sys.exit(1)
                                elif (key == "nature") and (("nature_" not in value) or (" " in value)):
                                    print(f"ERROR: {trainers[trainer_id]['name']} (id: {trainer_id}) has an invalid constant specified for {key}: {value}")
                                    sys.exit(1)
                                mon_dict[key] = value
                    parsed_mons.append(mon_dict)

                trainers[party_trainer_id]["party"] = parsed_mons
                trainer_id = None
                in_party = False
                mon_list = []
                current_mon = []
                continue
            else:
                if not current_mon:
                    print(f"encountered unexpected line {stripped}. inspect your trainers.s file at trainer {trainer_id}. 'ivs' should be the first attribute listed for each pokémon")
                    sys.exit(1)
                current_mon.append(stripped)

    return list(trainers.values())


def mon_additional_flag_check(trainer, mon, mon_index, flag, key):
    has_additionalflags_flag = "additionalflags" in mon
    has_flag = has_additionalflags_flag and flag.lower() in mon["additionalflags"]
    has_val = key in mon

    if has_flag and not has_val:
        return f"ERROR: {trainer['name']} (id: {trainer['id']}, mon: {mon_index}) has the {flag} flag but does not have {key} set"
    elif has_val and not has_flag:
        return f"ERROR: {trainer['name']} (id: {trainer['id']}, mon: {mon_index}) does not have the {flag} flag but has {key} set"
    return None


def trainer_flag_check(trainer, party, flag, key):
    has_trainer_flag = flag in trainer["trainermontype"]
    all_have_key = all(key in mon for mon in party)
    any_have_key = any(key in mon for mon in party)

    if has_trainer_flag and not all_have_key:
        return f"ERROR: {trainer['name']} (id: {trainer['id']}, flags: {trainer['trainermontype']}) has {flag} flag but not all party pokémon have {key} defined"
    elif not has_trainer_flag and any_have_key:
        return f"ERROR: {trainer['name']} (id: {trainer['id']}, flags: {trainer['trainermontype']}) does not have {flag} flag but some party pokémon have {key} defined"
    return None


def validate_single_field(trainer, party, flag, key):
    flag_errs = trainer_flag_check(trainer, party, flag, key)
    return [flag_errs] if flag_errs else []


def validate_items(trainer, party):
    return validate_single_field(trainer, party, "TRAINER_DATA_TYPE_ITEMS", "item")


# this does not use the trainer_flag_check func because it has extra logic for move count
def validate_moves(trainer, party):
    errors = []
    has_moves_flag = 'TRAINER_DATA_TYPE_MOVES' in trainer["trainermontype"]
    all_have_moves = all("move4" in mon for mon in party)
    any_have_moves = any("move1" in mon for mon in party)
    any_have_extra_moves = any("move5" in mon for mon in party)

    if has_moves_flag and not all_have_moves:
        errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']}, flags: {trainer['trainermontype']}) has TRAINER_DATA_TYPE_MOVES flag but not all party pokémon have four moves defined")
    elif not has_moves_flag and any_have_moves:
        errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']}, flags: {trainer['trainermontype']}) does not have the TRAINER_DATA_TYPE_MOVES flag but some party pokémon have move(s) defined")

    if has_moves_flag and any_have_extra_moves:
        errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']}, flags: {trainer['trainermontype']}) has extra moves for Pokémon in party")
    return errors


def validate_abilities(trainer, party):
    return validate_single_field(trainer, party, "TRAINER_DATA_TYPE_ABILITY", "ability")


def validate_fields_overall(trainer, party):
    errors = []
    required_fields = [
        "ivs", "abilityslot", "level", "ballseal"
    ]
    correct_field_order = [
        "ivs", "abilityslot", "level", "pokemon", "monwithform", "item",
        "move1", "move2", "move3", "move4",
        "ability", "setivs", "setevs", "nature",
        "shinylock", "additionalflags", "status",
        "stathp", "statatk", "statdef", "statspeed", "statspatk", "statspdef",
        "ppcounts", "nickname", "ballseal"
    ]
    for i, mon in enumerate(party):
        actual_order = []
        for field in mon.keys():
            if field.startswith("move"):
                actual_order.append((field, correct_field_order.index("move1")))
            elif field in correct_field_order:
                actual_order.append((field, correct_field_order.index(field)))

        indices = [idx for _, idx in actual_order]

        if indices != sorted(indices):
            errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']} mon {i}: field order is incorrect.")
            errors.append(f"  found order: {[f for f, _ in actual_order]}")
            errors.append(f"  expected order (if present): {correct_field_order}")

        missing = [f for f in required_fields if f not in mon]
        if "pokemon" not in mon and "monwithform" not in mon:
            missing.append("pokemon/monwithform")
        if missing:
            errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']}) mon {i}: missing required fields {missing}")
    return errors


def validate_additional_flags(trainer, party):
    errors = []
    flag_errs = trainer_flag_check(trainer, party, "TRAINER_DATA_TYPE_ADDITIONAL_FLAGS", "additionalflags")
    if (flag_errs):
        errors.append(flag_errs)
    flag_key_pairs = [
        ('TRAINER_DATA_EXTRA_TYPE_STATUS', 'status'),
        ('TRAINER_DATA_EXTRA_TYPE_HP', 'stathp'),
        ('TRAINER_DATA_EXTRA_TYPE_ATK', 'statatk'),
        ('TRAINER_DATA_EXTRA_TYPE_DEF', 'statdef'),
        ('TRAINER_DATA_EXTRA_TYPE_SPEED', 'statspeed'),
        ('TRAINER_DATA_EXTRA_TYPE_SP_ATK', 'statspatk'),
        ('TRAINER_DATA_EXTRA_TYPE_SP_DEF', 'statspdef'),
        ('TRAINER_DATA_EXTRA_TYPE_PP_COUNTS', 'ppcounts'),
        ('TRAINER_DATA_EXTRA_TYPE_NICKNAME', 'nickname')
    ]
    for i, mon in enumerate(party):
        for flag, key in flag_key_pairs:
            error = mon_additional_flag_check(trainer, mon, i, flag, key)
            if error:
                errors.append(error)
    return errors


def validate_trainers(trainers, print_team):
    errors = []
    for trainer in trainers:
        if trainer["id"] == 0:
            continue

        err_count = len(errors)

        party = trainer["party"]

        errors.extend(validate_items(trainer, party))
        errors.extend(validate_moves(trainer, party))
        errors.extend(validate_abilities(trainer, party))
        errors.extend(validate_single_field(trainer, party, "TRAINER_DATA_TYPE_BALL", "ball"))
        errors.extend(validate_single_field(trainer, party, "TRAINER_DATA_TYPE_IV_EV_SET", "setivs"))
        errors.extend(validate_single_field(trainer, party, "TRAINER_DATA_TYPE_IV_EV_SET", "setevs"))
        errors.extend(validate_single_field(trainer, party, "TRAINER_DATA_TYPE_NATURE_SET", "nature"))
        errors.extend(validate_single_field(trainer, party, "TRAINER_DATA_TYPE_SHINY_LOCK", "shinylock"))
        errors.extend(validate_additional_flags(trainer, party))
        errors.extend(validate_fields_overall(trainer, party))

        # Party size validation
        if len(party) != trainer["nummons"]:
            errors.append(f"ERROR: {trainer['name']} (id: {trainer['id']}, nummons: {trainer['nummons']}) has {len(party)} pokémon defined")

        if print_team and len(errors) > err_count:
            print(f'------- Start Party {trainer["id"]} -------')
            for mon in party:
                for k, v in mon.items():
                    print(f"{k}: {v}")
                print("\n")
            print(f'------- End Party {trainer["id"]} -------')

    if errors:
        for error in errors:
            print(error)
        sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    trainer_path = Path(args[0]) if len(args) == 1 else DEFAULT_TRAINERS

    if trainer_path.suffix.lower() == ".s":
        print("ERROR: trainers.s validation is obsolete; validate data/Trainers.c instead")
        sys.exit(1)

    try:
        trainers = parse_c_trainers(trainer_path)
    except Exception as exc:
        print(f"ERROR: failed to parse {trainer_path}: {exc}")
        sys.exit(1)

    errors = []
    party_mon_count = 0
    if not trainers:
        errors.append(f"ERROR: no trainers parsed from {trainer_path}")

    for trainer_id in sorted(trainers):
        trainer = trainers[trainer_id]
        if trainer_id == 0:
            continue

        party = trainer.party
        party_mon_count += len(party)
        label = f"trainer {trainer_id} ({trainer.name or '<unnamed>'})"

        if not trainer.name:
            errors.append(f"ERROR: {label} is missing .name")
        if not trainer.trainerclass:
            errors.append(f"ERROR: {label} is missing .data.trainerClass")
        if len(party) > CARD_SLOT_COUNT:
            errors.append(f"ERROR: {label} has {len(party)} party mons; max is {CARD_SLOT_COUNT}")

        for slot, mon in enumerate(party, start=1):
            species = str(mon.get("pokemon", "")).strip()
            level_raw = str(mon.get("level", "")).strip()
            moves = mon.get("moves", [])

            if not species or species == "SPECIES_NONE":
                errors.append(f"ERROR: {label} party slot {slot} is missing species")
            if not level_raw:
                errors.append(f"ERROR: {label} party slot {slot} is missing level")
            else:
                try:
                    level = int(level_raw, 0)
                except ValueError:
                    errors.append(f"ERROR: {label} party slot {slot} has non-numeric level {level_raw}")
                else:
                    if not 1 <= level <= 100:
                        errors.append(f"ERROR: {label} party slot {slot} has out-of-range level {level}")

            if len(moves) > 4:
                errors.append(f"ERROR: {label} party slot {slot} has {len(moves)} moves; max is 4")

    if errors:
        print("\n".join(errors))
        sys.exit(1)

    print(f"Validated {len(trainers)} trainer entries with {party_mon_count} party mons from {trainer_path}.")
