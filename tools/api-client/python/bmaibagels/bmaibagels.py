#!/usr/bin/env python3
import argparse
import random
import traceback
from os import listdir
from subprocess import Popen, PIPE
from bmaipy import BMAI, bmai_supported_skills

import fortune
from func_timeout import func_set_timeout, FunctionTimedOut

import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).parent.parent.resolve())+"/lib")

import bmutils
import game_data
import monitor

# are warrior dice not working well?

# the bot used to not consider your already-set-swing dice when it was alowed to adjust its own. fixed
# focus doesn't work when BMAI is running on linux for some reason.
# need to not accept games that have some specials skills we cant account for (Japanese Beetle)

always_odds = [item.lower() for item in ["Bagels", "AnnoDomini", "ElihuRoot"]]
debug_chat = [item.lower() for item in ["Bagels"]]


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "-b",
      "--binary",
      help="path to BMAI binary",
      type=str,
      default="./bmai-v3.0-45-g5f3e623",
  )
  parser.add_argument(
      "-c",
      "--config",
      help="config file containing site parameters",
      type=str,
      default=".bmrc",
  )
  parser.add_argument(
      "-s",
      "--site",
      help="name of config section within config file that defines what buttonweavers site to access",
      type=str)
  parser.add_argument(
      "-f",
      "--filter",
      help="filter out games",
      type=str,
      default="all",
      choices=["all", "odd", "even"],
  )
  parser.add_argument(
    "--sort",
    help="sort game list",
    default="asc",
    type=str,
    choices=["shuffle", "desc", "asc"],
  )
  parser.add_argument(
      "-g",
      "--gameid",
      help="game to run AI against. may make multiple moves against game but will not monitor for other games to play",
      type=int)
  parser.add_argument(
      "-p",
      "--ply",
      help="set AI ply (lookahead)",
      type=int,
      default=3,
      choices=[0, 1, 2, 3, 4, 5],
  )
  parser.add_argument(
      "--count",
      help="how many games to try before getting a new list of games. useful with `--sort desc` to play the most recent games first while continuing to look for recent games",
      type=int,
      default=-1,
  )
  return parser.parse_args()


