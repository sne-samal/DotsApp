import threading
import socket
import subprocess
import re


NIOS_CMD_SHELL_BAT = "your_nios_cmd_shell_bat_command_here"

# add a text box somewhere to initialise the username 
alias = input('Choose an alias >>> ')
# need to figure out how room initialisation works 
room = 0
# probably query the FPGA on initialisation for the value 
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('', ))

currentMessage = ""

def parse_room_number(text):
    match = re.search(r"New room number: (\d+)", text)
    if match:
        return int(match.group(1))  # Convert the matched number to an integer
    else:
        return -1  # Return -1 if there's no match


def client_receive():
    while True:
        try:
            message = client.recv(1024).decode('utf-8')
            if message == "alias?":
                client.send(alias.encode('utf-8'))
            elif message == "room?":
                client.send(str(room).encode('utf-8'))
            else:
                print(message)
        except:
            print('Error!')
            client.close()
            break

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

def ParseNios2(str):
    perhaps_room = parse_room_number(str)
    if (str == 'Dot'):
        currentMessage += '.'
    elif (str == 'Dash'):
        currentMessage += '-'
    elif (perhaps_room > -1):
        change_room(perhaps_room)
    elif (str == 'MORSE_BACKSPACE'):
        if (len(currentMessage) > 0):
            if (currentMessage[-1] == '.' or '-'):
                currentMessage = currentMessage[:-1]
    elif (str == 'ENGLISH_WORD_SPACE'):
        currentMessage += ' '
    elif (str == 'ENGLISH_CHARACTER_BACKSPACE'): 
        if (len(currentMessage) > 0):
            if (currentMessage[-1].isalpha()):
                currentMessage = currentMessage[:-1]
    elif (str == 'CONFIRM_ENGLISH_LETTER'):
            currentMessage  = morse_to_text(currentMessage)
    elif (str == 'Send'):
        #hhhhh
    else: 
        # error case
    


def build_message():
     # Send command to subprocess
    process = subprocess.Popen(
        NIOS_CMD_SHELL_BAT,
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True)
    
    process.stdin.write(f"nios2-terminal\n")
    process.stdin.flush()  # Flush the input buffer

    while True:
        line = process.stdout.readline()
        if not line:  # End of file reached
            break
        else:
            ParseNios2(line.strip())  # Print the line (remove trailing newline)
        if "nios2-terminal: exiting due to ^D on remote" in line:
            break


def client_send():
    while True:
        message = f'{currentMessage}'
        client.send(message.encode('utf-8'))

def change_room(newRoom):
    room = newRoom
    client.send((f'#### room: ({room})').encode('utf-8'))


receive_thread = threading.Thread(target=client_receive)
receive_thread.start()

send_thread = threading.Thread(target=client_send)
send_thread.start()

display_thread = threading.Thread(target=build_message)
display_thread.start()