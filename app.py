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
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# -------------------------------------------------------
# 🔑 OpenWeather API Key
# -------------------------------------------------------
OPENWEATHER_API_KEY = "" # add yours

# -------------------------------------------------------
# 📂 Load Egypt places
# -------------------------------------------------------
try:
    places_df = pd.read_csv("egypt_places.csv")
except Exception as e:
    st.error(f"[ERROR] Failed to load egypt_places.csv: {e}")
    places_df = pd.DataFrame()

# -------------------------------------------------------
# ⚙️ Streamlit UI Setup
# -------------------------------------------------------
st.set_page_config(page_title="غيط بوت - مساعد الفلاح", layout="wide")
st.title("🌾 غيط بوت - مساعد الفلاح المصري")

tab1, tab2, tab3 = st.tabs(["💬 الشات", "🗺 الخريطة", "📰 الأخبار والأسعار"])

# -------------------------------------------------------
# 💬 Chat
# -------------------------------------------------------
with tab1:
    st.subheader("اسأل سؤالك بالعامية 👨‍🌾")
    user_q = st.text_input("👨‍🌾 اكتب هنا:")

    if user_q and not places_df.empty:
        all_places = pd.concat([
            places_df["name"].dropna(),
            places_df["name_en"].dropna()
        ]).unique()

        closest = get_close_matches(user_q, all_places, n=1, cutoff=0.5)
        matched = places_df[
            (places_df["name"] == closest[0]) | (places_df["name_en"] == closest[0])
        ] if closest else pd.DataFrame()

        if not matched.empty:
            row = matched.iloc[0]
            lat, lon, city_ar = row["lat"], row["lon"], row["name"]

            if OPENWEATHER_API_KEY:
                url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ar"
                try:
                    data = requests.get(url, timeout=10).json()
                except:
                    data = {}

                if "main" in data:
                    temp = data["main"]["temp"]
                    wind = data["wind"]["speed"]
                    desc = data["weather"][0]["description"]

                    response = f"في {city_ar}: الحرارة {temp}°، {desc}، والرياح {wind} كم/س 🌬.\n"
                    if "طماطم" in user_q:
                        response += "🍅 الطماطم بتحب الجو المعتدل، لو الجو حر استنى أسبوعين."
                    elif "قمح" in user_q:
                        response += "🌾 القمح بيتزرع من نص أكتوبر لحد نص نوفمبر."
                    else:
                        if temp > 30:
                            response += "🔥 الجو حر، قلل الريّ."
                        elif temp < 15:
                            response += "❄ الجو برد، غطي الزرع."
                        else:
                            response += "🌿 الجو معتدل، تمام للزراعة."
                    st.success(response)
                else:
                    st.error("مقدرتش أجيب بيانات الطقس دلوقتي.")
            else:
                st.warning("⚠ من فضلك ضيف OpenWeather API Key.")
        else:
            st.error("معلش، ملقتش المكان ده. جرب تكتب اسم تاني.")

