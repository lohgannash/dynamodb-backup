import boto3
import json
import os
import datetime
import s3fs


Region = os.environ['Region']
BucketName = os.environ['BucketName']
BackupEnabledTag = os.environ['BackupEnabledTag']




def get_dynamodb_tables(client):
    paginator = client.get_paginator('list_tables')
    page_iterator = paginator.paginate(PaginationConfig={'PageSize': 100})
    table_names = []
    for page in page_iterator:
        table_names.extend(page['TableNames'])
    return table_names

def filter_tables(client, table_names):
    filtered_table_names = []
    for table_name in table_names:
        resp = client.describe_table(TableName=table_name)
        table_arn = resp['Table']['TableArn']
        resp = client.list_tags_of_resource(ResourceArn=table_arn)
        tags = resp['Tags']
        for tag in tags:
            if tag['Key'] == BackupEnabledTag:
                if tag['Value'].upper() == 'TRUE':
                    filtered_table_names.append(table_name)
                    break
    return filtered_table_names

def backup_table_config(client, bucket_path, table_name):
    response  = client.describe_table(TableName=table_name)
    fs = s3fs.S3FileSystem()
    s3_path = "{0}/{1}{2}-Configuration.json".format(BucketName, bucket_path, table_name)
    #    with fs.open(s3_path, 'w') as f:
    #        f.write(json.dumps(response))
    print(response)

def parse_data(data):
    for key in data.keys():
        if 'M' in data[key]:
            data[key]['M'] = parse_data(data[key]['M'])
        if 'B' in data[key]:
            data[key]['B'] = data[key]['B'].decode('ascii')
        if 'BS' in data[key]:
            binaryset = []
            for value in data[key]['BS']:
                binaryset.append(value.decode('ascii'))
            data[key]['BS'] = binaryset
    return data


def backup_table(bucket_path, table_name, frequency):
    print("Backing up table " + table_name)
    client = boto3.client("dynamodb", region_name=Region)

    backup_table_config(client, bucket_path, table_name)
    


    # paginate dynamo table contents and write to S3 object
    paginator = client.get_paginator('scan')
    page_iterator = paginator.paginate(TableName=table_name, Select='ALL_ATTRIBUTES', ConsistentRead=True, PaginationConfig={'PageSize': 100})
    fs = s3fs.S3FileSystem()
    s3_path = "{0}/{1}{2}-{3}.json".format(BucketName, bucket_path, table_name, frequency)
    with fs.open(s3_path, 'w') as f:
        for page in page_iterator:
            for item in page['Items']:
                item = parse_data(item)
                f.write(json.dumps(item) + "\n")
    print("Backup complete")
    print("Adding tags to backup")

    # tag newly created S3 Object
    tags = {}
    tags["TableName"] = table_name
    if frequency != None:
        tags["Frequency"] = frequency
    fs.put_tags(s3_path, tags)
    print("Tags added")
    

def invoke_lambda(client, arn, event={}):
    print(f"Invoking lambda: {arn} with event: {json.dumps(event)}")
    response = client.invoke(FunctionName=arn, InvocationType="Event", Payload=json.dumps(event))
    print(f"Response: {response}")


def create_backups(frequency, arn):
    ddb_client = boto3.client("dynamodb", region_name=Region)
    lambda_client = boto3.client("lambda", region_name=Region)

    tables = get_dynamodb_tables(ddb_client)
    tables = filter_tables(ddb_client, tables)

    for table in tables:
        event = {}
        event["action"] = "backup-table"
        event["table_name"] = table
        event["frequency"] = frequency
        invoke_lambda(lambda_client, arn, event)


def lambda_handler(event, context):
    dt = datetime.datetime.utcnow()
    frequency = None
    if "frequency" in event:
        frequency = event["frequency"]

    if "action" in event:
        if event["action"] == "create-backups":
            create_backups(frequency, context.invoked_function_arn)

        if event["action"] == "backup-table":
            if "table_name" in event:
                bucket_path = "{0}/{1}/{2}/{3}/{4}/".format(dt.year, dt.month, dt.day, dt.hour, dt.minute)
                backup_table(bucket_path, event["table_name"], frequency)
    else:
        raise Exception("An 'action' is missing from this invocations payload")

                


    

    

    



