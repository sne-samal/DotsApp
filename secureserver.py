import socket
import select
import time

HOST = '0.0.0.0'
PORT = 1492

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

sockets_list = [server_socket]
clients = {}
userID_counter = 0

def receive_message(client_socket):
    try:
        message = client_socket.recv(4096)
        return message
    except Exception as e:
        print(f"Error receiving message from {client_socket}: {e}")
        return None

def handle_new_connection():
    client_socket, client_address = server_socket.accept()
    global userID_counter
    userID_counter += 1
    userID = userID_counter
    clients[client_socket] = {"userID": userID, "session_secure": False, "partner_socket": None, "ready_for_secure": False}
    sockets_list.append(client_socket)
    print(f"[SERVER] Accepted new connection from {client_address} with userID {userID}")
    send_server_message(client_socket, f"Welcome! Your userID is {userID}")

def disconnect_client(client_socket):
    sockets_list.remove(client_socket)
    client_socket.close()
    partner_socket = clients[client_socket]["partner_socket"]
    if partner_socket:
        if clients[partner_socket]["session_secure"]:
            try:
                send_server_message(partner_socket, "Your chat partner has disconnected.")
            except OSError as e:
                print(f"Error sending message to partner socket: {e}")
        clients[partner_socket]["partner_socket"] = None
        clients[partner_socket]["ready_for_secure"] = False
        clients[partner_socket]["session_secure"] = False
    del clients[client_socket]

def send_server_message(client_socket, message):
    client_socket.send(f"/serverBroadcast {message}".encode('utf-8'))

def relay_messages(notified_socket, message):
    if message:
        if b"/join" in message:
            try:
                _, target_userID = message.decode().split()
                target_userID = int(target_userID)
                target_socket = None
                for sock, info in clients.items():
                    if info["userID"] == target_userID:
                        target_socket = sock
                        break
                if target_socket:
                    clients[notified_socket]["partner_socket"] = target_socket
                    clients[target_socket]["partner_socket"] = notified_socket
                    send_server_message(notified_socket, f"Chat initiated with userID {target_userID}.")
                    send_server_message(target_socket, f"Chat requested by userID {clients[notified_socket]['userID']}.")
                    print(f"[SERVER] Chat initiated between userID {clients[notified_socket]['userID']} and userID {target_userID}")
                    notified_socket.send(b"/ready")
                    time.sleep(1)
                    target_socket.send(b"/ready")
                    time.sleep(1)
                else:
                    send_server_message(notified_socket, f"UserID {target_userID} does not exist.")
            except ValueError:
                send_server_message(notified_socket, "Invalid userID format.")
        elif b"/ecdh_key" in message:
            partner_socket = clients[notified_socket]["partner_socket"]
            if partner_socket:
                try:
                    ecdh_key = message.split(b' ', 1)[1]
                    partner_socket.send(b"/ecdh_key " + ecdh_key)
                    print(f"[SERVER] Relayed ECDH key from userID {clients[notified_socket]['userID']} to userID {clients[partner_socket]['userID']}")
                except OSError as e:
                    print(f"Error sending message to partner socket: {e}")
        elif b"/secure" in message:
            clients[notified_socket]["session_secure"] = True
            print(f"[SERVER] Received /secure from userID {clients[notified_socket]['userID']}")
            partner_socket = clients[notified_socket]["partner_socket"]
            if partner_socket and clients[partner_socket]["session_secure"]:
                print(f"[SERVER] Secure session established between userID {clients[notified_socket]['userID']} and userID {clients[partner_socket]['userID']}")
                send_server_message(notified_socket, "Secure session established. You can now start chatting!")
                send_server_message(partner_socket, "Secure session established. You can now start chatting!")
        else:
            partner_socket = clients[notified_socket]["partner_socket"]
            if partner_socket and clients[notified_socket].get("session_secure"):
                try:
                    print(f"[SERVER] Relaying encrypted message from userID {clients[notified_socket]['userID']}: {message}")
                    partner_socket.send(message)
                    print(f"[SERVER] Relayed encrypted message to userID {clients[partner_socket]['userID']}")
                except OSError as e:
                    print(f"Error sending message to partner socket: {e}")

while True:
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

    for notified_socket in read_sockets:
        if notified_socket == server_socket:
            handle_new_connection()
        else:
            message = receive_message(notified_socket)
            if message:
                relay_messages(notified_socket, message)
            else:
                disconnect_client(notified_socket)

    for notified_socket in exception_sockets:
        if notified_socket in clients:
            disconnect_client(notified_socket)
