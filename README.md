# Kingdom generator for Dominion

This script generates recommended "kingdoms" for the card game [Dominion](https://en.wikipedia.org/wiki/Dominion_%28card_game%29) and its expansions.
It scrapes the [Dominion Strategy Wiki](http://wiki.dominionstrategy.com/index.php/Main_Page) to find connections between cards and then uses this graph to find sets of cards that should play well together.
In general, I've found the resulting games to be more fun than the randomly generated ones.

## Installation

The best way to install is using pip:

```bash
python -m pip install dominion
```

## Usage

You can generate a random, well-connected kingdom using all the expansions:

```bash
dominion generate
```

You can restrict the code to a subset of the expansions:

```bash
dominion generate -s base -s prosperity -s seaside
```

Note that you can list the supported expansions using:

```bash
dominion list sets
```

You can start the kingdom off with your favorite cards:

```bash
dominion generate -c "king's court" -c village
```

As above, you can see the available cards using:

```bash
dominion list cards
# or
dominion list cards -s prosperity -s base
```

Finally, for good measure you can get a deterministic result using:

```bash
dominion generate --seed 42
```

## Updating the graph

The graph of card information and connections is included in this repository, but you can update it using:

```bash
dominion setup data/cards.json
```

You'll need to have [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) and [requests](https://requests.readthedocs.io) installed, and installing [tqdm](https://tqdm.github.io/) doesn't hurt.
