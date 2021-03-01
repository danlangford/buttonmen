#!/usr/bin/env python3
import argparse
import random
from os import path
from subprocess import Popen, PIPE

import fortune

import game_data
import monitor
from lib import bmutils


# are warrior dice not working well?
# focus and chance dice were not working but that was fixed
# the bot used to not consider your already-set-swing dice when it was alowed to adjust its own. fixed
# focus doesnt work when BMAI is running on linux for some reason.
# need to no accept games that have some specials skills we cant account for (Japanese Beetle)


set_of_supported_skills = {'Twin', 'Swing', 'Poison', 'Speed', 'Shadow',
                           'Stealth', 'Queer', 'Trip', 'Mood', 'Null', 'Option',
                           'Berserk', 'TimeAndSpace', 'Mighty', 'Weak',
                           'Reserve', 'Ornery', 'Chance', 'Morphing', 'Focus',
                           'Warrior', 'Slow', 'Unique', 'Stinger', 'R Swing',
                           'S Swing', 'T Swing', 'U Swing', 'V Swing',
                           'W Swing', 'X Swing', 'Y Swing', 'Z Swing', }

list_of_fortunes = [
  '/usr/local/share/games/fortunes/art',
  '/usr/local/share/games/fortunes/ascii-art',
  '/usr/local/share/games/fortunes/computers',
  '/usr/local/share/games/fortunes/cookie',
  '/usr/local/share/games/fortunes/definitions',
  # '/usr/local/share/games/fortunes/drugs',
  '/usr/local/share/games/fortunes/education',
  # '/usr/local/share/games/fortunes/ethnic',
  '/usr/local/share/games/fortunes/food',
  '/usr/local/share/games/fortunes/fortunes',
  '/usr/local/share/games/fortunes/goedel',
  '/usr/local/share/games/fortunes/humorists',
  '/usr/local/share/games/fortunes/kids',
  '/usr/local/share/games/fortunes/law',
  '/usr/local/share/games/fortunes/linuxcookie',
  '/usr/local/share/games/fortunes/literature',
  '/usr/local/share/games/fortunes/love',
  '/usr/local/share/games/fortunes/magic',
  '/usr/local/share/games/fortunes/medicine',
  # '/usr/local/share/games/fortunes/men-women',
  '/usr/local/share/games/fortunes/miscellaneous',
  '/usr/local/share/games/fortunes/news',
  '/usr/local/share/games/fortunes/people',
  '/usr/local/share/games/fortunes/pets',
  '/usr/local/share/games/fortunes/platitudes',
  # '/usr/local/share/games/fortunes/politics',
  '/usr/local/share/games/fortunes/riddles',
  '/usr/local/share/games/fortunes/science',
  '/usr/local/share/games/fortunes/songs-poems',
  '/usr/local/share/games/fortunes/sports',
  '/usr/local/share/games/fortunes/startrek',
  # '/usr/local/share/games/fortunes/translate-me',
  '/usr/local/share/games/fortunes/wisdom',
  '/usr/local/share/games/fortunes/work',
  '/usr/local/share/games/fortunes/zippy',
] if path.isfile('/usr/local/share/games/fortunes/fortunes') else [
  '/usr/share/games/fortunes/art',
  '/usr/share/games/fortunes/ascii-art',
  '/usr/share/games/fortunes/computers',
  '/usr/share/games/fortunes/cookie',
  '/usr/share/games/fortunes/definitions',
  '/usr/share/games/fortunes/disclaimer',
  # '/usr/share/games/fortunes/drugs',
  '/usr/share/games/fortunes/education',
  # '/usr/share/games/fortunes/ethnic',
  '/usr/share/games/fortunes/food',
  '/usr/share/games/fortunes/fortunes',
  '/usr/share/games/fortunes/goedel',
  '/usr/share/games/fortunes/humorists',
  '/usr/share/games/fortunes/kids',
  # '/usr/share/games/fortunes/knghtbrd',
  '/usr/share/games/fortunes/law',
  '/usr/share/games/fortunes/linuxcookie',
  '/usr/share/games/fortunes/linux',
  '/usr/share/games/fortunes/literature',
  '/usr/share/games/fortunes/love',
  '/usr/share/games/fortunes/magic',
  '/usr/share/games/fortunes/medicine',
  # '/usr/share/games/fortunes/men-women',
  '/usr/share/games/fortunes/miscellaneous',
  '/usr/share/games/fortunes/news',
  '/usr/share/games/fortunes/paradoxum',
  '/usr/share/games/fortunes/people',
  '/usr/share/games/fortunes/perl',
  '/usr/share/games/fortunes/pets',
  '/usr/share/games/fortunes/platitudes',
  # '/usr/share/games/fortunes/politics',
  '/usr/share/games/fortunes/pratchett',
  '/usr/share/games/fortunes/riddles',
  '/usr/share/games/fortunes/science',
  '/usr/share/games/fortunes/songs-poems',
  '/usr/share/games/fortunes/sports',
  '/usr/share/games/fortunes/startrek',
  # '/usr/share/games/fortunes/translate-me',
  '/usr/share/games/fortunes/tao',
  '/usr/share/games/fortunes/wisdom',
  '/usr/share/games/fortunes/work',
  '/usr/share/games/fortunes/zippy',
]

