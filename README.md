## Gumshoe

Gumshoe is a quick script to help locate potential PII in S3 buckets.

### How To Run

#### First, intialize your environment using Poetry

```
poetry shell
poetry install
```

#### Supply your IAM credentials

Create IAM credentials with the appropriate permissions and set them in your environment:
```
export AWS_ACCESS_KEY_ID=<your-access-key-id>
export AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
```

You will need at least the following permissions:
- `s3:ListBucket`
- `s3:GetObject`
- `s3:GetObjectVersion`
- `s3:GetObjectVersionAcl`
- `s3:GetObjectVersionTagging`
- `s3:GetObjectVersionTorrent`
- `s3:GetObjectTorrent`
- `s3:GetObjectTagging`
- `comprehend:ContainsPiiEntities`
- `comprehend:DetectPiiEntities`

#### Run Gumshoe

```
python gumshoe.py
```
