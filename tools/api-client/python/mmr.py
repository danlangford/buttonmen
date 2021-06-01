#!/usr/bin/env python3

import operator
import os
from datetime import datetime, date, timezone, timedelta

import requests
from bs4 import BeautifulSoup
from trueskill import Rating, rate, expose
from lib.bmutils import BMClientParser

# CONFIG
bmrc = ".bmrc"
site = "www"
print_details = False
highlight_general = True
highlight_player = None
highlight_fmt = 'forum'
print_noteworthy = True
print_medals = True
print_winrates = "some" # some, all, none

class Strategy(object):
  qualifies = None

  def __init__(self, f):
    self.qualifies = f


# options: all, tl, fair, tlopen, hitlistfeb21
_strategy = "hitlistmay21"
_strategies = {"all": Strategy(
    lambda game: True),
  "tl": Strategy(
      lambda game: buttons[game['buttonNameA']][
                     'isTournamentLegal'] and \
                   buttons[game['buttonNameB']][
                     'isTournamentLegal']),
  "fair": Strategy(
      lambda game: 40 <= retrieved_button_stats[
        game['buttonNameA']].rate <= 60 and
                   retrieved_button_stats[
                     game[
                       'buttonNameA']].count > 10 and
                   40 <= retrieved_button_stats[
                     game[
                       'buttonNameB']].rate <= 60 and
                   retrieved_button_stats[
                     game['buttonNameB']].count > 10),
  "tlopen": Strategy(
      lambda game: buttons[game['buttonNameA']][
                     'buttonSet'] in tlopen_sets and
                   buttons[game['buttonNameB']][
                     'buttonSet'] in tlopen_sets),
  "hitlistfeb21": Strategy(
      lambda game: buttons[game['buttonNameA']][
                     'buttonSet'] in hitlistfeb21_sets and
                   buttons[game['buttonNameB']][
                     'buttonSet'] in hitlistfeb21_sets),
  "hitlistmar21": Strategy(
      lambda game: buttons[game['buttonNameA']][
                     'buttonName'] in hitlistmar21_buttons and
                   buttons[game['buttonNameB']][
                     'buttonName'] in hitlistmar21_buttons),
  "hitlistapr21": Strategy(
      lambda game: buttons[game['buttonNameA']][
                     'buttonName'] in hitlistapr21_buttons and
                   buttons[game['buttonNameB']][
                     'buttonName'] in hitlistapr21_buttons),
  "hitlistmay21": Strategy(
      lambda game: (buttons[game['buttonNameA']][
                      'buttonName'] in hitlistmay21_peloton and
                    buttons[game['buttonNameB']][
                      'buttonName'] in hitlistmay21_diceland) or
                   (buttons[game['buttonNameA']][
                      'buttonName'] in hitlistmay21_diceland and
                    buttons[game['buttonNameB']][
                      'buttonName'] in hitlistmay21_peloton)),

}

_start_date = date(2021, 5, 1)
# _stop_date = date(2021, 5, 20)
# _stop_date = date(2021, 5, 20)
_stop_date = date(2021, 6, 1) - timedelta(days=1)

tlopen_sets = ["Geekz", "Polycon", "Demicon the 13th", "Balticon 34",
               "SydCon 10"]
hitlistfeb21_sets = ["Free Radicals", "Chicago Crew", "Metamorphers"]
hitlistmar21_buttons = ["amica", "bigevildan", "Downen", "Hooloovoo",
                        "Jasyeman", "jgenzano", "juelki", "lunatic", "moekon",
                        "perlmunkee", "roujin27", "sanny", "Yagharek"]
hitlistapr21_buttons = ["Vermont", "Washington", "Minnesota", "eon", "Famine",
                        "Fuyuko", "Captain Bingo", "Johnny", "Phuong", "Calmon",
                        "Bull", "Darrin", "opedog"]
hitlistmay21_peloton = ["Julia", "Doyle", "Floriano", "Antonio", "Timea",
                        "Mariusz", "Roger", "Orlando"]
hitlistmay21_diceland = ["Z-Don", "Micro", "Crysis", "Buck", "Cass", "Golo"]

