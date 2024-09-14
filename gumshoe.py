"""
Gumshoe - a simple script to investigate AWS S3 buckets for PII
"""
import argparse
import boto3
import random
from pyfzf.pyfzf import FzfPrompt
from shutil import which

# A list of PII types that we don't want to report on
IGNORE_TYPES = [
    "DATE_TIME",
    "DATE",
    "TIME",
    "IP_ADDRESS",
    "MAC_ADDRESS",
    "URL"
]   

class GumshoeInspector:
    """
    GumshoeInspector class to inspect S3 buckets for PII using AWS Comprehend
    """
    def __init__(self, aws_region: str = "us-east-1", sample_size: int = 10, display_lines: int = 10):
        self.session = boto3.Session(region_name=aws_region)
        self.s3 = self.session.client("s3")
        self.comprehend = self.session.client("comprehend")
        self.sample_size = sample_size
        self.display_lines = display_lines

    def get_s3_buckets(self) -> list[str]:
        """
        Get a list of all S3 buckets in the current AWS account
        """
        return sorted([bucket["Name"] for bucket in self.s3.list_buckets()["Buckets"]])

    def sample_s3_bucket_contents(self, bucket: str) -> list[str]:
        """
        Get a random sample of 10 objects from an S3 bucket
        """
        response = self.s3.list_objects_v2(Bucket=bucket)
        
        if 'Contents' in response:
            all_objects = [obj["Key"] for obj in response["Contents"]]
            return random.sample(all_objects, min(10, len(all_objects)))
        else:
            print(f"The bucket '{bucket}' is empty or you don't have permission to list its contents.")
            return []  # or handle this case as appropriate for your use case

    def read_s3_object_content(self, bucket: str, key: str) -> str:
        """
        Read the content of the S3 object as a string

        Attempts to read the content as UTF-8, and if that fails, tries other encodings.
        """
        content = self.s3.get_object(Bucket=bucket, Key=key)['Body'].read()
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other encodings or use a more permissive method
            content_str = content.decode('utf-8', errors='ignore')
        return content_str

    def check_for_pii_using_aws_comprehend(self, bucket_name: str, object_name: str, content_str: str):
        """
        Check for PII using AWS Comprehend
        """
        if not content_str:
            print(f"Empty content in {bucket_name}/{object_name}")
            return None
        
        # Assign the first 90000 characters to a new variable
        # The actual limit is 100000 _bytes_, not characters, but this is a good buffer
        content_sample = content_str[:90000]
        
        return self.comprehend.contains_pii_entities(Text=content_sample, LanguageCode="en")


    def process_pii_entities(self, comprehend_response, object_name):
        """
        Process the result of the AWS Comprehend call,
        """
        if 'Labels' in comprehend_response:
            labels = comprehend_response['Labels']

            return [l for l in labels if l["Name"] not in IGNORE_TYPES]

        return None

    def inspect_bucket(self, bucket_name: str):
        """
        Inspect a specific S3 bucket
        """
        print(f"Inspecting bucket: {bucket_name}")
        sample = self.sample_s3_bucket_contents(bucket_name)

        for object_name in sample:
            print(f"Checking {bucket_name}/{object_name}")
            content_str = self.read_s3_object_content(bucket_name, object_name)
            comprehend_response = self.check_for_pii_using_aws_comprehend(bucket_name, object_name, content_str)
            if comprehend_response is None:
                continue
            labels = self.process_pii_entities(comprehend_response, object_name)
            if labels:
                print(f"PII entities found in {bucket_name}/{object_name}:")
                for label in labels:
                    name = label["Name"]
                    score = label["Score"]
                    print(f"  - Type: {name}, Score: {score}")
                
                if self.display_lines > 0:
                    # Print the first 10 lines of the content_str
                    print(f"First {self.display_lines} lines of {bucket_name}/{object_name}:")
                    content_lines = content_str.splitlines()
                    for i, line in enumerate(content_lines[:10], 1):
                        print(f"{i}: {line}")
                    if len(content_lines) > 10:
                        print("...")  # Indicate there might be more content
                print()
            else:
                print(f"No PII entities found in {bucket_name}/{object_name}")


def get_args():
    """Return the arguments passed to the script
    
    Constructs an argparse ArgumentParser and returns the parsed arguments.
    """
    parser = argparse.ArgumentParser(prog="gumshoe", description="Check S3 buckets for PII using AWS Comprehend")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region to use")
    parser.add_argument("--bucket-name", help="Specific S3 bucket to check")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of objects to sample from each bucket")
    parser.add_argument("--display-lines", type=int, default=10, help="Number of lines to display from each object. Defaults to 10. Set to 0 to not display any lines.")
    return parser.parse_args()

def main():
    """Main function to run the script
    
    This function gets the arguments passed to the script, initializes the GumshoeInspector,
    and either inspects a specific bucket or lists all available buckets for inspection.
    """
    args = get_args()

    gumshoe = GumshoeInspector(aws_region=args.aws_region, sample_size=args.sample_size, display_lines=args.display_lines)
    if args.bucket_name:
        gumshoe.inspect_bucket(args.bucket_name)
    else:
        if which("fzf"):
            buckets = gumshoe.get_s3_buckets()
            fzf = FzfPrompt()
            selected_bucket = fzf.prompt(buckets, "--header='Select a bucket to inspect:'")[0]
            gumshoe.inspect_bucket(selected_bucket)
        else:
            print("Bucket name not specified and fzf not found. Please install fzf (https://github.com/junegunn/fzf) to choose a bucket interactively.")
            exit(1)

if __name__ == "__main__":
    main()
