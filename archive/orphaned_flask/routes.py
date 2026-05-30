from flask import Blueprint, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validates, ValidationError
from app.config import Config
from models import Task

task_api = Blueprint('task_api', __name__)

db = SQLAlchemy()

class TaskSchema(Schema):
    title = fields.Str(required=True)
    description = fields.Str()
    status = fields.Str(required=True, choices=['pending', 'in_progress', 'completed'])
    created_at = fields.DateTime()

    @validates('status')
    def validate_status(self, value):
        if value not in ['pending', 'in_progress', 'completed']:
            raise ValidationError('Invalid task status')

def get_all_tasks():
    return Task.query.all()

def create_task(task_data):
    task_schema = TaskSchema()
    try:
        errors = task_schema.validate(task_data)
        if errors:
            return jsonify({'error': 'Validation error'}), 400
    except ValidationError as err:
        return jsonify({'error': str(err)}), 400

    new_task = Task(title=task_data['title'], description=task_data.get('description'), status=task_data['status'])
    db.session.add(new_task)
    db.session.commit()
    return jsonify(task_schema.dump(new_task)), 201

def get_task_by_id(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(TaskSchema().dump(task))

def update_task(task_id, task_data):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    task_schema = TaskSchema()
    try:
        errors = task_schema.validate(task_data)
        if errors:
            return jsonify({'error': 'Validation error'}), 400
    except ValidationError as err:
        return jsonify({'error': str(err)}), 400

    task.title = task_data['title']
    task.description = task_data.get('description')
    task.status = task_data['status']
    db.session.commit()
    return jsonify(task_schema.dump(task))

def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})

@task_api.route('/tasks', methods=['GET'])
def get_all_tasks_endpoint():
    return jsonify([TaskSchema().dump(task) for task in get_all_tasks()])

@task_api.route('/tasks', methods=['POST'])
def create_task_endpoint():
    task_data = request.get_json()
    return create_task(task_data)

@task_api.route('/tasks/<int:task_id>', methods=['GET'])
def get_task_by_id_endpoint(task_id):
    return get_task_by_id(task_id)

@task_api.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task_endpoint(task_id):
    task_data = request.get_json()
    return update_task(task_id, task_data)

@task_api.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_endpoint(task_id):
    return delete_task(task_id)