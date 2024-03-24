#!/usr/bin/env python
from pytz import timezone
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from requests import post
from icalendar import Calendar, Event
from requests.structures import CaseInsensitiveDict
from urllib.parse import quote
from os import makedirs, path, listdir
from pprint import pprint
import config
import re

tz = timezone("Europe/Berlin")


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
  for team in config.TEAM_COMMENTS:
    if not 'Stadion' in config.TEAM_COMMENTS[team]:
      continue
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
    for k,v in config.TEAM_COMMENTS['DEFAULT'].items():
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

def get_alltime_calendar(teamname):
  namelist=[teamname]
  ypattern = re.compile(".+U\d\d.*")
  if not ypattern.match(teamname):
    mpattern=re.compile("(.+ .+){2,}")
    if mpattern.match(teamname):
      namelist.append(teamname.split(" ")[1:])
    else:
      namelist.append(teamname.split(" ")[-1])      
  league_id = 2
  while league_id < 600:
    print(f"procesing league_id: {league_id}")
    soup=get_league_data(league_id)
    inleague=False
    for name in namelist:
      if name in str(soup):
        inleague=True
        break
    if not inleague:
      league_id += 1
      continue
    spielplan = soup.findAll("div", {"class": "game_result spielplan"})
    spielplaninfo = soup.findAll("div", {"class": "game_info spielplaninfo"})
    ligaplan = []
    teamplan = []
    for spiel in spielplan:
      info=spielplaninfo[spielplan.index(spiel)]
      game = get_game(spiel,info)
      ligaplan.append(game)
      if game['hometeam'] in namelist or game['guestteam'] in namelist:
        teamplan.append(game)
    teamfilename = f"{teamname.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}.ics"
    if len(teamplan) > 1:
      teamcal, year = createCalendar(teamplan, teamname)
      if not path.exists(f"calendars/{year}"):
        makedirs(f"calendars/{year}")
      print(f'saving calendar {teamfilename}')
      f = open(f"calendars/{year}/{teamfilename}", "wb")
      f.write(teamcal.to_ical())
      f.close()
    league_id += 1
  merge_teamcals(teamfilename)


def main(league_id, leaguename):
  soup=get_league_data(league_id)
  spielplan = soup.findAll("div", {"class": "game_result spielplan"})
  spielplaninfo = soup.findAll("div", {"class": "game_info spielplaninfo"})
  ligaplan = []
  teamplan = []
  stadiumdict = CaseInsensitiveDict()
  for spiel in spielplan:
    info=spielplaninfo[spielplan.index(spiel)]
    game = get_game(spiel,info)
    ligaplan.append(game)
    if game['hometeam'] in config.TEAMS or game['guestteam'] in config.TEAMS:
      teamplan.append(game)
    if game['hometeam'] not in stadiumdict:
      stadiumdict[game['hometeam']] = []
    if game['stadium'] not in stadiumdict[game['hometeam']]:
      stadiumdict[game['hometeam']].append(game['stadium'])
  if len(teamplan) > 1:
    if teamplan[0]['hometeam'] in config.TEAMS:
      teamname = teamplan[0]['hometeam']
    else:
      teamname = teamplan[0]['guestteam']
    teamfilename = f"{teamname.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')}.ics"
    teamcal, year = createCalendar(teamplan, teamname)
    if not path.exists(f"calendars/{year}"):
      makedirs(f"calendars/{year}")
    print(f'saving calendar {teamfilename}')
    f = open(f"calendars/{year}/{teamfilename}", "wb")
    f.write(teamcal.to_ical())
    f.close()
  merge_teamcals(teamfilename)
  leaguecal, year = createCalendar(ligaplan, leaguename)
  pprint(stadiumdict)
  if not path.exists(f"calendars/{year}"):
    makedirs(f"calendars/{year}")
  print(f'saving calendar {leaguename}.ics')
  f = open(f"calendars/{year}/{leaguename}.ics", "wb")
  f.write(leaguecal.to_ical())
  f.close()

if __name__ == "__main__":
  for league in config.LEAGUE_IDS:
    print(f'processing leage: {league["name"]}')
    main(league['id'], league['name'])
  # for team in config.TEAMS:
  #   get_alltime_calendar(team)
