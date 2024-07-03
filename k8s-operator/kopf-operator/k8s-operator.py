import kopf
import logging
import kubernetes
from prometheus_client import start_http_server, Gauge, Counter
import config
import os

# METRICS DEFINITION

num_clusters = Gauge('clusters_num', 'Number of currently running clusters in all providers')
num_providers = Gauge('providers_num', 'Number of currently running providers within ClusterAPI')
num_apps = Gauge('apps_num', 'Number of currently deployed apps via the orchestrator')
num_components = Gauge('components_num', 'Number of currently deployed components via the orchestrator')

def init_prometheus():
    # Start up the server to expose the metrics.
    start_http_server(8000)

    logging.info("PROMETHEUS UP AND RUNNING...")

@kopf.on.startup()
def operator_init(settings: kopf.OperatorSettings,logger, **kwargs):
    settings.persistence.progress_storage = kopf.StatusProgressStorage(field='status.kopf')
    logging.info("STARTING OPERATOR!!!")


    # Load Kubernetes configuration from default location
    kubernetes.config.load_kube_config(os.environ["KUBECONFIG"])
    # Create Kubernetes API client
    api_client = kubernetes.client.ApiClient()
    api_instance = kubernetes.client.CustomObjectsApi(api_client)
    api_response = api_instance.list_cluster_custom_object(
        group="charity-project.eu",
        version="v1",
        plural="lowlevelorchestrations"
    )

    init_prometheus()

    for resource in api_response["items"]:
        check_metrics(resource)

# kubernetes_config.load_kube_config()
# api = kubernetes_client.CoreV1Api()

# #TODO: Check errors during creation
# #TODO: Async creation

# @kopf.on.startup()
# def configure(settings: kopf.OperatorSettings, **_):
#     # Get the LoadBalancer service object
#     service = api.read_namespaced_service(os.environ["WEBHOOK_SERVICE_NAME"], os.environ["WEBHOOK_SERVICE_NAMESPACE"])

#     # Get the IP address assigned by the LoadBalancer
#     load_balancer_ip = service.status.load_balancer.ingress[0].ip

#     logging.info(f"The LoadBalancer IP is {load_balancer_ip}")

#     settings.admission.server = kopf.WebhookServer(addr='0.0.0.0', port=6000, host=load_balancer_ip)
#     # settings.admission.managed = 'auto.kopf.dev'
#     settings.admission.managed = 'lowlevelorchestrations.charity-project.eu'



#-----------------------WEBHOOKS-----------------------

# @kopf.on.validate("lowlevelorchestrations")
# def validate_crd(old, new, **kwargs):
#     for old_cluster in old['spec']['clusters']:
#         for new_cluster in new['spec']['clusters']:
#             if old_cluster['name'] != new_cluster['name']:
#                 raise kopf.AdmissionError("The 'name' field of the object is immutable.")
#             elif old_cluster['provider'] != new_cluster['provider']:
#                 raise kopf.AdmissionError("The 'provider' field of the object is immutable.")
#             elif old_cluster['worker-machine-flavor'] != new_cluster['worker-machine-flavor']:
#                 raise kopf.AdmissionError("The 'worker-machine-flavor' field of the object is immutable.")
#             elif old_cluster['control-plane-flavor'] != new_cluster['control-plane-flavor']:
#                 raise kopf.AdmissionError("The 'control-plane-flavor' field of the object is immutable.")
#             elif old_cluster['image'] != new_cluster['image']:
#                 raise kopf.AdmissionError("The 'image' field of the object is immutable.")
#             # elif int(new_cluster['worker-machine-count']) < 0:
#             #     raise kopf.AdmissionError("The number of workers cannot be a negative number")
#             # elif int(new_cluster['control-plane-count']) < 1:
#             #     raise kopf.AdmissionError("You need at least one control plane")

# @kopf.on.mutate("lowlevelorchestrations")
# def mutate_crd(old, new, **kwargs):
#     logging.info("ENTREI NO MUTATE")

#-----------------------WEBHOOKS-----------------------

