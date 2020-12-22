#!/usr/bin/env python3
# MONITOR
# Example script which provides "monitor" functionality, polling
# periodically for games which are waiting for you to act

import argparse
import sys
import time
from builtins import input
from datetime import datetime

from lib import bmutils


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
    type=str, default="www"
  )
  return parser.parse_args()


class Monitor(object):
  def __init__(self, client):
    self.client = client
    self.sleep_sec = 120
    if not self.client.verify_login():
      print("Could not login")
      sys.exit(1)

  def start(self, handle_new=lambda g: None, handle_active=lambda g: None,
    await_confirm=True):
    while True:

      newgames = self.client.wrap_load_new_games()
      for ng in newgames:
        if ng['isAwaitingAction']:
          print(f"{ng['gameId']}: "
                f"{self.client.username} ({ng['myButtonName']})"
                " vs. "
                f"{ng['opponentName']} ({ng['opponentButtonName']})")
          handle_new(ng)

      games = self.client.wrap_load_active_games()
      games_active = False
      for game in games:
        if game['isAwaitingAction']:
          print(f"{game['gameId']}: "
                f"{self.client.username} ({game['myButtonName']})"
                " vs. "
                f"{game['opponentName']} ({game['opponentButtonName']})")
          games_active = True
          handle_active(game)
      if games_active and await_confirm:
        input()
      else:
        print(
          f'Zzz for {self.sleep_sec} @ {datetime.isoformat(datetime.now())}')
        time.sleep(self.sleep_sec)


if __name__ == "__main__":
  args = parse_args()
  bmclient = bmutils.BMClientParser(args.config, args.site)
  mon = Monitor(bmclient)
  mon.start()
