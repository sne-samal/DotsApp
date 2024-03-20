import tkinter as tk
from tkinter import scrolledtext
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import socket
import threading
import base64
import os
import re

class Client:
    def __init__(self, host, port, chat_window, input_label):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.partner_ecdh_public_key = None
        self.shared_key = None
        self.chat_window = chat_window
        self.input_label = input_label
        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"Error connecting to server: {e}")
            exit()

        self.ecdh_private_key = x25519.X25519PrivateKey.generate()
        self.ecdh_public_key = self.ecdh_private_key.public_key()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()

        self.current_message = ""
        self.room = 0

    def listen_for_messages(self):
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
            formatted_message = self.parse_server_broadcast(message)
            self.chat_window.config(state='normal')
            self.chat_window.insert(tk.END, formatted_message + "\n")
            self.chat_window.config(state='disabled')
        elif message.startswith(b"/ready"):
            print("[CLIENT] Received server ready message")
            self.send_ecdh_key()
        else:
            if self.shared_key:
                print("[CLIENT] Received encrypted message", message)
                plaintext = self.receive_encrypted_message(message)
                if plaintext:
                    self.chat_window.config(state='normal')
                    self.chat_window.insert(tk.END, f"[CLIENT] Decrypted message: {plaintext}\n")
                    self.chat_window.config(state='disabled')
            else:
                print("[CLIENT] Received unexpected message:", message)

    def parse_server_broadcast(self, message_bytes):
        prefix = b"/serverBroadcast "
        if message_bytes.startswith(prefix):
            actual_message = message_bytes[len(prefix):]
            actual_message_str = actual_message.decode('utf-8')
            formatted_message = f"[SERVER] {actual_message_str}"
            return formatted_message
        else:
            return "Message does not start with the required command prefix."

    def send_commands(self, message):
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

    def print_curr_msg(self, text):
        message_to_display = f'{text}\n(Toggle SW9 to send!)'
        self.input_label.config(text=message_to_display)

    def parse_room_number(self, text):
        match = re.search(r"New room number: (\d+)", text)
        if match:
            new_room = int(match.group(1))
            return new_room
        else:
            return -1

    def check_final_character_not_morse(self, str):
        if not str:
            return True
        last_char = str[-1]
        return last_char not in ['*', '-']

    def morse_to_text(self, input_str):
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
            plaintext_part = ''
            morse_part = input_str

        morse_character = morse_code_dict.get(morse_part, '')
        return plaintext_part + morse_character

    def change_room(self, newRoom):
        self.room = newRoom
        self.send_commands(f'/join {self.room}')
        self.chat_window.config(state='normal')
        self.chat_window.delete('1.0', tk.END)
        self.chat_window.config(state='disabled')

    def parse_nios2(self, str):
        perhaps_room = self.parse_room_number(str)
        if (str == 'Dot'):
            self.current_message += '*'
            self.print_curr_msg(self.current_message)
        elif (str == 'Dash'):
            self.current_message += '-'
            self.print_curr_msg(self.current_message)
        elif (perhaps_room > -1):
            self.change_room(perhaps_room)
        elif (str == 'MORSE_BACKSPACE'):
            if (len(self.current_message) > 0):
                if (self.current_message[-1] == '*' or '-'):
                    self.current_message = self.current_message[:-1]
                    self.print_curr_msg(self.current_message)
        elif (str == 'ENGLISH_WORD_SPACE'):
            if(self.check_final_character_not_morse(self.current_message)):
                self.current_message += ' '
                self.print_curr_msg(self.current_message)
        elif (str == 'ENGLISH_CHARACTER_BACKSPACE'):
            if (len(self.current_message) > 0):
                if (self.check_final_character_not_morse(self.current_message)):
                    self.current_message = self.current_message[:-1]
                    self.print_curr_msg(self.current_message)
        elif (str == 'CONFIRM_ENGLISH_CHARACTER'):
            self.current_message = self.morse_to_text(self.current_message)
            self.print_curr_msg(self.current_message)
        elif (str == 'Send'):
            print("debug: " + self.current_message)
            self.send_commands(self.current_message)
            self.current_message = ""
            self.print_curr_msg(self.current_message)
        elif (str == 'Fullstop'):
            if(self.check_final_character_not_morse(self.current_message)):
                self.current_message += '.'
                self.print_curr_msg(self.current_message)
        elif (str == 'Comma'):
            if(self.check_final_character_not_morse(self.current_message)):
                self.current_message += ','
                self.print_curr_msg(self.current_message)
        elif (str == 'Exclamation'):
            if(self.check_final_character_not_morse(self.current_message)):
                self.current_message += '!'
                self.print_curr_msg(self.current_message)
        elif (str == 'Question'):
            if(self.check_final_character_not_morse(self.current_message)):
                self.current_message += '?'
                self.print_curr_msg(self.current_message)
        else:
            pass

class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Chat App")
        self.geometry("400x400")

        self.chat_window = scrolledtext.ScrolledText(self, state='disabled')
        self.chat_window.pack(fill=tk.BOTH, expand=True)

        self.input_label = tk.Label(self, text="")
        self.input_label.pack()

        self.client = Client(HOST, PORT, self.chat_window, self.input_label)

    def start(self):
        self.mainloop()

if __name__ == "__main__":
    HOST = '18.169.194.20'
    PORT = 1492

    app = ChatApp()
    app.start()
