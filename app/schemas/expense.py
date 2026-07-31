from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.models.expense import SPLIT_TYPES


class ParticipantSchema(Schema):
    user_id = fields.Integer(required=True)
    amount = fields.Decimal(required=False, places=2, as_string=True)
    percentage = fields.Decimal(required=False, places=2, as_string=True)


class ExpenseSchema(Schema):
    amount = fields.Decimal(required=True, places=2, as_string=True, validate=validate.Range(min=0.01))
    description = fields.String(required=False, allow_none=True, validate=validate.Length(max=255))
    split_type = fields.String(required=True, validate=validate.OneOf(SPLIT_TYPES))
    paid_by = fields.Integer(required=False)
    participants = fields.List(fields.Nested(ParticipantSchema), required=True, validate=validate.Length(min=1))

    @validates_schema
    def validate_participants(self, data, **kwargs):
        split_type = data.get("split_type")
        participants = data.get("participants", [])

        user_ids = [p["user_id"] for p in participants]
        if len(set(user_ids)) != len(user_ids):
            raise ValidationError("Duplicate participants are not allowed.", field_name="participants")

        if split_type == "unequal":
            for p in participants:
                if "amount" not in p:
                    raise ValidationError(
                        "Each participant needs an 'amount' for an unequal split.",
                        field_name="participants",
                    )
        elif split_type == "percentage":
            for p in participants:
                if "percentage" not in p:
                    raise ValidationError(
                        "Each participant needs a 'percentage' for a percentage split.",
                        field_name="participants",
                    )
