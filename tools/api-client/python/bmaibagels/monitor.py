#!/usr/bin/env python3
# MONITOR
# Example script which provides "monitor" functionality, polling
# periodically for games which are waiting for you to act

import argparse
import random
import sys
import time
from builtins import input
from datetime import datetime

import sys

sys.path.append("../lib")

import bmutils


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
      "-s", "--site", help="buttonmen site to access", type=str, default="www")
  return parser.parse_args()


class Monitor(object):

  def __init__(self, client):
    self.client = client
    self.sleep_sec = 120
    if not self.client.verify_login():
      print("Could not login")
      sys.exit(1)

  def start(
      self,
      handle_new=lambda g: None,
      handle_active=lambda g: None,
      await_confirm=True,
      sort="ASC",
      filter="all",
      max=-1,
  ):

    sort = sort.upper()
    sort = "SHUFFLE" if sort == "RANDOM" else sort

    while True:

      newgames = self.client.wrap_load_new_games()

      if sort == "SHUFFLE":
        random.shuffle(newgames)
      elif sort == "DESC":
        newgames.reverse()

      for ng in newgames:
        if ((filter == "all") or (filter == "odd" and ng["gameId"] % 2 != 0) or
            (filter == "even" and ng["gameId"] % 2 == 0)):
          if ng["isAwaitingAction"]:
            print(f"{ng['gameId']}: "
                  f"{self.client.username} ({ng['myButtonName']})"
                  " vs. "
                  f"{ng['opponentName']} ({ng['opponentButtonName']})")
            handle_new(ng)

      games = self.client.wrap_load_active_games()

      if sort == "SHUFFLE":
        random.shuffle(games)
      elif sort == "DESC":
        games.reverse()

      count=0
      games_active = False
      for game in games:
        if max > 0 and count >= max:
          print(f"count {count} reached max {max}")
          break
        if ((filter == "all") or
            (filter == "odd" and game["gameId"] % 2 != 0) or
            (filter == "even" and game["gameId"] % 2 == 0)):
          if game["isAwaitingAction"]:
            print(f"{game['gameId']}: "
                  f"{self.client.username} ({game['myButtonName']})"
                  " vs. "
                  f"{game['opponentName']} ({game['opponentButtonName']})")
            games_active = True
            if handle_active(game):
              count=count+1

      if games_active and await_confirm:
        input()
      else:
        if max<=0:
          print(
              f"Zzz for {self.sleep_sec} @ {datetime.isoformat(datetime.now())}")
          time.sleep(self.sleep_sec)


if __name__ == "__main__":
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  mon = Monitor(bmclient)
  mon.start()
