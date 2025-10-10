from scrap.scraper import scrap_results
from db.update import update_data

def update_whole_data():
    # 1️⃣ Scrape latest match results
    print("🔹 Scraping latest results...")
    scrap_results()
    print(f"✅ Scraped matches.")

    # 2️⃣ Update the database with new results
    print("🔹 Updating database...")
    update_data()
    print("✅ Database updated successfully.")

if __name__ == "__main__":
    update_whole_data()