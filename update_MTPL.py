import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 1. Firebase 초기화
firebase_key = os.environ.get('FIREBASE_KEY')
is_github = firebase_key is not None

try:
    if not firebase_admin._apps:
        if is_github:
            key_dict = json.loads(firebase_key)
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://metaplanet-mnav-default-rtdb.firebaseio.com/'
        })
except Exception as e:
    print(f"❌ Firebase 초기화 실패: {e}")
    exit()

def clean_num(text):
    if not text: return 0
    text = str(text).split('\n')[0]
    cleaned = re.sub(r'[^\d.]', '', text)
    try:
        return float(cleaned) if '.' in cleaned else int(cleaned)
    except: return 0

def run_mtpl_final_engine():
    url = "https://metaplanet.jp/jp/analytics"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        print(f"🌐 메타플래닛 접속 시작: {url}")
        start_time = time.time()
        driver.get(url)
        
        print("⏳ 15초 대기 중... (리눅스 서버 환경 최적화)")
        time.sleep(15) 

        elements = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, p, span, div")
        all_content = [el.text.strip() for el in elements if el.text.strip()]

        def get_by_key(idx_num):
            try:
                return all_content[int(idx_num) - 1]
            except: return "데이터없음"

        # --- [정밀 진단 로그] ---
        print("\n🔎 [이사님의 긴급 진단] 70번~110번 데이터 전수조사")
        print("-" * 50)
        for i in range(70, 111):
            val = get_by_key(str(i))
            mark = " ⭐ 찾았다!" if any(char.isdigit() for char in val) else ""
            print(f"인덱스 [{i}]: {val}{mark}")
        print("-" * 50)

        # --- [추출 및 단위 조정] ---
        extracted = {
            "mstrPrice":       clean_num(get_by_key("27")),
            "marketCap":       clean_num(get_by_key("340")) / 10,
            "enterpriseValue": clean_num(get_by_key("90")) / 10,
            "btcReserve":      clean_num(get_by_key("66")) / 10,
            "btcPrice":        clean_num(get_by_key("12")) / 100,
            "btcQuantity":     clean_num(get_by_key("42")),
            "debt":            clean_num(get_by_key("75")) / 10,
        }

        print("\n--- [추출 결과 보고] ---")
        for k, v in extracted.items():
            print(f"{k}: {v}")
        
        # 진단을 위해 안전장치를 4개로 대폭 늘려둠 (중단 방지)
        zero_count = list(extracted.values()).count(0)
        if zero_count >= 4:
            print(f"🚨 0이 {zero_count}개라 업데이트를 스킵합니다.")
            return

        # 계산 및 전송
        extracted["mnav"] = round(extracted["enterpriseValue"] / extracted["btcReserve"], 4) if extracted["btcReserve"] != 0 else 0
        extracted["usdReserve"] = extracted["marketCap"] + extracted["debt"] - extracted["enterpriseValue"]
        
        jst = timezone(timedelta(hours=9))
        extracted["updatetime"] = datetime.now(jst).strftime("%b %d, %Y, %H:%M JST")

        db.reference('/params').update(extracted)
        print(f"🚀 업데이트 성공! (소요: {int(time.time() - start_time)}초)")

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_mtpl_final_engine()