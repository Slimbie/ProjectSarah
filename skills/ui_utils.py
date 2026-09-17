import tkinter as tk


def show_notification(title: str, message: str):
    """Klein pop-upvenster met een boodschap en een OK-knop."""
    root = tk.Tk()
    root.title(title)
    root.geometry("280x130")
    root.attributes("-topmost", True)

    label = tk.Label(root, text=message, font=("Sans", 13), wraplength=250, justify="center")
    label.pack(pady=15, padx=10)

    ok_button = tk.Button(root, text="OK", command=root.destroy)
    ok_button.pack(pady=5)

    root.mainloop()