import streamlit as st
import csv
import os

CSV_PATH = "group_convo.csv"
ADMIN_FILE = "admin.txt"

# ----------------- Helpers -----------------
def load_groups():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["groupName"] for row in reader]

def save_groups(group_list):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["groupName", "Conversation"])
        for g in group_list:
            writer.writerow([g, "[]"])  # empty JSON array string

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="WhatsApp Automation", layout="centered")
st.title("📱 WhatsApp Task Automation")

# Load groups
groups = load_groups()

# ----------------- Admin Setup -----------------
st.subheader("👤 Admin Setup")

current_admin = ""
if os.path.exists(ADMIN_FILE):
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        current_admin = f.read().strip()

admin_name = st.text_input("Enter Admin Name:", value=current_admin)

if st.button("💾 Save Admin"):
    if admin_name.strip():
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            f.write(admin_name.strip())
        st.success(f"✅ Admin set to: {admin_name}")
    else:
        st.warning("Please enter a valid admin name.")

# ----------------- Group Setup -----------------
st.subheader("➕ Manage Groups")
new_group = st.text_input("Enter a new group name:")
if st.button("➕ Add Group"):
    if new_group.strip():
        groups.append(new_group.strip())
        save_groups(groups)
        st.success(f"Group '{new_group}' added!")
    else:
        st.warning("Please enter a valid group name.")

remove_group = st.selectbox("Select a group to remove:", [""] + groups)
if st.button("❌ Remove Group"):
    if remove_group and remove_group in groups:
        groups.remove(remove_group)
        save_groups(groups)
        st.success(f"Group '{remove_group}' removed!")

if groups:
    st.subheader("📋 Your Groups")
    st.write(groups)
else:
    st.info("No groups added yet.")

# ----------------- Automation Buttons -----------------
st.subheader("⚡ Run Automation Tasks")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    if st.button("🔄 Update Conversations"):
        try:
            from groupReader import update_csv
            update_csv(CSV_PATH)
            st.success("✅ Conversations updated!")
        except Exception as e:
            st.error(f"❌ Failed: {e}")

with col2:
    if st.button("🌅 Send Morning Messages"):
        try:
            from daily_task_morning import send_morning_message
            send_morning_message()
            st.success("✅ Morning messages sent!")
        except Exception as e:
            st.error(f"❌ Failed: {e}")

with col3:
    if st.button("🌆 Send Evening Messages"):
        try:
            from daily_task_evening import send_evening_messages
            send_evening_messages()
            st.success("✅ Evening messages sent!")
        except Exception as e:
            st.error(f"❌ Failed: {e}")

with col4:
    if st.button("📝 Summarize & Send"):
        try:
            from summarize_and_send import summarize_conversations_and_send
            summarize_conversations_and_send()
            st.success("✅ Summary sent to Admin!")
        except Exception as e:
            st.error(f"❌ Failed: {e}")
