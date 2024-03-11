import boto3

# Create a DynamoDB client using Boto3
dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')

# Define table name
table_name = 'ChatMessages'

# Create the DynamoDB table
try:
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'chatroom_id',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'timestamp',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'chatroom_id',
                'AttributeType': 'S' 
            },
            {
                'AttributeName': 'timestamp',
                'AttributeType': 'S' 
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5, # could be edited later needs testing
            'WriteCapacityUnits': 5
        }
    )
    # Wait for the table to be created
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    print(f"Table {table_name} created successfully.")
except Exception as e:
    print(f"Error creating table: {str(e)}")
