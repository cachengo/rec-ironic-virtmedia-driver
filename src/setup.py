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

VERSION = '0.1'
PROJECT = 'ironic_virtmedia_driver'

from setuptools import setup, find_packages
setup(
    name=PROJECT,
    version=VERSION,
    description='ironic-virtmedia-driver',
    author='Chandra Rangavajjula, Janne Suominen',
    author_email='chandra.s.rangavajjula@nokia.com, janne.suominen@nokia.com',
    platforms=['Any'],
    scripts=[],
    provides=[],
    install_requires=['openstack-ironic-common', 'ironic_virtmedia_driver'],
    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'ironic.hardware.types': [
            'ipmi_virtmedia = ironic_virtmedia_driver.ipmi_virtmedia:IPMIVirtmediaHardware',
            'ssh_virtmedia = ironic_virtmedia_driver.ssh_virtmedia:SSHVirtmediaHardware'
        ],
        'ironic.hardware.interfaces.boot': [
            'virtmedia_ipmi_boot = ironic_virtmedia_driver.virtmedia_ipmi_boot:VirtualMediaAndIpmiBoot',
            'virtmedia_ssh_boot = ironic_virtmedia_driver.virtmedia_ssh_boot:VirtualMediaAndSSHBoot'
        ],
    },
    zip_safe=False,
)
