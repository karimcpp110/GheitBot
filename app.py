import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import feedparser
from difflib import get_close_matches
from bs4 import BeautifulSoup
import datetime
import re

# Load Egypt places
try:
    places_df = pd.read_csv("egypt_places.csv")
    print("[INFO] egypt_places.csv loaded successfully.")
except Exception as e:
    print(f"[ERROR] Failed to load egypt_places.csv: {e}")

# Weather API Key
OPENWEATHER_API_KEY = "" #add yours 🤨
 

# --- UI Setup ---
st.set_page_config(page_title="غيط بوت - مساعد الفلاح", layout="wide")
st.title("🌾 غيط بوت - مساعد الفلاح المصري")

tab1, tab2, tab3 = st.tabs(["💬 الشات", "🗺 الخريطة", "📰 الأخبار والأسعار"])

# -------------------------------------------------------
# 💬 Chat
# -------------------------------------------------------
with tab1:
    st.subheader("اسأل سؤالك بالعامية 👨‍🌾")
    user_q = st.text_input("👨‍🌾 اكتب هنا:")

    if user_q:
        all_places = pd.concat([
            places_df["name"].dropna(),
            places_df["name_en"].dropna()
        ]).unique()

        closest = get_close_matches(user_q, all_places, n=1, cutoff=0.5)

        if closest:
            place_name = closest[0]
            matched = places_df[(places_df["name"] == place_name) | (places_df["name_en"] == place_name)]
        else:
            matched = pd.DataFrame()

        if not matched.empty:
            row = matched.iloc[0]
            lat, lon, city_ar = row["lat"], row["lon"], row["name"]

            if OPENWEATHER_API_KEY:
                url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ar"
                try:
                    data = requests.get(url, timeout=10).json()
                    print(f"[INFO] Weather API response for {city_ar}: OK")
                except Exception as e:
                    print(f"[ERROR] Weather API request failed: {e}")
                    data = {}

                if "main" in data:
                    temp = data["main"]["temp"]
                    wind = data["wind"]["speed"]
                    desc = data["weather"][0]["description"]

                    response = f"في {city_ar}: الحرارة {temp}°، {desc}، والرياح {wind} كم/س 🌬.\n"
                    if "طماطم" in user_q:
                        response += "🍅 الطماطم بتحب الجو المعتدل، لو الجو حر استنى أسبوعين."
                    elif "قمح" in user_q:
                        response += "🌾 القمح بيتزرع من نص أكتوبر لحد نص نوفمبر، استنى شوية."
                    else:
                        if temp > 30:
                            response += "🔥 الجو حر، قلل الريّ وخلي بالك من الشتلات."
                        elif temp < 15:
                            response += "❄ الجو برد، غطي الزرع."
                        else:
                            response += "🌿 الجو معتدل، تمام للزراعة."
                    st.success(response)
                else:
                    print("[WARN] Weather data missing 'main' field.")
                    st.error("مقدرتش أجيب بيانات الطقس دلوقتي.")
        else:
            print(f"[WARN] Place not found for query: {user_q}")
            st.error("معلش، ملقتش المكان ده في القايمة. جرب تكتب اسم تاني أو قريب منه.")

# -------------------------------------------------------
# 🗺 Map
# -------------------------------------------------------
with tab2:
    st.subheader("اختار مكان من مصر:")
    city_display = st.selectbox("اختر المكان:", places_df["name"].dropna().unique())

    row = places_df[places_df["name"] == city_display].iloc[0]
    lat, lon, city_ar = row["lat"], row["lon"], row["name"]

    st.write(f"📍 انت اخترت: *{city_ar}*")

    m = folium.Map(location=[lat, lon], zoom_start=7)
    folium.Marker([lat, lon], tooltip=city_ar).add_to(m)
    st_folium(m, width=700, height=500)

    if OPENWEATHER_API_KEY:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ar"
        try:
            response = requests.get(weather_url, timeout=10).json()
            print(f"[INFO] Weather API response for {city_ar}: OK")
        except Exception as e:
            print(f"[ERROR] Weather API request failed: {e}")
            response = {}

        if "main" in response:
            temp = response["main"]["temp"]
            wind = response["wind"]["speed"]
            desc = response["weather"][0]["description"]
            st.success(f"في {city_ar}: الحرارة {temp}°، {desc}، الرياح {wind} كم/س 🌬")
        else:
            print("[WARN] Weather data missing 'main' field.")
            st.error("مقدرتش أجيب بيانات الطقس دلوقتي.")

# -------------------------------------------------------
# 📰 News + Prices
# -------------------------------------------------------
def extract_prices_from_articles(entries):
    price_data = []
    for item in entries:
        try:
            r = requests.get(item["link"], timeout=10)
            soup = BeautifulSoup(r.content, "lxml")
            text = soup.get_text(" ", strip=True)

            matches = re.findall(r"(\w+)\s+(\d+)\s*(?:جنيه|ج)", text)
            for crop, price in matches:
                price_data.append({"المحصول": crop, "السعر (جنيه)": price, "المصدر": item["source"]})
            print(f"[INFO] Extracted prices from {item['link']}")
        except Exception as e:
            print(f"[ERROR] Failed to parse {item['link']}: {e}")
            continue
    return pd.DataFrame(price_data)

with tab3:
    st.subheader("📰 الأخبار الزراعية + 💰 أسعار المحاصيل (تتحدث كل دقيقتين)")
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=2 * 60 * 1000, key="refresh_news")

    feeds = {
        "أخبار زراعية (Agr-Egypt)": "https://www.agr-egypt.com/feed/",
        "زراعة مصر (Google News)": "https://news.google.com/rss/search?q=زراعة+مصر&hl=ar&gl=EG&ceid=EG:ar",
        "طقس (بوابة الأهرام)": "https://gate.ahram.org.eg/rss/97.aspx"
    }

    entries = []
    for src_name, url in feeds.items():
        try:
            for entry in feedparser.parse(url).entries[:5]:
                entries.append({"source": src_name, "title": entry.title, "link": entry.link})
            print(f"[INFO] Loaded feed: {src_name}")
        except Exception as e:
            print(f"[ERROR] Failed to load feed {src_name}: {e}")

    if entries:
        st.markdown("### 📰 أحدث الأخبار")
        for it in entries[:10]:
            st.write(f"- *({it['source']})* [{it['title']}]({it['link']})")
    else:
        st.warning("⚠ مش لاقيت أخبار دلوقتي.")

    st.markdown("### 📊 جدول أسعار المحاصيل المستخرجة من المقالات")
    df_prices = extract_prices_from_articles(entries)
    if not df_prices.empty:
        st.dataframe(df_prices)
    else:
        print("[INFO] No prices extracted from articles.")
        st.info("ℹ لسه ملاقيتش أسعار مباشرة في النصوص، بس الأخبار فوق موجودة.")

    st.caption(f"⏱ آخر تحديث: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
