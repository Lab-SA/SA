from tkinter import *
from BasicSAClient import BasicSAClient

root = Tk()
root.title("Client")
root.geometry("640x400+100+100")

client = BasicSAClient()
SARound = ["SetUp", "AdvertiseKeys", "ShareKeys", "MaskedInputCollection", "Unmasking"]
func = [client.setUp, client.advertiseKeys, client.shareKeys, client.MaskedInputCollection, client.Unmasking]
btn = []
for i, round in enumerate(SARound):
    btn.append(Button(root, text = round, command = func[i]))
    btn[i].pack()

root.mainloop()
