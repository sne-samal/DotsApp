import tkinter as tk
import tkinter.font as tkFont
import PIL as pil
import PIL.ImageTk as ptk

picDir = "C:/Users/snesa/Desktop/info-proc-labs/project/dotsappp.png" # CHANGE THIS TO YOUR DIRECTORY

class ChatRoom:
    def __init__(self, root):
        root.title("DotsApp")
        
        width=712
        height=600
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)

        # Frame for chat log 
        chat_frame = tk.Frame(root)
        chat_frame.place(x=0, y=0, width=440, height=520)

        # Chat log
        self.chat_log = tk.Text(chat_frame, bg="#ffffff", fg="#333333", font=tkFont.Font(size=12), wrap=tk.WORD)
        self.chat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.chat_log.config(state=tk.DISABLED)

        # Scroll bar
        scrollbar = tk.Scrollbar(root, command=self.chat_log.yview)
        scrollbar.place(x=440,y=0,width=20,height=520)
        self.chat_log.config(yscrollcommand=scrollbar.set)
        
        # Input label
        self.input_label=tk.Label(root)
        self.input_label["bg"] = "#ffffff"
        self.input_label["borderwidth"] = 2
        self.input_label["relief"] = "solid"
        ft = tkFont.Font(size=16)
        self.input_label["font"] = ft
        self.input_label["fg"] = "#333333"
        self.input_label["justify"] = "center"
        self.input_label["text"] = ""
        self.input_label.place(x=0,y=550,width=460,height=45)

        # Room label
        room_label=tk.Label(root)
        room_label["bg"] = "#1e9fff"
        room_label["fg"] = "#ffffff"
        ft = tkFont.Font(size=14)
        room_label["font"] = ft
        room_label["justify"] = "left"
        room_label["text"] = "Room: "
        room_label.place(x=0,y=520,width=460,height=30)

        # Open image 
        pic = pil.Image.open(picDir)
        # aspect_ratio = pic.width / pic.height
        new_width = 250
        # new_height = int(new_width / aspect_ratio)
        new_height = 595
        pic = pic.resize((new_width, new_height), pil.LANCZOS)
        self.photo = ptk.PhotoImage(pic)

        # Image label
        image_label=tk.Label(root)
        image_label["image"] = self.photo
        image_label.place(x=460,y=0,width=new_width,height=595)

    def setText(self, text):
        self.input_label.config(text=text)
        
    def setRoom(self, room_number):
        self.room_label.config(text=("Room: "+str(room_number)))
        
    def getText(self):
        return self.input_label.cget("text")

    def sendMessage(self, message):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.insert(tk.END, message + "\n")
        self.chat_log.config(state=tk.DISABLED)
    
    def clearLogs(self):
        self.chat_log.config(state=tk.NORMAL)
        self.chat_log.delete(1.0, tk.END)
        self.chat_log.config(state=tk.DISABLED)
        
        
""" root = tk.Tk()
chat_room = ChatRoom(root)
chat_room.sendMessage("Hello, world!\n" * 200)
root.mainloop() """
