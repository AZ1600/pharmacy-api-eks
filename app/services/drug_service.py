import json
from uuid import uuid4

from app.core.config import settings
from app.infra.dynamodb import events, table


def create_drug_service(
    drug_data,
    tenant_id: str,
    user_id: str,
):
    """
    Create a tenant-scoped drug record in DynamoDB
    and publish a DrugCreated event.
    """

    payload = (
        drug_data.model_dump()
        if hasattr(drug_data, "model_dump")
        else dict(drug_data)
    )

    item = {
        **payload,
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "created_by": user_id,
    }

    table.put_item(
        Item=item
    )

    event_response = events.put_events(
        Entries=[
            {
                "Source": "pharmacy-api",
                "DetailType": "DrugCreated",
                "Detail": json.dumps(item),
                "EventBusName": (
                    settings.EVENT_BUS_NAME
                ),
            }
        ]
    )

    failed_entries = event_response.get(
        "FailedEntryCount",
        0,
    )

    if failed_entries:
        raise RuntimeError(
            "Failed to publish DrugCreated "
            "event to EventBridge."
        )

    return {
        "message": (
            "Drug created successfully"
        ),
        "data": item,
    }


def get_drug_service(
    drug_id: str,
):
    """
    Fetch a drug by ID from DynamoDB.
    """

    response = table.get_item(
        Key={
            "id": drug_id,
        }
    )

    item = response.get(
        "Item"
    )

    if not item:
        return {
            "message": "Drug not found",
            "data": None,
        }

    return {
        "message": (
            "Drug retrieved successfully"
        ),
        "data": item,
    }