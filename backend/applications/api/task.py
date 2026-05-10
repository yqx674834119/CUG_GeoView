from fastapi import APIRouter

task_api = APIRouter(prefix="/api/v1/api/task", tags=["task"])


@task_api.get("/list")
def task_list():
    return {
        "code": 200,
        "success": True,
        "msg": "OK",
        "data": {"records": [], "total": 0, "curPage": 1, "pageSize": 10},
    }
