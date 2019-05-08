::

   Copyright 2019 Nokia

   Licensed under the Apache License, Version 2.0 (the "License");

   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=============================================================
Ironic Drivers for Virtual media based baremetal provisioning
=============================================================

:Author:
 Chandra Shekar Rangavajjula (chandra.s.rangavajjula@nokia.com)
 Janne Suominen (janne.suominen@nokia.com)

:Version: 1.0 2019.05
:Copyright: 2019 Nokia. All rights reserved.

Introduction
============
This project contains Ironic drivers for baremetal provisioning using Virtual media for Quanta Hardware and Virtual environment. The main motivation for writing own drivers is to avoid L2 Network dependency and to support L3 based deployment.

These drivers are implimented inline with new specification *"hardware types"*

*Ref*: "https://docs.openstack.org/ironic/latest/install/enabling-drivers.html"

Effort was to reuse existing hardware interfaces to the maximum, and impliment only those which specific/different in case of Quanta hardware.
Below is a breif listing/description on needed interfaces.

1. **Management**:- Boot order settings etc. We use existing hardware interfaces **ipmi/ssh**.

   enabled_management_interfaces = ipmitool, ssh

   enabled_hardware_types = ipmi_virtmedia, ssh_virtmedia

2. **Power**:- For power managment. We use existing hardware interfaces **ipmi/ssh**.

   enabled_power_interfaces = ipmitool, ssh

   enabled_hardware_types = ipmi_virtmedia, ssh_virtmedia

3. **Deploy**:- Defines how the image gets transferred to the target disk. We use existing hardware interface **Agent/direct** mode to deploy. This reduces load on ironic coductor and scales better with larger number of nodes parallely provisioning.

   enabled_deploy_interfaces = direct

   enabled_hardware_types = ipmi_virtmedia, ssh_virtmedia

4. **Console**:- Manages access to the console of a baremetal target node. We use existing interface **ipmitool-shellinabox/ssh-shellinabox**. At the moment only ipmitool-shellinabox is confiured and used on real environments. This redirects the console to a webpage.

   enabled_console_interfaces = ipmitool-shellinabox, ssh-shellinabox

   enabled_hardware_types = ipmi_virtmedia, ssh_virtmedia

   *Ref*: "https://docs.openstack.org/ironic/latest/admin/console.html"

5. **Boot**:- Manages booting of the deploy ramdisk on the baremetal node. We have in house developed hardware interfaces **virtmedia_ipmi_boot/virtmedia_ssh_boot** for booting baremetal nodes for deployment. This expects an iso containing ironic-pyton-agent Ramdisk and a kernel.
   
   *Ref*: "https://gerrit.akraino.org/r/#/admin/projects/ta/ipa-deployer/tree/master" to check ironic-deploy.iso creation procedure. This driver creates a floppy image per baremetal node with config-data (IP, Interface, GW etc,.). Quanta hardware does not support attaching 2 Virtual media devices over NFS using IPMI. Hence this floppy image is appended to the end of node iso to make it a single iso image. The consolidated image is then attached to the target. When the target is booted from ISO it first configures its IP using "virtmedia-netconfig.service"

Below is the example output of the driver info:

# ironic driver-list

+---------------------+----------------+
| Supported driver(s) | Active host(s) |
+---------------------+----------------+
| ipmi_virtmedia      | controller-1   |
+---------------------+----------------+
| ssh_virtmedia       | controller-1   |
+---------------------+----------------+

# ironic driver-properties ipmi_virtmedia

+--------------------------+-----------------------------------------------------------------------------------------------------------+
| Property                 | Description                                                                                               |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| deploy_forces_oob_reboot | Whether Ironic should force a reboot of the Node via the out-of-band channel after deployment is complete.|
|                          | Provides compatibility with older deploy ramdisks. Defaults to False. Optional.                           |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| deploy_kernel            | UUID (from Glance) of the deployment kernel. Required.                                                    |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| deploy_ramdisk           | UUID (from Glance) of the ramdisk with agent that is used at deploy time. Required.                       |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| image_http_proxy         | URL of a proxy server for HTTP connections. Optional.                                                     |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| image_https_proxy        | URL of a proxy server for HTTPS connections. Optional.                                                    |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| image_no_proxy           | A comma-separated list of host names, IP addresses and domain names (with optional :port) that will be    |
|                          | excluded from proxying. To denote a doman name, use a dot to prefix the domain name. This value will be   |
|                          | ignored if ``image_http_proxy`` and ``image_https_proxy`` are not specified. Optional.                    |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| **ipmi_address**         | **IP address or hostname of the node. Required.**                                                         |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_bridging            | bridging_type; default is "no". One of "single", "dual", "no". Optional.                                  |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_force_boot_device   | Whether Ironic should specify the boot device to the BMC each time the server is turned on, eg. because   |
|                          | the BMC is not capable of remembering the selected boot device across power cycles; default value is False|
|                          | Optional.                                                                                                 |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_local_address       | local IPMB address for bridged requests. Used only if ipmi_bridging is set to "single" or "dual". Optional|
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| **ipmi_password**        | **password. Optional.**                                                                                   |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_port                | remote IPMI RMCP port. Optional.                                                                          |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_priv_level          | privilege level; default is ADMINISTRATOR. One of ADMINISTRATOR, CALLBACK, OPERATOR, USER. Optional.      |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_protocol_version    | the version of the IPMI protocol; default is "2.0". One of "1.5", "2.0". Optional.                        |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_target_address      | destination address for bridged request. Required only if ipmi_bridging is set to "single" or "dual".     |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_target_channel      | destination channel for bridged request. Required only if ipmi_bridging is set to "single" or "dual".     |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| **ipmi_terminal_port**   | **node's UDP port to connect to. Only required for console access.**                                      |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_transit_address     | transit address for bridged request. Required only if ipmi_bridging is set to "dual".                     |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_transit_channel     | transit channel for bridged request. Required only if ipmi_bridging is set to "dual".                     |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| ipmi_username            | username; default is NULL user. Optional.                                                                 |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| **virtmedia_deploy_iso** | **Deployment ISO image file name. Required.**                                                             |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
| **nfs_server**           | **NFS server IP hosting deployment ISO and metadata Floppy images. Required.**                            |
+--------------------------+-----------------------------------------------------------------------------------------------------------+
