import boto3

from pepup.loader import load_credential


ses_client = boto3.client('ses', aws_access_key_id=load_credential("AWS_ACCESS_KEY"),
                        aws_secret_access_key=load_credential('AWS_SECRET_ACCESS_KEY'), region_name='us-east-1')


lambda_client = boto3.client('lambda', aws_access_key_id=load_credential("AWS_LAMBDA_ACCESS_KEY"),
                            aws_secret_access_key=load_credential("AWS_LAMBDA_SECRET_ACCESS_KEY"),
                            region_name='ap-northeast-2')

sns_client = boto3.client('sns', aws_access_key_id=load_credential("AWS_ACCESS_KEY"),
                        aws_secret_access_key=load_credential('AWS_SECRET_ACCESS_KEY'), region_name='ap-northeast-2')

s3_client = boto3.client('s3', aws_access_key_id=load_credential("AWS_ACCESS_KEY"),
                        aws_secret_access_key=load_credential('AWS_SECRET_ACCESS_KEY'), region_name='ap-northeast-2')
