import socket
import select
import random
import string
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

HOST = '0.0.0.0'
PORT = 1492

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

sockets_list = [server_socket]
clients = {}  # client_socket: {"alias": alias, "current_chatroom": "0"}
chatrooms = {str(i): [] for i in range(4)}  # Initializes chatrooms "0", "1", "2", "3"

def save_message(chatroom_id, timestamp, message, alias):
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')

    # Specify the table name
    table_name = 'ChatMessages'
    table = dynamodb.Table(table_name)

    try:
        response = table.put_item(
            Item={
                'chatroom_id': chatroom_id,
                'timestamp': timestamp,
                'message': message,
                'alias': alias
            }
        )
        print(f"Message saved successfully in chatroom {chatroom_id}.")
        return response
    except ClientError as e:
        print(f"An error occurred: {e.response['Error']['Message']}")
        return None
    
def query_and_broadcast_saved_chats(client_socket, chatroom_id):
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')

    # Specify the table name
    table_name = 'ChatMessages'
    table = dynamodb.Table(table_name)

    try:
        # Query DynamoDB for messages in the specified chatroom
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('chatroom_id').eq(chatroom_id),
            ScanIndexForward=True  # Ensures messages are returned in ascending timestamp order
        )

        # Check if messages exist
        if 'Items' in response and response['Items']:
            # Iterate over each message and send it to the newly joined user
            for item in response['Items']:
                # Format the message as "[timestamp] alias: message"
                formatted_message = f"[{item['timestamp']}] {item['alias']}: {item['message']}"
                client_socket.send(formatted_message.encode('utf-8'))
        else:
            # No messages found, notify the user
            no_messages_message = "No previous messages in this chatroom."
            client_socket.send(no_messages_message.encode('utf-8'))
    except ClientError as e:
        print(f"An error occurred while querying messages: {e.response['Error']['Message']}")
        error_message = "Could not retrieve previous messages due to an error."
        client_socket.send(error_message.encode('utf-8'))

def send_message_to_clients(message, chatroom_name):
    for client_socket in chatrooms[chatroom_name]:
        try:
            client_socket.send(message.encode('utf-8'))
        except:
            remove_client(client_socket)

def broadcast(message, chatroom_name, sender_socket, is_join_message=False):
    sender_alias = clients[sender_socket]["alias"] if sender_socket in clients else "Server"
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if is_join_message:
        # Format join messages as statements instead of regular chat messages
        formatted_message = f"System: {message}"
    else:
        formatted_message = f"[{time_stamp}] {sender_alias}: {message}"
        save_message(chatroom_name, time_stamp, message, sender_alias)

    print(f"[{chatroom_name}] {formatted_message}")  # Logs message on server console
    send_message_to_clients(formatted_message, chatroom_name)  # Corrected line


def handle_client_message(client_socket, message):
    if message.startswith('/join') and len(message.split()) > 1:
        _, chatroom_name = message.split(maxsplit=1)
        if chatroom_name in chatrooms:
            prev_chatroom = clients[client_socket]["current_chatroom"]
            if prev_chatroom in chatrooms:  # Check if the previous chatroom exists
                chatrooms[prev_chatroom].remove(client_socket)
            chatrooms[chatroom_name].append(client_socket)
            clients[client_socket]["current_chatroom"] = chatroom_name

            # Broadcast as a join statement
            join_message = f"{clients[client_socket]['alias']} has joined chatroom {chatroom_name}."
            broadcast(join_message, chatroom_name, client_socket, is_join_message=True)
            query_and_broadcast_saved_chats(client_socket, chatroom_name)
        else:
            client_socket.send(f"Chatroom {chatroom_name} does not exist.\n".encode('utf-8'))
    else:
        if clients[client_socket]["current_chatroom"]:
            broadcast(message, clients[client_socket]["current_chatroom"], client_socket)

        else:
            client_socket.send("You must join a chatroom to send messages.\n".encode('utf-8'))

def remove_client(client_socket):
    if client_socket in sockets_list:
        sockets_list.remove(client_socket)
    if client_socket in clients:
        chatroom = clients[client_socket]["current_chatroom"]
        if chatroom:
            chatrooms[chatroom].remove(client_socket)
            print(f"{clients[client_socket]['alias']} has left the chatroom {chatroom}.")
        del clients[client_socket]
    client_socket.close()

def generate_random_alias():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

print(f"Listening for connections on {HOST}:{PORT}...")

while True:
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)
    for notified_socket in read_sockets:
        if notified_socket == server_socket:
            client_socket, client_address = server_socket.accept()
            alias = generate_random_alias()
            clients[client_socket] = {"alias": alias, "current_chatroom": "0"}
            chatrooms["0"].append(client_socket)
            sockets_list.append(client_socket)
            print(f"New connection from {client_address[0]}:{client_address[1]} assigned alias {alias} and joined chatroom 0")
            welcome_message = "Welcome! You have been automatically added to chatroom '0'. Use '/join <chatroom_number>' to switch chatrooms.\n"
            client_socket.send(welcome_message.encode('utf-8'))
            query_and_broadcast_saved_chats(client_socket, "0")
        else:
            try:
                message = notified_socket.recv(1024).decode('utf-8').strip()
                if message:
                    handle_client_message(notified_socket, message)
                else:
                    raise Exception("Client disconnected")
            except Exception as e:
                print(f"Error: {e} - Client disconnected.")
                remove_client(notified_socket)

    for notified_socket in exception_sockets:
        remove_client(notified_socket)
