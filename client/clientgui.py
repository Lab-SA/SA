from tkinter import *
import BasicSAClient as sac

root = Tk()
root.title("Client")
root.geometry("640x400+100+100")

SARound = ["SetUp", "AdvertiseKeys", "ShareKeys", "MaskedInputCollection", "Unmasking"]
func = [sac.setUp, sac.advertiseKeys, sac.shareKeys, sac.MaskedInputCollection, sac.Unmasking]
btn = []
for i, round in enumerate(SARound):
    btn.append(Button(root, text = round, command = func[i]))
    btn[i].pack()

root.mainloop()
