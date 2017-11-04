# argomi-upload

Serverless sample of consuming Argomi APIs. This sample uploads CSV data into Argomi. A Step Functions state machine
is triggered whenever files are uploaded to a monitored S3 Bucket
![Upload state machine](https://github.com/paul-rs/argomi-upload/blob/master/state_machine.png?raw=true "Argomi Upload State Machine")

## Deploying using Cloudformation

~~~~
aws --region ap-northeast-1 cloudformation create-stack --stack-name argomi-upload \
--template-body file://upload-argomi-data.yaml \
--capabilities CAPABILITY_NAMED_IAM \
--parameters ParameterKey=AssetManagerId,ParameterValue=<your asset manager id> \
             ParameterKey=Environment,ParameterValue=production \
             ParameterKey=ArgomiUsername,ParameterValue=<your argomi email login> \
             ParameterKey=ArgomiPassword,ParameterValue=<your argomi password> \
             ParameterKey=BucketName,ParameterValue=<s3 bucket name to monitor> \
             ParameterKey=DeploymentBucketName,ParameterValue=<s3 bucket name where to deploy lambda code> \
             ParameterKey=ExecuteLambdaS3Key,ParameterValue=<s3 key for lambda> \
             ParameterKey=InitializeLambdaS3Key,ParameterValue=<s3 key for lambda> \
             ParameterKey=ImportLambdaS3Key,ParameterValue=<s3 key for lambda> \
             ParameterKey=GetPositionsLambdaS3Key,ParameterValue=<s3 key for lambda>
~~~~
