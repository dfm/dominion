# -*- coding: utf-8 -*-

__all__ = []

import json
import math
import random
from collections import Counter


non_supply_types = set(
    [
        "Artifact",
        "Boon",
        "Event",
        "Hex",
        "Landmark",
        "Project",
        "State",
        "Way",
    ]
)
non_supply_names = set(
    [
        "Curse",
        "Estate",
        "Duchy",
        "Provice",
        "Colony",
        "Copper",
        "Silver",
        "Gold",
        "Platinum",
    ]
)


def load_cards(filename, sets=None):
    with open(filename, "r") as f:
        cards = json.load(f)
    cards = [card for card in cards if card["Name"] not in non_supply_names]
    if sets is None:
        return cards
    sets = [s.lower() for s in sets]
    return [card for card in cards if card["Set"].lower() in sets]


def build_index(cards):
    return dict((card["Name"].lower(), i) for i, card in enumerate(cards))


def get_normalization(cards):
    total = Counter()
    for card in cards:
        total.update(card["forward"])
        total.update(card["reverse"])
    return total


def find_next(cards, index, norm, deck):
    links = Counter()
    for name in deck:
        card = cards[index[name.lower()]]
        links.update(card["reverse"])
        links.update(card["forward"])
    for name in list(links.keys()):
        if name.lower() not in index:
            del links[name]
            continue
        links[name] *= math.log(len(cards) / norm[name])
    if not len(links):
        return random.choice([c["Name"] for c in cards])
    return random.choices(*zip(*links.items()))[0]


def check_state(cards, index, deck):
    supplies = 0
    for name in deck:
        card = cards[index[name.lower()]]
        if card["Types"] in non_supply_types or card["Name"] == "Horse":
            continue
        supplies += 1
    if supplies >= 10:
        return False
    return True


def format_deck(cards, index, deck):
    supply = []
    other = []
    for name in deck:
        card = cards[index[name.lower()]]
        if card["Types"] in non_supply_types:
            other.append(
                "{0}:{1}:{2}".format(card["Set"], card["Name"], card["Types"])
            )
            continue

        supply.append(
            "{0}:{1}:{2}".format(card["Set"], card["Name"], card["Types"])
        )

    result = "Supply:\n" + "\n".join(sorted(supply))
    if len(other) > 3:
        random.shuffle(other)
        other = other[:3]
    if other:
        result += "\n\nOther:\n" + "\n".join(sorted(other))
    return result


cards = load_cards("cards.json", sets=["Menagerie", "prosperity"])
index = build_index(cards)
norm = get_normalization(cards)
deck = ["groom", "kiln", "goons"]
while check_state(cards, index, deck):
    deck.append(find_next(cards, index, norm, deck))
    deck = list(sorted(set(c.lower() for c in deck)))
print(format_deck(cards, index, deck))
