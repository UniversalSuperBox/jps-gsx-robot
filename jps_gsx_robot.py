# Copyright 2020 Dalton Durst
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import sys
import time
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

import conf


def eprint(*args, **kwargs):
    """Like print, but outputs to stderr."""
    print(*args, file=sys.stderr, **kwargs)


base_url = conf.JAMF_URL
search_id = conf.JAMF_SEARCH_ID

if conf.JAMF_SEARCH_TYPE.casefold() == "mobiledevice":
    search_type = "MobileDevice"
    assistant_type = "mobileDevice"
    include_type = "Devices"
elif conf.JAMF_SEARCH_TYPE.casefold() == "computer":
    search_type = "Computer"
    assistant_type = "computer"
    include_type = "Computers"
else:
    raise ValueError(
        "Value provided for JAMF_SEARCH_TYPE was not 'computer' or 'mobiledevice:",
        conf.JAMF_SEARCH_TYPE,
    )

session = requests.Session()

eprint("Logging in to JPS...")
login = session.post(
    "{}/".format(base_url),
    data={"username": conf.JAMF_USERNAME, "password": conf.JAMF_PASSWORD,},
    allow_redirects=False,
)

try:
    login.raise_for_status()
except requests.exceptions.HTTPError as e:
    eprint(
        "Login request failed. If this is a 401 error, please check your JAMF_USERNAME and JAMF_PASSWORD and try again."
    )
    eprint(e)
    sys.exit(1)

cookies = login.cookies
login = None


eprint(
    "Requesting results UUID for advanced {type} search {id}...".format(
        type=search_type, id=search_id
    )
)
mobile_device_search_url = "{base}/legacy/advanced{type}Searches.html?id={id}&o=v".format(
    base=base_url, type=search_type, id=search_id
)
mobile_device_search = session.post(
    mobile_device_search_url,
    cookies=cookies,
    params={"o": "v"},  # This asks for a search uuid which we can use later
    allow_redirects=True,
)

try:
    mobile_device_search.raise_for_status()
except requests.exceptions.HTTPError as e:
    eprint("Results UUID request failed:")
    eprint(e)
    sys.exit(1)

search_query_string = urlparse(mobile_device_search.url).query
search_query_params = parse_qs(search_query_string)
try:
    uuid = search_query_params["uuid"]
except KeyError:
    eprint(
        "Did not receive a search UUID after POSTing to",
        mobile_device_search_url + "?o=v",
    )
    eprint("The URL received in response to our POST was", mobile_device_search.url)
    sys.exit(1)
eprint("Got results UUID:", uuid)
uuid_params = {"uuid": uuid}
mobile_device_search = None


search_action_assistant_html = "{base}/legacy/{type}SearchActionAssistant.html".format(
    base=base_url, type=assistant_type
)
search_action_assistant_ajax = "{base}/{type}SearchActionAssistant.ajax".format(
    base=base_url, type=assistant_type
)


eprint("Receiving one-time session information by opening the search's 'Action' page...")
search_action_list = session.get(
    search_action_assistant_html, cookies=cookies, params=uuid_params,
)
search_action_soup = BeautifulSoup(search_action_list.text, "html.parser")
object_random_identifier = search_action_soup.find(id="OBJECT_RANDOM_IDENTIFIER").get(
    "value"
)
session_token = search_action_soup.find(id="session-token").get("value")
search_action_soup = None


eprint("Starting GSX search action...")
gsx_action_start = session.post(
    search_action_assistant_html,
    cookies=cookies,
    params=uuid_params,
    data={
        "session-token": session_token,
        "INCLUDE_PAGE_VARIABLE": "massAction{}Assistant.jsp".format(include_type),
        "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
        "type": "gsx",
        "action": "Next",
    },
)
gsx_action_start.raise_for_status()
gsx_action_start = None

while True:
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
        eprint("GSX search is complete, determining devices to update...")
        break

    eprint(monitor_soup.find("percent").text + "% finished")

# Now that the action is done, we can retrieve the table of results.
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
for sn in new_data_serial_numbers:
    print(sn)

num_devices_need_update = len(new_data_serial_numbers)
eprint("Updating", num_devices_need_update, "devices...")

gsx_action_complete = session.post(
    search_action_assistant_html,
    cookies=cookies,
    params=uuid_params,
    data={
        "session-token": session_token,
        "INCLUDE_PAGE_VARIABLE": "massGSX{}Update.jsp".format(include_type),
        "OBJECT_RANDOM_IDENTIFIER": object_random_identifier,
        "update": new_data_serial_numbers,
        "action": "Next",
    },
)

try:
    gsx_action_complete.raise_for_status()
except requests.exceptions.HTTPError as e:
    eprint("The request to update", num_devices_need_update, "devices failed:")
    eprint(e)
    eprint(gsx_action_complete.text)
    sys.exit(1)

print("Done")
