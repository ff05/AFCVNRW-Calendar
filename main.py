#!/usr/bin/env python
from pytz import timezone
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from requests import post
from icalendar import Calendar, Event
from requests.structures import CaseInsensitiveDict
from urllib.parse import quote
from os import makedirs, path, listdir
from json import dumps as json_dumps
from copy import copy
import config
import re

tz = timezone("Europe/Berlin")
ypattern = re.compile("^.{0,}(Jugend|Flag|Youth|Rookies|Juniors|I{2,}|\d).*")

def createCalendar(plan, name):
  cal = Calendar()
  cal.add("prodid", f"-//{name} Calendar//")
  cal.add("version", "2.0")
  for gameday in plan:
    game = Event()
    kickoff = datetime.strptime(
      f"{gameday['kickoff']}-+0200", "%m/%d/%Y, %H:%M:%S-%z"
    )
    year = kickoff.year
    location = f"{gameday['stadium']}\nhttps://www.google.de/maps/place/{quote(gameday['stadium'])}"
    game.add("summary", f"{gameday['hometeam']} vs {gameday['guestteam']}")
    game.add("dtstart", kickoff)
    game.add("dtend", kickoff + timedelta(hours=3))
    game.add("location", location)
    game.add("description", gameday['description'])
    cal.add_component(game)
  return cal, year

def get_league_data(league_id):
  url = "https://afcvnrw.de/wp-content/themes/afcv/ajax/games_spielplan.php"
  headers = CaseInsensitiveDict()
  headers['authority'] = "afcvnrw.de"
  headers['accept'] = "*/*"
  headers['accept-language'] = "en-US,en;q=0.9"
  headers['content-type'] = "application/x-www-form-urlencoded; charset=UTF-8"
  headers['origin'] = "https://afcvnrw.de"
  headers['referer'] = "https://afcvnrw.de/ergebnisse/spielplan/"
  headers['sec-ch-ua'] = '" Not A;Brand";v="99", "Chromium";v="101"'
  headers['sec-ch-ua-mobile'] = "?0"
  headers['sec-ch-ua-platform'] = '"Linux"'
  headers['sec-fetch-dest'] = "empty"
  headers['sec-fetch-mode'] = "cors"
  headers['sec-fetch-site'] = "same-origin"
  headers['user-agent'] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36"
  headers['x-requested-with'] = "XMLHttpRequest"
  # data = "league=493"
  data = f"league={str(league_id)}"
  page = post(url, headers=headers, data=data)
  return BeautifulSoup(page.content, "lxml")

def get_game(spiel, info):
  game= {}
  game['kickoff'] = datetime.strptime((spiel.find("div", {"class": "kickoff"}).text),"%d.%m.%y um %H:%M Uhr",).strftime("%m/%d/%Y, %H:%M:%S")
  game['hometeam'] = spiel.find("div", {"class": "team1"}).text
  game['guestteam'] = spiel.find("div", {"class": "team2"}).text
  game['stadium'] = info.find("div", {"class": "game_stadium"}).text[7:]
  game['description'] = [f'Ergebnis: {spiel.find("div",{"class":"resultbox"}).text}']
  found_by_stadium=False
  found_by_teamname=False
  config.TEAM_COMMENTS['1DEFAULT']['Stadion'] = []
  for team in config.TEAM_COMMENTS:
    if game['stadium'] in config.TEAM_COMMENTS[team]['Stadion']:
      found_by_stadium=True
      for k,v in config.TEAM_COMMENTS[team].items():
        if k in ['Stadion']:
          continue
        game['description'].append(f'{k}: {v}')
  if not found_by_stadium:
    if game['hometeam'] in config.TEAM_COMMENTS:
      found_by_teamname=True
      for k,v in config.TEAM_COMMENTS[game['hometeam']].items():
        if k in ['Stadion']:
          continue
        game['description'].append(f'{k}: {v}')
    else:
      for team_comment in config.TEAM_COMMENTS.keys():
        if team_comment in game['hometeam']:
          found_by_teamname=True
          for k,v in config.TEAM_COMMENTS[team_comment].items():
            if k in ['Stadion']:
              continue
            game['description'].append(f'{k}: {v}')
          break
  if not found_by_stadium and not found_by_teamname:
    for k,v in config.TEAM_COMMENTS['1DEFAULT'].items():
      if k in ['Stadion']:
        continue
      game['description'].append(f'{k}: {v}')
  game['description'] = "\n".join(game['description'])
  return game

def merge_teamcals(filename):
  merged_cal = Calendar()
  calstring = ""
  for d in listdir('calendars'):
    if (path.isdir(path.join('calendars', d))) and \
      (path.exists(path.join('calendars', d , filename))):
      f = open(path.join('calendars', d , filename), "r")
      calstring = f.read()
      f.close()
      cal = Calendar()
      cal = cal.from_ical(calstring)
      for e in cal.walk('vevent'):
        merged_cal.add_component(e)
  f = open(f"calendars/{filename}", "wb")
  f.write(merged_cal.to_ical())
  f.close()

