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

import time

from ironic.drivers.modules import ipmitool
from ironic.conductor import utils as manager_utils
from ironic.common import exception
from ironic.common import boot_devices

from .nokia_hw import NokiaIronicVirtMediaHW

class HW17(NokiaIronicVirtMediaHW):
    def __init__(self, log):
        super(HW17, self).__init__(log)

    def get_disk_attachment_status(self, task):
        # Check NFS Service Status
        (out, err) = ipmitool.send_raw(task, '0x3c 0x03')
        self.log.debug("get_disk_attachment_status: NFS service status: error:%r, output:%r" %(err, out))
        if out == ' 00\n':
            return 'mounted'
        elif out == ' 64\n':
            return 'mounting'
        elif out == ' 20\n':
            return 'nfserror'
        else:
            return 'dismounted'

    def attach_virtual_cd(self, image_filename, driver_info, task):

        # Stop virtual device and Clear NFS configuration
        ipmitool.send_raw(task, '0x3c 0x0')
        # Set NFS Configurations
        # NFS server IP
        ipmitool.send_raw(task, '0x3c 0x01 0x00 %s 0x00' %(self.hex_convert(driver_info['provisioning_server'])))
        # Set NFS Mount Root path
        ipmitool.send_raw(task, '0x3c 0x01 0x01 %s 0x00' %(self.hex_convert(self.remote_share)))
        # Set Image Name
        ipmitool.send_raw(task, '0x3c 0x01 0x02 %s 0x00' %(self.hex_convert(image_filename)))
        # Start NFS Service
        ipmitool.send_raw(task, '0x3c 0x02 0x01')

        time.sleep(1)

        return self.check_and_wait_for_cd_mounting(image_filename, task, driver_info)

    def detach_virtual_cd(self, driver_info, task):
        """Detaches virtual cdrom on the node.

        :param task: an ironic task object.
        """
        # Stop virtual device and Clear NFS configuration
        self.log.debug("detach_virtual_cd")
        ipmitool.send_raw(task, '0x3c 0x00')

    def set_boot_device(self, task):
        manager_utils.node_set_boot_device(task, boot_devices.FLOPPY, persistent=True)