banned_players = ['Nala', 'BMAI', 'BMBot', 'buttonbot', 'BMAIBagels', 'buttonbot2']
# banned_players = ['Nala', 'BMAI', 'BMBot', 'buttonbot', 'buttonbot2']
# banned_players = []


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
player_ratings = {}
button_ratings = {}
observed_button_stats = {}
players_total_game_count = {}
buttons_total_game_count = {}
players_total_win_count = {}
buttons_total_win_count = {}
players_button_counts = {}
buttons_player_counts = {}

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
  global player_ratings
  global button_ratings
  global players_total_game_count
  global buttons_total_game_count
  global players_total_win_count
  global buttons_total_win_count
  global total_games_included
  global players_button_counts
  global buttons_player_counts

  wplay, wbutt, lplay, lbutt = determine_winner(game)
  wprate = player_ratings.get(wplay, Rating())
  lprate = player_ratings.get(lplay, Rating())
  wbrate = button_ratings.get(wbutt, Rating())
  lbrate = button_ratings.get(lbutt, Rating())

  if highlight_player in [wplay, lplay] or highlight_general:
    wprate0=wprate
    lprate0=lprate
    wpexpo0=expose(wprate0)
    lpexpo0=expose(lprate0)

    wbrate0=wbrate
    lbrate0=lbrate
    wbexpo0=expose(wbrate0)
    lbexpo0=expose(lbrate0)

  (wprate,wbrate), (lprate,lbrate) = rate([[wprate,wbrate], [lprate,lbrate]])

  if highlight_player in [wplay, lplay] or highlight_general:
    wprate1=wprate
    lprate1=lprate

    wbrate1=wbrate
    lbrate1=lbrate

    wpmudiff = wprate1.mu-wprate0.mu
    lpmudiff = lprate1.mu-lprate0.mu
    wpsigmadiff = wprate1.sigma-wprate0.sigma
    lpsigmadiff = lprate1.sigma-lprate0.sigma

    wpexpo1=expose(wprate1)
    lpexpo1=expose(lprate1)
    wpexpodiff=wpexpo1-wpexpo0
    lpexpodiff=lpexpo1-lpexpo0

