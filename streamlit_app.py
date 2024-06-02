import streamlit as st
import sqlite3 as sq
import pandas as pd
import requests

# OpenAIのAPIキーを設定（ChatGPTのAPIキーをここに設定）
openai_api_key = "ダミー"

# SQLiteデータベースに接続
def get_data_from_db():
    conn = sq.connect('suumo_data.db')
    query = "SELECT * FROM properties"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 駅とその理由を取得する関数
def get_suggested_stations_and_reasons(work_station, commuting_time):
    prompt = f"{work_station}に{commuting_time}分以内に行ける、生活が便利で、住みやすい穴場の駅を5つ提案し、その理由を述べてください。"
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }
    )

    if response.status_code == 200:
        response_json = response.json()
        if 'choices' in response_json:
            content = response_json['choices'][0]['message']['content'].strip()
            # 提案メッセージの確認と削除
            if "提案します。" in content:
                content = content.split("提案します。")[1].strip()
            stations_and_reasons = content.split('\n')
            stations = []
            reasons = []
            current_reason = ""
            for line in stations_and_reasons:
                if line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ')):
                    if current_reason:
                        reasons.append(current_reason.strip())
                    stations.append(line)
                    current_reason = ""
                else:
                    current_reason += line + " "
            if current_reason:
                reasons.append(current_reason.strip())
            
            # Ensure there are exactly 5 stations and reasons
            while len(stations) < 5:
                stations.append("N/A")
                reasons.append("N/A")
                
            return stations[:5], reasons[:5]
        else:
            st.error("APIレスポンスに'choices'キーが含まれていません。")
            return [], []
    else:
        st.error(f"APIリクエストが失敗しました。ステータスコード: {response.status_code}, レスポンス: {response.text}")
        return [], []

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
    commuting_time = st.sidebar.number_input('職場の最寄り駅までの所要時間 (分)', min_value=1, max_value=60, value=10)

    if st.sidebar.button('駅検索スタートボタン'):
        suggested_stations, reasons = get_suggested_stations_and_reasons(work_station, commuting_time)
        st.session_state['suggested_stations'] = suggested_stations
        st.session_state['reasons'] = reasons

    if 'suggested_stations' in st.session_state:
        st.header('おすすめの駅と理由')
        st.write("東京駅から35分以内で行ける、生活が便利で住みやすい穴場の駅を以下に5つ提案します。")
        for i in range(len(st.session_state['suggested_stations'])):
            st.subheader(st.session_state['suggested_stations'][i])
            st.write(st.session_state['reasons'][i])

        selected_stations = st.sidebar.multiselect('興味がある駅を5つまで選択してください', st.session_state['suggested_stations'], max_selections=5)
        for i, station in enumerate(st.session_state['suggested_stations']):
            if station in selected_stations:
    else:
        selected_stations = []

    if st.sidebar.button('物件サーチボタン'):
        filtered_df = df[
            (df['家賃'] >= rent_range[0]) & (df['家賃'] <= rent_range[1]) &
            (df['管理費'] >= management_fee_range[0]) & (df['管理費'] <= management_fee_range[1]) &
            (df['築年数'] >= age_range[0]) & (df['築年数'] <= age_range[1]) &
            (df['面積'] >= area_range[0]) & (df['面積'] <= area_range[1])
        ]

        if layout != 'すべて':
            filtered_df = filtered_df[filtered_df['間取り'] == layout]

        if selected_stations:
            filtered_df = filtered_df[
                (df['駅名1'].isin(selected_stations)) |
                (df['駅名2'].isin(selected_stations)) |
                (df['駅名3'].isin(selected_stations))
            ]

        st.write(f'フィルタリング後の物件数: {len(filtered_df)}')
        st.dataframe(filtered_df[['名称', 'アドレス', '築年数', '家賃', '間取り', '面積', '駅名1', '徒歩分1', '物件画像URL', '間取画像URL', '物件詳細URL']])

if __name__ == '__main__':
    main()

