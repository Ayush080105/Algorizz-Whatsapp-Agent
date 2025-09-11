import streamlit as st
import csv
import os
from daily_task_morning import send_morning_message
from daily_task_evening import send_evening_messages
from groupReader import update_csv
from summarize_and_send import summarize_conversations_and_send

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

def load_admin():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_admin(name):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        f.write(name.strip())

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="WhatsApp Automation", layout="centered")
st.title("📱 WhatsApp Task Automation")

# ----------------- Admin Setup -----------------
st.subheader("👤 Admin Setup")

current_admin = load_admin()
admin_name = st.text_input("Enter Admin Name:", value=current_admin)

if st.button("💾 Save Admin"):
    if admin_name.strip():
        save_admin(admin_name)
        st.success(f"✅ Admin set to: {admin_name}")
    else:
        st.warning("Please enter a valid admin name.")

# ----------------- Group Setup -----------------
st.subheader("👥 Manage Groups")

groups = load_groups()

# Add group input
new_group = st.text_input("Enter a new group name:")
if st.button("➕ Add Group"):
    if new_group.strip():
        groups.append(new_group.strip())
        save_groups(groups)
        st.success(f"Group '{new_group}' added!")
    else:
        st.warning("Please enter a valid group name.")

# Remove group input
if groups:
    remove_group = st.selectbox("Select a group to remove:", groups)
    if st.button("❌ Remove Group"):
        groups = [g for g in groups if g != remove_group]
        save_groups(groups)
        st.success(f"Group '{remove_group}' removed!")

# Show existing groups
if groups:
    st.subheader("📋 Your Groups")
    st.write(groups)
else:
    st.info("No groups added yet.")

# ----------------- Automation Tasks -----------------
st.subheader("⚡ Run Automation Tasks")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    if st.button("🔄 Update Conversations"):
        update_csv(CSV_PATH)
        st.success("✅ Conversations updated!")

with col2:
    if st.button("🌅 Send Morning Messages"):
        send_morning_message()
        st.success("✅ Morning messages sent!")

with col3:
    if st.button("🌆 Send Evening Messages"):
        send_evening_messages()
        st.success("✅ Evening messages sent!")

with col4:
    if st.button("📝 Summarize & Send"):
        summarize_conversations_and_send()
        st.success("✅ Summaries sent to admin!")
