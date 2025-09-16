import tkinter as tk
from tkinter import messagebox, simpledialog, Listbox, END
import threading
import csv
import os

from groupReader import update_csv
from daily_task_morning import send_morning_message
from daily_task_evening import send_evening_messages
from summarize_and_send import summarize_conversations_and_send


# ----------------- Paths -----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))  # works for exe and script
CSV_PATH = os.path.join(BASE_PATH, "group_convo.csv")
ADMIN_FILE = os.path.join(BASE_PATH, "admin.txt")


# ----------------- File Init -----------------
def ensure_files():
    # Create admin.txt if missing
    if not os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "w", encoding="utf-8") as f:
            f.write("DefaultAdmin")

    # Create group_convo.csv if missing
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["groupName", "Conversation"])
            writer.writeheader()


# ----------------- Helpers -----------------
def run_in_thread(func):
    threading.Thread(target=func, daemon=True).start()


def load_admin():
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_admin(name):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        f.write(name)


def load_groups():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["groupName"] for row in reader]


def save_groups(group_list):
    """Save groups while preserving existing conversations"""
    existing = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["groupName"]] = row.get("Conversation", "[]")

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["groupName", "Conversation"])
        writer.writeheader()
        for group in group_list:
            writer.writerow({
                "groupName": group,
                "Conversation": existing.get(group, "[]")  # keep old convo if present
            })


# ----------------- UI Functions -----------------
def update_admin():
    new_name = simpledialog.askstring("Update Admin", "Enter new admin name:")
    if new_name:
        save_admin(new_name)
        admin_label.config(text=f"Admin: {new_name}")
        messagebox.showinfo("Success", "Admin updated!")


def refresh_group_list():
    group_listbox.delete(0, END)
    for g in load_groups():
        group_listbox.insert(END, g)


def add_group():
    new_group = simpledialog.askstring("Add Group", "Enter group name:")
    if new_group:
        groups = load_groups()
        if new_group in groups:
            messagebox.showwarning("Warning", "Group already exists!")
            return
        groups.append(new_group)
        save_groups(groups)
        refresh_group_list()
        messagebox.showinfo("Success", f"Group '{new_group}' added.")


def delete_group():
    selection = group_listbox.curselection()
    if not selection:
        messagebox.showwarning("Warning", "No group selected!")
        return
    group_name = group_listbox.get(selection[0])
    groups = load_groups()
    groups = [g for g in groups if g != group_name]
    save_groups(groups)
    refresh_group_list()
    messagebox.showinfo("Deleted", f"Group '{group_name}' removed.")


# ----------------- Tkinter Root -----------------
ensure_files()  # make sure admin.txt + group_convo.csv exist

root = tk.Tk()
root.title("Algorizz Whatsapp Agent")
root.geometry("500x500")

# ----------- Admin Section -----------
admin_name = load_admin()
admin_label = tk.Label(root, text=f"Admin: {admin_name}", font=("Arial", 12))
admin_label.pack(pady=10)

update_admin_btn = tk.Button(root, text="Update Admin", command=update_admin)
update_admin_btn.pack(pady=5)

# ----------- Group Management -----------
tk.Label(root, text="Groups:", font=("Arial", 12)).pack(pady=5)

group_listbox = Listbox(root, width=50, height=8)
group_listbox.pack(pady=5)

refresh_group_list()

tk.Button(root, text="Add Group", command=add_group).pack(pady=5)
tk.Button(root, text="Delete Group", command=delete_group).pack(pady=5)

# ----------- Automation Tasks -----------
tk.Label(root, text="Automation Tasks:", font=("Arial", 12)).pack(pady=10)

btn1 = tk.Button(root, text="Run Group Reader", width=30, command=lambda: run_in_thread(update_csv))
btn1.pack(pady=3)

btn2 = tk.Button(root, text="Run Daily Morning Message", width=30, command=lambda: run_in_thread(send_morning_message))
btn2.pack(pady=3)

btn3 = tk.Button(root, text="Run Daily Evening Message", width=30, command=lambda: run_in_thread(send_evening_messages))
btn3.pack(pady=3)

btn4 = tk.Button(root, text="Run Summarize & Send", width=30, command=lambda: run_in_thread(summarize_conversations_and_send))
btn4.pack(pady=3)

exit_btn = tk.Button(root, text="Exit", width=30, command=root.quit, bg="red", fg="white")
exit_btn.pack(pady=20)

root.mainloop()
