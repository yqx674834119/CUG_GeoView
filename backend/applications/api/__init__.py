from applications.api.analysis import analysis_api
from applications.api.file import file_api, legacy_file_api
from applications.api.history import history_api
from applications.api.model import model_api
from applications.api.service import service_api
from applications.api.system import system_api_blueprint
from applications.api.task import task_api


def system_api(app):
    app.include_router(file_api)
    app.include_router(legacy_file_api)
    app.include_router(history_api)
    app.include_router(analysis_api)
    app.include_router(model_api)
    app.include_router(service_api)
    app.include_router(task_api)
    app.include_router(system_api_blueprint)
