from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import socket
import threading
import base64
import os

class Client:
    def __init__(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.partner_ecdh_public_key = None
        self.shared_key = None
        self.server_DHReady = False
        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"Error connecting to server: {e}")
            exit()

        self.ecdh_private_key = x25519.X25519PrivateKey.generate()
        self.ecdh_public_key = self.ecdh_private_key.public_key()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        self.send_commands()

    def listen_for_messages(self):
        while True:
            try:
                message = self.socket.recv(4096)
                self.handle_incoming_message(message)
            except Exception as e:
                print(f"Error: {e}")
                self.socket.close()
                break

    def handle_incoming_message(self, message):
        print("Received message:", message)

        if message.startswith(b"/ecdh_key"):
            print("Received ECDH key")
            self.receive_ecdh_key(message)
            self.generate_shared_key()
            self.socket.send("/secure".encode('utf-8'))
        elif message.startswith(b"/serverBroadcast"):
            print("Received server broadcast")
            print(message.decode('utf-8'))
        elif message.startswith(b"/serverReady"):
            print("Received server ready")
            print("Server is now ready for DH key exchange")
            self.server_DHReady = True
            self.send_ecdh_key()
        elif message.startswith(b"Secure session established"):
            print("Received secure session established message")
            print(message.decode('utf-8'))
        else:
            if self.shared_key:
                print("Received encrypted message:", message)
            else:
                print("Received unexpected message:", message.decode('utf-8'))
                
    def send_commands(self):
        print("Connected to the server. Type '/join [userID]' to start chatting with someone.")
        while True:
            message = input("")
            if message.startswith("/join"):
                self.server_DHReady = False
                self.shared_key = None
                self.partner_ecdh_public_key = None
                try:
                    self.socket.send(message.encode('utf-8'))
                    # Wait for the server's response without blocking
                    retries = 0
                    max_retries = 5
                    while not self.server_DHReady:
                        try:
                            self.socket.settimeout(5)  # Set a timeout of 5 seconds
                            response = self.socket.recv(1024).decode('utf-8')
                            if response:
                                if response.startswith("UserID"):
                                    print(response)
                                    break
                                elif response.startswith("/serverReady"):
                                    self.server_DHReady = True
                        except socket.timeout:
                            retries += 1
                            if retries >= max_retries:
                                print("Error: Timeout waiting for server response. Retrying...")
                                self.socket.send(message.encode('utf-8'))  # Resend the join message
                                retries = 0
                        except OSError as e:
                            print(f"Error: {e}")
                            print("Connection closed by the server.")
                            raise  # Re-raise the exception to be caught by the outer try-except block
                    else:
                        self.send_ecdh_key()
                except OSError as e:
                    print(f"Error: {e}")
                    print("Connection closed by the server.")
                    break  # Exit the loop if the connection is closed
            elif message.startswith("/") or (message and self.shared_key):
                if self.shared_key:
                    self.send_encrypted_message(message)
                else:
                    try:
                        self.socket.send(message.encode('utf-8'))
                    except OSError as e:
                        print(f"Error: {e}")
                        print("Connection closed by the server.")
                        break  # Exit the loop if the connection is closed

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
        encrypted_message = ciphertext + b':' + iv + b':' + tag
        self.socket.send(encrypted_message)

    def receive_encrypted_message(self, encrypted_message):
        ciphertext, iv, tag = encrypted_message.split(b':')
        plaintext = self.decrypt_message(self.shared_key, ciphertext, iv, tag)
        return plaintext.decode('utf-8')

if __name__ == "__main__":
    HOST = '3.8.28.231'
    PORT = 1492
    client = Client(HOST, PORT)
