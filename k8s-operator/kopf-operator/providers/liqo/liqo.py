import logging
import requests

API_URL = "http://orch-backend.orchestration.charity-project.eu/v1"

def link_clusters(linkData):
    
    logging.info(API_URL + f"/peer?greenClusterName={linkData['greenClusterName']}&roseClusterName={linkData['roseClusterName']}")
    response = requests.get(API_URL + f"/peer?greenClusterName={linkData['greenClusterName']}&roseClusterName={linkData['roseClusterName']}")

    logging.info(f"Link request sent...")

# def unlink_clusters(linkData):