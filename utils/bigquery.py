from google.cloud import bigquery
from datetime import datetime
import pandas as pd

client = bigquery.Client(project="awesome-aurora-488510-k4")

# =====================================================
# TABLE SCHEMAS
# =====================================================

SCHEMAS = {
    "cohort_dim": [
        bigquery.SchemaField("Cohort_ID", "STRING"),
        bigquery.SchemaField("Cohort_Name", "STRING"),
        bigquery.SchemaField("Program", "STRING"),
        bigquery.SchemaField("Start_Date", "DATE"),
        bigquery.SchemaField("Mode", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ],
    "student_dim": [
        bigquery.SchemaField("Student_ID", "STRING"),
        bigquery.SchemaField("Student_Name", "STRING"),
        bigquery.SchemaField("Cohort_ID", "STRING"),
        bigquery.SchemaField("Enrollment_Type", "STRING"),
        bigquery.SchemaField("Joining_Date", "DATE"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ],
    "instructor_dim": [
        bigquery.SchemaField("Instructor_ID", "STRING"),
        bigquery.SchemaField("Instructor_Name", "STRING"),
        bigquery.SchemaField("Expertise", "STRING"),
        bigquery.SchemaField("Instructor_Type", "STRING"),
        bigquery.SchemaField("Experience_Years", "INTEGER"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ],
    "session_dim": [
        bigquery.SchemaField("Session_ID", "STRING"),
        bigquery.SchemaField("Cohort_ID", "STRING"),
        bigquery.SchemaField("Instructor_ID", "STRING"),
        bigquery.SchemaField("Session_Date", "DATE"),
        bigquery.SchemaField("Session_Type", "STRING"),
        bigquery.SchemaField("Topic", "STRING"),
        bigquery.SchemaField("Week_Number", "INTEGER"),
        bigquery.SchemaField("Month", "STRING"),
        bigquery.SchemaField("Is_Weekend", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ],
    "feedback_fact": [
        bigquery.SchemaField("Feedback_ID", "STRING"),
        bigquery.SchemaField("Timestamp", "TIMESTAMP"),
        bigquery.SchemaField("Session_ID", "STRING"),
        bigquery.SchemaField("Student_ID", "STRING"),
        bigquery.SchemaField("Session_Rating", "INTEGER"),
        bigquery.SchemaField("Trainer_Rating", "INTEGER"),
        bigquery.SchemaField("Content_Rating", "INTEGER"),
        bigquery.SchemaField("Pace", "STRING"),
        bigquery.SchemaField("Recommend", "STRING"),
        bigquery.SchemaField("Comment", "STRING"),
        bigquery.SchemaField("sentiment_score", "FLOAT"),
        bigquery.SchemaField("predicted_sentiment", "STRING"),
        bigquery.SchemaField("processed_at", "TIMESTAMP"),
    ]
}

# =====================================================
# PREPROCESSING
# =====================================================

def preprocess_dataframe(df):

    date_columns = ["Start_Date", "Joining_Date", "Session_Date"]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                format="%d-%m-%Y",
                errors="coerce"
            ).dt.date

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(
            df["Timestamp"],
            errors="coerce",
            dayfirst=True
        )

    int_columns = [
        "Experience_Years",
        "Week_Number",
        "Session_Rating",
        "Trainer_Rating",
        "Content_Rating"
    ]

    for col in int_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "sentiment_score" in df.columns:
        df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="coerce")

    return df


# =====================================================
# SORTING LOGIC
# =====================================================

def sort_dataframe(df, table_name):

    if table_name == "feedback_fact" and "Timestamp" in df.columns:
        df = df.sort_values(by="Timestamp")

    elif table_name == "student_dim" and "Joining_Date" in df.columns:
        df = df.sort_values(by="Joining_Date")

    elif table_name == "cohort_dim" and "Start_Date" in df.columns:
        df = df.sort_values(by="Start_Date")

    elif table_name == "session_dim" and "Session_Date" in df.columns:
        df = df.sort_values(by="Session_Date")

    return df


# =====================================================
# DUPLICATE FILTER (FEEDBACK ONLY)
# =====================================================

def filter_new_feedback(df, table_id):

    if df.empty:
        return df

    try:
        query = f"SELECT Feedback_ID FROM `{table_id}`"
        existing_ids = [row.Feedback_ID for row in client.query(query).result()]
        df = df[~df["Feedback_ID"].isin(existing_ids)]
    except Exception:
        pass

    return df


# =====================================================
# LOAD FUNCTION
# =====================================================

def load_table(df, table_id, table_name, mode="append"):

    if df.empty:
        print(f"No data to load for {table_name}.")
        return

    df = preprocess_dataframe(df)

    # Incremental detection logging
    if table_name == "feedback_fact" and mode == "append":
        original_count = len(df)
        df = filter_new_feedback(df, table_id)
        new_count = len(df)

        if new_count == 0:
            print("No new feedback records to insert. (Incremental load skipped)")
            return

        print(f"Incremental load detected: {new_count} new rows out of {original_count} total rows.")

    # SORT BEFORE LOAD
    df = sort_dataframe(df, table_name)

    df["processed_at"] = datetime.now()

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMAS[table_name],
        write_disposition=(
            bigquery.WriteDisposition.WRITE_APPEND
            if mode == "append"
            else bigquery.WriteDisposition.WRITE_TRUNCATE
        ),
        time_partitioning=bigquery.TimePartitioning(
            field="Timestamp"
        ) if table_name == "feedback_fact" else None
    )

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    load_type = "APPEND (Incremental)" if mode == "append" else "TRUNCATE (Full Reload)"
    print(f"{len(df)} rows loaded into {table_name}. Load Type: {load_type}")