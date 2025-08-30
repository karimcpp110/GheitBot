import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import feedparser
from difflib import get_close_matches
import datetime
from streamlit_autorefresh import st_autorefresh

# =======================================================
# 🔑 API KEYS
# =======================================================
OPENWEATHER_API_KEY = "044031a0a9711a73d5042fc5e97bc8f4"   # Weather API

# تحميل قائمة أماكن مصر
places_df = pd.read_csv("egypt_places.csv")

# --- إعداد الواجهة ---
st.set_page_config(page_title="غيط بوت - مساعد الفلاح", layout="wide")
st.title("🌾 غيط بوت - مساعد الفلاح المصري")

tab1, tab2, tab3 = st.tabs(["💬 الشات", "🗺 الخريطة", "📰 الأخبار"])

# =======================================================
# 🤖 دالة للإجابة على الأسئلة الزراعية (Rules Engine)
# =======================================================
def answer_agriculture_question(question, temp=None):
    q = question.strip().lower()
    response = ""

    if "طماطم" in q:
        if temp and temp > 30:
            response = "🍅 الطماطم بتحب الجو المعتدل، الجو حر دلوقتي، استنى أسبوعين قبل ما تزرع."
        else:
            response = "🍅 الطماطم مناسبة للزراعة دلوقتي."
    elif "قمح" in q:
        response = "🌾 القمح بيتزرع من نص أكتوبر لحد نص نوفمبر."
    elif "بطاطس" in q:
        response = "🥔 البطاطس بتحتاج تربة طينية جيدة الصرف وتتحمل الجو المعتدل."
    elif "ذرة" in q:
        response = "🌽 الذرة الصيفية تتزرع من مارس لحد مايو."
    else:
        response = "🤔 مش قادر أجاوبك بدقة، جرّب تسأل عن محصول زي: الطماطم، القمح، البطاطس، الذرة."

    return response

# =======================================================
# 💬 الشات
# =======================================================
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
                data = requests.get(url).json()

                if "main" in data:
                    temp = data["main"]["temp"]
                    wind = data["wind"]["speed"]
                    desc = data["weather"][0]["description"]

                    response = f"في {city_ar}: الحرارة {temp}°، {desc}، والرياح {wind} كم/س 🌬.\n"
                    if temp > 30:
                        response += "🔥 الجو حر، قلل الريّ وخلي بالك من الشتلات."
                    elif temp < 15:
                        response += "❄️ الجو برد، غطي الزرع."
                    else:
                        response += "🌿 الجو معتدل، تمام للزراعة."
                    st.success(response)

                    # ✅ إجابة زراعية حسب السؤال
                    agri_answer = answer_agriculture_question(user_q, temp)
                    st.info(f"👨‍🌾 نصيحة زراعية: {agri_answer}")
                else:
                    st.error("مقدرتش أجيب بيانات الطقس دلوقتي.")
        else:
            agri_answer = answer_agriculture_question(user_q)
            st.info(f"👨‍🌾 نصيحة زراعية: {agri_answer}")

# =======================================================
# 🗺 الخريطة
# =======================================================
with tab2:
    st.subheader("اختار مكان من مصر:")
    city_display = st.selectbox("اختر المكان:", places_df["name"].dropna().unique())

    row = places_df[places_df["name"] == city_display].iloc[0]
    lat, lon, city_ar = row["lat"], row["lon"], row["name"]

    st.write(f"📍 انت اخترت: **{city_ar}**")

    m = folium.Map(location=[lat, lon], zoom_start=7)
    folium.Marker([lat, lon], tooltip=city_ar).add_to(m)
    st_folium(m, width=700, height=500)

    if OPENWEATHER_API_KEY:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ar"
        response = requests.get(weather_url).json()
        if "main" in response:
            temp = response["main"]["temp"]
            wind = response["wind"]["speed"]
            desc = response["weather"][0]["description"]
            st.success(f"في {city_ar}: الحرارة {temp}°، {desc}، الرياح {wind} كم/س 🌬")

            if temp > 30:
                st.info("🌴 مناسب لمحاصيل زي: البلح، الذرة، البطيخ")
            elif temp < 15:
                st.info("🥦 مناسب لمحاصيل زي: القمح، الفول، البصل")
            else:
                st.info("🥒 مناسب لمحاصيل زي: الخيار، الطماطم، الفلفل")
        else:
            st.error("مقدرتش أجيب بيانات الطقس دلوقتي.")

# =======================================================
# 📰 الأخبار
# =======================================================
with tab3:
    st_autorefresh(interval=2 * 60 * 1000, key="refresh_news")
    st.subheader("📰 الأخبار الزراعية + الطقس + الأسعار (محدثة كل دقيقتين)")

    feeds = {
        "أخبار زراعية (Agr-Egypt)": "https://www.agr-egypt.com/feed/",
        "زراعة مصر (Google News)": "https://news.google.com/rss/search?q=زراعة+مصر&hl=ar&gl=EG&ceid=EG:ar",
        "طقس (بوابة الأهرام)": "https://gate.ahram.org.eg/rss/97.aspx",
        "اقتصاد (Google News)": "https://news.google.com/rss/search?q=اقتصاد+مصر&hl=ar&gl=EG&ceid=EG:ar"
    }

    entries = []
    for src_name, url in feeds.items():
        for entry in feedparser.parse(url).entries[:3]:
            snippet = entry.summary[:150] + "..." if hasattr(entry, "summary") else ""
            entries.append({"source": src_name, "title": entry.title, "link": entry.link, "snippet": snippet})

    if entries:
        for it in entries[:10]:
            st.write(f"🔹 **({it['source']})** [{it['title']}]({it['link']})")
            if it['snippet']:
                st.caption(it['snippet'])
    else:
        st.warning("⚠️ مش لاقيت أخبار دلوقتي.")

    st.caption(f"⏱ آخر تحديث: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
