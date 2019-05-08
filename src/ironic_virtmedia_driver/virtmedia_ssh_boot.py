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

import os

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import strutils

import retrying
import paramiko
import six

from ironic.common import exception
from ironic.common import utils
from ironic.common.i18n import _, _translators
from ironic.drivers import utils as driver_utils
from ironic.conf import CONF
from ironic_virtmedia_driver import virtmedia

LOG = logging.getLogger(__name__)

REQUIRED_PROPERTIES = {
    'ssh_address': _("IP address of the node to ssh into from where the VMs can be managed. "
                     "Required."),
    'ssh_username': _("username to authenticate as. Required."),
    'ssh_key_contents': _("private key(s). If ssh_password is also specified "
                          "it will be used for unlocking the private key. Do "
                          "not specify ssh_key_filename when this property is "
                          "specified.")
}

COMMON_PROPERTIES = REQUIRED_PROPERTIES.copy()
CONSOLE_PROPERTIES = {
    'ssh_terminal_port': _("node's UDP port to connect to. Only required for "
                           "console access and only applicable for 'virsh'.")
}

def _get_command_sets():
    """Retrieves the virt_type-specific commands.
    Returns commands are as follows:

    base_cmd: Used by most sub-commands as the primary executable
    list_all: Lists all VMs (by virt_type identifier) that can be managed.
        One name per line, must not be quoted.
    get_disk_list: Gets the list of Block devices connected to the VM
    attach_disk_device: Attaches a given disk device to VM
    detach_disk_device: Detaches a disk device from a VM
    """
    virt_type="virsh"
    if virt_type == "virsh":
        virsh_cmds = {
            'base_cmd': 'LC_ALL=C /usr/bin/virsh',
            'list_all': 'list --all --name',
            'get_disk_list': (
                "domblklist --domain {_NodeName_} | "
                "grep var | awk -F \" \" '{print $1}'"),
            'attach_disk_device': 'attach-disk --domain {_NodeName_} --source /var/lib/libvirt/images/{_ImageName_} --target {_TargetDev_} --sourcetype file --mode readonly --type {_DevType_} --config',
            'detach_disk_device': 'detach-disk --domain {_NodeName_} --target {_TargetDev_} --config',
        }

        return virsh_cmds
    else:
        raise exception.InvalidParameterValue(_(
            "SSHPowerDriver '%(virt_type)s' is not a valid virt_type, ") %
            {'virt_type': virt_type})

def _ssh_execute(ssh_obj, cmd_to_exec):
    """Executes a command via ssh.

    Executes a command via ssh and returns a list of the lines of the
    output from the command.

    :param ssh_obj: paramiko.SSHClient, an active ssh connection.
    :param cmd_to_exec: command to execute.
    :returns: list of the lines of output from the command.
    :raises: SSHCommandFailed on an error from ssh.

    """
    LOG.debug(_translators.log_error("Executing SSH cmd: %r"), cmd_to_exec)
    try:
        output_list = processutils.ssh_execute(ssh_obj,
                                               cmd_to_exec)[0].split('\n')
    except Exception as e:
        LOG.error(_translators.log_error("Cannot execute SSH cmd %(cmd)s. Reason: %(err)s."),
                  {'cmd': cmd_to_exec, 'err': e})
        raise exception.SSHCommandFailed(cmd=cmd_to_exec)

    return output_list


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
            "SSHPowerDriver requires the following parameters to be set in "
            "node's driver_info: %s.") % missing_info)

    address = info.get('ssh_address')
    username = info.get('ssh_username')
    key_contents = info.get('ssh_key_contents')
    terminal_port = info.get('ssh_terminal_port')

    if terminal_port is not None:
        terminal_port = utils.validate_network_port(terminal_port,
                                                    'ssh_terminal_port')

    # NOTE(deva): we map 'address' from API to 'host' for common utils
    res = {
        'host': address,
        'username': username,
        'port': 22,
        'uuid': node.uuid,
        'terminal_port': terminal_port
    }

    cmd_set = _get_command_sets()
    res['cmd_set'] = cmd_set

    if key_contents:
        res['key_contents'] = key_contents
    else:
        raise exception.InvalidParameterValue(_(
            "ssh_virtmedia Driver requires ssh_key_contents to be set."))
    return res

def _get_ssh_connection(connection):
    """Returns an SSH client connected to a node.

    :param node: the Node.
    :returns: paramiko.SSHClient, an active ssh connection.

    """
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key_contents = connection.get('key_contents')
        if key_contents:
            data = six.StringIO(key_contents)
            if "BEGIN RSA PRIVATE" in key_contents:
                pkey = paramiko.RSAKey.from_private_key(data)
            elif "BEGIN DSA PRIVATE" in key_contents:
                pkey = paramiko.DSSKey.from_private_key(data)
            else:
                # Can't include the key contents - secure material.
                raise ValueError(_("Invalid private key"))
        else:
            pkey = None
        ssh.connect(connection.get('host'),
                    username=connection.get('username'),
                    password=None,
                    port=connection.get('port', 22),
                    pkey=pkey,
                    key_filename=connection.get('key_filename'),
                    timeout=connection.get('timeout', 10))

        # send TCP keepalive packets every 20 seconds
        ssh.get_transport().set_keepalive(20)
    except Exception as e:
        LOG.debug("SSH connect failed: %s", e)
        raise exception.SSHConnectFailed(host=connection.get('host'))

    return ssh

