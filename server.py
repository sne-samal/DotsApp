import threading
import socket
host = ''
port = 12000
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()
nSwitches = 4
clients = []
aliases = []
for i in range(0, 2**nSwitches):
    clients.append([])
    aliases.append([])


def broadcast(message, room):
    # in case check length of list (people in room)
    for client in clients[room]:
        client.send(message)

def handle_client(client, room):
    while True:
        try:
            message = client.recv(1024)
            broadcast(message, room)
            # add function to move rooms, remove from current room and place in a different one
        except:
            disconnect(client, room, "NULL")
            break

def disconnect(client, currentRoom, newRoom):
    index = clients[currentRoom].index(client)
    clients[currentRoom].remove(client)
    alias = aliases[currentRoom][index]
    broadcast(f'{alias} has left the chat room!'.encode('utf-8'))
    aliases[currentRoom].remove(alias)
    
    if(newRoom!="NULL"):
        print()
    else:
        client.close()

def receive():
    while True:
        print('Server is running and listening ...')
        client, address = server.accept()
        print(f'connection is established with {str(address)}')
        client.send('alias?'.encode('utf-8'))
        alias = client.recv(1024)
        client.send('room?'.encode('utf-8'))
        room = client.recv(1024)
        aliases[room].append(alias)
        clients[room].append(client)
        print(f'The alias of this client is {alias}'.encode('utf-8'))
        broadcast(f'{alias} has connected to chat room {room}'.encode('utf-8'), room)
        client.send('you are now connected!'.encode('utf-8'))
        thread = threading.Thread(target=handle_client, args=(client,room,))
        thread.start()


if __name__ == "__main__":
    receive()
