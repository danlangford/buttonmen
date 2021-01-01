#!/usr/bin/env python3

from lib import bmutils

import challonge

bm = bmutils.BMClientParser('.bmrc', 'bot')

# http://api.challonge.com/v1
challonge.set_credentials("8bagels", "DzjXkY5sUXZQmv7eLfwD7BcFGXgfJg1EXbEZxOuo")

tournament = challonge.tournaments.show("thallium-event3",
                                        include_participants=1,
                                        include_matches=1)
tid = tournament["id"]
print(
  f"tournament {tournament['name']}({tid}) started {tournament['started_at']}")


def update_scores():

  keep_going = True
  size = 1000
  page = 1

  while keep_going:
    print(f"fetching page {page} of size {size}")
    search = bm.wrap_search_game_history(
      sortColumn="lastMove",
      searchDirection="ASC",
      numberOfResults=size,
      page=page,
      playerNameA='buttonbot',
      playerNameB='buttonbot2',
      status='COMPLETE',
    )

    for gameSummary in search['games']:
      if gameSummary['status'] == 'CANCELLED':
        continue

      game = bm.wrap_load_game_data(gameSummary['gameId'])
      if 'TLMadnessRR' not in game['description']:
        continue

      mid = game['description'].split(' ')[1]
      print(f'found mid {mid} on game {game["gameId"]}')
      scores = f"{gameSummary['roundsWonA']}-{gameSummary['roundsWonB']}"

      challonge.matches.update(tid, mid, scores_csv=scores)

      if gameSummary['status'] == 'COMPLETE':
        if gameSummary['roundsWonA'] == 3:
          aWon = True
        else:
          aWon = False
        match = challonge.matches.show(tid, mid, include_attachments=1)
        wid = match['player1_id'] if aWon else match['player2_id']
        challonge.matches.update(tid, mid, scores_csv=scores, winner_id=wid)
        challonge.matches.unmark_as_underway(tid, mid)
        print(f'persisted win on match {mid}')

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
    mid = match['id']
    p1 = players[match['player1_id']]['name'].split(']')[1]
    p2 = players[match['player2_id']]['name'].split(']')[1]
    # COMMENTED BELOW TO PREVENT ACCIDENTALLY CREATING MORE GAMES
    # game = bm.wrap_create_game(p1, p2, 'buttonbot','buttonbot2',f'TLMadnessRR {mid} https://thallium.challonge.com/event3')
    # gid = game['gameId']
    # print(f"{mid},{p1},{p2},{gid}")
    # challonge.attachments.create(tid,mid,url=f"http://buttonweavers.com/ui/game.html?game={gid}")
    # challonge.matches.mark_as_underway(tid,mid)


if __name__ == '__main__':
  update_scores()
