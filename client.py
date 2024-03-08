import socket
import threading
import sys
import subprocess
import re

# Server's IP address
# If the server is not on this machine,
# put the private (network) or public (internet) IP address
SERVER_HOST = '18.133.73.205'  # The server's hostname or IP address
SERVER_PORT = 1492 

# Nios 2 stuff
NIOS_CMD_SHELL_BAT = "your_nios_cmd_shell_bat_command_here"
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

currentMessage = ""
room = 0

def parse_room_number(text):
    match = re.search(r"New room number: (\d+)", text)
    if match:
        return int(match.group(1))  # Convert the matched number to an integer
    else:
        return -1  # Return -1 if there's no match


def morse_to_text(input_str):
    # Morse code mapping for single characters
    morse_code_dict = {
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
        '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
        '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
        '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
        '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
        '--..': 'Z'
    }
    
    for i in range(len(input_str) - 1, -1, -1):
        if input_str[i].isalpha():
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

def ParseNios2(str):
    global currentMessage
    global send
    perhaps_room = parse_room_number(str)
    if (str == 'Dot'):
        currentMessage += '.'
        print(currentMessage)
    elif (str == 'Dash'):
        currentMessage += '-'
        print(currentMessage)
    elif (perhaps_room > -1):
        change_room(perhaps_room)
    elif (str == 'MORSE_BACKSPACE'):
        if (len(currentMessage) > 0):
            if (currentMessage[-1] == '.' or '-'):
                currentMessage = currentMessage[:-1]
                print(currentMessage)
    elif (str == 'ENGLISH_WORD_SPACE'):
        currentMessage += ' '
        print(currentMessage)
    elif (str == 'ENGLISH_CHARACTER_BACKSPACE'): 
        if (len(currentMessage) > 0):
            if (currentMessage[-1].isalpha()):
                currentMessage = currentMessage[:-1]
                print(currentMessage)
    elif (str == 'CONFIRM_ENGLISH_LETTER'):
            currentMessage  = morse_to_text(currentMessage)
            print(currentMessage)
    elif (str == 'Send'):
        send = True
    else: 
        pass


def receive_messages():
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            print(message)
        except Exception as e:
            # Any error in receiving data implies the connection is closed
            print("Disconnected from the server.")
            client_socket.close()
            break

# Thread for receiving messages
receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()

try:
    # process = subprocess.Popen(
    #   NIOS_CMD_SHELL_BAT,
    #   bufsize=0,
    #   stdin=subprocess.PIPE,
    #   stdout=subprocess.PIPE,
    #   universal_newlines=True)
    
    # process.stdin.write(f"nios2-terminal.exe --cable 1\n")
    # process.stdin.flush()  # Flush the input buffer

    while True:
        #line = process.stdout.readline()
        line = input()
        if not line:  # End of file reached
            break
        else:
            ParseNios2(line.strip())  # Print the line (remove trailing newline)
        if "nios2-terminal: exiting due to ^D on remote" in line:
            break
        if send:
            client_socket.send(currentMessage.encode('utf-8'))
            send = False
            currentMessage = ''
except KeyboardInterrupt:
    # Handle abrupt client closure
    print("\nExiting gracefully...")
finally:
    # Close socket on any exit
    client_socket.close()

