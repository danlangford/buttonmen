#!/usr/bin/env python3

import operator
import os
import sys
from datetime import datetime, date, timezone, timedelta
import requests
from bs4 import BeautifulSoup
from trueskill import Rating, rate_1vs1, expose

# WEIRD IMPORT
bmutilspath = "./lib"
sys.path.append(os.path.expanduser(bmutilspath).rstrip("/"))
from lib.bmutils import BMClientParser

# END WEIRD IMPORT

# CONFIG
bmrc = ".bmrc"
site = "www"

# options: all, tl, fair, tlopen, hitlistfeb21
_strategy = "hitlistfeb21"
_start_date = date(2021, 2, 1)
# _stop_date = date(2021, 2, 20)
_stop_date = date(2021, 3, 1) - timedelta(days=1)

tlopen_sets = ["Geekz", "Polycon", "Demicon the 13th", "Balticon 34",
               "SydCon 10"]
hitlistfeb21_sets = ["Free Radicals", "Chicago Crew", "Metamorphers"]
highlightplayer = 'nycavri'

banned_players = ['Nala', 'BMAI', 'BMBot', 'buttonbot', 'BMAIBagels',
                  'buttonbot2']


# END CONFIG

# OBJECT DEFINITIONS
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
  # Retrieved button stats from stats webpage
  def __init__(self, name, set, tl, rate, count):
    self.name = name.string.strip()
    self.set = set.string.strip()
    self.tl = tl.string.strip() == "Y"
    self.rate = float(rate.string.strip())
    self.count = int(count.string.strip())


# END OBJECTS

# GLOBAL STATE

bm = {}
buttons = {}
ratings = {}
observed_button_stats = {}
players_total_game_count = {}
players_total_win_count = {}
players_button_counts = {}

total_games_included = 0

# END GLOBAL STATE

# TODO ISOLATE this logic only if using FAIR strategy
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


# END POSSIBLE ISOLATION

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

  ####
  highlighting = False
  if highlightplayer and highlightplayer.lower() in [wplay.lower(),
                                                     lplay.lower()]:
    highlighting = True

  if highlighting:
    highlightWon = wplay.lower() == highlightplayer.lower()
    highlightButt = wbutt if highlightWon else lbutt
    opponentButt = lbutt if highlightWon else wbutt
    if opponentButt in ['Gripen', 'Poly', 'Sailor Man', 'Caine']:
      print(
          f"{highlightplayer} {'win' if highlightWon else 'lose'} {highlightButt} vs {opponentButt}")

  # if highlighting:
  #   highlightWins = wplay.lower() == highlightplayer.lower()
  #   highlightExpose0 = expose(wrate if highlightWins else lrate)
  #   otherExpose0 = expose(lrate if highlightWins else wrate)
  ####

  wrate, lrate = rate_1vs1(wrate, lrate)

  ####
  # if highlighting:
  #   highlightExpose1 = expose(wrate if highlightWins else lrate)
  #   otherExpose1 = expose(lrate if highlightWins else wrate)
  #
  #   highlightChange = highlightExpose1 - highlightExpose0
  #   otherChange = otherExpose1 - otherExpose0
  #
  #
  #   if highlightWins:
  #     print(
  #       f'{wplay}({highlightExpose0:.2f},{wrate.mu:.2f},{wrate.sigma:.2f}) WINS v {lplay}({otherExpose0:.2f}). RANK  {wplay}+{highlightChange:.2f} and {lplay}{otherChange:.2f}')
  #   else:
  #     print(
  #       f'{lplay}({highlightExpose0:.2f},{lrate.mu:.2f},{lrate.sigma:.2f}) LOSES v {wplay}({otherExpose0:.2f}). RANK {lplay}{highlightChange:.2f} and {wplay}+{otherChange:.2f}')
  ####

  ratings[wplay] = wrate
  ratings[lplay] = lrate
  players_total_win_count[wplay] = players_total_win_count.get(wplay, 0) + 1
  players_total_game_count[wplay] = players_total_game_count.get(wplay, 0) + 1
  players_total_game_count[lplay] = players_total_game_count.get(lplay, 0) + 1
  total_games_included += 1

  w_butt_counts = players_button_counts.get(wplay, {'freq': {}, 'best': {},
                                                    'rate': {}})
  w_butt_counts['freq'][wbutt] = w_butt_counts['freq'].get(wbutt, 0) + 1
  w_butt_counts['best'][wbutt] = w_butt_counts['best'].get(wbutt, 0) + 1
  w_butt_counts['rate'][wbutt] = w_butt_counts['best'][wbutt] / \
                                 w_butt_counts['freq'][wbutt]
  players_button_counts[wplay] = w_butt_counts

  l_butt_counts = players_button_counts.get(lplay, {'freq': {}, 'best': {},
                                                    'rate': {}})
  l_butt_counts['freq'][lbutt] = l_butt_counts['freq'].get(lbutt, 0) + 1
  l_butt_counts['best'][lbutt] = l_butt_counts['best'].get(lbutt,
                                                           0)  # dont increment, but make sure the value is populated, even if 0
  l_butt_counts['rate'][lbutt] = l_butt_counts['best'][lbutt] / \
                                 l_butt_counts['freq'][lbutt]
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


