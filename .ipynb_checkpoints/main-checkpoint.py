import tkinter as tk
from tkinter import ttk, filedialog

from database import session
from models import CHO, Memory
from utils import extract_metadata

# ------------------------------
# MAIN WINDOW
# ------------------------------
root = tk.Tk()
root.title("CORDHISK App")
root.geometry("1200x600")

# ------------------------------
# LAYOUT (3 PANELS)
# ------------------------------
left_frame = tk.Frame(root, width=250, bg="lightgray")
left_frame.pack(side="left", fill="y")

middle_frame = tk.Frame(root, width=250, bg="white")
middle_frame.pack(side="left", fill="y")

right_frame = tk.Frame(root)
right_frame.pack(side="right", expand=True, fill="both")

# ------------------------------
# LEFT PANEL (CHOs)
# ------------------------------
tk.Label(left_frame, text="Cultural Heritage Objects").pack()

cho_listbox = tk.Listbox(left_frame)
cho_listbox.pack(fill="both", expand=True)

cho_entry = tk.Entry(left_frame)
cho_entry.pack()

def create_cho():
    title = cho_entry.get()
    if title:
        new = CHO(title=title)
        session.add(new)
        session.commit()
        cho_entry.delete(0, tk.END)
        load_chos()

tk.Button(left_frame, text="Add CHO", command=create_cho).pack()

def load_chos():
    cho_listbox.delete(0, tk.END)
    for cho in session.query(CHO).all():
        cho_listbox.insert(tk.END, f"{cho.id} - {cho.title}")

# ------------------------------
# MIDDLE PANEL (MEMORIES)
# ------------------------------
tk.Label(middle_frame, text="Memories").pack()

memory_listbox = tk.Listbox(middle_frame)
memory_listbox.pack(fill="both", expand=True)

def on_cho_select(event):
    selection = cho_listbox.get(tk.ACTIVE)
    if not selection:
        return

    cho_id = int(selection.split(" - ")[0])

    memory_listbox.delete(0, tk.END)

    memories = session.query(Memory).filter_by(cho_id=cho_id).all()

    for mem in memories:
        memory_listbox.insert(tk.END, f"{mem.id} - {mem.title}")

cho_listbox.bind("<<ListboxSelect>>", on_cho_select)

# ------------------------------
# RIGHT PANEL (TEXT EDITOR)
# ------------------------------
tk.Label(right_frame, text="Memory Editor").pack()

text_box = tk.Text(right_frame, wrap="word")
text_box.pack(expand=True, fill="both")

def on_memory_select(event):
    selection = memory_listbox.get(tk.ACTIVE)
    if not selection:
        return

    memory_id = int(selection.split(" - ")[0])
    memory = session.get(Memory, memory_id)

    text_box.delete("1.0", tk.END)
    text_box.insert(tk.END, memory.text)

memory_listbox.bind("<<ListboxSelect>>", on_memory_select)

# ------------------------------
# IMPORT / SAVE
# ------------------------------
def import_txt():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, "r") as f:
            content = f.read()
            text_box.delete("1.0", tk.END)
            text_box.insert(tk.END, content)

def save_memory():
    cho_sel = cho_listbox.get(tk.ACTIVE)
    if not cho_sel:
        print("Please select a CHO first")
        return

    cho_id = int(cho_sel.split(" - ")[0])
    content = text_box.get("1.0", tk.END)

    memory = Memory(title="Memory", text=content, cho_id=cho_id)
    session.add(memory)
    session.commit()

    on_cho_select(None)

# ------------------------------
# TAGGING
# ------------------------------
field_var = tk.StringVar(value="dc:description")

dropdown = tk.OptionMenu(
    right_frame,
    field_var,
    "dc:title",
    "dc:description",
    "dc:creator",
    "dcterms:spatial",
    "dcterms:temporal"
)
dropdown.pack()

def add_tag():
    try:
        selected_text = text_box.get(tk.SEL_FIRST, tk.SEL_LAST)
        tag = field_var.get()

        tagged_text = f"<{tag}>{selected_text}</{tag}>"

        text_box.delete(tk.SEL_FIRST, tk.SEL_LAST)
        text_box.insert(tk.INSERT, tagged_text)

    except:
        print("No text selected")

# ------------------------------
# METADATA VIEW
# ------------------------------
def view_metadata():
    text = text_box.get("1.0", tk.END)
    metadata = extract_metadata(text)

    win = tk.Toplevel()
    win.title("Metadata")

    tree = ttk.Treeview(win, columns=("Field", "Value"), show="headings")
    tree.heading("Field", text="EDM Field")
    tree.heading("Value", text="Value")

    tree.pack(expand=True, fill="both")

    for field, values in metadata.items():
        for val in values:
            tree.insert("", "end", values=(field, val))

# ------------------------------
# BUTTONS (RIGHT PANEL)
# ------------------------------
buttons_frame = tk.Frame(right_frame)
buttons_frame.pack()

tk.Button(buttons_frame, text="Import TXT", command=import_txt).grid(row=0, column=0)
tk.Button(buttons_frame, text="Save Memory", command=save_memory).grid(row=0, column=1)
tk.Button(buttons_frame, text="Add Tag", command=add_tag).grid(row=0, column=2)
tk.Button(buttons_frame, text="View Metadata", command=view_metadata).grid(row=0, column=3)

# ------------------------------
# INITIAL LOAD
# ------------------------------
load_chos()

# ------------------------------
# RUN APP
# ------------------------------
root.mainloop()