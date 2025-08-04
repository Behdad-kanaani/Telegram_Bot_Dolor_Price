import requests
import json
import time
from bs4 import BeautifulSoup

# ===== تنظیمات عمومی =====
SCRAPE_INTERVAL_MINUTES = 10   # فاصله زمانی بین هر بار اجرای اسکرپینگ
WORKER_URL = "The Proxy Or cloudFlare Worker Link"   # لینک Worker یا پروکسی
WORKER_TOKEN = "The Key For Security"                # توکن امنیتی Worker
TELEGRAM_BOT_TOKEN = "Telegram Bot Token"            # توکن ربات تلگرام
TELEGRAM_CHAT_ID = The_Chat_Id                       # شناسه چت تلگرام (int یا str)

# ===== لینک‌های هدف =====
SCRAPE_TARGETS = {
    "The Link": "gold",    # لینک قیمت طلا
    "The Link": "dollar",  # لینک قیمت دلار
    "The Link": "usdt"     # لینک قیمت تتر
}

# ===== هدرهای HTTP =====
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest"
}

# ===== حافظه برای ذخیره قیمت‌های قبلی =====
previous_prices = {label: None for label in SCRAPE_TARGETS.values()}


# ===== توابع =====

def clean_price_to_int(price_str: str):
    """تبدیل رشته قیمت به عدد صحیح (در صورت معتبر بودن)."""
    price_str = price_str.replace(",", "").strip()
    return int(price_str) if price_str.isdigit() else None


def format_price(price_int: int):
    """نمایش عدد قیمت به فرمت 1,000,000."""
    return f"{price_int:,}"


def send_telegram_message_via_worker(worker_url, worker_token, bot_token, chat_id, text):
    """ارسال پیام به تلگرام از طریق Worker یا پروکسی."""
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {"target": telegram_api_url}
    headers = {
        "Content-Type": "application/json",
        "x-access-token": worker_token,
    }
    payload = {"chat_id": chat_id, "text": text}
    
    return requests.post(worker_url, params=params, headers=headers, json=payload)


def scrape_price(soup: BeautifulSoup, label: str):
    """استخراج قیمت بر اساس نوع دارایی."""
    if label == "gold":
        for tbody in soup.select("tbody.table-padding-lg"):
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) > 1 and cols[0].text.strip() == "نرخ فعلی":
                    return cols[1].text.strip()

    elif label == "dollar":
        for row in soup.select("tr.pointer"):
            title_cell = row.find("th")
            if title_cell and title_cell.text.strip() == "دلار":
                cols = row.find_all("td")
                if cols:
                    return cols[0].text.strip()

    elif label == "usdt":
        for tbody in soup.select("tbody.table-padding-lg"):
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) > 1 and cols[0].text.strip() == "قیمت ریالی":
                    return cols[1].text.strip()

    return None


# ===== حلقه اصلی =====
while True:
    message_text = "💰 قیمت‌های لحظه‌ای بازار:\n\n"
    current_prices = {}

    for url, label in SCRAPE_TARGETS.items():
        try:
            print(f"در حال اسکرپینگ {label} از {url}...")
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # استخراج قیمت
            raw_price = scrape_price(soup, label)

            if raw_price:
                price_int = clean_price_to_int(raw_price)
                if price_int is not None:
                    # در صورت نیاز به مقیاس‌دهی (تقسیم بر 10)
                    price_int = price_int // 10
                    current_prices[label] = price_int
                    print(f"قیمت {label} یافت شد: {format_price(price_int)} تومان")
                else:
                    print(f"خطا: قیمت {label} قابل تبدیل به عدد نیست → '{raw_price}'")
            else:
                print(f"خطا: قیمت {label} پیدا نشد.")

        except requests.exceptions.RequestException as e:
            print(f"خطا در ارتباط با {url}: {e}")
        except Exception as e:
            print(f"خطا در پردازش داده‌ها از {url}: {e}")

    # ساخت پیام خروجی با تغییرات
    for asset in ["gold", "dollar", "usdt"]:
        if asset in current_prices:
            current_price = current_prices[asset]
            prev_price = previous_prices.get(asset)

            # تعیین تغییرات
            if prev_price is None:
                emoji, change_text = "⚪", ""
            else:
                diff = current_price - prev_price
                if diff > 0:
                    emoji, change_text = "🟢", f" (افزایش: {format_price(diff)} تومان)"
                elif diff < 0:
                    emoji, change_text = "🔴", f" (کاهش: {format_price(abs(diff))} تومان)"
                else:
                    emoji, change_text = "⚪", ""

            # اضافه کردن به پیام
            if asset == "gold":
                message_text += f"🔹 طلا: {format_price(current_price)} تومان {emoji}{change_text}\n"
            elif asset == "dollar":
                message_text += f"🔹 دلار: {format_price(current_price)} تومان {emoji}{change_text}\n"
            elif asset == "usdt":
                message_text += f"🔹 تتر: {format_price(current_price)} تومان {emoji}{change_text}\n"

    # به‌روزرسانی قیمت‌های قبلی
    previous_prices.update(current_prices)

    # ارسال پیام به تلگرام
    if current_prices:
        print(f"\nدر حال ارسال پیام به چت {TELEGRAM_CHAT_ID}...")
        response = send_telegram_message_via_worker(
            WORKER_URL, WORKER_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message_text
        )

        print("---")
        print("وضعیت HTTP:", response.status_code)
        try:
            print("پاسخ JSON:", response.json())
        except requests.exceptions.JSONDecodeError:
            print("پاسخ متنی:", response.text)
        print("---")

        if response.status_code == 200:
            print("✅ پیام با موفقیت ارسال شد!")
        else:
            print("❌ خطا در ارسال پیام.")
    else:
        print("هیچ قیمتی یافت نشد، پیام ارسال نشد.")

    # مکث تا اجرای بعدی
    time.sleep(60 * SCRAPE_INTERVAL_MINUTES)