#   and (wpexpo1>lpexpo1 or wprate1.mu > lprate1.mu)

    worth_highlighting = (wprate0.sigma<3.75 and lprate0.sigma<3.75 and (lpexpo0 - wpexpo0 > 3 ) and players_total_game_count.get(wplay,0)>=4 and players_total_game_count.get(lplay,0)>=4 )
    #worth_highlighting=True

    if highlight_player in [wplay, lplay] or worth_highlighting:
      if highlight_fmt=='forum':
        if print_details:
          wprint = f"({wplay}):{wbutt} μ={wprate0.mu:0.2f}{'+' if wpmudiff>=0 else ''}{wpmudiff:0.2f} σ={wprate0.sigma:0.2f}{'+' if wpsigmadiff>=0 else ''}{wpsigmadiff:0.2f} x={wpexpo0:0.2f}{'+' if wpexpodiff>=0 else ''}{wpexpodiff:0.2f}"
          lprint = f"({lplay}):{lbutt} μ={lprate0.mu:0.2f}{'+' if lpmudiff>=0 else ''}{lpmudiff:0.2f} σ={lprate0.sigma:0.2f}{'+' if lpsigmadiff>=0 else ''}{lpsigmadiff:0.2f} x={lpexpo0:0.2f}{'+' if lpexpodiff>=0 else ''}{lpexpodiff:0.2f}"
        else:
          wprint = f"({wplay}):{wbutt} [{wpexpo0:0.2f}{'+' if wpexpodiff>=0 else ''}{wpexpodiff:0.2f}]"
          lprint = f"({lplay}):{lbutt} [{lpexpo0:0.2f}{'+' if lpexpodiff>=0 else ''}{lpexpodiff:0.2f}]"
        print(f"[game={game['gameId']}] {wprint} vs {lprint}")
      elif highlight_fmt=='csv':
        wprint = f"{wplay},{wbutt},{wprate0.mu:0.2f},{'+' if wpmudiff>=0 else ''}{wpmudiff:0.2f},{wprate0.sigma:0.2f},{'+' if wpsigmadiff>=0 else ''}{wpsigmadiff:0.2f},{wpexpo0:0.2f},{'+' if wpexpodiff>=0 else ''}{wpexpodiff:0.2f}"
        lprint = f"{lplay},{lbutt},{lprate0.mu:0.2f},{'+' if lpmudiff>=0 else ''}{lpmudiff:0.2f},{lprate0.sigma:0.2f},{'+' if lpsigmadiff>=0 else ''}{lpsigmadiff:0.2f},{lpexpo0:0.2f},{'+' if lpexpodiff>=0 else ''}{lpexpodiff:0.2f}"
        print(f"{game['gameId']},{wprint},{lprint}")

  player_ratings[wplay] = wprate
  player_ratings[lplay] = lprate
  if wbutt==lbutt:
    #print("not counting mirror matches")
    pass
  else:
    button_ratings[wbutt] = wbrate
    button_ratings[lbutt] = lbrate

  # update winner & loser player counts
  players_total_win_count[wplay] = players_total_win_count.get(wplay, 0) + 1
  players_total_game_count[wplay] = players_total_game_count.get(wplay, 0) + 1
  players_total_game_count[lplay] = players_total_game_count.get(lplay, 0) + 1

  # update winner & loser button counts
  buttons_total_win_count[wbutt] = buttons_total_win_count.get(wbutt, 0) + 1
  buttons_total_game_count[wbutt] = buttons_total_game_count.get(wbutt, 0) + 1
  buttons_total_game_count[lbutt] = buttons_total_game_count.get(lbutt, 0) + 1

  total_games_included += 1

  # update more winner player stats about buttons
  wp_button_counts = players_button_counts.get(wplay, {'freq': {}, 'best': {},
                                                    'rate': {}})
  wp_button_counts['freq'][wbutt] = wp_button_counts['freq'].get(wbutt, 0) + 1
  wp_button_counts['best'][wbutt] = wp_button_counts['best'].get(wbutt, 0) + 1
  wp_button_counts['rate'][wbutt] = wp_button_counts['best'][wbutt] / \
                                 wp_button_counts['freq'][wbutt]
  players_button_counts[wplay] = wp_button_counts




  # update more winner button stats about players
  wb_player_counts = buttons_player_counts.get(wbutt, {'freq': {}, 'best': {},
                                                    'rate': {}})
  wb_player_counts['freq'][wplay] = wb_player_counts['freq'].get(wplay, 0) + 1
  wb_player_counts['best'][wplay] = wb_player_counts['best'].get(wplay, 0) + 1
  wb_player_counts['rate'][wplay] = wb_player_counts['best'][wplay] / \
                                 wb_player_counts['freq'][wplay]
  buttons_player_counts[wbutt] = wb_player_counts


  # update more loser player stats about buttons
  lp_button_counts = players_button_counts.get(lplay, {'freq': {}, 'best': {},
                                                    'rate': {}})
  lp_button_counts['freq'][lbutt] = lp_button_counts['freq'].get(lbutt, 0) + 1
  lp_button_counts['best'][lbutt] = lp_button_counts['best'].get(lbutt,
                                                           0)  # dont increment, but make sure the value is populated, even if 0
  lp_button_counts['rate'][lbutt] = lp_button_counts['best'][lbutt] / \
                                 lp_button_counts['freq'][lbutt]
  players_button_counts[lplay] = lp_button_counts


  # update more loser button stats about players
  lb_player_counts = buttons_player_counts.get(lbutt, {'freq': {}, 'best': {},
                                                       'rate': {}})
  lb_player_counts['freq'][lplay] = lb_player_counts['freq'].get(lplay, 0) + 1
  lb_player_counts['best'][lplay] = lb_player_counts['best'].get(lplay,
                                                                 0)  # dont increment, but make sure the value is populated, even if 0
  lb_player_counts['rate'][lplay] = lb_player_counts['best'][lplay] / \
                                    lb_player_counts['freq'][lplay]
  buttons_player_counts[lbutt] = lb_player_counts


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


def collect_qualifying_games(strategy: Strategy, status, start_date, stop_date):
  total_games_considered = 0
  keep_going = True
  size = 1000
  page = 1
  results = []

  while keep_going:
    # print(f"fetching page {page} of size {size}")
    print('.')
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

      if strategy.qualifies(game):
        results.append(game)

    if len(search['games']) == 0:
      keep_going = False

    page += 1

  return results


def rate_and_stats(games):
  if highlight_general or highlight_player is not None:
    print("[quote][b]HIGHLIGHTS[/b]")
  for game in games:
    do_the_ratings(game)
    collect_button_stats(game)
  if highlight_general or highlight_player is not None:
    print("[/quote]")


