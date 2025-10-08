import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.fcf.cat/calendari/2526/futbol-sala/lliga-tercera-divisio-catalana-futbol-sala/bcn-gr11"

def scrape_calendar(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    data = []
    for table in soup.find_all("table", class_="calendaritable"):
        header = table.find("thead").find("tr")
        jornada = header.find_all("th")[0].get_text(strip=True)
        date = header.find_all("th")[-1].get_text(strip=True)

        matches = []
        for row in table.find("tbody").find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 7:
                continue

            home_team = cols[0].get_text(strip=True)
            home_logo = cols[1].find("img")["src"]
            home_score = cols[2].get_text(strip=True) or None

            report_link_tag = cols[3].find("a")
            match_report = report_link_tag["href"] if report_link_tag else None

            away_score = cols[4].get_text(strip=True) or None
            away_logo = cols[5].find("img")["src"]
            away_team = cols[6].get_text(strip=True)

            matches.append({
                "home_team": home_team,
                "home_logo": home_logo,
                "home_score": home_score,
                "away_team": away_team,
                "away_logo": away_logo,
                "away_score": away_score,
                "match_report": match_report
            })

        data.append({
            "jornada": jornada,
            "date": date,
            "matches": matches
        })

    return data

if __name__ == "__main__":
    print("Scraping FCF futsal calendar...")
    results = scrape_calendar(URL)
    with open("futsal_calendar.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print("✅ Data saved to futsal_calendar.json")
