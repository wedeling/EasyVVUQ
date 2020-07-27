"""Provides element to execute a simulation on a Kubernetes cluster
and retrieve the output.

Examples
--------
"""

import os
import logging
import yaml
import time
import uuid
from kubernetes.client.api import core_v1_api
from kubernetes import config
from kubernetes.client import Configuration, V1ConfigMap, V1ObjectMeta
from . import BaseAction

__copyright__ = """

    Copyright 2020 Vytautas Jancauskas

    This file is part of EasyVVUQ

    EasyVVUQ is free software: you can redistribute it and/or modify
    it under the terms of the Lesser GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    EasyVVUQ is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    Lesser GNU General Public License for more details.

    You should have received a copy of the Lesser GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
__license__ = "LGPL"

logger = logging.getLogger(__name__)


class ActionStatusKubernetes():
    """Provides a way to track the status of an on-going Kubernetes
    action.

    Parameters
    ----------
    api : CoreV1Api
        will be used to communicate with the cluster
    pod_name : str
        pod identifier
    config_names : list of str
        list of ConfigMap identifiers
    namespace : str
        Kubernetes namespace
    outfile : str
        a filename to write the output of the simulation
    """
    def __init__(self, api, pod_name, config_names, namespace, outfile):
        self.core_v1 = api
        self.pod_name = pod_name
        self.config_names = config_names
        self.namespace = namespace
        self.outfile = outfile
        self.succeeded = False
    
    def finished(self):
        """Will return True if the pod has finished, otherwise will return False.
        """
        resp = self.core_v1.read_namespaced_pod(
            name=self.pod_name, namespace=self.namespace)
        if resp.status.phase not in ['Pending', 'Running']:
            if resp.status.phase == 'Succeeded':
                self.succeeded = True
            return True
        else:
            return False

    def finalise(self):
        """Will read the logs from the Kubernetes pod, output them to a file and
        delete the Kubernetes resources we have allocated.
        """
        log_ = self.core_v1.read_namespaced_pod_log(
            self.pod_name, namespace=self.namespace)
        with open(self.outfile, 'w') as fd:
            fd.write(log_)
        for _, id_ in self.config__names:
            self.core_v1.delete_namespaced_config_map(
                id_, namespace=self.namespace)
        self.core_v1.delete_namespaced_pod(
            self.pod_name, namespace=self.namespace)


    def succeeded(self):
        """Will return True if the pod has finished successfully, otherwise will return False.
        If the job hasn't finished yet will return False.
        """
        return self.succeeded


class ExecuteKubernetes(BaseAction):
    """ Provides an action element to run a shell command in a specified
    directory.

    Parameters
    ----------

    pod_config : str
        Filename of the YAML file with the Kubernetes Pod configuration.
    input_file_names : list of str
        A list of input file names for your simulation.
    output_file_name : str
        An output file name for the output of the simulation.
    """
    def __init__(self, pod_config, input_file_names, output_file_name):
        if os.name == 'nt':
            msg = ('Local execution is provided for testing on Posix systems'
                   'only. We detect you are using Windows.')
            logger.error(msg)
            raise NotImplementedError(msg)
        with open(pod_config, 'r') as fd:
            self.dep = yaml.load(fd)
        self.input_file_names = input_file_names
        self.output_file_name = output_file_name
        config.load_kube_config()
        c = Configuration()
        c.assert_hostname = False
        Configuration.set_default(c)
        self.core_v1 = core_v1_api.CoreV1Api()


    def create_volumes(self, file_names, dep):
        """Create descriptions of Volumes that will hold the input files.
        """
        volumes = [{'name': id_ + '-volume', 'configMap': {'name': id_}}
                   for _, id_ in file_names]
        volume_mounts = [{'name': id_ + '-volume',
                          'mountPath': os.path.join('/config/', os.path.basename(file_name)),
                          'subPath': os.path.basename(file_name),
                          'readOnly': True}
                         for file_name, id_ in file_names]
        dep['spec']['volumes'] = volumes
        dep['spec']['containers'][0]['volumeMounts'] = volume_mounts


    def create_config_maps(self, file_names):
        """Create Kubernetes ConfigMaps for the input files to the simulation.
        """
        for file_name, id_ in file_names:
            with open(file_name, 'r') as fd:
                data = fd.read()
            metadata = V1ObjectMeta(
                name=id_,
                namespace='default'
            )
            configmap = V1ConfigMap(
                api_version='v1',
                kind='ConfigMap',
                data={os.path.basename(file_name): data},
                metadata=metadata
            )
            self.core_v1.create_namespaced_config_map(namespace='default', body=configmap)


    def act_on_dir(self, target_dir):
        """Executes a dockerized simulation on input files found in `target_dir`.

        target_dir : str
            Directory in which to execute simulation.
        """
        file_names = [(os.path.join(target_dir, input_file_name), str(uuid.uuid4()))
                      for input_file_name in self.input_file_names]
        dep = dict(self.dep)
        self.create_config_maps(file_names)
        self.create_volumes(file_names, dep)
        dep['metadata']['name'] = str(uuid.uuid4())
        self.core_v1.create_namespaced_pod(body=dep, namespace="default")
        return ActionStatusKubernetes(
            self.core_v1, dep['metadata']['name'], file_names, 'default',
            os.path.join(target_dir, self.output_file_name))