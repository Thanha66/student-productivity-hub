import streamlit as st
import datetime
import random
import pandas as pd
from supabase import create_client, Client
from PIL import Image
import pytesseract
import json

# Supabase connection from secrets.toml
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Tesseract path (change if your install is different)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Student Productivity Hub", layout="wide")

quotes = [
    "Have a great day! Study hard and keep pushing! 🔥",
    "One more session = one step closer to your goals! 💪",
    "Exams are tough, but you've got this — never give up!",
    "Focus like your future depends on it! ☑️",
    "You're not just studying — you're building your future! Keep going!",
    "Take a break, recharge, then come back stronger! ☕",
    "Small consistent wins today = big success tomorrow.",
    "Study now, thank yourself later! 🚀",
    "Progress over perfection. Keep moving forward!",
    "One focused hour today beats four distracted hours tomorrow."
]

# Email login (per-user data in Supabase)
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_email:
    st.title("Login to Your Personal Hub")
    email = st.text_input("Enter your email (your unique ID)")
    if st.button("Login"):
        if email.strip():
            st.session_state.user_email = email.strip()
            st.rerun()
        else:
            st.warning("Enter an email")
    st.stop()

st.sidebar.title(f"Welcome, {st.session_state.user_email.split('@')[0]}!")

# Initialize ALL session state keys (fixes AttributeError)
if 'study_logs' not in st.session_state:
    st.session_state.study_logs = []
if 'exam_date' not in st.session_state:
    st.session_state.exam_date = datetime.date.today() + datetime.timedelta(days=30)
if 'project_tasks' not in st.session_state:
    st.session_state.project_tasks = []
if 'timetable' not in st.session_state:
    st.session_state.timetable = []

page = st.sidebar.radio("Go to", [
    "Dashboard",
    "Exam Countdown",
    "Study Logs & Progress",
    "Project Guidance",
    "Timetable",
    "Code Generator from Photo"
])

# Supabase helpers
def get_user_data(table):
    response = supabase.table(table).select("*").eq("user_email", st.session_state.user_email).execute()
    return response.data if response.data else []

def upsert_user_data(table, data):
    data["user_email"] = st.session_state.user_email
    supabase.table(table).upsert(data).execute()

def save_all():
    # No local JSON needed - everything goes to Supabase
    pass

# Dashboard
if page == "Dashboard":
    st.title("Welcome to Your Productivity Hub! 🚀")
    st.write("**Daily Motivation:** " + random.choice(quotes))

    exam_data = get_user_data("exam_dates")
    if exam_data:
        exam_date = datetime.date.fromisoformat(exam_data[0]["exam_date"])
        days_left = (exam_date - datetime.date.today()).days
        st.metric("Days to Next Exam", days_left if days_left > 0 else "Exam Over! Celebrate 🎉")
    else:
        st.metric("Days to Next Exam", "Not set yet")

# Exam Countdown
elif page == "Exam Countdown":
    st.title("Exam Countdown ⏳")

    exam_data = get_user_data("exam_dates")
    default_date = datetime.date.fromisoformat(exam_data[0]["exam_date"]) if exam_data else datetime.date.today() + datetime.timedelta(days=30)

    exam_date = st.date_input("Set your next exam date", default_date)
    if st.button("Save Exam Date"):
        upsert_user_data("exam_dates", {"exam_date": exam_date.isoformat()})
        st.success("Exam date saved permanently!")

    days_left = (exam_date - datetime.date.today()).days
    if days_left > 0:
        st.header(f"{days_left} days remaining!")
        st.progress(min(1 - days_left / 90, 1.0))
    else:
        st.header("Exam period passed! Great job 🎓")

# Study Logs & Progress
elif page == "Study Logs & Progress":
    st.title("Study Logs & Weekly Insights 📊")
    
    logs = get_user_data("study_logs")
    if logs:
        all_logs = []
        for l in logs:
            log_list = json.loads(l['logs']) if l.get('logs') else []
            all_logs.extend(log_list)
        if all_logs:
            df = pd.DataFrame(all_logs)
            df['date'] = pd.to_datetime(df['date'])
            st.dataframe(df)
        else:
            st.info("No logs yet.")
    else:
        st.info("No logs yet. Log sessions from other pages.")

# Project Guidance
elif page == "Project Guidance":
    st.title("Project / Assignment Breakdown 📝")
    
    project_name = st.text_input("Project or Assignment Name")
    steps_input = st.text_area("Enter main tasks / steps (one per line)")
    
    if st.button("Create Task List") and steps_input.strip():
        step_list = [s.strip() for s in steps_input.split('\n') if s.strip()]
        st.session_state.project_tasks = step_list
        save_all()
        st.success("Task list created!")
    
    if st.session_state.project_tasks:
        st.subheader(f"Tasks for: {project_name or 'Your Project'}")
        done_count = 0
        for task in st.session_state.project_tasks:
            if st.checkbox(task, key=f"task_{task}"):
                done_count += 1
        
        progress = done_count / len(st.session_state.project_tasks)
        st.progress(progress)
        st.write(f"Progress: {progress*100:.0f}% complete")
        
        if progress == 1:
            st.success("All tasks completed! Awesome job 🎉")

