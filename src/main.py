from scrap.scraper import scrap_results
from db.update import update_data

if __name__ == "__main__":
    # 1️⃣ Scrape latest match results
    print("🔹 Scraping latest results...")
    scrap_results()
    print(f"✅ Scraped matches.")

    # 2️⃣ Update the database with new results
    print("🔹 Updating database...")
    update_data()
    print("✅ Database updated successfully.")
