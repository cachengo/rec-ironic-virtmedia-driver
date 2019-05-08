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

import sys
import time

from oslo_log import log as logging

from ironic.common.i18n import _
from ironic.drivers.modules import ipmitool
from ironic.common import exception
from ironic.conductor import utils as manager_utils
from ironic_virtmedia_driver import virtmedia

LOG = logging.getLogger(__name__)

REQUIRED_PROPERTIES = {
    'provisioning_server': 'Provisioning server IP hosting deployment ISO and metadata Floppy images. Required.',
    'provisioning_server_http_port': 'Provisioning server port where the images can be obtained with http requests. Required.',
    'vendor': 'Vendor for the installed hardware. Required.',
    'product_family': 'Product family for the hardware. Required.'
}

COMMON_PROPERTIES = REQUIRED_PROPERTIES.copy()

def _parse_driver_info(node):
    """Gets the information needed for accessing the node.

    :param node: the Node of interest.
    :returns: dictionary of information.
    :raises: InvalidParameterValue if any required parameters are incorrect.
    :raises: MissingParameterValue if any required parameters are missing.

    """
    info = node.driver_info or {}
    missing_info = [key for key in REQUIRED_PROPERTIES if not info.get(key)]
    if missing_info:
        raise exception.MissingParameterValue(_(
            "virtmedia_ipmi driver requires the following parameters to be set in "
            "node's driver_info: %s.") % missing_info)

    provisioning_server = info.get('provisioning_server')
    provisioning_server_http_port = info.get('provisioning_server_http_port')
    vendor = info.get('vendor')
    product_family = info.get('product_family')
    ipmi_params = ipmitool._parse_driver_info(node)
    res = {
        'provisioning_server': provisioning_server,
        'provisioning_server_http_port': provisioning_server_http_port,
        'vendor': vendor,
        'product_family': product_family,
    }
    return dict(ipmi_params.items() + res.items())

def _get_hw_library(driver_info):
    try:
        vendor = driver_info.get('vendor').lower()
        product_family = driver_info.get('product_family').lower()
        obj = driver_info.get('product_family')

        modulename = 'ironic_virtmedia_driver.vendors.%s.%s'%(vendor, product_family)
        if modulename not in sys.modules:
            modulej = __import__(modulename, fromlist=[''])
            globals()[modulename] = modulej

        module = sys.modules[modulename]

        modj = None
        if obj in dir(module):
            modj = getattr(module, obj)
            globals()[obj] = modj
        else:
            msg = "Cannot find driver for your hardware from the module Vendor: %s Product family: %s" % (vendor, product_family)
            LOG.exception(msg)
            raise exception.NotFound(msg)

        return modj(LOG)

    except ImportError as err:
        msg = "Cannot import driver for your hardware Vendor: %s Product family: %s :: %s"% (vendor, product_family, str(err))
        LOG.exception(msg)
        raise exception.NotFound(msg)
    except KeyError as err:
        LOG.exception("virtmedia has a problem with hw type")
        raise exception.IronicException("Internal virtmedia error")
    return None

class VirtualMediaAndIpmiBoot(virtmedia.VirtmediaBoot):
    def __init__(self):
        """Constructor of VirtualMediaAndIpmiBoot.

        :raises: InvalidParameterValue, if config option has invalid value.
        """
        super(VirtualMediaAndIpmiBoot, self).__init__()

    def _attach_virtual_cd(self, task, image_filename):
        """Attaches the given url as virtual media on the node.

        :param node: an ironic node object.
        :param bootable_iso_filename: a bootable ISO image to attach to.
            The iso file should be present in NFS/CIFS server.
        :raises: VirtmediaOperationError if attaching virtual media failed.
        """
        retry_count = 2
        driver_info = _parse_driver_info(task.node)

        hw = _get_hw_library(driver_info)

        while not hw.attach_virtual_cd(image_filename, driver_info, task) and retry_count:
            retry_count -= 1
            time.sleep(1)
            LOG.debug("Virtual media attachment failed. Retrying again")

        if not retry_count:
            LOG.exception("Failed to attach Virtual media. Max retries exceeded")
            raise exception.InstanceDeployFailure(reason='NFS mount failed!')

    def _detach_virtual_cd(self, task):
        """Detaches virtual cdrom on the node.

        :param node: an ironic node object.
        :raises: VirtmediaOperationError if eject virtual cdrom failed.
        """
        driver_info = _parse_driver_info(task.node)
        hw = _get_hw_library(driver_info)
        hw.detach_virtual_cd(driver_info, task)

    def _set_deploy_boot_device(self, task):
        """Set the boot device for deployment"""
        driver_info = _parse_driver_info(task.node)
        hw = _get_hw_library(driver_info)
        hw.set_boot_device(task)