elif page == "Timetable":
    st.title("My Timetable 📅")

    # Load timetable from Supabase if not in session state
    if 'timetable' not in st.session_state or not st.session_state.timetable:
        timetable_data = get_user_data("timetables")
        if timetable_data:
            st.session_state.timetable = json.loads(timetable_data[0]['timetable']) if timetable_data[0].get('timetable') else []
        else:
            st.session_state.timetable = []

    st.subheader("Add New Class")
    with st.form("add_class"):
        subject = st.text_input("Subject / Class Name")
        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")
        day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        submit = st.form_submit_button("Add to Timetable")

    if submit and subject:
        new_entry = {
            "day": day,
            "subject": subject,
            "start": start_time.strftime("%H:%M"),
            "end": end_time.strftime("%H:%M")
        }
        st.session_state.timetable.append(new_entry)
        # Save to Supabase
        upsert_user_data("timetables", {"timetable": json.dumps(st.session_state.timetable)})
        st.success(f"Added: {subject} on {day} from {start_time} to {end_time}")
        st.rerun()

    if st.session_state.timetable:
        st.subheader("Your Timetable")
        df = pd.DataFrame(st.session_state.timetable)
        df['select'] = False

        edited_df = st.data_editor(
            df,
            column_config={
                "select": st.column_config.CheckboxColumn("Select to Delete", default=False)
            },
            hide_index=False,
            num_rows="dynamic",
            key="timetable_editor"
        )

        if st.button("Delete Selected Entries"):
            to_delete = edited_df[edited_df['select'] == True].index.tolist()
            if to_delete:
                st.session_state.timetable = [entry for i, entry in enumerate(st.session_state.timetable) if i not in to_delete]
                # Save updated list to Supabase
                upsert_user_data("timetables", {"timetable": json.dumps(st.session_state.timetable)})
                st.success(f"Deleted {len(to_delete)} entry(ies)!")
                st.rerun()
            else:
                st.warning("Select entries to delete")

        today_day = datetime.date.today().strftime("%A")
        today_classes = df[df['day'] == today_day]
        if not today_classes.empty:
            st.subheader(f"Today's Classes ({today_day})")
            st.dataframe(today_classes.drop(columns=['select']))
        else:
            st.info(f"No classes scheduled for today ({today_day})")
    else:
        st.info("No classes added yet. Use the form above to add your timetable!")

# ==================== CODE GENERATOR FROM PHOTO ====================
elif page == "Code Generator from Photo":
    st.title("Code Generator from Photo 💻")
    st.write("Upload a photo of a coding question — the app will try to generate Python code.")

    uploaded_file = st.file_uploader("Upload photo of question", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Question Photo", use_column_width=True)

        if st.button("Extract & Generate Code"):
            with st.spinner("Trying to read the question..."):
                try:
                    # Try OCR
                    text = pytesseract.image_to_string(image, lang='eng')
                    lower_text = text.lower().replace('\n', ' ').strip()

                    st.subheader("Extracted Text")
                    st.text_area("Raw Text", text, height=150)

                    # Simple rule-based code generation
                    code = "# Could not detect a known problem type."
                    explanation = "Detected no known pattern."

                    if any(word in lower_text for word in ["prime", "check prime", "is prime"]):
                        code = """
def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

print(is_prime(17))  # True
                        """
                        explanation = "Detected 'prime number' problem."

                    elif any(word in lower_text for word in ["fibonacci", "fib series"]):
                        code = """
def fibonacci(n):
    a, b = 0, 1
    sequence = []
    for _ in range(n):
        sequence.append(a)
        a, b = b, a + b
    return sequence

print(fibonacci(10))
                        """
                        explanation = "Detected 'fibonacci' problem."

                    elif any(word in lower_text for word in ["palindrome", "check palindrome"]):
                        code = """
def is_palindrome(s):
    s = s.lower().replace(" ", "")
    return s == s[::-1]

print(is_palindrome("racecar"))  # True
                        """
                        explanation = "Detected 'palindrome' problem."

                    elif any(word in lower_text for word in ["sum", "add numbers", "total"]):
                        code = """
def sum_of_list(numbers):
    return sum(numbers)

nums = [1, 2, 3, 4, 5]
print(sum_of_list(nums))  # 15
                        """
                        explanation = "Detected 'sum' problem."

                    st.subheader("Generated Code")
                    st.code(code, language="python")

                    st.subheader("Explanation")
                    st.write(explanation)

                    # Save to logs
                    log = {
                        "date": datetime.date.today().isoformat(),
                        "subject": "Code from Photo",
                        "hours": 0.0,
                        "note": f"Question: {text[:150]}... | Code: {explanation}"
                    }
                    logs = get_user_data("study_logs")
                    logs.append(log)
                    upsert_user_data("study_logs", {"logs": json.dumps(logs)})
                    st.success("Code generated and saved to logs!")

                except Exception as e:
                    st.error("Tesseract OCR is not available on the cloud version.")
                    st.info("Here are some example codes you can use for demonstration:")

                    st.subheader("Example 1: Sum of List")
                    st.code("""
def sum_of_list(numbers):
    return sum(numbers)

nums = [1, 2, 3, 4, 5]
print(sum_of_list(nums))  # 15
                    """, language="python")

                    st.subheader("Example 2: Check Prime")
                    st.code("""
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

print(is_prime(17))  # True
                    """, language="python")

# =================================================================

# Footer
st.sidebar.markdown("---")
st.sidebar.write("Built for You — Keep grinding!")