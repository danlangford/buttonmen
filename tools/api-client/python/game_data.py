#!/usr/bin/env python3

# GAME DATA
#
# Print out data about a game.

import argparse
import json
import sys
import yaml
from lib import bmutils


def parse_args():
  parser = argparse.ArgumentParser(description="Print out data about a game.")

  parser.add_argument('gameid', help="game number")

  parser.add_argument('--format', '-f',
                      choices=['json', 'yaml', 'bmai'], default='yaml',
                      help="output data format (default: yaml)")

  # Add general optional arguments.

  parser.add_argument('--site', '-s',
                      default='www',
                      help="site to check ('www' by default)")

  parser.add_argument('--config', '-c',
                      default='.bmrc',
                      help="config file containing site parameters")

  # Return the parser.

  return parser.parse_args()


class NoAliasDumper(yaml.SafeDumper):
  def ignore_aliases(self, _data):
    return True


class bmai(object):
  def recipe(d, vals=True):
    r = d['recipe']
    if ',' not in r:
      r = r.replace('(', '').replace(')', '')
    if vals:
      if '/' in r or 'Swing' in d['description']:
        r += '-' + str(d['sides'])
      r += f":{d['value']}"
    return r

  def dump(game):
    retval = f"game {game['maxWins']}\n"
    dieVals = False
    if game['gameState'] == "START_TURN":
      retval += "fight\n"
      dieVals = True
    elif game['gameState'] == "SPECIFY_DICE":
      retval += "preround\n"
    elif game['gameState'] == 'CHOOSE_RESERVE_DICE':
      retval += "reserve\n"
    # elif game['gameState'] == 'CHOOSE_AUXILIARY_DICE':
    #   retval += "auxpox?\n"
    else:
      retval += f"unhandled_{game['gameState']}\n"
    if game['player']['waitingOnAction']:
      player0, player1 = game['player'], game['opponent']
    else:
      player0, player1 = (game['opponent'], game['player'])
    retval += f"player 0 {len(player0['activeDieArray'])} {game['player']['gameScoreArray']['W']}\n"
    for d in player0['activeDieArray']:
      retval += f"{bmai.recipe(d, dieVals)}\n"
    retval += f"player 1 {len(player1['activeDieArray'])} {game['opponent']['gameScoreArray']['W']}\n"
    for d in player1['activeDieArray']:
      retval += f"{bmai.recipe(d, dieVals)}\n"
    retval += "ply 3\nmax_sims 100\nmin_sims 5\nmaxbranch 400\n"
    retval += "getaction\n"
    retval += "quit\n"
    return retval


class GameData(object):
  def __init__(self, client, format=None):
    self.client = client
    self.format = format
    if not self.client.verify_login():
      print("ERROR: Could not log in")
      sys.exit(1)

  def fetch(self, gameid, format_override=None):
    game = self.client.wrap_load_game_data(gameid)
    fmt = format_override or self.format
    if fmt == 'json':
      return json.dumps(game, indent=1, sort_keys=True)
    elif fmt == 'yaml':
      return yaml.dump(game, Dumper=NoAliasDumper)
    elif fmt == 'bmai':
      return bmai.dump(game)
    elif fmt is None:
      return game
    else:
      raise Exception(f"format {fmt} not supported")


if __name__ == "__main__":
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  game_data = GameData(bmclient, format=args.format)
  print(game_data.fetch(args.gameid))
