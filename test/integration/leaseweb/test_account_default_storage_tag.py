# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
""" tests for Default storage tag for Account in 4.11.2-leaseweb

    JIRA ticket: https://jira.ocom.com/browse/CLSTACK-4604

"""
# Import Local Modules
from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import cloudstackTestCase, unittest
from marvin.lib.utils import (validateList,
                              cleanup_resources)
from marvin.lib.base import (Account, VirtualMachine, Domain, Network, NetworkOffering, ServiceOffering, 
                            DiskOffering, Configurations, StoragePool, Volume)
from marvin.lib.common import get_domain, get_zone, get_template

class TestAccountDefaultStorageTag(cloudstackTestCase):

    @classmethod
    def setUpClass(self):
        self.testClient = super(
            TestAccountDefaultStorageTag,
            self).getClsTestClient()
        self.apiclient = self.testClient.getApiClient()
        self.testdata = self.testClient.getParsedTestDataConfig()

        # (1) get zone/domain/template/pools
        self.domain = get_domain(self.apiclient)
        self.zone = get_zone(self.apiclient, self.testClient.getZoneForTests())
        self.template = get_template(self.apiclient, self.zone.id, template_filter="all", template_type='USER')

        try:
            self.pools = StoragePool.list(self.apiclient, zoneid=self.zone.id)
        except Exception as e:
            self.skiptest = True
            return

        # (2) create domain/account
        self.user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        self.account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=self.user_domain.id
        )

        # (3) create shared network offering
        self.testdata["shared_network_offering"]["specifyVlan"] = 'True'
        self.testdata["shared_network_offering"]["specifyIpRanges"] = 'True'
        self.testdata["shared_network_offering"]["tags"] = None

        self.shared_network_offering = NetworkOffering.create(
            self.apiclient,
            self.testdata["shared_network_offering"]
        )

        NetworkOffering.update(
            self.shared_network_offering,
            self.apiclient,
            id=self.shared_network_offering.id,
            state="enabled"
        )

        # (4) create a shared network
        self.network = Network.create(
            self.apiclient,
            self.testdata["network2"],
            networkofferingid=self.shared_network_offering.id,
            zoneid=self.zone.id,
            accountid=self.account.name,
            domainid=self.account.domainid
        )

        # (5) add account/domain/network to cleanup_resources
        self._cleanup = []
        self._cleanup.append(self.network)
        self._cleanup.append(self.shared_network_offering)
        self._cleanup.append(self.account)
        self._cleanup.append(self.user_domain)

        Configurations.update(
            self.apiclient,
            name="vm.destroy.forcestop",
            value="true")

        return

    @classmethod
    def tearDownClass(self):
        try:
            # Cleanup resources used
            cleanup_resources(self.apiclient, self._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []

        return

    def tearDown(self):
        try:
            for storagePool in self.pools:
                StoragePool.update(self.apiclient, id=storagePool.id, tags="")

            Configurations.update(
                self.apiclient,
                name="account.default.storage.tag",
                value="")
            Configurations.update(
                self.apiclient,
                accountid=self.account.id,
                name="account.default.storage.tag",
                value="")

            # Clean up
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_01_success_vm_deployment_with_tagged_offerings_on_tagged_pool(self):
        """Deploy vm with tagged service/disk offerings to tagged storage pool

        # Validate the following:
        (0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        (1) get a storage pool and set storage pool tag to test2
        (2) create service offering with storage tag test2
        (3) create disk offering with storage tag test2
        (4) deploy a vm with service offering (2) and disk offering (3) in the network
        (5) check vm volumes should be stored in the pool
        """

        #(0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="false")

        #(1) get a storage pool and set storage pool tag to test2
        storage_pool = self.pools[0]
        StoragePool.update(self.apiclient, id=storage_pool.id, tags="test2")

        #(2) create service offering with storage tag test2
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"],
            tags="test2"
        )
        self.cleanup.append(self.service_offering)

        #(3) create disk offering with storage tag test2
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"],
            tags="test2"
        )
        self.cleanup.append(self.disk_offering)

        #(4) deploy a vm with service offering (2) and disk offering (3) in the network
        vm1 = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            domainid=self.user_domain.id,
            zoneid=self.zone.id,
            templateid=self.template.id,
            diskofferingid=self.disk_offering.id,
            serviceofferingid=self.service_offering.id)

        #(5) check vm volumes should be stored in the pool
        volumes = Volume.list(
            self.apiclient,
            virtualmachineid=vm1.id,
            listall=True
        )
        for volume in volumes:
            self.assertEqual(volume.storageid, storage_pool.id, "Volumes should be allocated to the pool with tag test2")

        VirtualMachine.delete(vm1, self.apiclient, expunge=True)
        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_02_success_vm_deployment_with_untagged_offerings_on_tagged_pool(self):
        """Deploy vm with untagged service/disk offerings to tagged storage pool

        # Validate the following:
        (0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        (1) get a storage pool and set storage pool tag to test2
        (6) create service offering with no storage tag
        (7) create disk offering with no storage tag
        (8) set account/account.default.storage.tag to test2
        (9) deploy a vm with service offering (6) and disk offering (7) in the network
        (10) check vm volumes should be stored in the pool
        """

        #(0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="false")

        #(1) get a storage pool and set storage pool tag to test2
        storage_pool = self.pools[0]
        StoragePool.update(self.apiclient, id=storage_pool.id, tags="test2")

        #(6) create service offering with no storage tag
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"]
        )
        self.cleanup.append(self.service_offering)

        #(7) create disk offering with no storage tag
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"]
        )
        self.cleanup.append(self.disk_offering)

        #(8) set account/account.default.storage.tag to test2
        configs = Configurations.update(
            self.apiclient,
            accountid=self.account.id,
            name="account.default.storage.tag",
            value="test2")

        #(9) deploy a vm with service offering (6) and disk offering (7) in the network
        vm2 = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            domainid=self.user_domain.id,
            zoneid=self.zone.id,
            templateid=self.template.id,
            diskofferingid=self.disk_offering.id,
            serviceofferingid=self.service_offering.id)

        #(10) check vm volumes should be stored in the pool
        volumes = Volume.list(
            self.apiclient,
            virtualmachineid=vm2.id,
            listall=True
        )
        for volume in volumes:
            self.assertEqual(volume.storageid, storage_pool.id, "Volumes should be allocated to the pool with tag test2")

        VirtualMachine.delete(vm2, self.apiclient, expunge=True)
        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_03_success_vm_deployment_with_untagged_offerings_on_tagged_pool(self):
        """Deploy vm with untagged service/disk offerings to tagged storage pool

        # Validate the following:
        (0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        (11) set storage pool tag to test2,test3
        (12) set global/account.default.storage.tag to test3
        (13) set account/account.default.storage.tag to null
        (14) deploy a vm with service offering (6) and disk offering (7) in the network
        (15) check vm volumes should be stored in the pool
        (16) set global/account.default.storage.tag to null
        """

        #(0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="false")

        #(11) set storage pool tag to test2,test3
        storage_pool = self.pools[0]
        StoragePool.update(self.apiclient, id=storage_pool.id, tags="test2,test3")

        #(12) set global/account.default.storage.tag to test3
        configs = Configurations.update(
            self.apiclient,
            name="account.default.storage.tag",
            value="test3")

        #(6) create service offering with no storage tag
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"]
        )
        self.cleanup.append(self.service_offering)

        #(7) create disk offering with no storage tag
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"]
        )
        self.cleanup.append(self.disk_offering)

        #(14) deploy a vm with service offering (6) and disk offering (7) in the network
        vm3 = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            domainid=self.user_domain.id,
            zoneid=self.zone.id,
            templateid=self.template.id,
            diskofferingid=self.disk_offering.id,
            serviceofferingid=self.service_offering.id)

        #(15) check vm volumes should be stored in the pool
        volumes = Volume.list(
            self.apiclient,
            virtualmachineid=vm3.id,
            listall=True
        )
        for volume in volumes:
            self.assertEqual(volume.storageid, storage_pool.id, "Volumes should be allocated to the pool with tag test2")

        VirtualMachine.delete(vm3, self.apiclient, expunge=True)
        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_04_success_vm_deployment_with_untagged_offerings_on_all_pool(self):
        """Deploy vm with untagged service/disk offerings to all storage pools

        # Validate the following:
        (16) set global/account.default.storage.tag to null
        (17) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to true
        (18) get all storage pool and set storage pools tag to test2
        (19) deploy a vm with service offering (6) and disk offering (7) in the network, operation should succeed
        """

        #(16) set global/account.default.storage.tag to null

        #(17) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to true
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="true")

        #(6) create service offering with no storage tag
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"]
        )
        self.cleanup.append(self.service_offering)

        #(7) create disk offering with no storage tag
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"]
        )
        self.cleanup.append(self.disk_offering)

        #(18) get all storage pool and set storage pools tag to test2
        for storagePool in self.pools:
            StoragePool.update(self.apiclient, id=storagePool.id, tags="test2")

        #(19) deploy a vm with service offering (6) and disk offering (7) in the network
        vm4 = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            domainid=self.user_domain.id,
            zoneid=self.zone.id,
            templateid=self.template.id,
            diskofferingid=self.disk_offering.id,
            serviceofferingid=self.service_offering.id)

        VirtualMachine.delete(vm4, self.apiclient, expunge=True)
        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_05_failed_vm_deployment_with_tagged_offerings_on_other_tagged_pool(self):
        """Deploy vm with tagged service/disk offerings to tagged storage pools with other tag

        # Validate the following:
        (1) get all storage pool and set storage pools tag to test2
        (2) create service offering with storage tag test3
        (3) create disk offering with storage tag test3
        (4) deploy a vm with service offering (2) and disk offering (3) in the network
        (5) operation should fail
        """

        #(1) get all storage pool and set storage pools tag to test2
        for storagePool in self.pools:
            StoragePool.update(self.apiclient, id=storagePool.id, tags="test2")

        #(2) create service offering with storage tag test3
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"],
            tags="test3"
        )
        self.cleanup.append(self.service_offering)

        #(3) create disk offering with storage tag test3
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"],
            tags="test3"
        )
        self.cleanup.append(self.disk_offering)

        #(4) deploy a vm with service offering (2) and disk offering (3) in the network, operation should fail
        try:
            vm5 = VirtualMachine.create(
                self.apiclient,
                self.testdata["virtual_machine"],
                accountid=self.account.name,
                domainid=self.user_domain.id,
                zoneid=self.zone.id,
                templateid=self.template.id,
                diskofferingid=self.disk_offering.id,
                serviceofferingid=self.service_offering.id)

            VirtualMachine.delete(vm5, self.apiclient, expunge=True)
            self.fail("Deploy vm with mismatched storage tag should fail")
        except Exception as e:
            self.debug("Deploy vm with mismatched storage tag failed as expected with Exception %s" % e)

        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_06_failed_vm_deployment_with_untagged_offerings_on_all_tagged_pool(self):
        """Deploy vm with untagged service/disk offerings to tagged storage pools

        # Validate the following:
        (0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        (1) get all storage pool and set storage pools tag to test2
        (6) create service offering with no storage tag
        (7) create disk offering with no storage tag
        (8) deploy a vm with service offering (6) and disk offering (7) in the network, operation should fail
        """

        #(0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to false
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="false")

        #(1) get all storage pool and set storage pools tag to test2
        for storagePool in self.pools:
            StoragePool.update(self.apiclient, id=storagePool.id, tags="test2")

        #(6) create service offering with no storage tag
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"]
        )
        self.cleanup.append(self.service_offering)

        #(7) create disk offering with no storage tag
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"]
        )
        self.cleanup.append(self.disk_offering)

        #(8) deploy a vm with service offering (6) and disk offering (7) in the network, operation should fail
        try:
            vm6 = VirtualMachine.create(
                self.apiclient,
                self.testdata["virtual_machine"],
                accountid=self.account.name,
                domainid=self.user_domain.id,
                zoneid=self.zone.id,
                templateid=self.template.id,
                diskofferingid=self.disk_offering.id,
                serviceofferingid=self.service_offering.id)

            VirtualMachine.delete(vm6, self.apiclient, expunge=True)
            self.fail("Deploy vm6 with untagged offering should fail")
        except Exception as e:
            self.debug("Deploy vm6 with untagged offering failed as expected with Exception %s" % e)

        return

    @attr(tags=["advanced", "advancedsg"], required_hardware="false")
    def test_07_failed_vm_deployment_with_untagged_offerings_on_all_tagged_pool(self):
        """Deploy vm with untagged service/disk offerings to tagged storage pools

        # Validate the following:
        (0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to true
        (1) get all storage pool and set storage pools tag to test2
        (6) create service offering with no storage tag
        (7) create disk offering with no storage tag
        (9) set account/account.default.storage.tag to test3
        (10) deploy a vm with service offering (6) and disk offering (7) in the network, operation should fail
        """

        #(0) update global setting allow.service.disk.offering.without.storage.tag.on.all.storage.pools to true
        Configurations.update(
            self.apiclient,
            name="allow.service.disk.offering.without.storage.tag.on.all.storage.pools",
            value="true")

        #(1) get all storage pool and set storage pools tag to test2
        for storagePool in self.pools:
            StoragePool.update(self.apiclient, id=storagePool.id, tags="test2")

        #(6) create service offering with no storage tag
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offering"]
        )
        self.cleanup.append(self.service_offering)

        #(7) create disk offering with no storage tag
        self.disk_offering = DiskOffering.create(
            self.apiclient,
            self.testdata["disk_offering"]
        )
        self.cleanup.append(self.disk_offering)

        #(9) set account/account.default.storage.tag to test3
        configs = Configurations.update(
            self.apiclient,
            accountid=self.account.id,
            name="account.default.storage.tag",
            value="test3")

        #(10) deploy a vm with service offering (6) and disk offering (7) in the network, operation should fail
        try:
            vm7 = VirtualMachine.create(
                self.apiclient,
                self.testdata["virtual_machine"],
                accountid=self.account.name,
                domainid=self.user_domain.id,
                zoneid=self.zone.id,
                templateid=self.template.id,
                diskofferingid=self.disk_offering.id,
                serviceofferingid=self.service_offering.id)

            VirtualMachine.delete(vm7, self.apiclient, expunge=True)
            self.fail("Deploy vm7 with untagged offering should fail")
        except Exception as e:
            self.debug("Deploy vm7 with untagged offering failed as expected with Exception %s" % e)

        return
