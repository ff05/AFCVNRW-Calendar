#!/usr/bin/python3
import requests, bs4, datetime, pytz
from icalendar import Calendar, Event
from requests.structures import CaseInsensitiveDict

tz = pytz.timezone('Europe/Berlin')

def createCalendar(plan,name):
    
    cal=Calendar()
    cal.add('prodid', '-//%s Calendar//' % name)
    cal.add('version', '2.0')
    for gameday in plan:
        game= Event()
        kickoff=datetime.datetime.strptime("%s-+0200" % gameday['kickoff'],"%m/%d/%Y, %H:%M:%S-%z")
        game.add('summary', '%s vs %s' %(gameday['hometeam'], gameday['guestteam']))
        game.add('dtstart', kickoff)
        game.add('dtend', kickoff + datetime.timedelta(hours=3))
        cal.add_component(game)
    return cal

def main():
    team='Gelsenkirchen Devils'
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
    #data = "league=493"
    data = "league=530"
    page = requests.post(url, headers=headers, data=data)
    soup=bs4.BeautifulSoup(page.content, 'lxml')
    ligaplanhtm=soup.findAll("div",{"class":"game_result spielplan"})
    ligaplan=[]
    teamplan=[]
    for gamehtm in ligaplanhtm:
        game={}
        kickoff=datetime.datetime.strptime((gamehtm.find("div",{"class":"kickoff"}).text),'%d.%m.%y um %H:%M Uhr')
        game['kickoff']=kickoff.strftime("%m/%d/%Y, %H:%M:%S")
        game['hometeam']=(gamehtm.find("div",{"class":"team1"}).text)
        game['guestteam']=(gamehtm.find("div",{"class":"team2"}).text)
        ligaplan.append(game)
        if game['hometeam'] == team or game['guestteam'] == team:
            teamplan.append(game)


    teamcal=createCalendar(teamplan,team)
    leaguecal=createCalendar(ligaplan, "league")

    team +=".ics"
    f = open(team, 'wb')
    f.write(teamcal.to_ical())
    f.close()
    f = open("liga.ics", 'wb')
    f.write(leaguecal.to_ical())
    f.close()

if __name__ == "__main__":
    main()