always_odds = [item.lower() for item in ['Bagels','devious']]


# TODO consider shipping with own fortune files in the future

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "-c", "--config",
    help="config file containing site parameters",
    type=str, default=".bmrc"
  )
  parser.add_argument(
    "-s", "--site",
    help="buttonmen site to access",
    type=str, default="bmai"
  )
  parser.add_argument(
    "-f", "--filter",
    help="filter out games",
    type=str, default="all", choices=["all", "odd", "even"]
  )
  parser.add_argument(
    "-r", "--random",
    help="randomize game list", default=False, action='store_true',
    dest='random'
  )
  parser.add_argument(
    "-g", "--gameid",
    help="run on 1 specific game",
    type=int
  )
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

  def start_monitor(self):
    self.monitor.start(handle_active=self.monitor_handler,
                       handle_new=self.new_challenge,
                       await_confirm=False,
                       shuffle=self.doshuffle,
                       filter=self.filter)

  def new_challenge(self, game):
    # TODO: some dice exist where we could "accept" the game and not "use" the dice
    # like AUX dice. they would need to be hidden from BMAI
    gameid = game['gameId']
    if len(self.buttons) == 0:
      self.buttons = self.client.wrap_load_button_names()
    myskills = self.buttons[game['myButtonName']]['dieTypes'] + \
               self.buttons[game['myButtonName']]['dieSkills']
    theirskills = self.buttons[game['opponentButtonName']]['dieTypes'] + \
                  self.buttons[game['opponentButtonName']]['dieSkills']
    supportset = set(myskills + theirskills)
    disallowedset = supportset - set_of_supported_skills
    if len(disallowedset) > 0:
      print(f"I don't think we support the following: {disallowedset}")
      action = "reject"
    else:
      action = "accept"

    retval = self.client.react_to_new_game(gameid, action)
    print(retval.message)
    return retval.status == "ok"

  def monitor_handler(self, game):
    gameid = game['gameId']
    if gameid in self.bad_games:
      return
    game = self.game_data.fetch(gameid)

    # may have come in recursivly and we need to break away if its not actually our turn
    if not game['player']['waitingOnAction']:
      print('not my turn')
      return

    bmai_input = game_data.bmai.dump(game)
    self.exec_bmai(bmai_input, game=game, state=game['gameState'])

    # lets immediately try to go again
    # to quickly address the situations where we won initiative
    # or the other player was forced to pass
    self.monitor_handler(game)

  def exec_bmai(self, input, game, state):
    bmai = Popen(['./bmai'], stdin=PIPE, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True)
    bmai.stdin.write(input)
    bmai.stdin.flush()
    copyright = bmai.stdout.readline() + bmai.stdout.readline()
    acted = False
    printed = False
    winOdds = None
    stats = None
    for line in bmai.stdout:
      if " p0 best move " in line and "%" in line:
        winOdds = line.split("%")[0].split()[-1]
      if line.startswith('stats '):
        stats = line
      if "err" in line or "fail" in line:
        print(line, end='')
        printed = True
      if 'action' in line:
        if state == 'SPECIFY_DICE':
          # TODO swing/opt better
          swings = len(game['player']['swingRequestArray'])
          opts = len(game['player']['optRequestArray'])
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
        elif state == 'CHOOSE_RESERVE_DICE':
          l = bmai.stdout.readline().strip()
          acted = self.submit_reserve(game, l)
          continue
        elif state == 'START_TURN':
          turbos = len(game['player']['turboSizeArray'])
          turbo_select = []
          atk_type = bmai.stdout.readline().strip()
          source_dice = bmai.stdout.readline().strip()
          target_dice = bmai.stdout.readline().strip()
          for t in range(turbos):
            l = bmai.stdout.readline().strip()
            if len(l) > 0:
              turbo_select.append(l)
          isok = self.submit_attack(game, atk_type, source_dice, target_dice,
                                    turbo_select=turbo_select,
                                    copyright=copyright, winOdds=winOdds,
                                    stats=stats)
          if isok:
            acted = True
          continue
        elif state == 'REACT_TO_INITIATIVE':
          action = bmai.stdout.readline().strip()
          acted = self.react_initiative(game, action)
          continue
    if printed:
      print('')
    if not acted:
      self.bad_games.append(game['gameId'])
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

    retval = self.client.submit_die_values(game['gameId'],
                                           swingArray=swing_array,
                                           optionArray=opt_array,
                                           roundNumber=game['roundNumber'],
                                           timestamp=game['timestamp'])
    print(retval.message)
    return retval.status == 'ok'

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
    retval = self.client.react_to_initiative(game['gameId'], action, idx, val,
                                             roundNumber=game['roundNumber'],
                                             timestamp=game['timestamp'])
    print(retval.message)
    if "did not turn your focus dice down far enough" in retval.message:
      # BMAI sometimes does this sometimes and will get stuck
      # currently i dont have a loop to retrigger BMAI
      # and if i did i dont have a way of telling BMAI to produce something
      # different with the same inputs
      # for now, decline
      retval = self.client.react_to_initiative(game['gameId'], "decline", [],
                                               [],
                                               roundNumber=game['roundNumber'],
                                               timestamp=game['timestamp'])
      print(retval.message)
    return retval.status == 'ok'

  def submit_reserve(self, game, reserve_cmd):
    dieIdx = reserve_cmd.split()[1]
    if dieIdx == '-1':
      retval = self.client.choose_reserve_dice(game['gameId'], 'decline')
    else:
      retval = self.client.choose_reserve_dice(game['gameId'], 'add', dieIdx)

    print(retval.message)
    return retval.status == 'ok'

  def submit_attack(self, game, type, source, target, turbo_select,
    copyright=None, winOdds=None, stats=None):
    my_idx = game['activePlayerIdx']
    their_idx = 0 if my_idx == 1 else 1
    dieSelects = self._generate_attack_array(game, my_idx, their_idx,
                                             source.split(" "),
                                             target.split(" "))
    turbo_array = dict()
    for turbo in turbo_select:
      parts = turbo.split(" ")
      turbo_array[parts[1]] = parts[2]
    retval = self.client.submit_turn(game['gameId'], my_idx, their_idx,
                                     dieSelectStatus=dieSelects,
                                     attackType=type.capitalize(),
                                     timestamp=game['timestamp'],
                                     roundNumber=game['roundNumber'],
                                     turboVals=turbo_array,
                                     chat=self.determineChat(game, copyright,
                                                             winOdds, stats))
    print(retval.message)
    return retval.status == 'ok'

  def _generate_attack_array(self, game, my_idx, their_idx, attackers,
    defenders):
    attack = {}
    for i in range(len(game['playerDataArray'][my_idx]['activeDieArray'])):
      attack[f'playerIdx_{my_idx:d}_dieIdx_{i:d}'] = True if str(
        i) in attackers else False
    for i in range(len(game['playerDataArray'][their_idx]['activeDieArray'])):
      attack[f'playerIdx_{their_idx:d}_dieIdx_{i:d}'] = True if str(
        i) in defenders else False
    return attack

  def determineChat(self, game, copyright, winOdds=None, stats=None):

    sortedchat = sorted(game['gameChatLog'], key=lambda x: x['timestamp'])

    ihavetalked = False
    opponentNeedsReply = False

    lasttheirchattime = 0
    lasttheirmessage = ''
    lastmychattime = 0
    lastmymessage = ''

    for c in sortedchat:
      if c['player'] == self.client.username:
        lastmychattime = max(lastmychattime, c['timestamp'])
        lastmymessage = c['message']
      else:
        lasttheirchattime = max(lasttheirchattime, c['timestamp'])
        lasttheirmessage = c['message']

    if lastmychattime > 0:
      ihavetalked = True
    if lasttheirchattime > lastmychattime:
      opponentNeedsReply = True

    retval = None
    if not ihavetalked:
      retval = copyright + '\nCOMMANDS: odds, stats'
    elif opponentNeedsReply:
      if lasttheirmessage.lower().startswith('bad bot'):
        retval = 'sorry :-('
      elif lasttheirmessage.lower().startswith('good bot'):
        retval = 'thanks (*^.^*)'
      elif stats is not None and 'stats' in lasttheirmessage.lower():
        retval = stats
      elif winOdds is not None and (
        'win?' in lasttheirmessage.lower() or 'odds' in lasttheirmessage.lower() or
        game['opponent']['playerName'].lower() in always_odds):
        retval = f'{winOdds}% chance to win (before the re-roll)'
      else:
        retval = fortune.get_random_fortune(random.choice(list_of_fortunes))
    elif game['opponent']['playerName'].lower() in always_odds:
      retval = f'{winOdds}% chance to win'

    if not retval:
      return ''
    else:
      print(retval)
      return f'[code]{retval}[/code]'


if __name__ == '__main__':
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  bmaibagels = BMAIBagels(bmclient, filter=args.filter, shuffle=args.random)
  if args.gameid:
    bmaibagels.monitor_handler({'gameId': args.gameid})
  else:
    bmaibagels.start_monitor()