class BMAIBagels(object):

  def __init__(self,
               client: bmutils.BMClientParser,
               ply,
               binary,
               filter="all",
               sort="asc",
               count=-1):
    self.client = client
    self.monitor = monitor.Monitor(self.client)
    self.game_data = game_data.GameData(self.client)
    self.bad_games = []
    self.buttons = []
    self.filter = filter
    self.sort = sort
    self.bmai = BMAI()
    self.utils = SomeUtils()
    self.ply = ply
    self.binary = binary
    self.count = count

  def start_monitor(self):
    self.monitor.start(
        handle_active=self.monitor_handler,
        handle_new=self.new_challenge,
        await_confirm=False,
        sort=self.sort,
        filter=self.filter,
        max=self.count,
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

    return self.client.wrap_react_to_new_game(gameid, action)

  def monitor_handler(self, game, calc_other_side=False):
    gameid = game["gameId"]
    if gameid in self.bad_games:
      return False

    # if gameid not in [80638]:
    #   return

    game = self.game_data.fetch(gameid)

    if game["gameState"] in ["END_GAME", "CANCELLED", "DETERMINE_INITIATIVE"]:
      print(f"game {gameid} state is {game['gameState']}")
      return True

    if not game["player"]["waitingOnAction"] and not calc_other_side:
      # may have come in recursivly and we need to break away if its not actually our turn
      print(f"not my turn in game {gameid}")
      return True

    if calc_other_side:

      if game["gameState"] not in ["START_TURN"]:
        print(f"game {gameid} is at {game['gameState']}, dont waste time calculating other side")
        return True

      if game["player"]["waitingOnAction"]:
        print(f"game {gameid} is waiting on action, no time to calculate other side")
        return True
      else:
        print(f"calculating the other side")


    can_check_other_odds = False

    for ply in range(self.ply, -1, -1):
      if ply is not self.ply:
        print(f"trying ply {ply}")
      bmai_input = game_data.bmai.dump(game, ply=ply)
      try:
        can_check_other_odds = self.exec_bmai(
            bmai_input,
            game=game,
            state=game["gameState"],
            other_odds=calc_other_side,
        )
        break
      except FunctionTimedOut:
        print(f"timed out gameId={game['gameId']} ply={ply}")
        if ply == 0:
          ## tried ply all the way down to 0. still timout problems
          self.bad_game(game["gameId"], bmai_input, f"started at ply={self.ply} and reached ply={ply} while still timing out")
          return False
      except BaseException as e:
        ## some other problem
        message = getattr(e, 'message', repr(e))
        print(f"Exception {message}")
        if "You can't edit the requested chat message now" in message:
          break
        traceback.print_tb(e.__traceback__)
        self.bad_game(game["gameId"], bmai_input, message)
        return False

    # if we have been calcing the other side then we need to be DONE!!!
    if calc_other_side:
      return True

    # lets immediately try to go again
    # to quickly address the situations where we won initiative
    # or the other player was forced to pass
    # also try to calculate the new odds after a re-roll
    return self.monitor_handler(game, calc_other_side=can_check_other_odds)

  @func_set_timeout(60 * 60)  #
  def exec_bmai(self, input, game, state, other_odds=False):
    bmai = Popen([self.binary],
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

    acted = False
    printed = False
    can_check_other_odds = False
    win_odds = None
    stats = None
    problem = None

    for line in bmai.stdout:
      if " p0 best move " in line and "%" in line:
        win_odds = line.split("%")[0].split()[-1]
      if line.startswith("stats "):
        stats = line
      if "err" in line or "fail" in line:
        print(line, end="")
        problem = line
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
          (isok, can_check_other_odds, atk_resp) = self.submit_attack(
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
          else:
            problem = atk_resp
          continue
        elif state == "REACT_TO_INITIATIVE":
          action = bmai.stdout.readline().strip()
          acted = self.react_initiative(game, action)
          continue
    if printed:
      print("")
    if not acted and other_odds and win_odds is not None:
      new_odds = "%0.1f" % (100 - float(win_odds))
      print(f"other_odds={other_odds} win_odds={win_odds} new_odds={new_odds}")
      (chat, x) = self.determine_chat(
          game, None, win_odds=new_odds, other_odds=True)
      lastchatlog = game["gameChatLog"][0]
      chat = lastchatlog["message"] + "\nedit: " + chat
      retval = self.client.wrap_submit_chat(game["gameId"], chat, edit_timestamp=lastchatlog["timestamp"])
    if not acted and not other_odds:
      print("¯\\_(ツ)_/¯")
      self.bad_game(game["gameId"], input, f"no action taken\n¯\\_(ツ)_/¯\n{problem}")
    bmai.stdin.flush()
    bmai.stdin.close()
    bmai.stdout.flush()
    bmai.stdout.close()
    bmai.stderr.flush()
    bmai.stderr.close()
    return can_check_other_odds

  def submit_swings(self, game, swing_select, opt_select):
    swing_array = dict()
    opt_array = dict()
    for swing in swing_select:
      parts = swing.split(" ")
      swing_array[parts[1]] = parts[2]
    for opt in opt_select:
      parts = opt.split(" ")
      opt_array[parts[1]] = parts[2]

    retval = self.client.client.submit_die_values(
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
    retval = self.client.client.react_to_initiative(
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
      retval = self.client.client.react_to_initiative(
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
      retval = self.client.client.choose_reserve_dice(game["gameId"], "decline")
    else:
      retval = self.client.client.choose_reserve_dice(game["gameId"], "add",
                                                      die_idx)

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

    (chat, can_check_other_odds) = self.determine_chat(game, banner, win_odds,
                                                       stats)

    retval = self.client.client.submit_turn(
        game["gameId"],
        my_idx,
        their_idx,
        dieSelectStatus=die_selects,
        attackType=type.capitalize(),
        timestamp=game["timestamp"],
        roundNumber=game["roundNumber"],
        turboVals=turbo_array,
        chat=chat,
    )
    print(retval.message)
    return retval.status == "ok", can_check_other_odds, retval.message

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

  def determine_chat(self,
                     game,
                     banner,
                     win_odds=None,
                     stats=None,
                     other_odds=False):

    debug = f" @ {game['gameState']}" if game["opponent"]["playerName"].lower() in debug_chat else ""
    
    sorted_chat = sorted(game["gameChatLog"], key=lambda x: x["timestamp"])

    bot_has_talked = False
    opponent_needs_reply = False

    opponent_last_chat_time = 0
    opponent_last_chat_mesg = ""
    bot_last_chat_time = 0
    bot_last_chat_mesg = ""

    for c in sorted_chat:
      if c["player"] == self.client.username:
        bot_last_chat_time = max(bot_last_chat_time, c["timestamp"])
        bot_last_chat_mesg = c["message"]
      else:
        opponent_last_chat_time = max(opponent_last_chat_time, c["timestamp"])
        opponent_last_chat_mesg = c["message"]

    if bot_last_chat_time > 0:
      bot_has_talked = True
    if opponent_last_chat_time > bot_last_chat_time:
      opponent_needs_reply = True

    retval = None
    if other_odds and "chance BMAIBagels wins" in bot_last_chat_mesg:
      retval = f"{win_odds}% chance BMAIBagels wins (after re-roll) {debug}"
    elif not bot_has_talked:
      retval = banner + "\nCOMMANDS: odds, stats"
    elif opponent_needs_reply:
      if opponent_last_chat_mesg.lower().startswith("bad bot"):
        retval = "sorry :-("
      elif opponent_last_chat_mesg.lower().startswith("good bot"):
        retval = "thanks (*^.^*)"
      elif stats is not None and "stats" in opponent_last_chat_mesg.lower():
        retval = stats
      elif win_odds is not None and (
          "win?" in opponent_last_chat_mesg.lower() or
          "odds" in opponent_last_chat_mesg.lower() or
          game["opponent"]["playerName"].lower() in always_odds):
        retval = f"{win_odds}% chance BMAIBagels wins (before re-roll) {debug}"
      else:
        retval = self.utils.get_random_fortune()
    elif game["opponent"]["playerName"].lower() in always_odds:
      retval = f"{win_odds}% chance BMAIBagels wins (before re-roll) {debug}"

    print(f"chat: {retval}")
    if not retval:
      return "", False
    else:
      return retval, ("chance BMAIBagels wins" in retval and not other_odds)

  def bad_game(self, game_id, game_input, info=None):
    self.bad_games.append(game_id)
    text_file = open(f"{game_id}-input.txt", "wt")
    text_file.write(game_input)
    text_file.close()
    if info is not None:
      text_file = open(f"{game_id}-info.txt", "wt")
      text_file.write(info)
      text_file.close()


class SomeUtils:

  def get_fortune_file(self):
    current_dir = pathlib.Path(__file__).parent.resolve()
    return f"{current_dir}/fortunes/" + random.choice(listdir(f"{current_dir}/fortunes")).replace(
        ".dat", "")

  def get_random_fortune(self):
    return fortune.get_random_fortune(self.get_fortune_file())


if __name__ == "__main__":
  print("startup fortune test:")
  print(SomeUtils().get_random_fortune())
  args = parse_args()
  print(f"args={args}")
  bmclient = bmutils.BMClientParser(args.config, args.site)
  bmaibagels = BMAIBagels(
      bmclient,
      filter=args.filter,
      sort=args.sort,
      ply=args.ply,
      binary=args.binary,
      count=args.count,
  )
  if args.gameid:
    bmaibagels.monitor_handler({"gameId": args.gameid})
  else:
    bmaibagels.start_monitor()
