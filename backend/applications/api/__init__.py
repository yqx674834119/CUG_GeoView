from applications.api.analysis import analysis_api
from applications.api.file import file_api, legacy_file_api
from applications.api.model import model_api
from applications.api.service import service_api
from applications.api.system import system_api_blueprint
from applications.api.task import task_api


def register_api(app):
    app.register_blueprint(file_api)
    app.register_blueprint(legacy_file_api)
    app.register_blueprint(analysis_api)
    app.register_blueprint(model_api)
    app.register_blueprint(service_api)
    app.register_blueprint(task_api)
    app.register_blueprint(system_api_blueprint)


def system_api(app):
    register_api(app)
