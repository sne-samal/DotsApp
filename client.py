import threading
import socket
# add a text box somewhere to initialise the username 
alias = input('Choose an alias >>> ')
# need to figure out how room initialisation works 
room = 0
# probably query the FPGA on initialisation for the value 
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('', ))
currentMessage = ""


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


def build_message():
    while True:
        # retreive input data 
        currentMessage = ""
        # send to GUI display, update label 

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