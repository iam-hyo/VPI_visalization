import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

def scrap_subscriber(channel_id: str) -> pd.DataFrame:
    # === CONFIG ===
    URL = f"https://socialcounts.org/youtube-live-subscriber-count/{channel_id}"

    # === Start browser ===
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2
    }
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)

    # Wait for the stats table to load
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
    except:
        print(f"⚠️ No table found for channel: {channel_id}")
        driver.quit()
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=["Date", "Subscribers", "Daily Subscribers", "isChange", "Spread Change"])

    # === Parse HTML ===
    table_html = driver.find_element(By.TAG_NAME, "tbody").get_attribute("outerHTML")
    soup = BeautifulSoup(table_html, "html.parser")
    driver.quit()

    # === Extract data ===
    rows = []
    table = soup.find("tbody")
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        # td[0]: Date string
        date_divs = tds[0].find_all("div")
        if len(date_divs) < 1:
            continue
        try:
            date_str = date_divs[0].text.strip()
            date_obj = datetime.strptime(date_str, "%b %d, %Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except:
            continue

        # td[1]: Subscriber number
        sub_divs = tds[1].find_all("div")
        if len(sub_divs) < 1:
            continue
        try:
            subs = int(sub_divs[0].text.replace(",", "").strip())
        except:
            continue

        rows.append({
            "Date": formatted_date,
            "Subscribers": subs
        })

    # === Create and save DataFrame ===
    df = pd.DataFrame(rows)
    df = df[::-1].reset_index(drop=True)  # reverse to chronological order
    df["Daily Subscribers"] = df["Subscribers"].diff().fillna(0).astype(int)
    df["isChange"] = df["Daily Subscribers"] != 0

    # Save to CSV
    # os.makedirs("../data", exist_ok=True)
    # filename = os.path.join("..", "data", f"{channel_id}_subs_only.csv")
    # df.to_csv(filename, index=False)
    # print(f"✅ Saved to: {filename}")

    return df