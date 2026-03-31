import json
import os
import sys
import tempfile
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from applications import create_app


class TestServiceApi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = os.path.join(self.temp_dir.name, "online_services.json")
        self.app = create_app("testing")
        self.app.config["PROPAGATE_EXCEPTIONS"] = True
        self.app.config["ONLINE_SERVICE_STORE"] = self.store_path
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self._write_services([
            {
                "serviceId": 1,
                "serviceName": "变化检测在线服务",
                "serviceCreator": "alice",
                "serviceStatus": 1,
                "taskType": 1,
                "serviceDescription": "初始服务",
                "dispatchId": 1001,
                "serviceCreateTime": "2026-03-31T00:00:00",
                "serviceUpdateTime": "2026-03-31T00:00:00"
            },
            {
                "serviceId": 2,
                "serviceName": "目标检测离线服务",
                "serviceCreator": "bob",
                "serviceStatus": 3,
                "taskType": 2,
                "dispatchId": 1002,
                "serviceCreateTime": "2026-03-31T00:00:00",
                "serviceUpdateTime": "2026-03-31T00:00:00"
            }
        ])

    def tearDown(self):
        self.ctx.pop()
        self.temp_dir.cleanup()

    def _write_services(self, payload):
        with open(self.store_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def _read_services(self):
        with open(self.store_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def test_list_filters_and_pagination(self):
        response = self.client.get("/api/v1/api/service/list", query_string={
            "curPage": 1,
            "pageSize": 10,
            "serviceCreator": "alice",
            "taskType": 1,
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total"], 1)
        self.assertEqual(data["data"]["records"][0]["serviceId"], 1)

    def test_detail_supports_query_param(self):
        response = self.client.get("/api/v1/api/service/detail", query_string={
            "serviceId": 2
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["data"]["serviceName"], "目标检测离线服务")

    def test_restart_and_stop_update_service_status(self):
        restart_response = self.client.post("/api/v1/api/service/restart", json={
            "serviceRestartDTO": {
                "ids": "2"
            }
        })
        self.assertEqual(restart_response.status_code, 200)
        services = self._read_services()
        restarted = [item for item in services if item["serviceId"] == 2][0]
        self.assertEqual(restarted["serviceStatus"], 1)

        stop_response = self.client.post("/api/v1/api/service/stop", json={
            "serviceStopDTO": {
                "serviceIds": [1]
            }
        })
        self.assertEqual(stop_response.status_code, 200)
        services = self._read_services()
        stopped = [item for item in services if item["serviceId"] == 1][0]
        self.assertEqual(stopped["serviceStatus"], 2)
        self.assertEqual(stopped["offlineServiceStatus"], "stopped")

    def test_update_and_delete(self):
        update_response = self.client.post("/api/v1/api/service/update", json={
            "serviceInfoDTO": {
                "serviceId": 1,
                "serviceName": "变化检测在线服务-已更新",
                "serviceDescription": "新的描述",
                "serviceStatus": 3
            }
        })
        self.assertEqual(update_response.status_code, 200)
        services = self._read_services()
        updated = [item for item in services if item["serviceId"] == 1][0]
        self.assertEqual(updated["serviceName"], "变化检测在线服务-已更新")
        self.assertEqual(updated["serviceStatus"], 3)

        delete_response = self.client.delete("/api/v1/api/service/delete", query_string={
            "ids": "2"
        })
        self.assertEqual(delete_response.status_code, 200)
        services = self._read_services()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["serviceId"], 1)

    def test_deploy_stub_returns_not_implemented_message(self):
        response = self.client.post("/api/v1/api/task/model/deploy", json={
            "serviceInfoDTO": {
                "serviceName": "占位服务"
            }
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["msg"], "暂未实现")
        self.assertFalse(data["data"])


if __name__ == "__main__":
    unittest.main()
