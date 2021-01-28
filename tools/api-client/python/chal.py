#!/usr/bin/env python3
from datetime import datetime, timezone

from lib import bmutils

import challonge

bm = bmutils.BMClientParser('.bmrc', 'bot')

# http://api.challonge.com/v1
challonge.set_credentials("8bagels", "DzjXkY5sUXZQmv7eLfwD7BcFGXgfJg1EXbEZxOuo")

tournament = challonge.tournaments.show("thallium-event3b",
                                        include_participants=1,
                                        include_matches=1)
tid = tournament["id"]
print(
  f"tournament {tournament['name']}({tid}) started {tournament['started_at']}")


def update_scores():

  keep_going = True
  size = 1000
  page = 1
  persisted=0

  while keep_going:
    print(f"fetching page {page} of size {size}")
    search = bm.wrap_search_game_history(
      sortColumn="lastMove",
      searchDirection="ASC",
      numberOfResults=size,
      page=page,
      playerNameA='buttonbot',
      playerNameB='buttonbot2',
      lastMoveMin=int(datetime(2021, 1, 19, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    )

    for gameSummary in search['games']:
      if gameSummary['status'] == 'CANCELLED':
        continue

      # 0-69914
      if int(gameSummary['gameId']) <= 69915:
        continue

      # 69949-69973
      if 69949 <= int(gameSummary['gameId']) <= 69973:
        continue

      # 0-70016
      if int(gameSummary['gameId']) <= 70016:
        continue

      game = bm.wrap_load_game_data(gameSummary['gameId'])
      if 'TLMadnessSE-B' not in game['description']:
        continue

      mid = game['description'].split(' ')[1]
      print(f'found mid {mid} on game {game["gameId"]}')
      scores = f"{gameSummary['roundsWonA']}-{gameSummary['roundsWonB']}"

      # ###
      # for x in ['buttonNameA','buttonNameB']:
      #   buttX = bm.wrap_load_button_data(gameSummary[x])
      #   if buttX['specialText']:
      #     print(f"button:{buttX['buttonName']} special:{buttX['specialText']}")
      # ###

      forceAWon=False
      forcedAWon=False
      forceComplete=False
      if gameSummary['buttonNameA'] in ['The Flying Squirrel','The Japanese Beetle']:
        forceComplete=True
        forceAWon=True
        forcedAWon=False
        scores = "0-3"
      if gameSummary['buttonNameB'] in ['The Flying Squirrel','The Japanese Beetle']:
        forceComplete=True
        scores = "3-0"
        forceAWon=True
        forcedAWon=True

      ###

      challonge.matches.update(tid, mid, scores_csv=scores)

      if gameSummary['status'] == 'COMPLETE' or forceComplete:
        if not forceAWon and gameSummary['roundsWonA'] == 3:
          aWon = True
        elif not forceAWon and gameSummary['roundsWonB'] == 3:
          aWon = False
        elif forceAWon:
          aWon=forcedAWon
        else:
          raise Exception("ahhhh i dont know what happened around aWon")
        match = challonge.matches.show(tid, mid, include_attachments=1)
        wid = match['player1_id'] if aWon else match['player2_id']
        challonge.matches.update(tid, mid, scores_csv=scores, winner_id=wid)
        challonge.matches.unmark_as_underway(tid, mid)
        print(f'persisted win on match {mid}')
        persisted +=1
        print(persisted)

    if len(search['games']) == 0:
      keep_going = False
    page += 1


def create_games():
  # Retrieve the participants for a given tournament.
  players = {}
  participants = challonge.participants.index(tid)

  for participant in participants:
    players[participant['id']] = participant
    for gpi in participant['group_player_ids']:
      players[gpi] = participant

  allMatches = challonge.matches.index(tid)
  for match in allMatches:
    if match['state'] == 'open' and match['player1_id'] and match['player2_id']:
      mid = match['id']
      p1 = players[match['player1_id']]['name'].split(']')[1]
      p2 = players[match['player2_id']]['name'].split(']')[1]
      print(f"{p1} vs {p2}")
      # COMMENTED BELOW TO PREVENT ACCIDENTALLY CREATING MORE GAMES
      game = bm.wrap_create_game(p1, p2, 'buttonbot','buttonbot2',f'TLMadnessSE-B {mid} https://thallium.challonge.com/event3b')
      gid = game['gameId']
      print(f"{mid},{p1},{p2},{gid}")
      challonge.attachments.create(tid,mid,url=f"http://buttonweavers.com/ui/game.html?game={gid}")
      challonge.matches.mark_as_underway(tid,mid)
      continue


if __name__ == '__main__':
  # create_games()
  update_scores()
  pass
