#!/usr/bin/env python3
import argparse
import random
from os import path, listdir
from subprocess import Popen, PIPE
from bmaipy import BMAI, bmai_supported_skills

import fortune

import game_data
import monitor
from lib import bmutils
from func_timeout import func_set_timeout, FunctionTimedOut

# are warrior dice not working well?
# focus and chance dice were not working but that was fixed
# the bot used to not consider your already-set-swing dice when it was alowed to adjust its own. fixed
# focus doesn't work when BMAI is running on linux for some reason.
# need to not accept games that have some specials skills we cant account for (Japanese Beetle)

always_odds = [item.lower() for item in ["Bagels", "AnnoDomini", "ElihuRoot"]]


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "-c",
      "--config",
      help="config file containing site parameters",
      type=str,
      default=".bmrc",
  )
  parser.add_argument(
      "-s", "--site", help="buttonmen site to access", type=str, default="bmai")
  parser.add_argument(
      "-f",
      "--filter",
      help="filter out games",
      type=str,
      default="all",
      choices=["all", "odd", "even"],
  )
  parser.add_argument(
      "-r",
      "--random",
      help="randomize game list",
      default=False,
      action="store_true",
      dest="random",
  )
  parser.add_argument("-g", "--gameid", help="run on 1 specific game", type=int)
  return parser.parse_args()


