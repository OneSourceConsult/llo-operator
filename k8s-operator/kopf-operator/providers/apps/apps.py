import logging
import requests

API_URL = "http://orch-backend.orchestration.charity-project.eu/v1"

def install_app(appData):

    response = requests.post(API_URL + "/installapp", json=appData)

    
    logging.info(f"Install App request sent...")

def uninstall_app(appData):
    response = requests.delete(API_URL + "/uninstallapp", params=appData)

    logging.info(f"Uninstall App request sent...")