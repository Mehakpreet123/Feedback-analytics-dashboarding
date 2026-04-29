import os
from flask import Flask

from utils.sheets import fetch_sheet_data
from utils.sentiments import analyze_sentiment
from utils.bigquery import load_table

PROJECT = "awesome-aurora-488510-k4"
DATASET = "feedback_ds"
SHEET_NAME = "Dummy data-feedback analysis"

app = Flask(__name__)

# =====================================================
# 🔧 MINIMAL CLEANING (ONLY ID CASTING)
# =====================================================

def clean_dataframe(df):

    if df.empty:
        return df

    id_columns = [
        "Student_ID",
        "Instructor_ID",
        "Session_ID",
        "Cohort_ID",
        "Feedback_ID"
    ]

    for col in id_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df


# =====================================================
# 🚀 MAIN PIPELINE LOGIC
# =====================================================

def update_all_tables():

    # 1️⃣ STATIC TABLES (REPLACE DAILY)

    cohort_df = clean_dataframe(fetch_sheet_data(SHEET_NAME, "Cohort"))
    load_table(cohort_df, f"{PROJECT}.{DATASET}.cohort_dim", "cohort_dim", mode="replace")

    student_df = clean_dataframe(fetch_sheet_data(SHEET_NAME, "Student"))
    load_table(student_df, f"{PROJECT}.{DATASET}.student_dim", "student_dim", mode="replace")

    instructor_df = clean_dataframe(fetch_sheet_data(SHEET_NAME, "Instructor"))
    load_table(instructor_df, f"{PROJECT}.{DATASET}.instructor_dim", "instructor_dim", mode="replace")

    session_df = clean_dataframe(fetch_sheet_data(SHEET_NAME, "Session"))
    load_table(session_df, f"{PROJECT}.{DATASET}.session_dim", "session_dim", mode="replace")

    # 2️⃣ FEEDBACK (APPEND)

    feedback_df = clean_dataframe(fetch_sheet_data(SHEET_NAME, "Feedback"))

    if feedback_df.empty:
        return "No feedback found."

    sentiments = feedback_df["Comment"].fillna("").apply(analyze_sentiment)
    feedback_df["predicted_sentiment"] = [s[0] for s in sentiments]
    feedback_df["sentiment_score"] = [s[1] for s in sentiments]

    load_table(
        feedback_df,
        f"{PROJECT}.{DATASET}.feedback_fact",
        "feedback_fact",
        mode="append"
    )

    return "Pipeline executed successfully."


# =====================================================
# 🌐 CLOUD RUN ENTRYPOINT
# =====================================================

@app.route("/", methods=["GET"])
def run_pipeline():
    result = update_all_tables()
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)