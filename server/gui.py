from tkinter import *
import BasicSAServer

root = Tk()
root.title("Server")
root.geometry("640x400+100+100")

SARound = ["SetUp", "AdvertiseKeys", "ShareKeys", "MaskedInputCollection", "Unmasking"]
func = [BasicSAServer.setUp, BasicSAServer.advertiseKeys, BasicSAServer.shareKeys, BasicSAServer.maskedInputCollection, BasicSAServer.unmasking]
btn = []

for i, round in enumerate(SARound):
    btn.append(Button(root, text=round, command=func[i]))
    btn[i].pack()

root.mainloop()
