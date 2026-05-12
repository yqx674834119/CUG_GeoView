from flask import Blueprint

task_api = Blueprint("task_api", __name__, url_prefix="/api/v1/api/task")


@task_api.route("/list", methods=["GET"])
def task_list():
    return {
        "code": 200,
        "success": True,
        "msg": "OK",
        "data": {"records": [], "total": 0, "curPage": 1, "pageSize": 10},
    }


@task_api.route("/model/deploy", methods=["POST"])
def task_model_deploy():
    return {"code": 200, "success": False, "msg": "暂未实现", "data": False}
