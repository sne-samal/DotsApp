from pgpy import PGPKey, PGPMessage, PGPUID
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm
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
    def __init__(self, host, port, openpgp_key_path):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.openpgp_key_path = openpgp_key_path
        self.partner_ecdh_public_key = None
        self.shared_key = None
        self.server_DHReady = False
        try:
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"Error connecting to server: {e}")
            exit()

        self.check_openpgp_key_pair()
        self.ecdh_private_key = x25519.X25519PrivateKey.generate()
        self.ecdh_public_key = self.ecdh_private_key.public_key()

        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        self.send_commands()

    def check_openpgp_key_pair(self):
        if not os.path.exists(self.openpgp_key_path):
            print("OpenPGP key pair not found. Generating a new key pair...")
            key = PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, 4096)
            uid = PGPUID.new('Client', comment='Client Key')
            key.add_uid(uid, usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                    hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512, HashAlgorithm.SHA224],
                    ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
                    compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP, CompressionAlgorithm.Uncompressed])
            with open(self.openpgp_key_path, 'w') as f:
                f.write(str(key))
            print(f"New OpenPGP key pair generated and saved to {self.openpgp_key_path}")

    def listen_for_messages(self):
        while True:
            try:
                message = self.socket.recv(4096)
                if message.startswith(b"/ecdh_key"):
                    partner_pgp_key_ascii = input("Please paste the partner's PGP public key:\n")
                    self.verify_ecdh(message, partner_pgp_key_ascii)
                    self.generate_shared_key()
                    self.socket.send("/secure".encode('utf-8'))
                elif message.startswith(b"/serverBroadcast"):
                    print(message.decode('utf-8'))
                elif message.startswith(b"/serverReady"):
                    print("Server is now ready for DH key exchange")
                    self.server_DHReady = True
                    self.send_ecdh_key_and_signature()
                else:
                    if self.shared_key:
                        plaintext = self.receive_encrypted_message(message)
                        if plaintext:
                            print(f"Decrypted message: {plaintext}")
            except Exception as e:
                print(f"Error: {e}")
                self.socket.close()
                break

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
                    while not self.server_DHReady:
                        try:
                            self.socket.settimeout(1)  # Set a timeout for the socket
                            response = self.socket.recv(1024).decode('utf-8')
                            if response:
                                if response.startswith("UserID"):
                                    print(response)
                                    break
                                elif response.startswith("/serverReady"):
                                    self.server_DHReady = True
                        except socket.timeout:
                            pass  # No response received within the timeout
                        except OSError as e:
                            print(f"Error: {e}")
                            print("Connection closed by the server.")
                            raise  # Re-raise the exception to be caught by the outer try-except block
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

    def send_ecdh_key_and_signature(self):
        public_key_bytes = self.ecdh_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        signature = self.sign_data(public_key_bytes)
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        self.socket.send(f"/ecdh_key {public_key_b64} {signature_b64}".encode('utf-8'))

    def verify_ecdh(self, incoming_message, partner_pgp_key_ascii):
        try:
            _, partner_public_key_b64, signature_b64 = incoming_message.split(b' ', 2)
            partner_public_key_bytes = base64.b64decode(partner_public_key_b64)
            signature_bytes = base64.b64decode(signature_b64)

            partner_pgp_key = PGPKey()
            partner_pgp_key.parse(partner_pgp_key_ascii)

            message = PGPMessage.new(partner_public_key_bytes, file=True)

            if partner_pgp_key.verify(message, signature=signature_bytes):
                self.partner_ecdh_public_key = x25519.X25519PublicKey.from_public_bytes(partner_public_key_bytes)
                print("Signature verified successfully.")
                return True
            else:
                print("Failed to verify signature.")
                return False
        except Exception as e:
            print(f"An error occurred during signature verification: {e}")
            return False

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

    def sign_data(self, data):
        with open(self.openpgp_key_path, 'r') as f:
            private_key, _ = PGPKey.from_blob(f.read())
        message = PGPMessage.new(data)
        signature = private_key.sign(message)
        return bytes(signature)

if __name__ == "__main__":
    HOST = '3.10.53.32'
    PORT = 1492
    OPENPGP_KEY_PATH = "openpgp_key_pair.asc"
    client = Client(HOST, PORT, OPENPGP_KEY_PATH)
