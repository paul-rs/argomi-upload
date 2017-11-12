# argomi-upload

Serverless sample of consuming Argomi APIs. This sample uploads CSV data into Argomi. A Step Functions state machine
is triggered whenever files are uploaded to a monitored S3 Bucket
![Upload state machine](https://github.com/paul-rs/argomi-upload/blob/master/state_machine.png?raw=true "Argomi Upload State Machine")

## Deploying using Cloudformation

~~~~
aws --region ap-northeast-1 cloudformation deploy --stack-name argomi-upload \
    --template-file upload-argomi-data.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
    Environment=production  \
    ArgomiUsername=<Argomi email/API login> \
    ArgomiPassword=<Argomi user/ API password> \
    UploadBucketName=<S3 Bucket name for Import files> \
    OutputBucketName=<S3 Bucket name for Output files> \
    DeploymentBucketName=<S3 Bucket name where lambda packages are deployed> \
    ExecuteLambdaS3Key=<Execute Lambda zip package> \
    InitializeLambdaS3Key=<Initialize Lambda zip package> \
    ImportLambdaS3Key=<Import Lambda zip package> \
    ExportLambdaS3Key=<Export Lambda zip package>
~~~~
