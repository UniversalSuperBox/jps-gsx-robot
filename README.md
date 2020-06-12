# JPS GSX Robot

Your friendly neighborhood giant death robot bent on nothing but destroying your tedious Apple Global Service Exchange import to Jamf Pro Server.

jps-gsx-robot takes the ID of a mobile device search. It then runs through the GSX Inventory Lookup bulk action on the mobile device search's resultset, just like you would do in your browser. All devices with new data (those that appear in the first tab of the results screen) will be updated when the script is finished.

## Prerequisites

To use jps-gsx-robot, you will need Python3 and pipenv installed.

### Install Python

#### macOS

To install Python3 on macOS, download the pkg from https://www.python.org/downloads/. Once you've run and installed the pkg, find "Python 3.*x*" in your Applications directory and run the `Update Shell Profile.command` file, then the `Install Certificates.command` file.

#### Windows

To install Python3 on Windows, download its installer from https://www.python.org/downloads/. While installing, check the option to add Python to your PATH. Once the installation completes, reboot your computer so Python can be run from a command prompt.

### Install Pipenv

Pipenv is used to install the dependencies for jps-gsx-robot and keep them separate from any other Python projects on your computer. To install pipenv, run the following command in a terminal or command prompt:

```
pip3 install --user pipenv
```

## Usage

### Download jps-gsx-robot

You can download the script and its example configuration by selecting "Download ZIP" under the Clone or Download menu, clicking [this link](https://github.com/UniversalSuperBox/jps-gsx-robot/archive/master.zip), or cloning it with `git`.

### Configure jps-gsx-robot

To start, copy `conf.py.example` to `conf.py`.

Then, you may either edit the `conf.py` file to enter your desired values (replacing the `environ[...]` portions of the configuration) or set the values in your shell environment before running the script.

To set the configuration environment variables under most shells, type `export VARIABLE_NAME=value`, where VARIABLE_NAME is the part within quotes in the `conf.py` script. For example, to provide LDAP_FILTER to the script exclusively from the environment, type:

```
export JAMF_USERNAME='jps-gsx-robot'
```

Under a Windows shell, replace `export` with `set`.

Unless otherwise specified in this section, the environment variable used to set a configuration option uses the same name as the configuration option itself. `JAMF_USERNAME` in the default config file can be set as `JAMF_USERNAME` in the environment, for example.

#### JAMF_URL

This URL points to the base of your JPS. For example, `https://jps.mydomain.tld:8443`.

#### JAMF_USERNAME and JAMF_PASSWORD

These values specify the username and password used to sign in to the JPS. This user must have the permissions needed to view Advanced Computer Searches and Advanced Device Searches, and must be able to update GSX records for all of these. We're still unsure exactly what these needed permissions are.

#### JAMF_DEVICE_SEARCH

Contains the ID of a mobile device search. jps-gsx-robot will read this list of devices and initiate the GSX inventory lookup on them.

### Run jps-gsx-robot

Change into the script's directory. With the script configured and its dependencies installed, it can be run with:

```
pipenv install --three
pipenv run python ./jps-gsx-robot.py
