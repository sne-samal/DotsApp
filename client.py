import socket
import threading
import sys
import subprocess
import re
import tkinter as tk
from gui2 import ChatRoom

# separate gui thread
def start_gui():
    root = tk.Tk()
    global chat_room
    chat_room = ChatRoom(root)
    root.mainloop()

gui_thread = threading.Thread(target=start_gui)
gui_thread.start()

# Server's IP address
# If the server is not on this machine,
# put the private (network) or public (internet) IP address
SERVER_HOST = '18.133.73.205'  # The server's hostname or IP address
SERVER_PORT = 1492 

# Nios 2 stuff
NIOS_CMD_SHELL_BAT = "C:/intelFPGA_lite/18.1/nios2eds/Nios II Command Shell.bat"
send = False

# Initialize socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
try:
    client_socket.connect((SERVER_HOST, SERVER_PORT))
except ConnectionRefusedError:
    print("Failed to connect to the server")
    sys.exit()

print(f"Connected to the server at {SERVER_HOST}:{SERVER_PORT}")
print(r"""#######################################################
#                                                     #
#                                                     #
#      ____        _            _                     #
#     |  _ \  ___ | |_ ___     / \   _ __  _ __       #
#     | | | |/ _ \| __/ __|   / _ \ | '_ \| '_ \      #
#     | |_| | (_) | |_\__ \  / ___ \| |_) | |_) |     #
#     |____/ \___/ \__|___/ /_/   \_\ .__/| .__/      #
#                                   |_|   |_|         #
#                                                     #
#                                                     #
#######################################################
#######################################################
#                                                     #
#     CLIENT: 1                                       #
#                                                     #
#     USE:                                            #
#     Left Tilt:            Morse Backspace           #
#     Right Tilt:           Send English Letter       #
#     Forward Tilt:         English Letter Space      #
#     Bakward Tilt:         English Letter Space      #
#                                                     #
#######################################################
      """)


currentMessage = ""
room = 0

# updates input label
def print_curr_msg(text):
    message_to_display = f'{text}\n(Toggle SW9 to send!)'
    #if chat_room:  # check for chatroom
    chat_room.input_label.config(text=message_to_display) 
    #else:
        #print(message_to_display) 

def parse_room_number(text):
    match = re.search(r"New room number: (\d+)", text)
    if match:
        new_room = int(match.group(1))  # Convert the matched number to an integer
        #change_room(new_room)
        return new_room
    else:
        return -1  # Return -1 if there's no match
    
def check_final_character_not_morse(str):
    if not str:
        return True
    
    # Get the last character of the string
    last_char = str[-1]
    
    # Check if the last character is not an asterisk or a dash
    return last_char not in ['*', '-']


def morse_to_text(input_str):
    # Morse code mapping for single characters
    morse_code_dict = {
    '*-': 'A', '-***': 'B', '-*-*': 'C', '-**': 'D', '*': 'E',
    '**-*': 'F', '--*': 'G', '****': 'H', '**': 'I', '*---': 'J',
    '-*-': 'K', '*-**': 'L', '--': 'M', '-*': 'N', '---': 'O',
    '*--*': 'P', '--*-': 'Q', '*-*': 'R', '***': 'S', '-': 'T',
    '**-': 'U', '***-': 'V', '*--': 'W', '-**-': 'X', '-*--': 'Y',
    '--**': 'Z',
    '-----': '0', '*----': '1', '**---': '2', '***--': '3', '****-': '4',
    '*****': '5', '-****': '6', '--***': '7', '---**': '8', '----*': '9'
    }
    
    for i in range(len(input_str) - 1, -1, -1):
        if (input_str[i].isalpha() or input_str[i] == ' '):
            plaintext_part = input_str[:i+1]
            morse_part = input_str[i+1:]
            break
    else:
        # In case the entire string is Morse code
        plaintext_part = ''
        morse_part = input_str
    
    # Convert Morse code part to text
    morse_character = morse_code_dict.get(morse_part, '')

    # Concatenate and return the result
    return plaintext_part + morse_character

def change_room(newRoom):
    global room
    room = newRoom
    client_socket.send(f'/join {room}'.encode('utf-8'))
    #if chat_room: # updates room display
    #chat_room.setRoom(room)
    chat_room.clearLogs()

def ParseNios2(str):
    global currentMessage
    global send
    perhaps_room = parse_room_number(str)
    if (str == 'Dot'):
        currentMessage += '*'
        print_curr_msg(currentMessage)
    elif (str == 'Dash'):
        currentMessage += '-'
        print_curr_msg(currentMessage)
    elif (perhaps_room > -1):
        change_room(perhaps_room)
    elif (str == 'MORSE_BACKSPACE'):
        if (len(currentMessage) > 0):
            if (currentMessage[-1] == '*' or '-'):
                currentMessage = currentMessage[:-1]
                print_curr_msg(currentMessage)
    elif (str == 'ENGLISH_WORD_SPACE'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += ' '
            print_curr_msg(currentMessage)
    elif (str == 'ENGLISH_CHARACTER_BACKSPACE'): 
        if (len(currentMessage) > 0):
            if (check_final_character_not_morse(currentMessage)):
                currentMessage = currentMessage[:-1]
                print_curr_msg(currentMessage)
    elif (str == 'CONFIRM_ENGLISH_CHARACTER'):
            currentMessage  = morse_to_text(currentMessage)
            print_curr_msg(currentMessage)
    elif (str == 'Send'): #updates chat log
        send = True
        #if chat_room:  # check for chat room then .after used to update chat log
        #chat_room.chat_log.after(0, lambda: chat_room.sendMessage(currentMessage))
    elif (str == 'Fullstop'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '.'
    elif (str == 'Comma'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += ','
    elif (str == 'Exclamation'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '!'
    elif (str == 'Question'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '?'
    else: 
        pass

# updates chat log
def receive_messages():
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            #if chat_room:  # check for chat room
            chat_room.chat_log.after(0, lambda m=message: chat_room.sendMessage(m))
        except Exception as e:
            # Any error in receiving data implies the connection is closed
            print(f"Disconnected from the server: {e}")
            client_socket.close()
            # exit()
            # break
            return 

# Thread for receiving messages
receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()

try:
    process = subprocess.Popen(
        NIOS_CMD_SHELL_BAT,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True)
    
    process.stdin.write(f"nios2-terminal.exe --cable 1\n")
    process.stdin.flush()  # Flush the input buffer

    while True:
        line = process.stdout.readline()
        if not line:  # End of file reached
            break
        else:
            ParseNios2(line.strip())  # Print the line (remove trailing newline)
        if "nios2-terminal: exiting due to ^D on remote" in line:
            exit 
            # quit
            
        if send:
            client_socket.send(currentMessage.encode('utf-8'))
            print("sent.")
            send = False
            currentMessage = ''
except KeyboardInterrupt:
    # Handle abrupt client closure
    print("\nExiting gracefully...")
    #quit
finally:
    # Close socket on any exit
    client_socket.close()
    exit

