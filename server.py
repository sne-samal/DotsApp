import threading
import socket
import re
host = ''
port = 12000
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()
nSwitches = 4
clients = []
for i in range(0, 2**nSwitches):
    clients.append([])

class ClientInfo:
    def __init__(self, alias, client, room):
        self.client = client
        self.alias = alias
        self.room = room
    def change_room(self, new_room):
        self.room = new_room

def parse_room_switch(message):
    # Regular expression to match the pattern "#### room: x" where x is an integer
    match = re.match(r'^#### room: (\d+)$', message)
    if match:
        # If the pattern matches, extract the room number
        room_number = int(match.group(1))
        return True, room_number
    else:
        # If the pattern does not match, return False and -1
        return False, -1

def broadcast(message, room):
    # in case check length of list (people in room)
    for client in clients[room]:
        client.send(message)

def handle_client(clientObj):
    while True:
        room = clientObj.room
        try:
            message = clientObj.client.recv(1024)
            change, newRoom = parse_room_switch(message)
            if(change):
                disconnect(clientObj.client, newRoom)
            else:
                message = f'{clientObj.alias}: {message}'
                broadcast(message, room)
            # add function to move rooms, remove from current room and place in a different one
        except:
            disconnect(clientObj, "NULL")
            break

def disconnect(clientObj, newRoom):
    currentRoom = clientObj.room
    clients[currentRoom].remove(clientObj.client)
    alias = clientObj.alias
    broadcast(f'{alias} has left the chat room!'.encode('utf-8'))
    
    if(newRoom!="NULL"):
        clientObj.change_room(newRoom)
        clients[newRoom].append(clientObj.client)
        broadcast(f'{alias} has joined chat room {newRoom}!'.encode('utf-8'))
    else:
        clientObj.client.close()

def receive():
    while True:
        print('Server is running and listening ...')
        client, address = server.accept()
        print(f'connection is established with {str(address)}')
        client.send('alias?'.encode('utf-8'))
        alias = client.recv(1024)
        client.send('room?'.encode('utf-8'))
        room = int(client.recv(1024))
        clientObj = ClientInfo(alias, client, room)
        clients[room].append(clientObj)
        print(f'The alias of this client is {alias}'.encode('utf-8'))
        broadcast(f'{alias} has connected to chat room {room}'.encode('utf-8'), room)
        client.send('you are now connected!'.encode('utf-8'))
        thread = threading.Thread(target=handle_client, args=(clientObj,))
        thread.start()


if __name__ == "__main__":
    receive()
