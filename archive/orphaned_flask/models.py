from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validates, ValidationError
from marshmallow.validate import OneOf

db = SQLAlchemy()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), required=True)
    description = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending', validate=OneOf(['pending', 'in-progress', 'completed']))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class TaskSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str()
    status = fields.Str(validate=OneOf(['pending', 'in-progress', 'completed']))
    created_at = fields.DateTime(dump_only=True)

    @validates('status')
    def validate_status(self, value):
        if value not in ['pending', 'in-progress', 'completed']:
            raise ValidationError('Invalid task status')

class TaskValidator:
    @staticmethod
    def validate_task(task_schema, data):
        errors = {}
        try:
            TaskSchema().load(data, unknown='ignore')
        except ValidationError as err:
            for field, msg in err.messages.items():
                if field not in errors:
                    errors[field] = []
                errors[field].append(msg)
        return errors