@kopf.on.create("lowlevelorchestrations") # type: ignore
def llorchestration_create(body, **kwargs):
    # logging.info("CLUSTER CREATED!!!")
    llorch_name = body["metadata"]["name"]
    
    if "spec" in body and "clusters" in body["spec"]:
        clusters = body["spec"]["clusters"]
    else:
        clusters = []
    
    for cluster in clusters:
        cluster_name = cluster["name"]
        provider = cluster["kubernetes-type"]

        clusterData = {
            "clusterName":  cluster_name,
            "kubernetesType": "kubeadm",
            "kubernetesVersion": cluster["kubernetes-version"],
            "controlPlaneCount": cluster["control-plane-count"],
            "controlPlaneFlavor": cluster["control-plane-flavor"],
            "workerMachineCount": cluster["worker-machine-count"],
            "workerMachineFlavor": cluster["worker-machine-flavor"],
            "image": cluster["image"],
            "status": cluster["status"],
            "datacenter": cluster["datacenter"]
        }

        logging.info(clusterData)
        # if cluster["provider"] != "external":
        provider_module = config.PROVIDERS[provider]
        provider_module.create_cluster(clusterData)
        logging.info(f"Lowlevel Orchestration cluster created {clusterData}")
    # else:
        logging.info(f"Cluster {cluster_name} added to the CRD")

    if "spec" in body and "links" in body["spec"]:
        links = body["spec"]["links"]
    else:
        links = []

    for link in links:
        
        linkData = {
            "greenClusterName":  link[0],
            "roseClusterName":  link[1]
        }

        link_module = config.LINKS["liqo"]
        link_module.link_clusters(linkData)
        
        logging.info(f"Lowlevel Orchestration link created {linkData}")
    

    if "spec" in body and "apps" in body["spec"]:
        apps = body["spec"]["apps"]
    else:
        apps = []

    for app in apps:   
        appData = {
            "name": app["name"],
            "owner": app["owner"],
            "cluster":  app["cluster"],
            "components": app["components"],
            "id": app["id"],
            "status": app["status"],
            "crd_name": llorch_name
        }

        # logging.info(appData)        

        app_module = config.APPS["apps"]
        app_module.install_app(appData)
        
        logging.info(f"Lowlevel Orchestration app created {appData}")

    check_metrics(body)
@kopf.on.delete("lowlevelorchestrations") # type: ignore
def llorchestration_delete(body, old, new, **kwargs):

    changes_clusters = diff_clusters(old, new)
    change_apps = diff_apps(old, new)

    llorch_name = body["metadata"]["name"]
    
    if len(change_apps['delete']) >= 1:
        for app in change_apps['delete']:
            app_module = config.APPS["apps"]
            appData = {
                "name": app["name"],
                "cluster":   app["cluster"],
                "id": app["id"] 
            }

            app_module.uninstall_app(appData)

            logging.info(f"Lowlevel Orchestration app deleted {appData}")
    else:
        logging.info("Skipping deletion of the whole CRD")

    if len(changes_clusters['delete']) >= 1:
        for cluster in changes_clusters['delete']:
            cluster_name = cluster["name"]
            provider = cluster["kubernetes-type"]
            if cluster["status"] == "error":
                logging.info("Skipping deletion of the whole CRD")
            else: 
                provider_module = config.PROVIDERS[provider]
                provider_module.delete_cluster(cluster_name, cluster["datacenter"])
                logging.info(f"Lowlevel Orchestration delete {provider} {provider_module}")
    else:
        logging.info("Skipping deletion of the whole CRD")
    
    check_metrics(body)


