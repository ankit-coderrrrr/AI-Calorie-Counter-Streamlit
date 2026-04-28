import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import re
import os
from datetime import date

# --- 1. CONFIGURATION & AI SETUP ---
st.set_page_config(page_title="AI Calorie Tracker", layout="centered", page_icon='🍎')

# Instead of genai.configure(api_key="..."), use:
genai.configure(api_key=st.secrets["GEMINI_KEY"])

# We use gemini-3-flash-preview as found in your list_models() check
model = genai.GenerativeModel('gemini-3-flash-preview')

DB_FILE = "calorie_history.csv"


# --- 2. HELPER FUNCTIONS ---
def load_history():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=["Date", "Item", "Calories"])


def save_to_history(new_data_list):
    df = load_history()
    # Create new rows from the AI list (excluding the TOTAL row for history)
    new_rows = pd.DataFrame(new_data_list)
    new_rows = new_rows[new_rows['Item'] != 'TOTAL']
    new_rows['Date'] = date.today()

    updated_df = pd.concat([df, new_rows], ignore_index=True)
    updated_df.to_csv(DB_FILE, index=False)


# --- 3. USER INTERFACE ---
st.title("🍎 AI Visual Calorie Counter")
st.markdown("---")

# Sidebar for History
with st.sidebar:
    st.header("📊 Daily Progress")
    history_df = load_history()
    today_data = history_df[history_df['Date'] == date.today()]
    total_today = today_data['Calories'].sum()

    st.metric("Total Calories Today", f"{total_today} kcal")
    if not today_data.empty:
        st.write("Recent Meals:")
        st.dataframe(today_data[['Item', 'Calories']], hide_index=True)

    if st.button("🗑️ Clear All Logs"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            st.rerun()

# Main Upload Area
uploaded_file = st.file_uploader("Upload a photo of your meal...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Your Meal", use_container_width=True)

    if st.button("🔍 Analyze Calories", key="analyze_btn"):
        with st.spinner("AI is examining your food..."):
            # 4. THE AI PROMPT (JSON MODE)
            prompt = """
            Analyze the food in this image. Return the data ONLY in this JSON format:
            [
              {"Item": "Food Name", "Calories": 100},
              {"Item": "TOTAL", "Calories": 100}
            ]
            Do not include any text before or after the JSON.
            """

            try:
                response = model.generate_content([prompt, image])

                # 5. PARSING THE RESPONSE
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())

                    # 6. PANDAS SHOWCASE
                    df_meal = pd.DataFrame(data)

                    # Separate items for display
                    items_only = df_meal[df_meal["Item"] != "TOTAL"]
                    meal_total = df_meal[df_meal["Item"] == "TOTAL"]["Calories"].values[0]

                    st.success("Analysis Complete!")
                    st.write("### 🥗 Meal Breakdown")
                    st.table(items_only)  # Showcase using Pandas Table

                    st.metric("Total for this Meal", f"{meal_total} kcal")

                    # 7. PERSISTENCE (Save to CSV)
                    save_to_history(data)
                    st.info("Meal saved to daily history!")
                    st.button("Refresh Dashboard", on_click=st.rerun())

                else:
                    st.error("Could not find data in AI response. Try a clearer photo.")
                    st.write("Raw Output:", response.text)

            except Exception as e:
                st.error(f"Error: {e}")
