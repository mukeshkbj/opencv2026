# Deploy Twice to AWS

The stack runs the FastAPI app and the built web app in one Lambda container on Graviton (arm64). A Function URL exposes it.

It also creates a versioned S3 bucket with Object Lock, two KMS keys, a log group and an error alarm.

## Prerequisites

- An AWS account and credentials in your shell (`aws sts get-caller-identity` must work).
- AWS CLI v2, AWS SAM CLI and Docker.
- Bedrock access to Claude in the region you choose.

## Enable Bedrock model access

1. Open the Amazon Bedrock console in the region you plan to use. The default is `us-east-1`.
2. Open the model catalog and select the Claude model, `anthropic.claude-opus-5-5` by default.
3. Accept the terms and request access if the console asks.

To use another region or model, pass `--parameter-overrides BedrockRegion=... BedrockModelId=...` to the deploy script.

## Deploy

```bash
./deploy/deploy.sh
```

The script runs `sam build`, then `sam deploy` with `deploy/samconfig.toml`. It prints the Function URL at the end.
The first build takes several minutes. SAM builds the image for arm64 and uploads it to a managed ECR repository.

To get an email when the function fails, add `--parameter-overrides AlarmEmail=you@example.com`. Confirm the subscription email from SNS.

## Verify

```bash
curl https://<function-url>/api/health
```

The reply must show `"signer":"ECDSA_SHA_256"` and `"captioner":"bedrock:anthropic.claude-opus-5-5"`.
If the captioner shows `rules`, the Bedrock region variable is missing. If the signer shows `Ed25519`, the KMS key is not set.

Open the Function URL in a browser to use the web app. Look for the `Twice` metrics in CloudWatch under the `Twice` namespace.

## Upload size limit

A Function URL accepts request bodies up to 6 MB. Binary bodies are base64 encoded first, so photos above about 4.5 MB fail.
The web app shrinks every photo to at most 2400 px before upload, which keeps it near 1 to 2 MB. The server rejects bodies above 4 MB with a 413.

## Tear down

The bucket has versioning and Object Lock, so CloudFormation cannot delete it while it holds objects. Empty it first.

```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name twice \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
for KIND in Versions DeleteMarkers; do
  aws s3api list-object-versions --bucket "$BUCKET" --output json \
    --query "{Objects: $KIND[].{Key:Key,VersionId:VersionId}}" > batch.json
  aws s3api delete-objects --bucket "$BUCKET" --bypass-governance-retention \
    --delete file://batch.json || true
done
sam delete --stack-name twice --no-prompts
```

The loop deletes up to 1000 entries of each kind. Run it again if the bucket holds more. An error for an empty kind is harmless.
The two KMS keys enter a seven day deletion window. The managed ECR repository stays until you delete it.

## Cost notes

- Lambda bills per request and per GB-second. At 3008 MB, one 10 second check costs a fraction of a cent.
- Idle cost is close to zero. The function does not run when nobody uses it.
- Each KMS key costs about 1 USD per month. Signing calls cost about 0.15 USD per 10,000 requests for ECC keys.
- S3 objects expire after 30 days. Object Lock holds each object for 1 day in GOVERNANCE mode, and a privileged user can bypass it.
- Bedrock bills per token. Each confirmed change sends two small image crops to Claude.
- CloudWatch logs are kept for 14 days.