@kopf.on.update("lowlevelorchestrations") # type: ignore
def llorchestration_update(body, spec, old, new, diff, **_kwargs):
    
    
    llorch_name = body["metadata"]["name"]
    change = False
        
    changes_clusters = diff_clusters(old, new)
    change_apps = diff_apps(old, new)

    changes_links = diff_links(old, new)


    #logging.info(changes_links)

    # logging.info(change_apps)

    for app in change_apps['create']:
        appData = {
            "name": app["name"],
            "owner": app["owner"],
            "cluster":  app["cluster"],
            "components": app["components"],
            "id" : app["id"],
            "crd_name": llorch_name
        }

        # logging.info(appData)        

        app_module = config.APPS["apps"]
        app_module.install_app(appData)
        
        logging.info(f"Lowlevel Orchestration app created {appData}")

    for app in change_apps['delete']:
        app_module = config.APPS["apps"]
        appData = {
            "name": app["name"],
            "cluster":  app["cluster"],
            "id": app["id"] 
        }

        logging.info(appData)
        app_module.uninstall_app(appData)

        logging.info(f"Lowlevel Orchestration app deleted {appData}")

    for cluster in changes_clusters['create']:
        provider = cluster["kubernetes-type"]
        provider_module = config.PROVIDERS[provider]
        cluster_name = cluster["name"]
        clusterData = {
                        "clusterName":  cluster["name"],
                        "kubernetesType": "kubeadm",
                        "kubernetesVersion": cluster["kubernetes-version"],
                        "controlPlaneCount": cluster["control-plane-count"],
                        "controlPlaneFlavor": cluster["control-plane-flavor"],
                        "workerMachineCount": cluster["worker-machine-count"],
                        "workerMachineFlavor": cluster["worker-machine-flavor"],
                        "image": cluster["image"],
                        "datacenter": cluster["datacenter"]

                    }

        # if cluster["provider"] != "external":
        provider_module = config.PROVIDERS[provider]
        provider_module.create_cluster(clusterData)
        logging.info(f"Lowlevel Orchestration cluster created {clusterData}")
    # else:
        logging.info(f"Cluster {cluster_name} added to the CRD")
        
        logging.info(f"Lowlevel Orchestration resource created {provider} {provider_module}")
        
    for old_cluster in changes_clusters['update']['old']:
        for new_cluster in changes_clusters['update']['new']:
            change = False
            provider = new_cluster['kubernetes-type']
            provider_module = config.PROVIDERS[provider]
            
            if new_cluster['control-plane-count'] != old_cluster['control-plane-count']:
                change = True
                
            elif new_cluster['worker-machine-count'] != old_cluster['worker-machine-count']:
                change = True
            
            if change == True:
                clusterData = {
                        "clusterName":  new_cluster["name"],
                        "kubernetesType": "kubeadm",
                        "kubernetesVersion": new_cluster["kubernetes-version"],
                        "controlPlaneCount": new_cluster["control-plane-count"],
                        "controlPlaneFlavor": new_cluster["control-plane-flavor"],
                        "workerMachineCount": new_cluster["worker-machine-count"],
                        "workerMachineFlavor": new_cluster["worker-machine-flavor"],
                        "image": new_cluster["image"]
                    }
                if new_cluster["provider"] != "external":
                    provider_module.update_cluster(clusterData)

                else:
                    logging.info(f"Cluster {cluster_name} added to the CRD")

    for cluster in changes_clusters['delete']:
        cluster_name = cluster["name"]
        provider = cluster["kubernetes-type"]
        if cluster["status"] == "error":
            logging.info("Skipping deletion of the whole CRD")
        else:  
            
            # if cluster["provider"] != "external":
            provider_module = config.PROVIDERS[provider]
            provider_module.delete_cluster(cluster_name, cluster["datacenter"])
            logging.info(f"Lowlevel Orchestration delete {provider} {provider_module}")
        # else:
            logging.info(f"Cluster {cluster_name} added to the CRD")

                

    for links in changes_links['create']:
        linkData = {
            "greenClusterName":  links[0],
            "roseClusterName":  links[1]
        }

        link_module = config.LINKS["liqo"]
        link_module.link_clusters(linkData)

    check_metrics(body)



