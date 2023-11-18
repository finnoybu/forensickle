import tkinter as tk
from tkinter import ttk

from utilities import user


is_admin = user.is_admin()
print("is_admin: {}".format(is_admin))


# root = tk.Tk()
# frm = ttk.Frame(root, padding=10)
# frm.grid()
# ttk.Label(frm, text="Hello World!").grid(column=0, row=0)
# ttk.Button(frm, text="Quit", command=root.destroy).grid(column=1, row=0)
# root.mainloop()