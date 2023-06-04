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
    location = '%s, https://www.google.de/maps/place/%s' % (gameday["stadium"], quote(gameday["stadium"]))
    game.add("summary", "%s vs %s" % (gameday["hometeam"], gameday["guestteam"]))
    game.add("dtstart", kickoff)
    game.add("dtend", kickoff + datetime.timedelta(hours=3))
    game.add("location", location)
    game.add("description", gameday["description"])

    cal.add_component(game)
  return cal


def main(id, leaguename):
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
  headers[
    "user-agent"
  ] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36"
  headers["x-requested-with"] = "XMLHttpRequest"
  # data = "league=493"
  data = "league=%s" % str(id)
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
      for team in config.SAUSAGE_BAD:
        if team in game["hometeam"]:
          game["description"] = "schlechte Bratwurst"
      for team in config.SAUSAGE_GOOD:
        if team in game["hometeam"]:
          game["description"] = "Gute Bratwurst"
      if "description" not in game:
        game["description"] = "Keine Bratwurst Information"
      ligaplan.append(game)
      if game["hometeam"] == config.TEAM or game["guestteam"] == config.TEAM:
        teamplan.append(game)
      i+=1
    except IndexError:
      break

  teamcal = createCalendar(teamplan, config.TEAM)
  leaguecal = createCalendar(ligaplan, "league")

  teamcalfile = "%s.ics" % config.TEAM
  f = open(teamcalfile, "wb")
  f.write(teamcal.to_ical())
  f.close()
  f = open("%s.ics" % leaguename, "wb")
  f.write(leaguecal.to_ical())
  f.close()

if __name__ == "__main__":
  for league in config.LEAGUE_IDS:
    main(league["id"], league["name"])