def merge_comments(game):
  if not ypattern.match(game['hometeam']):
    if game['hometeam'] not in configdict:
      for team in configdict:
        if game['stadium'] in configdict[team]['Stadion']:
          return
      configdict[game['hometeam']] = copy(config.TEAM_COMMENTS['1DEFAULT'])
    if game['stadium'] not in configdict[game['hometeam']]['Stadion']:
      configdict[game['hometeam']]['Stadion'].append(game['stadium'])

def get_alltime_calendars(teams):
  teamsdict = CaseInsensitiveDict()
  for team in teams:
    teamsdict[team] = CaseInsensitiveDict()
    teamsdict[team]['names'] = [team]
    if not ypattern.match(team):
      mpattern=re.compile("(.+ .+){2,}")
      if mpattern.match(team):
        teamsdict[team]['names'].append(team.split(" ")[1:])
      else:
        teamsdict[team]['names'].append(team.split(" ")[-1])      
  league_id = 2
  while league_id < 600:
    print(f"procesing league_id: {league_id}")
    soup=get_league_data(league_id)
    inleague=False
    for team in teamsdict:
      teamsdict[team]['found'] = False
      for name in team:
        if name in str(soup):
          teamsdict[team]['found'] = True
          teamsdict[team]['cal'] = []
          inleague = True
    if not inleague:
      league_id += 1
      continue
    namelist = []
    for team in teamsdict:
      if teamsdict[team]['found']:
        for name in teamsdict[team]['names']:
          namelist.append(name)
    spielplan = soup.findAll("div", {"class": "game_result spielplan"})
    spielplaninfo = soup.findAll("div", {"class": "game_info spielplaninfo"})
    for spiel in spielplan:
      info=spielplaninfo[spielplan.index(spiel)]
      config.TEAM_COMMENTS['1DEFAULT']['Stadion'] = []
      game = get_game(spiel,info)
      if game['hometeam'] in namelist or game['guestteam'] in namelist:
        for team in teamsdict:
          if game['hometeam'] in teamsdict[team]['names'] or game['guestteam'] in teamsdict[team]['names']:
            teamsdict[team]['cal'].append(game)
            merge_comments(game)
    for team in teamsdict:
      if not teamsdict[team]['found']:
        continue
      teamfilename = f"{team.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}.ics"
      if len(teamsdict[team]['cal']) > 1:
        teamcal, year = createCalendar(teamsdict[team]['cal'], team)
        if not path.exists(f"calendars/{year}"):
          makedirs(f"calendars/{year}")
        print(f'saving calendar {year} {teamfilename}')
        f = open(f"calendars/{year}/{teamfilename}", "wb")
        f.write(teamcal.to_ical())
        f.close()
    league_id += 1



def main(league_id, leaguename, team):
  soup=get_league_data(league_id)
  if not team in str(soup):
    return False
  spielplan = soup.findAll("div", {"class": "game_result spielplan"})
  spielplaninfo = soup.findAll("div", {"class": "game_info spielplaninfo"})
  ligaplan = []
  teamplan = []
  teamfilename = f"{team.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}.ics"
  for spiel in spielplan:
    info=spielplaninfo[spielplan.index(spiel)]
    config.TEAM_COMMENTS['1DEFAULT']['Stadion'] = []
    game = get_game(spiel,info)
    ligaplan.append(game)
    if game['hometeam'] == team or game['guestteam'] == team:
      teamplan.append(game)
    merge_comments(game)
  if len(teamplan) > 1:
    teamcal, year = createCalendar(teamplan, team)
    if not path.exists(f"calendars/{year}"):
      makedirs(f"calendars/{year}")
    print(f'saving calendar {teamfilename}')
    f = open(f"calendars/{year}/{teamfilename}", "wb")
    f.write(teamcal.to_ical())
    f.close()
  leaguecal, year = createCalendar(ligaplan, leaguename)
  if not path.exists(f"calendars/{year}"):
    makedirs(f"calendars/{year}")
  print(f'saving calendar {leaguename}.ics')
  f = open(f"calendars/{year}/{leaguename}.ics", "wb")
  f.write(leaguecal.to_ical())
  f.close()

if __name__ == "__main__":
  configdict= copy(config.TEAM_COMMENTS)
  for team in config.TEAMS:
    for league in config.LEAGUE_IDS:
      print(f'processing leage: {league["name"]}')
      main(league['id'], league['name'], team)
    teamfilename = f"{team.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}.ics"
    merge_teamcals(teamfilename)
  get_alltime_calendars(config.TEAMS)
  with open("new_comments", "w", encoding='utf8') as new_comments:
    new_comments.write(json_dumps(configdict, indent=4, ensure_ascii=False, sort_keys=True))
