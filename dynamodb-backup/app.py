import boto3
import json
import os
import datetime
import s3fs


Region = os.environ['Region']
BucketName = os.environ['BucketName']
BackupEnabledTag = os.environ['BackupEnabledTag']
UseDataPipelineFormat = os.environ['UseDataPipelineFormat'].lower() == 'true'


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

# def parse_list(l):
#     for attributeValue in l:

def parse_attribute(attribute): # e.g. {"type": "value"}


def parse_item(item):
    # for reference on all attribute types:
    # https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_AttributeValue.html
    if UseDataPipelineFormat:
        response = {}
        for attribute in item.keys():
            response[attribute] = {}
            if 'B' in item[attribute]: # binary e.g. {"B": "dGhpcyB0ZXh0IGlzIGJhc2U2NC1lbmNvZGVk"}
                response[attribute]['b'] = parse_attribute(item_attribute)# item[attribute]['B'].decode('ascii')
            elif 'BOOL' in item[attribute]: # boolean e.g. {"BOOL": true}
                response[attribute]['bOOL'] = item[attribute]['BOOL']
            elif 'BS' in item[attribute]: # binary set e.g. {"BS": ["U3Vubnk=", "UmFpbnk=", "U25vd3k="]}
                binaryset = []
                for value in item[attribute]['BS']:
                    binaryset.append(value.decode('ascii'))
                response[attribute]['bS'] = binaryset
            elif 'L' in item[attribute]: # list e.g. {"L": [ {"S": "Cookies"} , {"S": "Coffee"}, {"N", "3.14159"}]}
                l = []
                for nestedItem in item[attribute]['L']:
                    l.append(parse_item(nestedItem))
                response[attribute]['l'] = l
            elif 'M' in item[attribute]: # map e.g. {"M": {"Name": {"S": "Joe"}, "Age": {"N": "35"}}}
                response[attribute]['m'] = parse_item(item[attribute]['M'])
            elif 'N' in item[attribute]: # number e.g. {"N": "123.45"}
                response[attribute]['n'] = item[attribute]['N']
            elif 'NS' in item[attribute]: # number set e.g. {"NS": ["42.2", "-19", "7.5", "3.14"]}
                response[attribute]['nS'] = item[attribute]['NS']
            elif 'NULL' in item[attribute]: # e.g. {"NULL": true}
                response[attribute]['nULLValue'] = item[attribute]['NULL']
            elif 'S' in item[attribute]: # string e.g. {"S": "Hello"}
                response[attribute]['s'] = item[attribute]['S']
            elif 'SS' in item[attribute]: # string set e.g. {"SS": ["Giraffe", "Hippo" ,"Zebra"]}
                response[attribute]['sS'] = item[attribute]['SS']
            else:
                print(f"ERROR: unrecognised attribute type {json.dumps(item[attribute])}")
                # pass # should raise exception
        return response
    else:
        # just manipulate original item object
        for attribute in item.keys():
            if 'M' in item[attribute]:
                item[attribute]['M'] = parse_item(item[attribute]['M'])
            if 'L' in item[attribute]:
                l = []
                for nestedItem in item[attribute]['L']:
                    l.append(parse_item(nestedItem))
                item[attribute]['L'] = l
            if 'B' in item[attribute]:
                item[attribute]['B'] = item[attribute]['B'].decode('ascii')
            if 'BS' in item[attribute]:
                binaryset = []
                for value in item[attribute]['BS']:
                    binaryset.append(value.decode('ascii'))
                item[attribute]['BS'] = binaryset
    return item


def backup_table(bucket_path, table_name, frequency):
    print("Backing up table " + table_name)
    client = boto3.client("dynamodb", region_name=Region)

    backup_table_config(client, bucket_path, table_name)

    # paginate dynamo table contents and write to S3 object
    paginator = client.get_paginator('scan')
    page_iterator = paginator.paginate(TableName=table_name, Select='ALL_ATTRIBUTES', ConsistentRead=True, PaginationConfig={'PageSize': 100})
    fs = s3fs.S3FileSystem()
    s3_path = f'{BucketName}/{bucket_path}/{table_name}-{frequency}.json'
    with fs.open(s3_path, 'w') as f:
        for page in page_iterator:
            for item in page['Items']:
                item = parse_item(item)
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
                bucket_path = dt.strftime('%Y-%m-%d/%H.%M.%S') # formats to '2020-12-31/23.59.59'
                backup_table(bucket_path, event["table_name"], frequency)
    else:
        raise Exception("An 'action' is missing from this invocations payload")

                


    

    

    



