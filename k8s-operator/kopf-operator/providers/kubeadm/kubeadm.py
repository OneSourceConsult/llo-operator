import logging
import requests

API_URL = "http://orch-backend.orchestration.charity-project.eu/v1"

def create_cluster(clusterData):

    clusterName = clusterData["clusterName"]
    # logging.info(clusterData)
    response = requests.post(API_URL + "/deploycluster", json=clusterData)

    logging.info(f"Cluster {clusterName} is being created...")

def delete_cluster(clusterName, datacenter):

    response = requests.delete(API_URL + "/deletecluster/" + clusterName + "/" + datacenter, json=clusterName)

    logging.info(f"Cluster {clusterName} is being deleted...")

def update_cluster(clusterData):
    clusterName = clusterData["clusterName"]

    response = requests.patch(API_URL + "/cluster/" + clusterName, json=clusterData)

    logging.info(f"Cluster {clusterName} is being updated...")
