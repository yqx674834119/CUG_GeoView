from flask import Blueprint, jsonify

task_api = Blueprint("task_api", __name__, url_prefix="/api/v1/api/task")


@task_api.post("/model/deploy")
def deploy_online_service():
    return jsonify({
        "code": 200,
        "success": False,
        "msg": "暂未实现",
        "data": False,
    }), 200
