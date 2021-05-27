#!/usr/bin/env python3

import os
import json
from lib.bmutils import BMClientParser

# CONFIG
bmrc = ".bmrc"
site = "www"
button_set_mapping = {}


def login():
  bm_client = BMClientParser(os.path.expanduser(bmrc), site)
  if not bm_client.verify_login():
    print("Could not login")
    raise Exception("Could not login")
  return bm_client


def read_json(filename):
  with open(filename, mode='r') as file:
    return json.load(file)


def translate_buttons_into_sets(buttons_data, client: BMClientParser):
  set_data = []
  for d in buttons_data:
    set_data.append({
      's1': find_set(d['b1'], client),
      's2': find_set(d['b2'], client),
      'ng': d['ng'], 'b1': d['b1'], 'b2': d['b2']})
  return set_data


def find_set(buttonName: str, client: BMClientParser):
  global button_set_mapping
  if buttonName in button_set_mapping.keys():
    return button_set_mapping.get(buttonName)
  else:
    try:
      set = client.wrap_load_button_data(buttonName)['buttonSet']
      button_set_mapping[buttonName] = set
    except ValueError as ve:
      print(f"err:{ve} button:{buttonName}")
      button_set_mapping[buttonName] = str(ve)
    return button_set_mapping[buttonName]


def write_json(data, file_name):
  with open(file_name, mode="w") as outfile:
    json.dump(data, outfile)


def condense(data):
  stats = {}
  for d in data:
    if "Promo" in d['s1'] or "Promo" in d['s2']:
      continue
    elif "con " in d['s1'].lower() or "con " in d['s2'].lower():
      continue
    elif d['s1'].lower().endswith("con") or d['s2'].lower().endswith("con"):
      continue
    elif "random" in d['s1'].lower() or "random" in d['s2'].lower():
      continue
    elif "loadButtonData" in d['s1'] or "loadButtonData" in d['s2']:
      continue
    elif d['s1'] != d['s2']:
      key = f"{d['s1']}-{d['s2']}"
      existing = stats.get(key, {'ng': 0, 'b1': [], 'b2': []})
      newb1 = set(list(existing['b1'])+[d['b1']])
      newb2 = set(list(existing['b2'])+[d['b2']])
      stats[key] = {'s1': d['s1'], 's2': d['s2'],
                    'ng': existing['ng'] + d['ng'],
                    'c1': len(newb1), 'c2': len(newb2),
                    'b1': newb1, 'b2': newb2
                    }

  return stats


if __name__ == "__main__":
  # init some global state
  #bm = login()
  #button_data = read_json('win_percentage_stats.json')
  #button_set_mapping = read_json('button_set.json')

  #set_data = translate_buttons_into_sets(button_data, bm)
  #write_json(button_set_mapping, "button_set.json")
  #write_json(set_data, "set_data.json")

  set_data = read_json('set_data.json')
  set_stats = condense(set_data)

  for ss in dict(sorted(set_stats.items())):
    if True or set_stats[ss]['ng'] == 0 and set_stats[ss]['c1'] >= 5 and set_stats[ss]['c2'] >= 5:
      x=set_stats[ss]
      print(f"{x['s1']}({x['c1']}) vs {x['s2']}({x['c2']}) #{x['ng']} ")

  print('done')
