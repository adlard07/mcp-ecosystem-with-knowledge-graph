import os
from typing import List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from dotenv import load_dotenv

from utils.utils import logging

load_dotenv(override=True)


class DynamoConfig:
    def __init__(self) -> None:
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.aws_region = os.getenv("AWS_REGION", "ap-south-1")
        missing = [
            k
            for k, v in {
                "AWS_ACCESS_KEY_ID": self.aws_access_key_id,
                "AWS_SECRET_ACCESS_KEY": self.aws_secret_access_key,
                "AWS_REGION": self.aws_region,
            }.items()
            if not v
        ]
        if missing:
            raise ValueError(f"Missing env vars: {', '.join(missing)}")

    def _kwargs(self) -> dict:
        return dict(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )

    def resource(self):
        return boto3.resource("dynamodb", **self._kwargs())

    def client(self):
        return boto3.client("dynamodb", **self._kwargs())


class DatabaseInit:
    def __init__(self):
        cfg = DynamoConfig()
        self._resource = cfg.resource()
        self._client = cfg.client()

    # ── table management ──────────────────────────────────────────────

    def create_table(
        self,
        table_name: str,
        key_schema: List[dict],
        attribute_definitions: List[dict],
        global_secondary_indexes: Optional[List[dict]] = None,
        ttl_attribute: Optional[str] = None,
    ):
        try:
            self._client.describe_table(TableName=table_name)
            logging.info(f"Table '{table_name}' already exists.")
            return self._resource.Table(table_name)  # type: ignore
        except self._client.exceptions.ResourceNotFoundException:
            pass

        kwargs: dict = dict(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
        )
        if global_secondary_indexes:
            kwargs["GlobalSecondaryIndexes"] = global_secondary_indexes

        table = self._resource.create_table(**kwargs)  # type: ignore
        table.wait_until_exists()
        logging.info(f"Table '{table_name}' created.")

        if ttl_attribute:
            self._client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    "Enabled": True,
                    "AttributeName": ttl_attribute,
                },
            )
            logging.info(f"TTL enabled on '{table_name}'.{ttl_attribute}")

        return table

    def delete_table(self, table_name: str) -> None:
        try:
            self._client.delete_table(TableName=table_name)
            logging.info(f"Table '{table_name}' deleted.")
        except self._client.exceptions.ResourceNotFoundException:
            logging.warning(f"Table '{table_name}' does not exist.")

    # ── resource-based CRUD (returns deserialized Python types) ───────

    def put_item(self, table_name: str, item: dict) -> None:
        self._resource.Table(table_name).put_item(Item=item)  # type: ignore

    def get_item(self, table_name: str, key: dict) -> Optional[dict]:
        response = self._resource.Table(table_name).get_item(Key=key)  # type: ignore
        return response.get("Item")

    def update_item(
        self,
        table_name: str,
        key: dict,
        update_expression: str,
        expression_attribute_names: dict,
        expression_attribute_values: dict,
    ) -> None:
        self._resource.Table(table_name).update_item(  # type: ignore
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )

    def delete_item(self, table_name: str, key: dict) -> None:
        self._resource.Table(table_name).delete_item(Key=key)  # type: ignore

    def query_index(
        self,
        table_name: str,
        index_name: str,
        key_name: str,
        key_value: str,
    ) -> List[dict]:
        response = self._resource.Table(table_name).query(  # type: ignore
            IndexName=index_name,
            KeyConditionExpression=Key(key_name).eq(key_value),
        )
        return response.get("Items", [])

    def scan(self, table_name: str) -> List[dict]:
        response = self._resource.Table(table_name).scan()  # type: ignore
        return response.get("Items", [])
