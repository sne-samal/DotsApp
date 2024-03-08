import socket
import threading
import sys

# Server's IP address
# If the server is not on this machine,
# put the private (network) or public (internet) IP address
SERVER_HOST = '18.133.73.205'  # The server's hostname or IP address
SERVER_PORT = 1492 

# Initialize socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
try:
    client_socket.connect((SERVER_HOST, SERVER_PORT))
except ConnectionRefusedError:
    print("Failed to connect to the server")
    sys.exit()

print(f"Connected to the server at {SERVER_HOST}:{SERVER_PORT}")

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
    while True:
        # Input command or message
        message = input('')
        # Send message to the server
        if message:
            client_socket.send(message.encode('utf-8'))
        if message == '/quit':
            break
except KeyboardInterrupt:
    # Handle abrupt client closure
    print("\nExiting gracefully...")
finally:
    # Close socket on any exit
    client_socket.close()

