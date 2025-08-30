import re

def extract_prices_from_articles(entries):
    price_data = []

    for item in entries:
        try:
            r = requests.get(item["link"], timeout=10)
            soup = BeautifulSoup(r.content, "lxml")
            text = soup.get_text(" ", strip=True)

            # ندور على أرقام مع كلمة "جنيه" أو "ج"
            matches = re.findall(r"(\w+)\s+(\d+)\s*(?:جنيه|ج)", text)
            for crop, price in matches:
                price_data.append({"المحصول": crop, "السعر (جنيه)": price, "المصدر": item["source"]})
        except:
            continue

    return pd.DataFrame(price_data)
