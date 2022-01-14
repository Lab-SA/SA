from tkinter import *

root = Tk()
root.title("Client")
root.geometry("640x400+100+100")

setupBtn = Button(root, text="Setup")
Round0Btn = Button(root, text="AdvertiseKeys")
Round1Btn = Button(root, text="ShareKeys")
Round2Btn = Button(root, text="MaskedInputCollection")
Round4Btn = Button(root, text="Unmasking")

setupBtn.pack()
Round0Btn.pack()
Round1Btn.pack()
Round2Btn.pack()
Round4Btn.pack()

root.mainloop()