class BMAIBagels(object):

  def __init__(self,
               client: bmutils.BMClientParser,
               filter="all",
               shuffle=False):
    self.client = client
    self.monitor = monitor.Monitor(self.client)
    self.game_data = game_data.GameData(self.client)
    self.bad_games = []
    self.buttons = []
    self.filter = filter
    self.doshuffle = shuffle
    self.bmai = BMAI()
    self.utils = SomeUtils()

  def start_monitor(self):
    self.monitor.start(
        handle_active=self.monitor_handler,
        handle_new=self.new_challenge,
        await_confirm=False,
        shuffle=self.doshuffle,
        filter=self.filter,
    )

  def new_challenge(self, game):
    # TODO: some dice exist where we could "accept" the game
    #  and not "use" the dice like AUX dice.
    #  they would need to be hidden from BMAI
    gameid = game["gameId"]
    if len(self.buttons) == 0:
      self.buttons = self.client.wrap_load_button_names()
    myskills = (
        self.buttons[game["myButtonName"]]["dieTypes"] +
        self.buttons[game["myButtonName"]]["dieSkills"])
    theirskills = (
        self.buttons[game["opponentButtonName"]]["dieTypes"] +
        self.buttons[game["opponentButtonName"]]["dieSkills"])
    supportset = set(myskills + theirskills)
    disallowedset = supportset - bmai_supported_skills
    if len(disallowedset) > 0:
      print(f"Not accepting games with the following: {disallowedset}")
      action = "reject"
    else:
      action = "accept"

    retval = self.client.react_to_new_game(gameid, action)
    print(retval.message)
    return retval.status == "ok"

  def monitor_handler(self, game, calc_other_side=False):
    gameid = game["gameId"]
    if gameid in self.bad_games:
      return

    # if gameid not in [80638]:
    #   return

    game = self.game_data.fetch(gameid)

    if not game["player"]["waitingOnAction"] and calc_other_side:
      print("calculating the other side")

    # may have come in recursivly and we need to break away if its not actually our turn
    if not game["player"]["waitingOnAction"] and not calc_other_side:
      self.monitor_handler(game, calc_other_side=True)
      print("not my turn")
      return

    bmai_input = game_data.bmai.dump(game)
    try:
      self.exec_bmai(bmai_input, game=game, state=game["gameState"], other_odds = calc_other_side)
    except FunctionTimedOut:
      print(f"timed out in {game['gameId']}")

      print("trying ply 2")
      bmai_input = game_data.bmai.dump(game, 2)
      try:
        self.exec_bmai(bmai_input, game=game, state=game["gameState"], other_odds = calc_other_side)
      except FunctionTimedOut:
        print(f"timed out in {game['gameId']}")

        print("trying ply 1")
        bmai_input = game_data.bmai.dump(game, 1)
        try:
          self.exec_bmai(bmai_input, game=game, state=game["gameState"], other_odds = calc_other_side)
        except FunctionTimedOut:
          print(f"timed out in {game['gameId']}")

          ## tried ply 3, 2, and 1. still timout problems
          self.bad_game(game["gameId"], bmai_input)


    # if we have been calcing the other side then we need to be DONE!!!
    if calc_other_side:
      return

    # lets immediately try to go again
    # to quickly address the situations where we won initiative
    # or the other player was forced to pass
    self.monitor_handler(game, calc_other_side=False)
    # someday use 'calc_other_side' to determine the new odds of winning.
    # this will be don by making the other players move, extracting odds, and calculating the inverse odds

  @func_set_timeout(3600)
  def exec_bmai(self, input, game, state, other_odds=False):
    bmai = Popen(["./bmai"],
                 stdin=PIPE,
                 stdout=PIPE,
                 stderr=PIPE,
                 universal_newlines=True)
    bmai.stdin.write(input)
    bmai.stdin.flush()

    _title = bmai.stdout.readline()
    _copyright = bmai.stdout.readline()
    _contact = bmai.stdout.readline()
    _version = bmai.stdout.readline()
    banner = _title + _copyright + _version

    if other_odds:
      print(123)

    acted = False
    printed = False
    win_odds = None
    stats = None
    for line in bmai.stdout:
      if " p0 best move " in line and "%" in line:
        win_odds = line.split("%")[0].split()[-1]
      if line.startswith("stats "):
        stats = line
      if "err" in line or "fail" in line:
        print(line, end="")
        printed = True
      if not other_odds and "action" in line:
        if state == "SPECIFY_DICE":
          # TODO swing/opt better
          swings = len(game["player"]["swingRequestArray"])
          opts = len(game["player"]["optRequestArray"])
          swing_select = []
          opt_select = []
          for s in range(swings + opts):
            l = bmai.stdout.readline().strip()
            if l.startswith("swing"):
              swing_select.append(l)
            elif l.startswith("option"):
              opt_select.append(l)
          acted = self.submit_swings(game, swing_select, opt_select)
          continue
        elif state == "CHOOSE_RESERVE_DICE":
          l = bmai.stdout.readline().strip()
          acted = self.submit_reserve(game, l)
          continue
        elif state == "START_TURN":
          turbos = len(game["player"]["turboSizeArray"])
          turbo_select = []
          atk_type = bmai.stdout.readline().strip()
          source_dice = bmai.stdout.readline().strip()
          target_dice = bmai.stdout.readline().strip()
          for t in range(turbos):
            l = bmai.stdout.readline().strip()
            if len(l) > 0:
              turbo_select.append(l)
          isok = self.submit_attack(
              game,
              atk_type,
              source_dice,
              target_dice,
              turbo_select=turbo_select,
              banner=banner,
              win_odds=win_odds,
              stats=stats,
          )
          if isok:
            acted = True
          continue
        elif state == "REACT_TO_INITIATIVE":
          action = bmai.stdout.readline().strip()
          acted = self.react_initiative(game, action)
          continue
    if printed:
      print("")
    if not acted and other_odds:
      print(f"other_odds={other_odds} win_odds={float(win_odds)} inverse={100-float(win_odds)}")
      new_odds = 100-float(win_odds)
      # self.submit_chat_edit() this will need to call determine_chat
      # i think we need to eventually call submitChat
      # MIME Type: application/x-www-form-urlencoded; charset=UTF-8
      # {"type":"submitChat","game":"91841","chat":"testing chat edit"}
    if not acted and not other_odds:
      print("¯\_(ツ)_/¯ ")
      self.bad_game(game["gameId"], input)
    bmai.stdin.flush()
    bmai.stdin.close()
    bmai.stdout.flush()
    bmai.stdout.close()
    bmai.stderr.flush()
    bmai.stderr.close()

  def submit_swings(self, game, swing_select, opt_select):
    swing_array = dict()
    opt_array = dict()
    for swing in swing_select:
      parts = swing.split(" ")
      swing_array[parts[1]] = parts[2]
    for opt in opt_select:
      parts = opt.split(" ")
      opt_array[parts[1]] = parts[2]

    retval = self.client.submit_die_values(
        game["gameId"],
        swingArray=swing_array,
        optionArray=opt_array,
        roundNumber=game["roundNumber"],
        timestamp=game["timestamp"],
    )
    print(retval.message)
    return retval.status == "ok"

  def react_initiative(self, game, action):
    idx = []
    val = []
    if action == "pass":
      action = "decline"
    else:
      parts = action.split()
      action = parts[0]
      idx.append(parts[1])
      if len(parts) > 2:
        val.append(parts[2])
    retval = self.client.react_to_initiative(
        game["gameId"],
        action,
        idx,
        val,
        roundNumber=game["roundNumber"],
        timestamp=game["timestamp"],
    )
    print(retval.message)
    if "did not turn your focus dice down far enough" in retval.message:
      # BMAI sometimes does this sometimes and will get stuck
      # currently i dont have a loop to retrigger BMAI
      # and if i did i dont have a way of telling BMAI to produce something
      # different with the same inputs
      # for now, decline
      retval = self.client.react_to_initiative(
          game["gameId"],
          "decline",
          [],
          [],
          roundNumber=game["roundNumber"],
          timestamp=game["timestamp"],
      )
      print(retval.message)
    return retval.status == "ok"

  def submit_reserve(self, game, reserve_cmd):
    die_idx = reserve_cmd.split()[1]
    if die_idx == "-1":
      retval = self.client.choose_reserve_dice(game["gameId"], "decline")
    else:
      retval = self.client.choose_reserve_dice(game["gameId"], "add", die_idx)

    print(retval.message)
    return retval.status == "ok"

  def submit_attack(
      self,
      game,
      type,
      source,
      target,
      turbo_select,
      banner=None,
      win_odds=None,
      stats=None,
  ):
    my_idx = game["activePlayerIdx"]
    their_idx = 0 if my_idx == 1 else 1
    die_selects = self._generate_attack_array(game, my_idx, their_idx,
                                             source.split(" "),
                                             target.split(" "))
    turbo_array = dict()
    for turbo in turbo_select:
      parts = turbo.split(" ")
      # i know this turbo die finder isnt ideal.
      # will break when there are multiple turbos
      turbo_idx = max(source.split(" "))
      turbo_array[turbo_idx] = parts[2]
    retval = self.client.submit_turn(
        game["gameId"],
        my_idx,
        their_idx,
        dieSelectStatus=die_selects,
        attackType=type.capitalize(),
        timestamp=game["timestamp"],
        roundNumber=game["roundNumber"],
        turboVals=turbo_array,
        chat=self.determine_chat(game, banner, win_odds, stats),
    )
    print(retval.message)
    return retval.status == "ok"

  def _generate_attack_array(self, game, my_idx, their_idx, attackers,
                             defenders):
    attack = {}
    for i in range(len(game["playerDataArray"][my_idx]["activeDieArray"])):
      attack[f"playerIdx_{my_idx:d}_dieIdx_{i:d}"] = (True if str(i)
                                                      in attackers else False)
    for i in range(len(game["playerDataArray"][their_idx]["activeDieArray"])):
      attack[f"playerIdx_{their_idx:d}_dieIdx_{i:d}"] = (
          True if str(i) in defenders else False)
    return attack

  def determine_chat(self, game, banner, win_odds=None, stats=None, other_odds=False):

    sortedchat = sorted(game["gameChatLog"], key=lambda x: x["timestamp"])

    ihavetalked = False
    opponent_needs_reply = False

    lasttheirchattime = 0
    lasttheirmessage = ""
    lastmychattime = 0
    lastmymessage = ""

    for c in sortedchat:
      if c["player"] == self.client.username:
        lastmychattime = max(lastmychattime, c["timestamp"])
        lastmymessage = c["message"]
      else:
        lasttheirchattime = max(lasttheirchattime, c["timestamp"])
        lasttheirmessage = c["message"]

    if lastmychattime > 0:
      ihavetalked = True
    if lasttheirchattime > lastmychattime:
      opponent_needs_reply = True

    retval = None
    if other_odds and "chance to win" in lastmymessage:
      retval = f"{win_odds}% chance to win (after the re-roll)"
    elif not ihavetalked:
      retval = banner + "\nCOMMANDS: odds, stats"
    elif opponent_needs_reply:
      if lasttheirmessage.lower().startswith("bad bot"):
        retval = "sorry :-("
      elif lasttheirmessage.lower().startswith("good bot"):
        retval = "thanks (*^.^*)"
      elif stats is not None and "stats" in lasttheirmessage.lower():
        retval = stats
      elif win_odds is not None and ("win?" in lasttheirmessage.lower() or
                                    "odds" in lasttheirmessage.lower() or
                                     game["opponent"]["playerName"].lower()
                                     in always_odds):
        retval = f"{win_odds}% chance to win (before the re-roll)"
      else:
        retval = self.utils.get_random_fortune()
    elif game["opponent"]["playerName"].lower() in always_odds:
      retval = f"{win_odds}% chance to win"

    if not retval:
      return ""
    else:
      print(retval)
      return f"[code]{retval}[/code]"

  def bad_game(self, game_id, game_input):
    self.bad_games.append(game_id)
    text_file = open(f"{game_id}input.txt", "wt")
    n = text_file.write(game_input)
    text_file.close()


class SomeUtils:

  def get_fortune_file(self):
    return "./fortunes/" + random.choice(listdir("./fortunes")).replace(
        ".dat", "")

  def get_random_fortune(self):
    return fortune.get_random_fortune(self.get_fortune_file())


if __name__ == "__main__":
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  bmaibagels = BMAIBagels(bmclient, filter=args.filter, shuffle=args.random)
  if args.gameid:
    bmaibagels.monitor_handler({"gameId": args.gameid})
  else:
    bmaibagels.start_monitor()
