import requests
# test_apis = ["ping", "orderDetails", "binCheck", "gotoSitePause", "gotoSiteResume", "", "", "", ""]
# res = requests.get("http://58.34.177.164:8088/orderDetails/123")
# print("res:", res.text)
order = {
  "id": "task1",
  "fromLoc": "Loc-01",
  "toLoc": "Loc-02"
}
res = requests.post("http://192.168.8.59:8885/setOrder", json=order)
