#!/usr/bin/env python3
import operator
import os
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from trueskill import Rating, rate_1vs1, expose

bmutilspath = "./lib"

sys.path.append(os.path.expanduser(bmutilspath).rstrip("/"))
from lib.bmutils import BMClientParser

bmrc = ".bmrc"
site = "www"

bm = BMClientParser(os.path.expanduser(bmrc), site)
if not bm.verify_login():
  print("Could not login")

# options: all, tl, fair, tlopen
allowed_games = "tlopen"

tlopen_sets = ["Geekz", "Polycon", "Demicon the 13th", "Balticon 34",
               "SydCon 10"]


class OStat(object):
  def __init__(self):
    self.games_won = 0
    self.games_lost = 0
    self.rounds_won = 0
    self.rounds_lost = 0
    self.rounds_tied = 0
    self.games_played = 0

  def add(self, games_won=0, games_lost=0, rounds_won=0, rounds_lost=0,
    rounds_tied=0, games_played=0):
    self.games_won += games_won
    self.games_lost += games_lost
    self.rounds_won += rounds_won
    self.rounds_lost += rounds_lost
    self.rounds_tied += rounds_tied
    self.games_played += games_played


class RStat(object):
  def __init__(self, name, set, tl, rate, count):
    self.name = name.string.strip()
    self.set = set.string.strip()
    self.tl = tl.string.strip() == "Y"
    self.rate = float(rate.string.strip())
    self.count = int(count.string.strip())


banned_players = ['Nala', 'BMAI', 'BMBot', 'buttonbot', 'BMAIBagels']
observed_button_stats = {}
buttons = bm.wrap_load_button_names()
ratings = {}
players_total_game_count = {}
players_button_counts = {}
total_games_considered = 0
total_games_included = 0

soup = BeautifulSoup(requests.get(
  "http://stats.dev.buttonweavers.com/ui/stats/button_stats.html").text,
                     'html.parser')
stat_rows = soup.find_all("tr")
retrieved_button_stats = {}
for s_r in stat_rows:
  tds = s_r.find_all(name="td", recursive=False)
  if len(tds) == 0:
    continue
  rstat = RStat(tds[0], tds[1], tds[2], tds[3], tds[4])
  retrieved_button_stats[rstat.name] = rstat


def determine_winner(game):
  if game['roundsWonA'] is game['targetWins']:
    return game['playerNameA'], game['buttonNameA'], game['playerNameB'], \
           game['buttonNameB']
  elif game['roundsWonB'] is game['targetWins']:
    return game['playerNameB'], game['buttonNameB'], game['playerNameA'], \
           game['buttonNameA']
  else:
    raise Exception("I DONT KNOW WHATS GOING ON DETERMINING THE WINNER")


def do_the_ratings(game):
  global ratings
  global players_total_game_count
  global total_games_included
  wplay, wbutt, lplay, lbutt = determine_winner(game)
  wrate = ratings.get(wplay, Rating())
  lrate = ratings.get(lplay, Rating())
  wrate, lrate = rate_1vs1(wrate, lrate)
  ratings[wplay] = wrate
  ratings[lplay] = lrate
  players_total_game_count[wplay] = players_total_game_count.get(wplay, 0) + 1
  players_total_game_count[lplay] = players_total_game_count.get(lplay, 0) + 1
  total_games_included += 1

  w_butt_counts = players_button_counts.get(wplay, {'freq': {}, 'best': {}})
  w_butt_counts['freq'][wbutt] = w_butt_counts['freq'].get(wbutt, 0) + 1
  w_butt_counts['best'][wbutt] = w_butt_counts['best'].get(wbutt, 0) + 1
  players_button_counts[wplay] = w_butt_counts
  l_butt_counts = players_button_counts.get(lplay, {'freq': {}, 'best': {}})
  l_butt_counts['freq'][lbutt] = l_butt_counts['freq'].get(lbutt, 0) + 1
  players_button_counts[lplay] = l_butt_counts


def collect_button_stats(game):
  s_a = observed_button_stats.get(game['buttonNameA'], OStat())
  s_b = observed_button_stats.get(game['buttonNameB'], OStat())
  s_a.add(games_played=1, rounds_won=game['roundsWonA'],
          rounds_lost=game['roundsWonB'], rounds_tied=game['roundsDrawn'])
  s_b.add(games_played=1, rounds_won=game['roundsWonB'],
          rounds_lost=game['roundsWonA'], rounds_tied=game['roundsDrawn'])

  if game['roundsWonA'] is game['targetWins']:
    s_a.add(games_won=1)
    s_b.add(games_lost=1)
  elif game['roundsWonB'] is game['targetWins']:
    s_b.add(games_won=1)
    s_a.add(games_lost=1)
  else:
    raise Exception("DONT KNOW WHATS GOING ON DETERMINING BUTTON STATS")
  observed_button_stats[game['buttonNameA']] = s_a
  observed_button_stats[game['buttonNameB']] = s_b


