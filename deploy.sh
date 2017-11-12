LAMBDAS="execute \
         initialize \
         import \
         export"

docker_build() (
    docker build -t argomiupload .
)

docker_deploy() (
    folder=$1
    AWS_ACCESS_KEY_ID=$(aws --profile default configure get aws_access_key_id)
    AWS_SECRET_ACCESS_KEY=$(aws --profile default configure get aws_secret_access_key)

    docker run -it --rm \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    argomiupload \
    /bin/bash -c "cd $folder; lambda upload --use-requirements"
)

docker_deploy_all() (
    for lambda in $LAMBDAS; do
        echo "Deploying Lambda $lambda"
        docker_deploy $lambda
    done
)