#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import math
import os
import random
import re
from typing import Counter, Dict, List, Optional, Set, TypedDict
from urllib.parse import unquote

import click
import pkg_resources

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda *args, **kwargs: args[0]  # noqa

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .dominion_version import __version__

BASE_URL: str = "http://wiki.dominionstrategy.com/index.php"
DEFAULT_FILENAME: str = pkg_resources.resource_filename(
    __name__, "data/cards.json"
)

non_supply_types: Set[str] = set(
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
non_supply_names: Set[str] = set(
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


class Card(TypedDict, total=False):
    Name: str
    Set: str
    Types: str
    Cost: str
    Text: str
    Actions_Villagers: str
    Cards: str
    Buys: str
    Coins_Coffers: str
    Trash: str
    Exile: str
    Junk: str
    Gain: str
    Victory_Points: str
    Forward: List[str]
    Reverse: List[str]
    Recommended: List[str]


filename_option = click.option(
    "-f", "--filename", type=click.Path(), default=DEFAULT_FILENAME
)
sets_option = click.option("-s", "--sets", type=str, multiple=True)


@click.group()
def cli():
    pass


@cli.command()
def version():
    print(__version__)


@cli.group(name="list")
def info():
    pass


@info.command()
@filename_option
def sets(filename: click.Path) -> None:
    cards = load_cards(str(filename))
    sets = set(card["Set"] for card in cards)
    print("\n".join(sorted(sets)))


@info.command()
@filename_option
@sets_option
def cards(filename: click.Path, sets: Optional[List[str]]) -> None:
    if not sets:
        sets = None
    cards = load_cards(str(filename), sets=sets)
    header = ["Set", "Name", "Types"]
    table = list(
        sorted((card["Set"], card["Name"], card["Types"]) for card in cards)
    )
    widths = [
        len(max(table, key=lambda row: len(row[i]))[i])
        for i in range(len(header))
    ]

    top = "+ " + " | ".join(v.ljust(w) for w, v in zip(widths, header)) + " +"
    full_width = len(top)
    sep = "+" + "-" * (full_width - 2) + "+"
    print(sep)
    print(top)
    print(sep)
    print(
        "\n".join(
            "+ " + " | ".join(v.ljust(w) for w, v in zip(widths, row)) + " +"
            for row in table
        )
    )
    print(sep)


@cli.command()
@click.argument("filename", type=click.Path())
def setup(filename: click.Path) -> None:
    if BeautifulSoup is None:
        raise ImportError("bs4 is required for building the graph")
    load_cards(str(filename), clobber=True)


def get_and_parse_page(pagename: str) -> BeautifulSoup:
    import requests

    url = f"{BASE_URL}/{pagename}"
    r = requests.get(url)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")


def get_all_cards():
    soup = get_and_parse_page("All_Cards")
    cards = []
    headers = None
    for row in soup.find("table", {"class": "wikitable"}).find_all("tr"):
        entries = [d.text.strip() for d in row.find_all("th")]
        if entries:
            headers = entries
            continue

        entries = []
        for data in row.find_all("td"):
            for img in data.find_all("img"):
                alt = img.get("alt", "")
                if (
                    alt.startswith("$")
                    or alt == "P"
                    or alt == "VP"
                    or alt.endswith("D")
                ):
                    img.replaceWith(alt)
            for br in data.find_all("br"):
                br.replaceWith("\n")
            entries.append(data.text.strip())
        card = dict(zip(headers, entries))

        parts = card["Set"].split(", ")
        if len(parts) > 1 and parts[1] == "1E":
            continue
        card["Set"] = parts[0]
        cards.append(card)

    return cards


def find_links(soup: BeautifulSoup, names: Set[str]) -> List[str]:
    links: List[str] = []
    for a in soup.find_all("a"):
        match = re.search("/index.php/(.+)$", a.get("href", ""))
        if not match:
            continue
        result = match.group(1)
        result = unquote(result.replace("_", " "))
        if result.lower() not in names:
            continue
        links.append(result)
    return links


def find_recommended_sets(cards: List[Card]) -> List[Card]:
    index = build_index(cards)
    names = set(index.keys())
    sets = list(sorted(set(card["Set"] for card in cards)))
    for setname in tqdm(sets, leave=False):
        if setname == "Promo":
            continue
        if setname == "Menagerie":
            setname = "Menagerie_(expansion)"
        soup = get_and_parse_page(setname)
        header = soup.find(
            "span", {"class": "mw-headline"}, text=re.compile("Recommended"),
        ).parent
        for table in header.find_next_siblings(
            "table", {"class": "wikitable"}
        ):
            links = find_links(table, names)
            for n, name1 in enumerate(links[:-1]):
                for name2 in links[n + 1 :]:
                    card1 = cards[index[name1.lower()]]
                    card2 = cards[index[name2.lower()]]
                    if "Recommended" not in card1:
                        card1["Recommended"] = [name2]
                    else:
                        card1["Recommended"].append(name2)
                    if "Recommended" not in card2:
                        card2["Recommended"] = [name1]
                    else:
                        card2["Recommended"].append(name1)
    for card in cards:
        card["Recommended"] = list(sorted(set(card.get("Recommended", []))))
    return cards


def find_links_for_card(cards: List[Card], name: str) -> List[str]:
    names = set(card["Name"].lower() for card in cards)
    soup = get_and_parse_page(name)
    page = soup.find("div", {"id": "mw-content-text"})
    for element in page.find_all("table", {"class": "mw-collapsible"}):
        element.replaceWith("")
    return list(sorted(set(find_links(page, names))))


def find_forward_links(cards: List[Card]) -> List[Card]:
    for card in tqdm(cards, leave=False):
        if "Forward" in card:
            continue
        card["Forward"] = find_links_for_card(cards, card["Name"])
    return cards


def populate_reverse_links(cards: List[Card]) -> List[Card]:
    index = build_index(cards)
    for card in tqdm(cards, leave=False):
        for link in card["Forward"]:
            target = cards[index[link.lower()]]
            if "Reverse" not in target:
                target["Reverse"] = [card["Name"]]
            else:
                target["Reverse"].append(card["Name"])
    for card in cards:
        card["Reverse"] = list(sorted(set(card.get("Reverse", []))))
    return cards


def build_graph() -> List[Card]:
    print("Getting the list of all cards...")
    cards = get_all_cards()

    print("Finding the recommended sets of 10...")
    cards = find_recommended_sets(cards)

    print("Finding the forward links...")
    cards = find_forward_links(cards)

    print("Populating the reverse links...")
    cards = populate_reverse_links(cards)

    return cards


def load_cards(
    filename: str, sets: Optional[List[str]] = None, clobber: bool = False
) -> List[Card]:
    if os.path.exists(filename) and not clobber:
        with open(filename, "r") as f:
            cards = json.load(f)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        cards = build_graph()
        with open(filename, "w") as f:
            json.dump(cards, f, indent=2, sort_keys=True)

    # Remove non-supply cards
    cards = [card for card in cards if card["Name"] not in non_supply_names]
    if sets is None:
        return cards

    # Restrict to the target sets
    sets = [s.lower() for s in sets]
    return [card for card in cards if card["Set"].lower() in sets]


def build_index(cards: List[Card]) -> Dict[str, int]:
    return dict((card["Name"].lower(), i) for i, card in enumerate(cards))


def get_normalization(cards: List[Card]) -> Counter[str]:
    total: Counter[str] = Counter()
    for card in cards:
        total.update(card["Forward"])
        total.update(card["Reverse"])
        total.update(card["Recommended"])
    return total


def find_next(
    cards: List[Card],
    index: Dict[str, int],
    norm: Counter[str],
    deck: List[str],
) -> str:
    links: Counter[str] = Counter()
    for name in deck:
        card = cards[index[name.lower()]]
        links.update(card["Forward"])
        links.update(card["Reverse"])
        links.update(card["Recommended"])
    total = sum(links.values())
    final_links: Dict[str, float] = dict(
        (k, v / total) for k, v in links.items()
    )
    for name in list(links.keys()):
        if name.lower() not in index:
            del links[name]
            continue
        final_links[name] *= math.log(len(cards) / norm[name])
    if not len(links):
        return random.choice([c["Name"] for c in cards])
    return random.choices(*zip(*links.items()))[0]


def check_state(
    cards: List[Card], index: Dict[str, int], deck: List[str],
) -> bool:
    supplies = 0
    for name in deck:
        card = cards[index[name.lower()]]
        if card["Types"] in non_supply_types or card["Name"] == "Horse":
            continue
        supplies += 1
    if supplies >= 10:
        return False
    return True


def format_deck(
    cards: List[Card],
    index: Dict[str, int],
    deck: List[str],
    max_other: int = 3,
) -> str:
    supply = []
    other = []
    for name in deck:
        card = cards[index[name.lower()]]

        if card["Name"] == "Horse":
            continue

        if card["Types"] in non_supply_types:
            other.append(f" - {card['Set']}: {card['Name']} ({card['Types']})")
            continue

        supply.append(f" - {card['Set']}: {card['Name']} ({card['Types']})")

    # Deal with extra cards
    if len(other) > 3:
        random.shuffle(other)
        other = other[:3]

    # Format the results
    result = f"Supply ({len(supply)}):\n" + "\n".join(sorted(supply))
    if other:
        result += f"\n\nOther ({len(other)}):\n" + "\n".join(sorted(other))
    return result


def build_new_deck(
    cards: List[Card],
    index: Dict[str, int],
    deck: List[str],
    seed: Optional[int] = None,
    max_other: int = 3,
) -> str:
    if seed is not None:
        random.seed(seed)

    norm = get_normalization(cards)
    while check_state(cards, index, deck):
        deck.append(find_next(cards, index, norm, deck))
        deck = list(sorted(set(c.lower() for c in deck)))

    return format_deck(cards, index, deck, max_other=max_other)


@cli.command()
@filename_option
@sets_option
@click.option("-c", "--cards", type=str, multiple=True)
@click.option("-m", "--max-other", type=int, default=3)
@click.option("--seed", type=int, default=None)
def generate(
    filename: click.Path,
    sets: Optional[List[str]],
    cards: List[str],
    max_other: int,
    seed: Optional[int],
) -> None:
    if not sets:
        sets = None
    all_cards = load_cards(str(filename), sets=sets)
    index = build_index(all_cards)
    deck = []
    for card in cards:
        if card.lower() not in index:
            raise ValueError(f"unrecognized card '{card}'")
        deck.append(all_cards[index[card.lower()]]["Name"])
    print(
        build_new_deck(all_cards, index, deck, seed=seed, max_other=max_other)
    )


if __name__ == "__main__":
    cli()