keep_going = True
size = 1000
page = 1

while keep_going:
  print(f"fetching page {page} of size {size}")
  search = bm.wrap_search_game_history(
    sortColumn="lastMove",
    searchDirection="ASC",
    numberOfResults=size,
    page=page,
    status="COMPLETE",
    lastMoveMin=int(
      datetime(2020, 12, 15, 0, 0, 0, 0, timezone.utc).timestamp()),
    lastMoveMax=int(
      datetime(2020, 12, 21, 0, 0, 0, 0, timezone.utc).timestamp()))

  for game in search['games']:

    # all games observed
    total_games_considered += 1

    # some games we do not want to count regardless of strategy
    if game['buttonNameA'] not in buttons or game[
      'buttonNameB'] not in buttons:
      continue
    if game['playerNameA'] in banned_players or game[
      'playerNameB'] in banned_players:
      continue

    if allowed_games == "tl":
      if buttons[game['buttonNameA']]['isTournamentLegal'] and \
        buttons[game['buttonNameB']]['isTournamentLegal']:
        do_the_ratings(game)
        collect_button_stats(game)

    elif allowed_games == "fair":
      if 40 <= retrieved_button_stats[game['buttonNameA']].rate <= 60 and \
        retrieved_button_stats[game['buttonNameA']].count > 10 and \
        40 <= retrieved_button_stats[game['buttonNameB']].rate <= 60 and \
        retrieved_button_stats[game['buttonNameB']].count > 10:
        do_the_ratings(game)
        collect_button_stats(game)

    elif allowed_games == "tlopen":
      if buttons[game['buttonNameA']]['buttonSet'] in tlopen_sets and \
        buttons[game['buttonNameB']]['buttonSet'] in tlopen_sets:
        do_the_ratings(game)
        collect_button_stats(game)

    elif allowed_games == "all":
      do_the_ratings(game)
      collect_button_stats(game)

    else:
      raise Exception("must use a proper strategy for allowed_games")

  if len(search['games']) == 0:
    keep_going = False

  page += 1

print(
  f"strat:{allowed_games} games counted {total_games_included} / games considered {total_games_considered}")

print("LEADERBOARD")

# leaderboard = sorted(ratings, key=env.expose, reverse=True)

# sigma less than 4
# leaderboard = dict(filter(lambda elem: elem[1].sigma < 4.0, ratings.items()))
# OR
# min games played
min_games_played = 5
leaderboard = dict(
  filter(lambda elem: players_total_game_count[elem[0]] >= min_games_played,
         ratings.items()))

leaderboard = {k: v for k, v in
               sorted(leaderboard.items(), key=lambda item: expose(item[1]),
                      reverse=True)}
listedboard = list(leaderboard)
for k in leaderboard:
  num = listedboard.index(k) + 1
  tot_games = players_total_game_count[k]
  most_games = \
    max(players_button_counts[k]['freq'].items(), key=operator.itemgetter(1))[0]
  best_games = \
    max(players_button_counts[k]['best'].items(), key=operator.itemgetter(1))[0]
  print(
    f"{num:02} [player={k}] games={tot_games} most=[button={most_games}] best=[button={best_games}]")

print("CHALLENGERS")

leaderboard_challengers = dict(
  filter(lambda elem: players_total_game_count[elem[0]] < min_games_played,
         ratings.items()))
leaderboard_challengers = {k: v for k, v in
                           sorted(leaderboard_challengers.items(),
                                  key=lambda item: players_total_game_count[
                                    item[0]],
                                  reverse=True)}

listedboard_challengers = list(leaderboard_challengers)
for k in leaderboard_challengers:
  tot_games = players_total_game_count[k]
  most_games = \
    max(players_button_counts[k]['freq'].items(), key=operator.itemgetter(1))[0]
  if len(players_button_counts[k]['best']) > 0:
    best_games = \
      max(players_button_counts[k]['best'].items(), key=operator.itemgetter(1))[
        0]
  else:
    best_games = "n/a"
  print(
    f"[player={k}] games={tot_games} most=[button={most_games}] best=[button={best_games}]")

# observed_button_stats = {k: v for k, v in sorted(observed_button_stats.items(),
#                                                  key=lambda item: item[
#                                                                       1].games_won /
#                                                                   item[
#                                                                       1].games_played,
#                                                  reverse=True)}
# for s in bstats:
#     stat = bstats[s]
#     print(
#         f"{s} ({stat.games_won}/{stat.games_lost}) ({stat.rounds_won}/{stat.rounds_lost}/{stat.rounds_tied})")
