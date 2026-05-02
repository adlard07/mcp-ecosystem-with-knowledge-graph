from src.database.dynamo.services import DatabaseServices
from src.models.servers import CreateServer, Server

dbs = DatabaseServices()


def create_server(server: CreateServer):
    return dbs.create_server(server)


def get_server(server_id: str):
    return dbs.get_server(server_id)


def update_server(server: Server):
    return dbs.update_server(server)


def delete_server(server_id: str):
    return dbs.delete_server(server_id)


if __name__ == "__main__":
    server = CreateServer(
        server_name="Expense Tracker",
        server_description="""Track your expenses, manage your budget, register transactions, visualize spending patterns, identify spending habits, and save money.""",
        server_url="http://localhost:7000",
        health_check="/health",
        server_sufixes={
            "add transaction": {
                "description": "Add a new income, expense, or transfer transaction",
                "method": "POST",
                "suffix": "/transactions/add",
                "params": {
                    "user_id": "string",
                    "amount": "float",
                    "title": "string",
                    "notes": "string | optional",
                    "transaction_type": "income | expense | transfer",
                    "merchant_id": "string | optional",
                    "category_id": "string | optional",
                    "attachments": "list[string] | optional",
                    "source": "string | optional",
                },
                "example_payload": {
                    "user_id": "46775c8e-dd7f-4c11-bf0d-15d04e0305b0",
                    "amount": 482.00,
                    "title": "Dinner order",
                    "transaction_type": "expense",
                    "merchant_id": "swiggy",
                    "category_id": "cat_food_dining",
                    "notes": "Dinner order from Swiggy",
                    "source": "UPI",
                },
            },
            "get user transactions": {
                "description": "Get all transactions for a user",
                "method": "POST",
                "suffix": "/transactions/user",
                "params": {
                    "body": {
                        "user_id": "string",
                    },
                    "query": {
                        "limit": "integer | optional | 1-100",
                    },
                },
                "example_payload": {
                    "user_id": "46775c8e-dd7f-4c11-bf0d-15d04e0305b0",
                },
            },
            "get transactions by category": {
                "description": "Get transactions by user id and category id",
                "method": "GET",
                "suffix": "/transactions/user/{user_id}/category/{category_id}",
                "params": {
                    "path": {
                        "user_id": "string",
                        "category_id": "string",
                    },
                    "query": {
                        "limit": "integer | optional | 1-100",
                    },
                },
            },
            "get transaction": {
                "description": "Get a single transaction by user id and transaction id",
                "method": "GET",
                "suffix": "/transactions/user/{user_id}/{transaction_id}",
                "params": {
                    "path": {
                        "user_id": "string",
                        "transaction_id": "string",
                    },
                },
            },
            "update transaction": {
                "description": "Update a transaction by user id and transaction id",
                "method": "PUT",
                "suffix": "/transactions/user/{user_id}/{transaction_id}",
                "params": {
                    "path": {
                        "user_id": "string",
                        "transaction_id": "string",
                    },
                    "body": {
                        "amount": "float | optional",
                        "transaction_type": "income | expense | transfer | optional",
                        "currency": "INR | USD | EUR | optional",
                        "merchant_id": "string | optional",
                        "category_id": "string | optional",
                        "notes": "string | optional",
                        "source": "string | optional",
                    },
                },
                "example_payload": {
                    "amount": 500.00,
                    "notes": "Updated dinner amount",
                },
            },
            "delete transaction": {
                "description": "Delete a transaction by user id and transaction id",
                "method": "DELETE",
                "suffix": "/transactions/user/{user_id}/{transaction_id}",
                "params": {
                    "path": {
                        "user_id": "string",
                        "transaction_id": "string",
                    },
                },
            },
            "mark transaction duplicate": {
                "description": "Mark a transaction as duplicate",
                "method": "POST",
                "suffix": "/transactions/user/{user_id}/{transaction_id}/mark-duplicate",
                "params": {
                    "path": {
                        "user_id": "string",
                        "transaction_id": "string",
                    },
                    "query": {
                        "duplicate_of": "string",
                    },
                },
            },
        },
    )

    # create_server(server)
