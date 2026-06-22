import tkinter as tk
from tkinter import messagebox
from utils import RE_ANY_TAG, RE_STRIP
from db import session

class Editor:
    def __init__(self, parent, state):
        self.state = state

        self.text = tk.Text(parent)
        self.text.pack(fill="both", expand=True)

        self.text.tag_config("tagged", background="lightyellow")
        self.text.bind("<<Modified>>", self.on_change)

    def on_change(self, event):
        if self.text.edit_modified():
            self.state.unsaved_changes = True

        self.text.edit_modified(False)

    def load(self, memory):
        self.text.unbind("<<Modified>>")
    
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, memory.text or "")
    
        
        self.highlight()
        
        self.state.unsaved_changes = False
        self.text.edit_modified(False)
        
        if hasattr(self.state, "metadata_panel"):
            self.state.metadata_panel.refresh()
        
        return True

    def save(self):
        m = self.state.current_memory
        if not m:
            return

        txt = self.text.get("1.0", tk.END)
        m.text = txt

        if m.file_path:
            with open(m.file_path, "w", encoding="utf-8") as f:
                f.write(txt)

        session.commit()
        self.state.unsaved_changes = False

    def highlight(self):
        self.text.tag_remove("tagged", "1.0", tk.END)
        data = self.text.get("1.0", tk.END)

        for m in RE_ANY_TAG.finditer(data):
            self.text.tag_add("tagged",
                f"1.0+{m.start(1)}c",
                f"1.0+{m.end(1)}c")

    def add_tag(self, field, cho):
        import tkinter as tk
        from tkinter import messagebox
    
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
    
            if not cho:
                messagebox.showerror("Error", "No CHO specified")
                return
    
            if not field:
                messagebox.showerror("Error", "No metadata field selected")
                return
    
            tagged = f'<{field} cho="{cho}">{sel}</{field}>'
    
            self.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.text.insert(tk.INSERT, tagged)
    
            self.highlight()
    
        except tk.TclError:
            messagebox.showerror("Error", "Select text first")


    def remove_tag(self):
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            clean = RE_STRIP.sub("", sel)

            self.text.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.text.insert(tk.INSERT, clean)

            self.highlight()
        except:
            pass