# -------------------------------------------------------
# 🗺 Map + Crops Advice
# -------------------------------------------------------
with tab2:
    if not places_df.empty:
        st.subheader("اختار مكان من مصر:")
        city_display = st.selectbox("اختر المكان:", places_df["name"].dropna().unique())

        row = places_df[places_df["name"] == city_display].iloc[0]
        lat, lon, city_ar = row["lat"], row["lon"], row["name"]

        m = folium.Map(location=[lat, lon], zoom_start=7)
        folium.Marker([lat, lon], tooltip=city_ar).add_to(m)
        st_folium(m, width=700, height=500)

        try:
            crops_df = pd.read_csv("crops_egypt.csv")
        except:
            crops_df = pd.DataFrame()

        if OPENWEATHER_API_KEY:
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ar"
            try:
                response = requests.get(url, timeout=10).json()
            except:
                response = {}

            if "main" in response and not crops_df.empty:
                temp = response["main"]["temp"]
                wind = response["wind"]["speed"]
                humidity = response["main"]["humidity"]
                desc = response["weather"][0]["description"]

                st.success(f"📍 {city_ar}: الحرارة {temp}°، الرطوبة {humidity}%، {desc}، الرياح {wind} كم/س 🌬")

                chosen_crop = st.selectbox("اختر المحصول:", crops_df["المحصول"].unique())
                crop_row = crops_df[crops_df["المحصول"] == chosen_crop].iloc[0]

                st.markdown(f"### 🌱 {chosen_crop}")
                st.write(f"📅 موسم الزراعة: {crop_row['موسم_الزراعة']}")
                st.write(f"🌍 نوع التربة: {crop_row['نوع_التربة']}")
                st.write(f"💧 احتياجات الري: {crop_row['احتياجات_الري']}")
                st.write(f"🧪 التسميد: {crop_row['التسميد']}")
                st.write(f"☀ المناخ المناسب: {crop_row['المناخ_المناسب']}")
                st.write(f"📝 ملاحظات: {crop_row['ملاحظات']}")

                if "حار" in crop_row["المناخ_المناسب"] and temp >= 28:
                    advice = f"👌 الجو مناسب لزراعة {chosen_crop} (حار)."
                elif "بارد" in crop_row["المناخ_المناسب"] and temp <= 18:
                    advice = f"👌 الجو مناسب لزراعة {chosen_crop} (بارد)."
                elif "معتدل" in crop_row["المناخ_المناسب"] and 18 < temp < 28:
                    advice = f"👌 الجو مناسب لزراعة {chosen_crop} (معتدل)."
                else:
                    advice = f"⚠ الظروف الحالية مش مثالية لـ {chosen_crop}."
                st.info(advice)

# -------------------------------------------------------
# 📰 News + Prices
# -------------------------------------------------------
def extract_prices_from_articles(entries, crop_list):
    price_data = []
    for item in entries:
        try:
            r = requests.get(item["link"], timeout=10)
            soup = BeautifulSoup(r.content, "lxml")
            text = soup.get_text(" ", strip=True)

            for crop in crop_list:
                match = re.search(rf"{crop}[^0-9]{{0,20}}(\d+)(?:\s*[-–إلى]\s*(\d+))?\s*(?:جنيه|ج|EGP)", text)
                if match:
                    if match.group(2):
                        price = f"{match.group(1)} - {match.group(2)}"
                    else:
                        price = match.group(1)
                    price_data.append({"المحصول": crop, "السعر (جنيه)": price, "المصدر": item["source"]})
        except:
            continue
    return pd.DataFrame(price_data)

with tab3:
    st.subheader("📰 الأخبار الزراعية + 💰 أسعار المحاصيل (تتحدث كل دقيقتين)")
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
                entries.append({
                    "source": src_name,
                    "title": entry.title,
                    "link": entry.link,
                    "published": getattr(entry, "published", "—")
                })
        except:
            continue

    if entries:
        st.markdown("### 📰 أحدث الأخبار")
        for it in entries[:10]:
            with st.expander(f"{it['title']}"):
                st.write(f"📌 {it['source']} | 🗓 {it['published']}")
                st.markdown(f"[🔗 اقرأ الخبر]({it['link']})")
    else:
        st.warning("⚠ مش لاقيت أخبار دلوقتي.")

    try:
        crops_df = pd.read_csv("crops_egypt.csv")
        crop_list = crops_df["المحصول"].dropna().unique()
    except:
        crop_list = []

    st.markdown("### 📊 أسعار المحاصيل")
    df_prices = extract_prices_from_articles(entries, crop_list)
    if not df_prices.empty:
        st.dataframe(df_prices)
        fig = px.bar(df_prices, x="المحصول", y="السعر (جنيه)", color="المصدر", text="السعر (جنيه)")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ لسه ملاقيتش أسعار للمحاصيل في الأخبار.")

    st.caption(f"⏱ آخر تحديث: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
