import tkinter as tk
from tkinter import ttk, font
from scrape import get_episodes

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("The Chosen episode downloader")  # Change the title here
        self.root.geometry("1280x720+640+360")  # Set the default size and position
        self.root.resizable(True, True)  # Make the window resizable

        # Create toolbar with the "Fetch Data" button
        self.create_toolbar()

        # Create main body with table
        self.create_table()

    def create_toolbar(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Fetch Data button
        self.button1 = tk.Button(toolbar, text="Fetch Data", command=self.on_button1_click)
        self.button1.pack(side=tk.LEFT, padx=5, pady=5)

    def create_table(self):
        columns = ("Season", "Episode", "Title", "Duration", "URL")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        self.tree.tag_configure('oddrow', background='lightgrey')
        self.tree.tag_configure('evenrow', background='white')
        for col in columns:
            self.tree.heading(col, text=col)
            if col in ["Season", "Episode"]:
                self.tree.column(col, anchor=tk.CENTER, width=font.Font().measure(col))
            elif col == "Duration":
                self.tree.column(col, anchor=tk.W, width=font.Font().measure("00:00"))
            else:
                self.tree.column(col, anchor=tk.W)

        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def on_button1_click(self):
        # Make request
        data = get_episodes()
        self.populate_table(data)
        self.auto_resize_window()

    def populate_table(self, data):
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Sort data by Season and Episode
        data.sort(key=lambda x: (x[1], x[2]))

        # Insert new data
        for index, item in enumerate(data):
            duration = self.format_duration(item[3])
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=(item[1], item[2], item[4], duration, item[0]), tags=(tag,))

    def format_duration(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}"

    def auto_resize_window(self):
        self.root.update_idletasks()
        width = self.tree.winfo_width()
        height = self.tree.winfo_height() + self.tree.winfo_rooty() - self.root.winfo_rooty()
        self.root.geometry(f"{width}x{height}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()