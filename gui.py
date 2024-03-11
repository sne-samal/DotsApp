import tkinter as tk

class ChatRoom:
    def __init__(self, master):
        self.master = master
        master.title("Chat Room")

        # Frame to hold chat log, scrollbar, and input box
        self.frame = tk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Chat log
        self.chat_log = tk.Text(self.frame, wrap="word", width=50, height=20)
        self.chat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.chat_log.config(state=tk.DISABLED)

        # Add scrollbar
        scrollbar = tk.Scrollbar(self.frame, command=self.chat_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_log.config(yscrollcommand=scrollbar.set)

        # Input box
        self.input_label = tk.Label(master, text="", width=50, wraplength=400)
        self.input_label.pack(side=tk.BOTTOM)

        # Room display
        self.room_label = tk.Label(master, text="Room: ", bg="lightblue", fg="black")
        self.room_label.pack(side=tk.TOP, anchor='nw')

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



# root = tk.Tk()
# chat_room = ChatRoom(root)
# chat_room.setText("Input message")
# chat_room.sendMessage("Hello, world!\n" * 20)
# print("Got message: "+chat_room.getText())
# root.mainloop()

