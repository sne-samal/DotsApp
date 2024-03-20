from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import socket
import threading
import base64
import os
import sys
import subprocess
import re
import tkinter as tk
from gui2 import ChatRoom

gui_ready = threading.Event()

# separate gui thread
def start_gui():
    root = tk.Tk()
    global chat_room
    chat_room = ChatRoom(root)
    gui_ready.set()
    root.mainloop()

gui_thread = threading.Thread(target=start_gui)
gui_thread.start()

gui_ready.wait() 


# Nios 2 stuff
NIOS_CMD_SHELL_BAT = "C:/intelFPGA_lite/18.1/nios2eds/Nios II Command Shell.bat"

currentMessage = ""
room = 0

# updates input label
def print_curr_msg(text):
    global chat_room
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
    global chat_room
    room = newRoom
    client.send_commands(f'/join {room}'.encode('utf-8'))
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
        print("debug: " + currentMessage)
        client.send_commands(currentMessage)

        currentMessage = ""
        print_curr_msg(currentMessage)
    elif (str == 'Fullstop'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '.'
            print_curr_msg(currentMessage)
    elif (str == 'Comma'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += ','
            print_curr_msg(currentMessage)
    elif (str == 'Exclamation'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '!'
            print_curr_msg(currentMessage)
    elif (str == 'Question'):
        if(check_final_character_not_morse(currentMessage)):
            currentMessage += '?'
            print_curr_msg(currentMessage)
    else: 
        pass

class Client:
    def __init__(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.partner_ecdh_public_key = None
        self.shared_key = None
        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"Error connecting to server: {e}")
            exit()

        self.ecdh_private_key = x25519.X25519PrivateKey.generate()
        self.ecdh_public_key = self.ecdh_private_key.public_key()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
    
    
        try:
            process = subprocess.Popen(
                NIOS_CMD_SHELL_BAT,
                bufsize=0,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True)
            
            process.stdin.write(f"nios2-terminal.exe\n")
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
        except KeyboardInterrupt:
            # Handle abrupt client closure
            print("\nExiting gracefully...")
            #quit


    def listen_for_messages(self,):
        while True:
            try:
                message = self.socket.recv(4096)
                self.handle_incoming_message(message)
            except Exception as e:
                print(f"Error: {e}")

    def handle_incoming_message(self, message):
        if message.startswith(b"/ecdh_key"):
            print("[CLIENT] Received ECDH key")
            self.receive_ecdh_key(message)
            self.generate_shared_key()
            self.socket.send("/secure".encode('utf-8'))
        elif message.startswith(b"/serverBroadcast"):
            print(self.parse_server_broadcast(message))
        elif message.startswith(b"/ready"):
            print("[CLIENT] Received server ready message")
            self.send_ecdh_key()
        else:
            if self.shared_key:
                print("[CLIENT] Received encrypted message", message)
                plaintext = self.receive_encrypted_message(message)
                if plaintext:
                    print(f"[CLIENT] Decrypted message: {plaintext}")
            else:
                print("[CLIENT] Received unexpected message:", message)
    def parse_server_broadcast(self, message_bytes):
        prefix = b"/serverBroadcast "
        
        if message_bytes.startswith(prefix):
            actual_message = message_bytes[len(prefix):]
            
            actual_message_str = actual_message.decode('utf-8')
            
            # Format the message as required
            formatted_message = f"[SERVER] {actual_message_str}"
            
            return formatted_message
        else:
            return "Message does not start with the required command prefix."
    def send_commands(self, message):
        print("Connected to the server. Type '/join [userID]' to start chatting with someone.")
        # message = input("")
        if message.startswith("/join"):
            self.shared_key = None
            self.partner_ecdh_public_key = None
            try:
                self.socket.send(message.encode('utf-8'))
            except OSError as e:
                print(f"Error: {e}")
                print("Connection closed by the server.")
        elif message.startswith("/") or (message and self.shared_key):
            if self.shared_key:
                self.send_encrypted_message(message)
            else:
                try:
                    self.socket.send(message.encode('utf-8'))
                except OSError as e:
                    print(f"Error: {e}")
                    print("Connection closed by the server.")

    def send_ecdh_key(self):
        public_key_bytes = self.ecdh_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')
        self.socket.send(f"/ecdh_key {public_key_b64}".encode('utf-8'))

    def receive_ecdh_key(self, incoming_message):
        try:
            _, partner_public_key_b64 = incoming_message.split(b' ', 1)
            partner_public_key_bytes = base64.b64decode(partner_public_key_b64)
            self.partner_ecdh_public_key = x25519.X25519PublicKey.from_public_bytes(partner_public_key_bytes)
        except Exception as e:
            print(f"An error occurred while receiving ECDH key: {e}")

    def generate_shared_key(self):
        if self.partner_ecdh_public_key is None:
            print("Partner's public key not set. Cannot generate shared key.")
            return None

        shared_secret = self.ecdh_private_key.exchange(self.partner_ecdh_public_key)
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'handshake data',
        ).derive(shared_secret)

        self.shared_key = derived_key

    def encrypt_message(self, key, plaintext):
        try:
            iv = os.urandom(12)
            encryptor = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            ).encryptor()
            ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
            return (ciphertext, iv, encryptor.tag)
        except Exception as e:
            print(f"Error during encryption: {e}")
            return None

    def decrypt_message(self, key, ciphertext, iv, tag):
        try:
            decryptor = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=default_backend()
            ).decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e:
            print(f"Error during decryption: {e}")
            return None

    def send_encrypted_message(self, message):
        ciphertext, iv, tag = self.encrypt_message(self.shared_key, message)
        # Prefix each part with its length
        encrypted_message = len(ciphertext).to_bytes(4, 'big') + ciphertext \
                            + len(iv).to_bytes(4, 'big') + iv \
                            + len(tag).to_bytes(4, 'big') + tag
        self.socket.send(encrypted_message)
        print("[CLIENT] Sending encrypted message: ", encrypted_message)

    def receive_encrypted_message(self, encrypted_message):
        try:
            # Extract each part by reading its length first
            iv_start = 4 + int.from_bytes(encrypted_message[:4], 'big')
            tag_start = iv_start + 4 + int.from_bytes(encrypted_message[iv_start:iv_start+4], 'big')
            ciphertext = encrypted_message[4:iv_start]
            iv = encrypted_message[iv_start+4:tag_start]
            tag = encrypted_message[tag_start+4:]
            plaintext = self.decrypt_message(self.shared_key, ciphertext, iv, tag)
            return plaintext.decode('utf-8')
        except Exception as e:
            print(f"Error during decryption: {e}")
            return None



if __name__ == "__main__":
    global client
    HOST = '18.169.194.20'
    PORT = 1492
    client = Client(HOST, PORT)










