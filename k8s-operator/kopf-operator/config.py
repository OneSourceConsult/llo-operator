from providers.kubeadm import kubeadm
from providers.liqo import liqo
from providers.apps import apps

PROVIDERS = {
   "kubeadm": kubeadm
}

LINKS = {
    "liqo": liqo
}

APPS = {
    "apps": apps
}