def _get_disk_attachment_status(driver_info, node_name, ssh_obj, target_disk='hda'):
    cmd_to_exec = "%s %s" % (driver_info['cmd_set']['base_cmd'],
                             driver_info['cmd_set']['get_disk_list'])
    cmd_to_exec = cmd_to_exec.replace('{_NodeName_}', node_name)
    blk_dev_list = _ssh_execute(ssh_obj, cmd_to_exec)
    LOG.debug("Attached block devices list for node %(node_name)s: %(blk_dev_list)s", {'node_name': node_name, 'blk_dev_list': blk_dev_list})
    if target_disk in blk_dev_list:
        return True
    else:
        return False

def _get_sftp_connection(connection):
    try:
        key_contents = connection.get('key_contents')
        if key_contents:
            data = six.StringIO(key_contents)
            if "BEGIN RSA PRIVATE" in key_contents:
                pkey = paramiko.RSAKey.from_private_key(data)
            elif "BEGIN DSA PRIVATE" in key_contents:
                pkey = paramiko.DSSKey.from_private_key(data)
            else:
                # Can't include the key contents - secure material.
                raise ValueError(_("Invalid private key"))
        else:
            pkey = None

        sftp_obj = paramiko.Transport((connection.get('host'), connection.get('port', 22)))
        sftp_obj.connect(None, username=connection.get('username'),
                    password=None, pkey=pkey)
        return sftp_obj
    except Exception as e:
        LOG.error(_translators.log_error("Cannot establish connection to sftp target. Reason: %(err)s."),
                  {'err': e})
        raise exception.CommunicationError(e)

def _copy_media_to_virt_server(sftp_obj, media_file):
    LOG.debug("Copying file: %s to target" %(media_file))
    sftp = paramiko.SFTPClient.from_transport(sftp_obj)
    try:
        sftp.put('/remote_image_share_root/%s' %media_file, '/var/lib/libvirt/images/%s' %media_file)
    except Exception as e:
        LOG.error(_translators.log_error("Cannot copy %(media_file)s to target. Reason: %(err)s."),
                  {'media_file': media_file, 'err': e})
        raise exception.CommunicationError(media_file)

class VirtualMediaAndSSHBoot(virtmedia.VirtmediaBoot):
    def __init__(self):
        """Constructor of VirtualMediaAndSSHBoot.

        :raises: InvalidParameterValue, if config option has invalid value.
        """
        super(VirtualMediaAndSSHBoot, self).__init__()

    def _attach_virtual_cd(self, task, image_filename):
        driver_info = _parse_driver_info(task.node)
        ssh_obj = _get_ssh_connection(driver_info)
        sftp_obj = _get_sftp_connection(driver_info)
        node_name = task.node.name
        if _get_disk_attachment_status(driver_info, node_name, ssh_obj, 'hda'):
            LOG.debug("A CD is already attached to node %s, not taking any action", node_name)
            return

        _copy_media_to_virt_server(sftp_obj, image_filename)
        cmd_to_exec = "%s %s" % (driver_info['cmd_set']['base_cmd'],
                                 driver_info['cmd_set']['attach_disk_device'])
        cmd_to_exec = cmd_to_exec.replace('{_NodeName_}', node_name)
        cmd_to_exec = cmd_to_exec.replace('{_ImageName_}', image_filename)
        cmd_to_exec = cmd_to_exec.replace('{_TargetDev_}', 'hda')
        cmd_to_exec = cmd_to_exec.replace('{_DevType_}', 'cdrom')
        LOG.debug("Ironic node-name: %s, virsh domain name: %s, image_filename: %s" %(task.node.name, node_name, image_filename))

        _ssh_execute(ssh_obj, cmd_to_exec)

    def _detach_virtual_cd(self, task):
        driver_info = _parse_driver_info(task.node)
        ssh_obj = _get_ssh_connection(driver_info)
        node_name = task.node.name

        if not _get_disk_attachment_status(driver_info, node_name, ssh_obj, 'hda'):
            LOG.debug("No CD is attached to node %s, not taking any action", node_name)
            return

        cmd_to_exec = "%s %s" % (driver_info['cmd_set']['base_cmd'],
                                 driver_info['cmd_set']['detach_disk_device'])
        cmd_to_exec = cmd_to_exec.replace('{_NodeName_}', node_name)
        cmd_to_exec = cmd_to_exec.replace('{_TargetDev_}', 'hda')
        _ssh_execute(ssh_obj, cmd_to_exec)
