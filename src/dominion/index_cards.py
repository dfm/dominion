# -*- coding: utf-8 -*-

__all__ = ["build_index"]

import os
import re
import json
import requests
import tqdm
from bs4 import BeautifulSoup


BASE_URL: str = "http://wiki.dominionstrategy.com/index.php"


def get_and_parse_page(pagename: str) -> BeautifulSoup:
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
                if img.get("alt", "").startswith("$"):
                    img.replaceWith(img.get("alt", ""))
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


def load_cards(filename):
    if not os.path.exists(filename):
        data = get_all_cards()
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    with open(filename, "r") as f:
        return json.load(f)


def find_links_for_card(cards, name):
    links = []
    names = set(card["Name"] for card in cards)
    soup = get_and_parse_page(name)
    page = soup.find("div", {"id": "mw-content-text"})
    for element in page.find_all("table", {"class": "mw-collapsible"}):
        element.replaceWith("")
    for a in page.find_all("a"):
        match = re.search("/index.php/(.+)$", a.get("href", ""))
        if match and match.group(1) in names:
            links.append(match.group(1))
    return list(sorted(set(links)))


def find_forward_links(filename):
    cards = load_cards(filename)
    for card in tqdm.tqdm(cards):
        if "forward" in card:
            continue
        card["forward"] = find_links_for_card(cards, card["Name"])
        with open(filename, "w") as f:
            json.dump(cards, f, indent=2, sort_keys=True)


def populate_reverse_links(filename):
    cards = load_cards(filename)
    index = dict((card["Name"], i) for i, card in enumerate(cards))
    for card in tqdm.tqdm(cards):
        for link in card["forward"]:
            target = cards[index[link]]
            if "reverse" not in target:
                target["reverse"] = []
            target["reverse"].append(card["Name"])
    for card in cards:
        card["reverse"] = list(sorted(set(card.get("reverse", []))))
    with open(filename, "w") as f:
        json.dump(cards, f, indent=2, sort_keys=True)


def build_index(filename):
    find_forward_links(filename)
    populate_reverse_links(filename)


if __name__ == "__main__":
    build_index("cards.json")
