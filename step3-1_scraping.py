import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3 as sq
from retry import retry

@retry(tries=3, delay=3, backoff=2)
def get_html(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup

# 東京23区を対象とした検索URL
base_url = "https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&ta=13&sc=13101&sc=13102&sc=13103&sc=13104&sc=13105&sc=13113&sc=13106&sc=13107&sc=13108&sc=13118&sc=13121&sc=13122&sc=13123&sc=13109&sc=13110&sc=13111&sc=13112&sc=13114&sc=13115&sc=13120&sc=13116&sc=13117&sc=13119&cb=0.0&ct=9999999&mb=0&mt=9999999&et=9999999&cn=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&sngz=&po1=25&pc=50&page={}"
all_data = []
max_page = 2200

for page in range(1, max_page+1):
    # URLを定義
    url = base_url.format(page)
    # HTMLを取得
    soup = get_html(url)
    # 項目を抽出
    items = soup.findAll("div", {"class": "cassetteitem"})
    print("page", page, "items", len(items))
    # 各項目を処理
    for item in items:
        stations = item.findAll("div", {"class": "cassetteitem_detail-text"})
        # 各駅を処理
        for station in stations:
            # 変数を定義
            base_data = {}
            # 基本情報を収集    
            base_data["名称"] = item.find("div", {"class": "cassetteitem_content-title"}).getText().strip()
            base_data["カテゴリー"] = item.find("div", {"class": "cassetteitem_content-label"}).getText().strip()
            base_data["アドレス"] = item.find("li", {"class": "cassetteitem_detail-col1"}).getText().strip()
            base_data["アクセス"] = station.getText().strip()
            base_data["築年数"] = item.find("li", {"class": "cassetteitem_detail-col3"}).findAll("div")[0].getText().strip()
            base_data["構造"] = item.find("li", {"class": "cassetteitem_detail-col3"}).findAll("div")[1].getText().strip()
            # 各部屋を処理
            tbodys = item.find("table", {"class": "cassetteitem_other"}).findAll("tbody")
            for tbody in tbodys:
                data = base_data.copy()
                data["階数"] = tbody.findAll("td")[2].getText().strip()
                data["家賃"] = tbody.findAll("td")[3].findAll("li")[0].getText().strip()
                data["管理費"] = tbody.findAll("td")[3].findAll("li")[1].getText().strip()
                data["敷金"] = tbody.findAll("td")[4].findAll("li")[0].getText().strip()
                data["礼金"] = tbody.findAll("td")[4].findAll("li")[1].getText().strip()
                data["間取り"] = tbody.findAll("td")[5].findAll("li")[0].getText().strip()
                data["面積"] = tbody.findAll("td")[5].findAll("li")[1].getText().strip()
                all_data.append(data)

# データフレームに変換
df = pd.DataFrame(all_data)

# 重複データの削除
df = df.drop_duplicates() 
df.head(2)

# 数値変換のための関数
def convert_to_number(text):
    try:
        return float(re.sub(r'[^\d.]', '', text)) if text else None
    except ValueError:
        return None

# アクセス情報を分割する関数
def split_access(row):
    accesses = row['アクセス'].split(', ')
    results = {}
    for i, access in enumerate(accesses, start=1):
        if i > 3:
            break  # 最大3つのアクセス情報のみを考慮
        parts = access.split('/')
        if len(parts) == 2:
            line_station, walk = parts
            if ' 歩' in walk:
                station, walk_min = walk.split(' 歩')
                walk_min = int(re.search(r'\d+', walk_min).group())
            else:
                station = None
                walk_min = None
        else:
            line_station = access
            station = walk_min = None
        results[f'路線名{i}'] = line_station.strip() if line_station else None
        results[f'駅名{i}'] = station.strip() if station else None
        results[f'徒歩分{i}'] = walk_min
    return pd.Series(results)

# データフレームをSQLiteに保存する関数
def save_to_sqlite(df, db_name="suumo_data.db"):
    # SQLiteデータベースへの接続を確立
    conn = sq.connect(db_name)
    cursor = conn.cursor()
    # テーブルを作成するSQLクエリ
    create_table_query = """
    CREATE TABLE IF NOT EXISTS properties (
        名称 TEXT,
        カテゴリー TEXT,
        アドレス TEXT,
        築年数 REAL,
        構造 TEXT,
        階数 REAL,
        家賃 REAL,
        管理費 REAL,
        敷金 REAL,
        礼金 REAL,
        間取り TEXT,
        面積 REAL,
        路線名1 TEXT,
        駅名1 TEXT,
        徒歩分1 REAL,
        路線名2 TEXT,
        駅名2 TEXT,
        徒歩分2 REAL,
        路線名3 TEXT,
        駅名3 TEXT,
        徒歩分3 REAL
    )
    """
    # テーブルを作成
    cursor.execute(create_table_query)
    # データフレームをSQLデータベースに挿入
    df.to_sql("properties", conn, if_exists="append", index=False)
    # コミットして接続を閉じる
    conn.commit()
    conn.close()

# アクセス情報を分割して新しい列を追加
access_splits = df.apply(split_access, axis=1)
df = pd.concat([df, access_splits], axis=1)
df = df.drop(columns=['アクセス'])  # 元のアクセス列を削除

# テキストを数値に変換
df['築年数'] = df['築年数'].apply(lambda x: convert_to_number(x))
df['階数'] = df['階数'].apply(lambda x: convert_to_number(x))
df['家賃'] = df['家賃'].apply(lambda x: convert_to_number(x))
df['管理費'] = df['管理費'].apply(lambda x: convert_to_number(x))
df['敷金'] = df['敷金'].apply(lambda x: convert_to_number(x))
df['礼金'] = df['礼金'].apply(lambda x: convert_to_number(x))
df['面積'] = df['面積'].apply(lambda x: convert_to_number(x))

# データフレームの最初の2行を表示
print(df.head(2))

# データフレームをSQLiteに保存
save_to_sqlite(df)
