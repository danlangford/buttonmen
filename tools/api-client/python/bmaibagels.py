#!/usr/bin/env python3
import argparse
from subprocess import Popen, PIPE, STDOUT, run
import fortune
import monitor
import game_data
import random
from lib import bmutils

set_of_supported_skills = {'Twin', 'Swing', 'Poison', 'Speed', 'Shadow',
                           'Stealth', 'Queer', 'Trip', 'Mood', 'Null', 'Option',
                           'Berserk', 'TimeAndSpace', 'Mighty', 'Weak',
                           'Reserve', 'Ornery', 'Chance', 'Morphing', 'Focus',
                           'Warrior', 'Slow', 'Unique', 'Stinger'}

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
]


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
    type=str, default="bot"
  )
  return parser.parse_args()


class BMAIBagels(object):
  def __init__(self, client: bmutils.BMClientParser):
    self.client = client
    self.monitor = monitor.Monitor(self.client)
    self.game_data = game_data.GameData(self.client)
    self.bad_games = []
    self.buttons = []

  def start_monitor(self):
    self.monitor.start(handle_active=self.monitor_handler,
                       handle_new=self.new_challenge, await_confirm=False)

  def new_challenge(self, game):
    print(game['gameId'])
    if len(self.buttons) == 0:
      self.buttons = self.client.wrap_load_button_names()
    myskills = self.buttons[game['myButtonName']]['dieTypes'] + \
               self.buttons[game['myButtonName']]['dieSkills']
    theirskills = self.buttons[game['opponentButtonName']]['dieTypes'] + \
                  self.buttons[game['opponentButtonName']]['dieSkills']
    supportset = set(myskills + theirskills)
    for s in supportset:
      s.lower()
    disallowedset = supportset - set_of_supported_skills
    print(disallowedset)
    # myskills = self.client.

  def monitor_handler(self, game):
    gameid = game['gameId']
    if gameid in self.bad_games:
      return
    game = self.game_data.fetch(gameid)

    # may have come in recursivly and we need to break away if its not actually our turn
    if not game['player']['waitingOnAction']:
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
    for line in bmai.stdout:
      if "err" in line or "fail" in line or "grend" in game['player']['button'][
        'name']:  # or "Jedite" in game['player']['button']['name']:
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
          self.submit_swings(game, swing_select, opt_select)
          acted = True
          continue
        elif state == 'CHOOSE_RESERVE_DICE':
          l = bmai.stdout.readline().strip()
          self.submit_reserve(game, l)
          acted = True
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
                                    copyright=copyright)
          if isok:
            acted = True
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

  def submit_reserve(self, game, reserve_cmd):
    # currently i do not support the "decline" action which can omit the dieIdx?
    retval = self.client.choose_reserve_dice(game['gameId'], 'add',
                                             reserve_cmd.split()[1])
    print(retval.message)
    return retval.status == 'ok'

  def submit_attack(self, game, type, source, target, turbo_select,
    copyright=None):
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
                                     chat=self.determineChat(game, copyright))
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

  def determineChat(self, game, copyright):

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
      retval = copyright
    elif opponentNeedsReply:
      if lasttheirmessage.lower().startswith('bad bot'):
        retval = 'sorry :-('
      elif lasttheirmessage.lower().startswith('good bot'):
        retval = 'thanks (*^.^*)'
      else:
        retval = fortune.get_random_fortune(random.choice(list_of_fortunes))

    if not retval:
      return ''
    else:
      return f'[code]{retval}[/code]'


if __name__ == '__main__':
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  bmaibagels = BMAIBagels(bmclient)
  bmaibagels.start_monitor()
