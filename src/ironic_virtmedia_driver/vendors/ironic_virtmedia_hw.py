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

class IronicVirtMediaHW(object):
    def __init__(self, log):
        self.log = log

    def attach_virtual_cd(self, image_filename, driver_info, task):
        """Attaches the given image as virtual media on the node.

        :param image_filename: the filename of the image to be attached.
        :param driver_info: the information about the node that the media
            is being attached to. (provisioning_server, ipmi params etc.)
        :param task: a TaskManager instance.
        :raises: VirtmediaOperationError if attaching virtual media failed.
        """

        raise NotImplementedError

    def detach_virtual_cd(self, driver_info, task):
        """Detach virtual cd/dvd from a node

        :param task: a TaskManager instance.
        :raises: VirtmediaOperationError if attaching virtual media failed.
        """
        raise NotImplementedError

    def set_boot_device(self, task):
        """Set virtual boot device from a node

        :param task: a TaskManager instance.
        :raises: VirtmediaOperationError if attaching virtual media failed.
        """
        raise NotImplementedError
