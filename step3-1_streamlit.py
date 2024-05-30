import streamlit as st
import sqlite3 as sq
import pandas as pd
import requests

# OpenAIのAPIキーを設定（ChatGPTのAPIキーをここに設定）
openai_api_key = 'YOUR_OPENAI_API_KEY'

# SQLiteデータベースに接続
def get_data_from_db():
    conn = sq.connect('suumo_data.db')
    query = "SELECT * FROM properties"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ChatGPTのAPIを呼び出して駅を提案する関数
def get_suggested_stations(work_station, walk_time):
    prompt = f"職場の最寄り駅は{work_station}です。職場の最寄り駅から職場までの所要時間は徒歩で{walk_time}分です。生活が便利な住みやすい穴場の駅を5つ提案してください。なお、提案する駅は、その駅から職場の最寄り駅に行くまでの所要時間と、職場の最寄り駅から職場までの徒歩での所要時間の合計が50分以下になることを前提として下さい"
    response = requests.post(
        "https://api.openai.com/v1/completions",
        headers={
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "text-davinci-003",
            "prompt": prompt,
            "max_tokens": 100
        }
    )
    response_json = response.json()
    stations = response_json['choices'][0]['text'].strip().split('\n')
    return stations

# Streamlitアプリケーション
def main():
    st.title('おのぼりホームズ')

    df = get_data_from_db()

# サイドバーのフィルタリングオプション
st.sidebar.header('希望条件')
    rent_range = st.sidebar.slider('家賃 (円)', 0, 250000, (0, 250000), step=1000)
    management_fee_range = st.sidebar.slider('管理費 (円)', 0, 50000, (0, 50000), step=1000)
    age_range = st.sidebar.slider('築年数', 0, 50, (0, 50), step=1)
    area_range = st.sidebar.slider('面積 (m²)', 0, 200, (0, 200), step=1)
    layout = st.sidebar.selectbox('間取り', ['すべて', '1K', '1DK', '1LDK', '2K', '2DK', '2LDK', '3K', '3DK', '3LDK', '4LDK'])

    work_station = st.sidebar.text_input('職場の最寄り駅')
    walk_time = st.sidebar.number_input('職場までの徒歩所要時間 (分)', min_value=1, max_value=60, value=10)

 # ChatGPTを使って駅を提案
    if st.sidebar.button('駅検索スタートボタン'):
        suggested_stations, reasons = get_suggested_stations_and_reasons(work_station, walk_time)
        selected_station = st.sidebar.selectbox('オススメの駅', suggested_stations)
        st.sidebar.text_area(reasons[suggested_stations.index(selected_station)], height=100)
    else:
        selected_station = None

    # フィルタリング
    filtered_df = df[
        (df['家賃'] >= rent_range[0]) & (df['家賃'] <= rent_range[1]) &
        (df['管理費'] >= management_fee_range[0]) & (df['管理費'] <= management_fee_range[1]) &
        (df['築年数'] >= age_range[0]) & (df['築年数'] <= age_range[1]) &
        (df['面積'] >= area_range[0]) & (df['面積'] <= area_range[1])
    ]

    if layout != 'すべて':
        filtered_df = filtered_df[filtered_df['間取り'] == layout]

    if selected_station:
        filtered_df = filtered_df[
            (filtered_df['駅名1'] == selected_station) |
            (filtered_df['駅名2'] == selected_station) |
            (filtered_df['駅名3'] == selected_station)
        ]

    st.write(f'フィルタリング後の物件数: {len(filtered_df)}')
    st.dataframe(filtered_df)

if __name__ == '__main__':
    main()