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

from ironic.conductor import utils as manager_utils
from ironic.common import boot_devices
from ironic.common import exception

from .rm18 import RM18

class OE19(RM18):
    def __init__(self, log):
        super(OE19, self).__init__(log)

    def set_boot_device(self, task):
        manager_utils.node_set_boot_device(task, boot_devices.FLOPPY, persistent=True)


