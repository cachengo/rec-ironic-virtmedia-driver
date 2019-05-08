# Copyright 2019 Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json

from ironic.common.i18n import _

from ironic_virtmedia_driver.vendors.ironic_virtmedia_hw import IronicVirtMediaHW
from ironic_virtmedia_driver import virtmedia_exception

import redfish.ris.tpdefs
from redfish import AuthMethod, redfish_client
from redfish.rest.v1 import ServerDownOrUnreachableError

class HP(IronicVirtMediaHW):
    def __init__(self, log):
        super(HP, self).__init__(log)
        self.remote_share = '/bootimages/'
        self.typepath = None

    def _init_connection(self, driver_info):
        """Get connection info and init rest_object"""
        host = 'https://' + driver_info['address']
        user = driver_info['username']
        password = driver_info['password']
        redfishclient = None
        try:
            redfishclient = redfish_client(base_url=host, \
                  username=user, password=password, \
                  default_prefix="/redfish/v1")
            redfishclient.login(auth=AuthMethod.SESSION)
            self._init_typepath(redfishclient)
        except ServerDownOrUnreachableError as error:
            operation = _("iLO not responding")
            raise virtmedia_exception.VirtmediaOperationError(
                operation=operation, error=error)
        except Exception as error:
            operation = _("Failed to login to iLO")
            raise virtmedia_exception.VirtmediaOperationError(
                operation=operation, error=error)
        return redfishclient

    def _init_typepath(self, connection):
        typepath = redfish.ris.tpdefs.Typesandpathdefines()
        typepath.getgen(url=connection.get_base_url())
        typepath.defs.redfishchange()
        self.typepath = typepath

    def _search_for_type(self, typename, resources):
        instances = []
        nosettings = [item for item in resources["resources"] if "/settings/" not in item["@odata.id"]]
        for item in nosettings:
            if "@odata.type" in item and \
               typename.lower() in item["@odata.type"].lower():
                instances.append(item)
        return instances

    def _get_instances(self, connection):
        resources = {}

        response = connection.get("/redfish/v1/resourcedirectory/")
        if response.status == 200:
            resources["resources"] = response.dict["Instances"]
        else:
            return []

        return self._search_for_type("Manager.", resources)

    def _get_error(self, response):
        message = json.loads(response.text)
        error = message["error"]["@Message.ExtendedInfo"][0]["MessageId"].split(".")
        return error


    def _umount_virtual_cd(self, connection, cd_location):
        unmount_path = cd_location
        unmount_body = {"Action": "EjectVirtualMedia", "Target": self.typepath.defs.oempath}
        resp = connection.post(path=unmount_path, body=unmount_body)
        if resp.status != 200:
            self.log.error("Unmounting cd failed: %r, cd location: %r", resp, unmount_path)
            operation = _("Failed to unmount image")
            error = self._get_error(resp)
            raise virtmedia_exception.VirtmediaOperationError(
                operation=operation, error=error)


    def _get_virtual_media_devices(self, connection, instance):
        rsp = connection.get(instance["@odata.id"])
        rsp = connection.get(rsp.dict["VirtualMedia"]["@odata.id"])
        return rsp.dict['Members']

    def _mount_virtual_cd(self, connection, image_location):
        instances = self._get_instances(connection)
        for instance in instances:
            for vmlink in self._get_virtual_media_devices(connection, instance):
                response = connection.get(vmlink["@odata.id"])

                if response.status == 200 and "DVD" in response.dict["MediaTypes"]:
                    if response.dict['Inserted']:
                        self._umount_virtual_cd(connection, vmlink["@odata.id"])

                    body = {"Image": image_location}

                    if image_location:
                        body["Oem"] = {self.typepath.defs.oemhp: {"BootOnNextServerReset": \
                                                        True}}

                        response = connection.patch(path=vmlink["@odata.id"], body=body)
                elif response.status != 200:
                    self.log.error("Failed to mount image")
                    error = self._get_error(response)
                    operation = _("Failed to mount image")
                    raise virtmedia_exception.VirtmediaOperationError(
                        operation=operation, error=error)

    def attach_virtual_cd(self, image_filename, driver_info, task):
        connection = self._init_connection(driver_info)
        image_location = 'http://' + driver_info['provisioning_server'] + ':' + driver_info['provisioning_server_http_port'] + self.remote_share + image_filename
        self._mount_virtual_cd(connection, image_location)
        connection.logout()
        return True

    def detach_virtual_cd(self, driver_info, task):
        connection = self._init_connection(driver_info)
        instances = self._get_instances(connection)
        for instance in instances:
            for vmlink in self._get_virtual_media_devices(connection, instance):
                response = connection.get(vmlink["@odata.id"])
                if response.status == 200 and "DVD" in response.dict["MediaTypes"]:
                    if response.dict['Inserted']:
                        self._umount_virtual_cd(connection, vmlink["@odata.id"])
        connection.logout()
        return True

    def set_boot_device(self, task):
        """ This is done during the mounting"""
        pass