def collect_qualifying_games(strategy, status, start_date, stop_date):
  total_games_considered = 0
  keep_going = True
  size = 1000
  page = 1
  results = []

  while keep_going:
    print(f"fetching page {page} of size {size}")
    search = bm.wrap_search_game_history(
        sortColumn="lastMove",
        searchDirection="ASC",
        numberOfResults=size,
        page=page,
        status=status,  # "COMPLETE",  # ACTIVE
        lastMoveMin=int(datetime.combine(start_date, datetime.min.time(),
                                         tzinfo=timezone.utc).timestamp()),
        lastMoveMax=int(datetime.combine(stop_date, datetime.min.time(),
                                         tzinfo=timezone.utc).timestamp()))

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

      if strategy == "tl":
        if buttons[game['buttonNameA']]['isTournamentLegal'] and \
            buttons[game['buttonNameB']]['isTournamentLegal']:
          results.append(game)

      elif strategy == "fair":
        if 40 <= retrieved_button_stats[game['buttonNameA']].rate <= 60 and \
            retrieved_button_stats[game['buttonNameA']].count > 10 and \
            40 <= retrieved_button_stats[game['buttonNameB']].rate <= 60 and \
            retrieved_button_stats[game['buttonNameB']].count > 10:
          results.append(game)

      elif strategy == "tlopen":
        if buttons[game['buttonNameA']]['buttonSet'] in tlopen_sets and \
            buttons[game['buttonNameB']]['buttonSet'] in tlopen_sets:
          results.append(game)

      elif strategy == "hitlistfeb21":
        if buttons[game['buttonNameA']]['buttonSet'] in hitlistfeb21_sets and \
            buttons[game['buttonNameB']]['buttonSet'] in hitlistfeb21_sets:
          results.append(game)

      elif strategy == "all":
        results.append(game)

      else:
        raise Exception("must use a proper strategy for strategy")

    if len(search['games']) == 0:
      keep_going = False

    page += 1

  return results


def rate_and_stats(games):
  for game in games:
    do_the_ratings(game)
    collect_button_stats(game)


def print_report():
  print("[quote][b]LEADERBOARD[/b]")

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
    tot_wins = players_total_win_count[k]

    tot_win_rate = tot_wins / tot_games * 100
    tot_win_rate = f', {tot_win_rate:.0f}%' if tot_win_rate > 50 else ''

    # first [0] gets the first (max when reverse=true) in the list
    # second [0] gets the KEY from the KEY/value pair
    most_played = \
      sorted(players_button_counts[k]['freq'].items(),
             key=operator.itemgetter(1),
             reverse=True)
    most_won = \
      sorted(players_button_counts[k]['best'].items(),
             key=operator.itemgetter(1),
             reverse=True)
    most_rate = \
      sorted(players_button_counts[k]['rate'].items(),
             key=operator.itemgetter(1),
             reverse=True)

    interesting = ""
    for bn in players_button_counts[k]['freq']:
      bc = players_button_counts[k]['freq'][bn]
      br = players_button_counts[k]['rate'][bn] * 100
      if bc >= 5 and br > 50:
        if not interesting.startswith("Noteworthy"):
          interesting = "Noteworthy: " + interesting
        interesting += f"[button={bn}]({bc}, {br:.0f}%) "

      exposure = expose(ratings[k])

      if exposure >= 24.0:
        medal = "🥇"
      elif exposure >= 20.0:
        medal = "🥈"
      elif exposure >= 10.0:
        medal = "🥉"
      else:
        medal = "  "

    print(
        f"{num:2} [{exposure:5.2f}] {medal} [player={k}]({tot_games}{tot_win_rate}) {interesting}")

  print("[/quote]\n")
  print("[quote][b]PLACEMENT[/b]")

  leaderboard_placement = dict(
      filter(lambda elem: players_total_game_count[elem[0]] < min_games_played,
             ratings.items()))
  leaderboard_placement = {k: v for k, v in
                           sorted(leaderboard_placement.items(),
                                  key=lambda item: players_total_game_count[
                                    item[0]],
                                  reverse=True)}

  listedboard_placement = list(leaderboard_placement)
  for k in leaderboard_placement:
    tot_games = players_total_game_count[k]
    tot_wins = players_total_win_count.get(k, 0)

    tot_win_rate = tot_wins / tot_games * 100
    tot_win_rate = f', {tot_win_rate:.0f}%' if tot_win_rate > 50 and tot_games > 2 else ''
    print(
        f"[player={k}]({tot_games}{tot_win_rate})")

  print('[/quote]')


def login():
  bm_client = BMClientParser(os.path.expanduser(bmrc), site)
  if not bm_client.verify_login():
    print("Could not login")
    raise Exception("Could not login")
  return bm_client


if __name__ == "__main__":
  # init some global state
  bm = login()
  buttons = bm.wrap_load_button_names()
  completed_games = collect_qualifying_games(_strategy, "COMPLETE", _start_date,
                                             _stop_date)

  print(
      f"strategy:{_strategy} found {len(completed_games)} qualifying games "
      f"completed during…\n{_start_date} - {_stop_date}")

  rate_and_stats(completed_games)

  print_report()

  active_games = collect_qualifying_games(_strategy, "ACTIVE", _start_date,
                                          _stop_date)
  print(
    f"there are currently {len(active_games)} qualifying games still in progress")
