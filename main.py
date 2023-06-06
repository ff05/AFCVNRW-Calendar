#!/usr/bin/env python
import requests, bs4, datetime, pytz, overpy
from icalendar import Calendar, Event
from requests.structures import CaseInsensitiveDict
from urllib.parse import quote
import config

tz = pytz.timezone("Europe/Berlin")


def createCalendar(plan, name):
  cal = Calendar()
  cal.add("prodid", "-//%s Calendar//" % name)
  cal.add("version", "2.0")
  for gameday in plan:
    game = Event()
    kickoff = datetime.datetime.strptime(
      "%s-+0200" % gameday["kickoff"], "%m/%d/%Y, %H:%M:%S-%z"
    )
    location = f'{gameday["stadium"]}\nhttps://www.google.de/maps/place/{quote(gameday["stadium"])}'
    game.add("summary", "%s vs %s" % (gameday["hometeam"], gameday["guestteam"]))
    game.add("dtstart", kickoff)
    game.add("dtend", kickoff + datetime.timedelta(hours=3))
    game.add("location", location)
    game.add("description", gameday["description"])
    cal.add_component(game)
  return cal


def main(league_id, leaguename):
  url = "https://afcvnrw.de/wp-content/themes/afcv/ajax/games_spielplan.php"
  headers = CaseInsensitiveDict()
  headers["authority"] = "afcvnrw.de"
  headers["accept"] = "*/*"
  headers["accept-language"] = "en-US,en;q=0.9"
  headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
  headers["origin"] = "https://afcvnrw.de"
  headers["referer"] = "https://afcvnrw.de/ergebnisse/spielplan/"
  headers["sec-ch-ua"] = '" Not A;Brand";v="99", "Chromium";v="101"'
  headers["sec-ch-ua-mobile"] = "?0"
  headers["sec-ch-ua-platform"] = '"Linux"'
  headers["sec-fetch-dest"] = "empty"
  headers["sec-fetch-mode"] = "cors"
  headers["sec-fetch-site"] = "same-origin"
  headers["user-agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36"
  headers["x-requested-with"] = "XMLHttpRequest"
  # data = "league=493"
  data = "league=%s" % str(league_id)
  page = requests.post(url, headers=headers, data=data)
  soup = bs4.BeautifulSoup(page.content, "lxml")
  spielplan = soup.findAll("div", {"class": "game_result spielplan"})
  gameinfo = soup.findAll("div", {"class": "game_info spielplaninfo"})
  ligaplan = []
  teamplan = []
  i = 0
  while i < 29:
    try:
      game = {}
      kickoff = datetime.datetime.strptime(
        (spielplan[i].find("div", {"class": "kickoff"}).text),
        "%d.%m.%y um %H:%M Uhr",
      )
      game["kickoff"] = kickoff.strftime("%m/%d/%Y, %H:%M:%S")
      game["hometeam"] = spielplan[i].find("div", {"class": "team1"}).text
      game["guestteam"] = spielplan[i].find("div", {"class": "team2"}).text
      game["stadium"] = gameinfo[i].find("div", {"class": "game_stadium"}).text[7:]
      ergebnis = spielplan[i].find("div",{"class":"resultbox"}).text
      description = [f'Ergebnis: {ergebnis}']
      for team in config.SAUSAGE_BAD:
        if team in game["hometeam"]:
          description.append("schlechte Bratwurst")
      for team in config.SAUSAGE_GOOD:
        if team in game["hometeam"]:
          description.append("Gute Bratwurst")
      if "description" not in game:
        description.append("Keine Bratwurst Information")
      for k in config.TEAM_COMMENTS:
        if game["hometeam"] == k:
          description.append(config.TEAM_COMMENTS[k])
          break
      ligaplan.append(game)
      if game["hometeam"] in config.TEAMS or game["guestteam"] in config.TEAMS:
        teamplan.append(game)
      game["description"] = "\n".join(description)
      i+=1
    except IndexError:
      break
  
  if len(teamplan) > 1:
    if teamplan[0]["hometeam"] in config.TEAMS:
      teamname = teamplan[0]["hometeam"]
    else:
      teamname = teamplan[0]["guestteam"]
    teamname = teamname.replace('/','-').replace(' ','_').replace('Ä','Ae').replace('Ö','Oe').replace('Ü','Ue').replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
    teamcal = createCalendar(teamplan, teamname)
    teamcalfile = "%s.ics" % teamname
    f = open(teamcalfile, "wb")
    f.write(teamcal.to_ical())
    f.close()
  leaguecal = createCalendar(ligaplan, "league")
  f = open("%s.ics" % leaguename, "wb")
  f.write(leaguecal.to_ical())
  f.close()

if __name__ == "__main__":
  for league in config.LEAGUE_IDS:
    main(league["id"], league["name"])