def print_report(ratings, total_game_count, total_win_count, itemized_counts, tag_primary, tag_secondary):
  if print_details:
    print("PLACE=leaderboard numbering | EXPOSURE=how leaderboard is sorted, Mu-3*Sigma, approaches 25 | MU=estimated skill rating, everybody starts at 25 | SIGMA=confidense (inverse), everybody starts at 8.33… | MEDAL=static Exposure goal lines for personal acheivment, gold>=24, silver>=20, bronze>=10")
  print(f"[quote][b]{tag_primary.upper()} LEADERBOARD[/b]")

  min_games_played = 5
  leaderboard = dict(
      filter(lambda elem: total_game_count[elem[0]] >= min_games_played,
             ratings.items()))

  leaderboard = {k: v for k, v in
                 sorted(leaderboard.items(), key=lambda item: expose(item[1]),
                        reverse=True)}
  listedboard = list(leaderboard)
  for k in leaderboard:
    num = listedboard.index(k) + 1
    tot_games = total_game_count[k]
    tot_wins = total_win_count.get(k, 0)

    tot_win_rate = tot_wins / tot_games * 100
    if print_details:
      tot_win_rate = f', win_rate={tot_win_rate:.0f}%'
    elif print_winrates=='all':
      tot_win_rate = f', {tot_win_rate:.0f}%'
    elif print_winrates=='some':
      tot_win_rate = f', {tot_win_rate:.0f}%' if tot_win_rate > 50 else ''
    else:
      tot_win_rate = ''

    # first [0] gets the first (max when reverse=true) in the list
    # second [0] gets the KEY from the KEY/value pair
    most_played = \
      sorted(itemized_counts[k]['freq'].items(),
             key=operator.itemgetter(1),
             reverse=True)
    most_won = \
      sorted(itemized_counts[k]['best'].items(),
             key=operator.itemgetter(1),
             reverse=True)
    most_rate = \
      sorted(itemized_counts[k]['rate'].items(),
             key=operator.itemgetter(1),
             reverse=True)

    interesting = ""
    if print_noteworthy:
      for i_n in itemized_counts[k]['freq']:
        i_c = itemized_counts[k]['freq'][i_n]
        i_r = itemized_counts[k]['rate'][i_n] * 100
        if i_c >= 5 and i_r > 50:
          if not interesting.startswith("Noteworthy"):
            interesting = "Noteworthy: " + interesting
          interesting += f"[{tag_secondary}={i_n}]({i_c}, {i_r:.0f}%) "

    exposure = expose(ratings[k])

    medal = "medal=" if print_details else ""
    if print_medals:
      if exposure >= 24.0:
        medal += "🥇"
      elif exposure >= 20.0:
        medal += "🥈"
      elif exposure >= 10.0:
        medal += "🥉"
      else:
        medal += "  "

    if print_details:
      print(f"place={num:2} exposure=[{exposure:0.2f}] mu={ratings[k].mu:0.2f} sigma={ratings[k].sigma:0.2f} {medal} {tag_primary}=[{tag_primary}={k}](games={tot_games}{tot_win_rate}) {interesting}")
    else:
      print(f"{num:2} [{exposure:5.2f}] {medal} [{tag_primary}={k}]({tot_games}{tot_win_rate}) {interesting}")

  print("[/quote]")
  if print_details:
    print("the PLACEMENT table is sorted by number of placement matches, not by Exposure. Exposure is shown so you can see where they might slot into the rest of the leaderboard")
  print(f"[quote][b]{tag_primary.upper()} PLACEMENT[/b]")

  leaderboard_placement = dict(
      filter(lambda elem: total_game_count[elem[0]] < min_games_played,
             ratings.items()))
  leaderboard_placement = {k: v for k, v in
                           sorted(leaderboard_placement.items(),
                                  key=lambda item: total_game_count[
                                    item[0]],
                                  reverse=True)}

  listedboard_placement = list(leaderboard_placement)
  for k in leaderboard_placement:
    tot_games = total_game_count[k]
    tot_wins = total_win_count.get(k, 0)

    tot_win_rate = tot_wins / tot_games * 100
    if print_details:
      tot_win_rate = f', win_rate={tot_win_rate:.0f}%'
    else:
      tot_win_rate = f', {tot_win_rate:.0f}%' if tot_win_rate > 50 and tot_games > 2 else ''

    if print_details:
      print(f"exposure=[{expose(ratings[k]):0.2f}] mu={ratings[k].mu:0.2f} sigma={ratings[k].sigma:0.2f} {tag_primary}=[{tag_primary}={k}](games={tot_games}{tot_win_rate})")
    else:
      print(f"[{tag_primary}={k}]({tot_games}{tot_win_rate})")

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
  completed_games = collect_qualifying_games(_strategies[_strategy],
                                             "COMPLETE", _start_date,
                                             _stop_date)

  print(
      f"strategy:{_strategy} found {len(completed_games)} qualifying games "
      f"completed during…\n{_start_date} - {_stop_date}")

  rate_and_stats(completed_games)

  print_report(player_ratings, players_total_game_count, players_total_win_count, players_button_counts, 'player', 'button')
  print('\n')
  print_report(button_ratings, buttons_total_game_count, buttons_total_win_count, buttons_player_counts, 'button', 'player')

  active_games = collect_qualifying_games(_strategies[_strategy],
                                          "ACTIVE",
                                          _start_date,
                                          _stop_date)
  print(
      f"there are currently {len(active_games)} qualifying games still in progress")
