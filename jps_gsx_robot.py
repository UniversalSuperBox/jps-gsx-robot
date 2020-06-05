import sys
import time
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

import conf

default_post_data = {
    "username": conf.JAMF_USERNAME,
    "password": conf.JAMF_PASSWORD,
}

session = requests.Session()

# Get and set our session cookie so we can perform further actions
login = session.post(
    "{}/".format(conf.JAMF_URL), data=default_post_data, allow_redirects=False,
)
cookies = login.cookies
login = None

# Get the desired mobile device search
mobile_device_search_url = "{}/legacy/advancedMobileDeviceSearches.html?id={}&o=v".format(
    conf.JAMF_URL, conf.JAMF_DEVICE_SEARCH
)
mobile_device_search = session.post(
    mobile_device_search_url,
    cookies=cookies,
    params={"o": "v"},  # This asks for a search uuid which we can use later
    allow_redirects=True,
)

search_query_string = urlparse(mobile_device_search.url).query
search_query_params = parse_qs(search_query_string)
try:
    uuid = search_query_params["uuid"]
except KeyError:
    print(
        "Did not receive a search UUID after POSTing to",
        mobile_device_search_url + "?o=v",
    )
    sys.exit(1)
uuid_params = {"uuid": uuid}
mobile_device_search = None


search_action_assistant_html = (
    conf.JAMF_URL + "/legacy/mobileDeviceSearchActionAssistant.html"
)
search_action_assistant_ajax = conf.JAMF_URL + "/mobileDeviceSearchActionAssistant.ajax"

# Open the Action page to get the OBJECT_RANDOM_IDENTIFIER and session-token
search_action_list = session.get(
    search_action_assistant_html, cookies=cookies, params=uuid_params,
)
search_action_soup = BeautifulSoup(search_action_list.text, "html.parser")
object_random_identifier = search_action_soup.find(id="OBJECT_RANDOM_IDENTIFIER").get(
    "value"
)
session_token = search_action_soup.find(id="session-token").get("value")
print(session_token)
search_action_soup = None

# Start the GSX search action
print(search_action_list.url)
gsx_action_start = session.post(
    search_action_assistant_html,
    cookies=cookies,
    params=uuid_params,
    data={
        "session-token": session_token,
        "INCLUDE_PAGE_VARIABLE": "massActionDevicesAssistant.jsp",
        "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
        "type": "gsx",
        "action": "Next",
    },
)
gsx_action_start.raise_for_status()
print(gsx_action_start.request.body)
print("Choose an Action" in gsx_action_start.text)
gsx_action_start = None

check_status = True
while check_status:
    time.sleep(2)
    gsx_action_monitor = session.post(
        search_action_assistant_ajax,
        cookies=cookies,
        params=uuid_params,
        data={
            "ajaxAction": "AJAX_ACTION_MONITOR",
            "session-token": session_token,
            "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
        },
        headers={
            "Referer": search_action_list.url,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    monitor_soup = BeautifulSoup(gsx_action_monitor.text, "html.parser")
    if monitor_soup.find("status").text == "complete":
        check_status = False
    else:
        print(monitor_soup.find("percent").text)

gsx_action_results = session.post(
    search_action_assistant_html,
    cookies=cookies,
    params=uuid_params,
    data={
        "session-token": session_token,
        "INCLUDE_PAGE_VARIABLE": "massActionGsxMonitor.jsp",
        "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
    },
)
gsx_action_results.raise_for_status()
results_soup = BeautifulSoup(gsx_action_results.text, "html.parser")
new_data_table = results_soup.find(id="newData")

devices_with_new_data = []
table_body = new_data_table.find("tbody")
rows = table_body.find_all("tr")
for row in rows:
    columns = row.find_all("td")
    columns = [element.text.strip() for element in columns]
    devices_with_new_data.append(
        [element for element in columns if element]
    )  # Get rid of empty values

if not devices_with_new_data[0]:
    print("Everything is up to date!")
    sys.exit(0)

new_data_serial_numbers = [device[1] for device in devices_with_new_data]

print(len(new_data_serial_numbers), "devices to update.")

gsx_action_complete = session.post(
    search_action_assistant_html,
    cookies=cookies,
    params=uuid_params,
    data={
        "session-token": session_token,
        "INCLUDE_PAGE_VARIABLE": "massGSXDevicesUpdate.jsp",
        "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
        "update": new_data_serial_numbers,
        "action": "Next",
    },
)

print(gsx_action_complete)
print("Done")
