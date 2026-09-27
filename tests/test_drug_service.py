import unittest
from unittest.mock import patch

from app.models.drug import DrugRequest
from app.services.drug_service import (
    create_drug_service,
)


class TestCreateDrugService(
    unittest.TestCase
):

    @patch(
        "app.services.drug_service.events"
    )
    @patch(
        "app.services.drug_service.table"
    )
    def test_create_drug_adds_identity_and_persists_record(
        self,
        mock_table,
        mock_events,
    ):
        mock_events.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [
                {
                    "EventId": "event-123",
                }
            ],
        }

        drug = DrugRequest(
            drug_name="Amoxicillin",
            batch_number="AMX-001",
            quantity=50,
            reorder_level=10,
            expiry_date="2027-12-31",
            supplier="Demo Supplier",
        )

        result = create_drug_service(
            drug,
            tenant_id="tenant_001",
            user_id="user_123",
        )

        item = (
            mock_table
            .put_item
            .call_args
            .kwargs["Item"]
        )

        self.assertEqual(
            item["drug_name"],
            "Amoxicillin",
        )

        self.assertEqual(
            item["tenant_id"],
            "tenant_001",
        )

        self.assertEqual(
            item["created_by"],
            "user_123",
        )

        self.assertTrue(
            item["id"]
        )

        self.assertEqual(
            result["message"],
            "Drug created successfully",
        )

        mock_table.put_item.assert_called_once()

        mock_events.put_events.assert_called_once()

        event_call = (
            mock_events
            .put_events
            .call_args
            .kwargs
        )

        self.assertEqual(
            event_call["Entries"][0][
                "Source"
            ],
            "pharmacy-api",
        )

        self.assertEqual(
            event_call["Entries"][0][
                "DetailType"
            ],
            "DrugCreated",
        )

    @patch(
        "app.services.drug_service.events"
    )
    @patch(
        "app.services.drug_service.table"
    )
    def test_create_drug_raises_when_eventbridge_publish_fails(
        self,
        mock_table,
        mock_events,
    ):
        mock_events.put_events.return_value = {
            "FailedEntryCount": 1,
            "Entries": [
                {
                    "ErrorCode":
                        "InternalFailure",
                    "ErrorMessage":
                        "Event publishing failed",
                }
            ],
        }

        drug = DrugRequest(
            drug_name="Amoxicillin",
            batch_number="AMX-002",
            quantity=50,
            reorder_level=10,
            expiry_date="2027-12-31",
            supplier="Demo Supplier",
        )

        with self.assertRaises(
            RuntimeError
        ):
            create_drug_service(
                drug,
                tenant_id="tenant_001",
                user_id="user_123",
            )

        mock_table.put_item.assert_called_once()
        mock_events.put_events.assert_called_once()


if __name__ == "__main__":
    unittest.main()