def diff_clusters(old, new):
    if "spec" in old and "clusters" in old['spec']:
        old_clusters = old['spec']['clusters']
    else:
        old_clusters = {}
    
    if "spec" in new and "clusters" in new['spec']:
        new_clusters = new['spec']['clusters']
    else:
        new_clusters = {}
    
    create_clusters = []
    update_clusters = {'old': [], 'new': []}
    delete_clusters = []

    # Check for create and update clusters
    for new_cluster in new_clusters:
        match_found = False
        for old_cluster in old_clusters:
            if new_cluster['name'] == old_cluster['name']:
                match_found = True
                
                # Extract the status to ignore changes in it
                new_cluster_status= new_cluster.pop("status")
                old_cluster_status= old_cluster.pop("status")

                # If the change in the cluster is just the status, ignore to avoid loops: 
                if new_cluster != old_cluster:
                 
                    update_clusters['old'].append(old_cluster)
                    update_clusters['new'].append(new_cluster)
                
                #Put the status back
                new_cluster['status'] = new_cluster_status
                old_cluster['status'] = old_cluster_status
                break
        if not match_found:
            create_clusters.append(new_cluster)

    # Check for delete clusters
    for old_cluster in old_clusters:
        match_found = False
        for new_cluster in new_clusters:
            if old_cluster['name'] == new_cluster['name']:
                match_found = True
                break
        if not match_found and len(old_cluster) > 1:
            delete_clusters.append(old_cluster)

    diff = {
        'create': create_clusters,
        'update': update_clusters,
        'delete': delete_clusters
    }

    return diff

def diff_links(old, new):
    if "spec" in old and "links" in old['spec']:
        old_links = old['spec']['links']
    else:
        old_links = []

    if "spec" in new and "links" in new['spec']:
        new_links = new['spec']['links']
    else:
        new_links = []

    create_links = []
    update_links = {'old': [], 'new': []}
    delete_links = []

    # Check for create and update links
    for new_link in new_links:
        match_found = False
        for old_link in old_links:
            if new_link[0] == old_link[0]:
                match_found = True
                if new_link[1] != old_link[1]:
                    update_links['old'].append(old_link)
                    update_links['new'].append(new_link)
                break
        if not match_found:
            create_links.append(new_link)

    # Check for delete links
    for old_link in old_links:
        match_found = False
        for new_link in new_links:
            if old_link[0] == new_link[0]:
                match_found = True
                break
        if not match_found:
            delete_links.append(old_link)

    diff = {
        'create': create_links,
        'update': update_links,
        'delete': delete_links
    }

    return diff

def diff_apps(old, new):
    if "spec" in old and "apps" in old['spec']:
        old_apps = old['spec']['apps']
    else:
        old_apps = []

    if "spec" in new and "apps" in new['spec']:
        new_apps = new['spec']['apps']
    else:
        new_apps = []

    create_apps = []
    update_apps = {'old': [], 'new': []}
    delete_apps = []

    for new_app in new_apps:
        match_found = False
        for old_app in old_apps:
            if new_app["id"] == old_app["id"]:
                match_found = True
                new_app_status= new_app.pop("status")
                old_app_status= old_app.pop("status")

                # If the change in the app is just the status, ignore to avoid loops: 
                if new_app != old_app:
                 
                    update_apps['old'].append(old_app)
                    update_apps['new'].append(new_app)
                
                #Put the status back
                new_app['status'] = new_app_status
                old_app['status'] = old_app_status
                break
        if not match_found:
            create_apps.append(new_app)

    # Check for delete apps
    for old_app in old_apps:
        match_found = False
        for new_app in new_apps:
            if old_app["id"] == new_app["id"]:
                match_found = True
                break
        if not match_found:
            delete_apps.append(old_app)

    diff = {
        'create': create_apps,
        'update': update_apps,
        'delete': delete_apps
    }

    return diff
    
def check_metrics(body):
    if body:
        apps = []
        clusters = []
        components = 0
        providers = []

        
        if "spec" in body:
            if "clusters" in body["spec"]:
                clusters = body["spec"]["clusters"]
                for cluster in clusters:
                    if "kubernetes-type" in cluster:
                        providers.append(cluster["kubernetes-type"])
            if "apps" in body["spec"]:
                apps = body["spec"]["apps"]
            

            for app in apps:
                if "components" in app:
                    components += len(app["components"])

        num_clusters.set(len(clusters))
        num_apps.set(len(apps))
        num_components.set(components)
        num_providers.set(len(set(providers)))
    else:
        num_providers.set(0)
        num_clusters.set(0)
        num_apps.set(0)
        num_components.set(0)