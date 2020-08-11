# dynamodb-backup

This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- hello_world - Code for the application's Lambda function.
- events - Invocation events that you can use to invoke the function.
- tests - Unit tests for the application code. 
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions and an API Gateway API. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

If you prefer to use an integrated development environment (IDE) to build and test your application, you can use the AWS Toolkit.  
The AWS Toolkit is an open source plug-in for popular IDEs that uses the SAM CLI to build and deploy serverless applications on AWS. The AWS Toolkit also adds a simplified step-through debugging experience for Lambda function code. See the following links to get started.

* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [Visual Studio](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/welcome.html)

## Deploy the sample application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

You can find your API Gateway Endpoint URL in the output values displayed after deployment.

## Data Pipeline Format

The SAM template contains a parameter `UseDataPipelineFormat` which you can toggle to update the backup lambda's environment variable (also named `UseDataPipelineFormat`). If set to true then the backup lambda will output a backup file which can be used in the Data Pipeline job template `Import DynamoDB backup data from S3`. Refer to [step by step instructions from AWS Docs here](https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-importexport-ddb.html).

NOTE! From the AWS Docs (above):
> DynamoDB tables configured for On-Demand Capacity are supported only when using Amazon EMR release version 5.24.0 or later. When you use a template to create a pipeline for DynamoDB, choose Edit in Architect and then choose Resources to configure the Amazon EMR cluster that AWS Data Pipeline provisions. For Release label, choose emr-5.24.0 or later.


Also if `UseDataPipelineFormat` is set to `true` then the IAM policy `DataPipelineEbsKmsPolicy` will also be created.

This policy specifies additional permissions that may be required by the IAM role `DataPipelineDefaultRole`.
The `DataPipelineDefaultRole` role gets created for you automatically by Data Pipeline ([refer to AWS Docs here](https://docs.aws.amazon.com/datapipeline/latest/DeveloperGuide/dp-get-setup.html#dp-iam-roles-new)) and uses the `AWSDataPipelineRole` managed policy.

However if you have specified a default EBS encryption key in a region then the managed policy will not have sufficient permissions to run the Data Pipeline import (or export) job successfully. The `DataPipelineEbsKmsPolicy` in the SAM template contains the additional permissions required.

To check if your region is using a custom EBS encryption key you can run the [AWS CLI/API command](https://docs.aws.amazon.com/cli/latest/reference/ec2/get-ebs-default-kms-key-id.html) to find the ARN:

```bash
aws ec2 get-ebs-default-kms-key-id --region ap-southeast-2
```

If the result is `alias/aws/ebs` then you are *not* specifying a custom KMS key. However if the result is a KMS key ARN then you will need to copy this ARN into the SAM template parameter `DefaultEbsEncryptionKeyArn`.

Once the stack has launched and the policy has been created then you can check the `DataPipelineDefaultRole` IAM role to verify that the `DataPipelineEbsKmsPolicy` has been attached.

## Cross Account Replication

To enable replication of S3 bucket objects (i.e. backups files) to a cross account bucket e.g. databunker account bucket, set `EnableCrossAccountReplication` to true.

NOTE: These settings are currently not supported by AWS CloudFormation and so need to be configured manually:

- [DeleteMarkerReplication](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-deletemarkerreplication.html)
- [ReplicationTime](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-replicationtime.html)
- [Metrics](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-metrics.html)
- [ReplicationRuleFilter](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-replicationrulefilter.html)
- [Priority](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-s3-bucket-replicationconfiguration-rules.html#cfn-s3-bucket-replicationrule-priority)

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command.

```bash
dynamodb-backup$ sam build --use-container
```

The SAM CLI installs dependencies defined in `hello_world/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

Run functions locally and invoke them with the `sam local invoke` command.

```bash
dynamodb-backup$ sam local invoke HelloWorldFunction --event events/event.json
```

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
dynamodb-backup$ sam local start-api
dynamodb-backup$ curl http://localhost:3000/
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        HelloWorld:
          Type: Api
          Properties:
            Path: /hello
            Method: get
```

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
dynamodb-backup$ sam logs -n HelloWorldFunction --stack-name dynamodb-backup --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Unit tests

Tests are defined in the `tests` folder in this project. Use PIP to install the [pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```bash
dynamodb-backup$ pip install pytest pytest-mock --user
dynamodb-backup$ python -m pytest tests/ -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name dynamodb-backup
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
