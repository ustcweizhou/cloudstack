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
""" tests for Network router offerings in 4.11.2-leaseweb

    JIRA ticket: https://jira.ocom.com/browse/CLSTACK-4604

"""

import logging
# Import Local Modules
from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import cloudstackTestCase, unittest
from marvin.lib.utils import (validateList,
                              cleanup_resources,
                              random_gen)
from marvin.lib.base import (Account,
                             Configurations,
                             PublicIpRange,
                             Domain,
                             Network,
                             Router,
                             NetworkOffering,
                             PublicIPAddress,
                             FireWallRule,
                             VPC,
                             VpcOffering,
                             LoadBalancerRule,
                             Resources,
                             VirtualMachine,
                            ServiceOffering,
                            DiskOffering,
                             updateResourceCount)
from marvin.lib.common import (get_domain,
                               get_zone,
                               get_free_vlan,
                               get_template,
                               matchResourceCount)
from marvin.codes import (PASS,
                          FAIL
                          )
from netaddr import IPAddress
import random


class TestNetworkOfferingSettings(cloudstackTestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger('TestNetworkOfferingSettings')
        testClient = super(TestNetworkOfferingSettings, cls).getClsTestClient()
        cls.apiclient = testClient.getApiClient()
        cls.services = testClient.getParsedTestDataConfig()
        cls.testdata = cls.testClient.getParsedTestDataConfig()
        cls._cleanup = []

        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.apiclient)
        cls.zone = get_zone(cls.apiclient, testClient.getZoneForTests())
        cls.services['mode'] = cls.zone.networktype

        try:
            # Create new domain, account, network and VM
            cls.user_domain = Domain.create(
                cls.apiclient,
                services=cls.testdata["acl"]["domain2"],
                parentdomainid=cls.domain.id)

            # Create account
            cls.account1 = Account.create(
                cls.apiclient,
                cls.testdata["acl"]["accountD2"],
                admin=True,
                domainid=cls.user_domain.id
            )

            # Create second account
            cls.account2 = Account.create(
                cls.apiclient,
                cls.testdata["acl"]["accountD2A"],
                admin=True,
                domainid=cls.domain.id
            )

            cls._cleanup.append(cls.account1)
            cls._cleanup.append(cls.account2)
            cls._cleanup.append(cls.user_domain)

            cls.hypervisor = cls.testClient.getHypervisorInfo()

            cls.template = get_template(cls.apiclient, cls.zone.id)

            # Create small service offering
            cls.service_offering = ServiceOffering.create(
                cls.apiclient,
                cls.testdata["service_offerings"]["small"]
            )

            # Create service offering with multiple cores
            cls.service_offering_multiple_cores = ServiceOffering.create(
                cls.apiclient,
                cls.testdata["service_offerings"]["large"]
            )

            cls._cleanup.append(cls.service_offering)
            cls._cleanup.append(cls.service_offering_multiple_cores)

            # cls.disk_offering = DiskOffering.create(
            #     cls.apiclient,
            #     cls.testdata["disk_offering"]
            # )
            #
            cls.services["network"]["zoneid"] = cls.zone.id

            cls.network_offering = NetworkOffering.create(
                cls.apiclient,
                cls.services["network_offering"],
            )
            #Enable Network offering
            cls.network_offering.update(cls.apiclient, state='Enabled')

            cls.services["network"]["networkoffering"] = cls.network_offering.id
            # Create network for first account
            cls.network1 = Network.create(
                cls.apiclient,
                cls.services["network"],
                cls.account1.name,
                cls.account1.domainid
            )

            # Create network for second account
            cls.network2 = Network.create(
                cls.apiclient,
                cls.services["network"],
                cls.account2.name,
                cls.account2.domainid
            )

            # Create a virtual machine so that VR is created in the network
            cls.testdata["virtual_machine"]["zoneid"] = cls.zone.id
            cls.testdata["virtual_machine"]["template"] = cls.template.id
            cls.virtual_machine1 = VirtualMachine.create(
                cls.apiclient,
                cls.testdata["virtual_machine"],
                accountid=cls.account1.name,
                domainid=cls.account1.domainid,
                templateid=cls.template.id,
                serviceofferingid=cls.service_offering.id,
                networkids=cls.network1.id
            )

            # Create second virtual machine
            cls.virtual_machine2 = VirtualMachine.create(
                cls.apiclient,
                cls.testdata["virtual_machine"],
                accountid=cls.account2.name,
                domainid=cls.account2.domainid,
                templateid=cls.template.id,
                serviceofferingid=cls.service_offering_multiple_cores.id,
                networkids=cls.network2.id
            )

            # Create new domain/account/network and virtual machine
            cls.second_domain = Domain.create(
                cls.apiclient,
                services=cls.testdata["acl"]["domain2"],
                parentdomainid=cls.domain.id)

            # Create account
            cls.account3 = Account.create(
                cls.apiclient,
                cls.testdata["acl"]["accountD2"],
                admin=True,
                domainid=cls.second_domain.id
            )

            # create network
            cls.network3 = Network.create(
                cls.apiclient,
                cls.services["network"],
                cls.account3.name,
                cls.account3.domainid
            )

            # create virtual machine
            cls.virtual_machine3 = VirtualMachine.create(
                cls.apiclient,
                cls.testdata["virtual_machine"],
                accountid=cls.account3.name,
                domainid=cls.account3.domainid,
                templateid=cls.template.id,
                serviceofferingid=cls.service_offering.id,
                networkids=cls.network3.id
            )

            cls._cleanup.append(cls.account3)
            cls._cleanup.append(cls.second_domain)
        except Exception as e:
            cls.tearDownClass()
            raise unittest.SkipTest(e)

        return

    @classmethod
    def tearDownClass(cls):
        try:
            # Cleanup resources used
            cleanup_resources(cls.apiclient, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return


    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.cleanup = []

        return

    def tearDown(self):
        try:
            # Clean up
            Configurations.update(
                self.apiclient,
                name="network.router.service.offering",
                value='NULL',
                networkid=self.network1.id
            )

            Configurations.update(
                self.apiclient,
                name="network.router.service.offering",
                value='NULL',
                networkid=self.network2.id
            )

            Configurations.update(
                self.apiclient,
                name="network.router.service.offering",
                value='NULL',
                networkid=self.network3.id
            )

            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL',
                accountid=self.account1.id
            )

            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL',
                accountid=self.account2.id
            )

            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL',
                accountid=self.account3.id
            )

            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL',
                domainid=self.user_domain.id
            )

            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL',
                domainid=self.second_domain.id
            )

            # Set the global setting to new service offering value
            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value='NULL'
            )
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def test_01_restart_network_without_cleanup(self):
        """
        1. Update network.router.service.offering to new service offering
        2. Restart the network without cleanup option
        3. Ensure that the VR is still using the old service offering
        """
        # Update service offering
        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value=self.service_offering_multiple_cores.id,
            networkid=self.network1.id
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # Before restarting network with cleanup, the VR should use the old service offering
        self.assertNotEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should be same as original offering before restart"
        )

        self.network1.restart(
            self.apiclient,
            cleanup=False
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart without cleanup, VR should not use new service offering
        self.assertNotEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should NOT point to new service offering if cleanup is not done"
        )

    def test_02_restart_network_with_cleanup(self):
        """
        1. set network.router.service.offering to new value
        2. Restart the network with cleanup option
        3. Ensure that the vr is using the new service offering
        """
        # Update service offering
        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value=self.service_offering_multiple_cores.id,
            networkid=self.network1.id
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # Before restarting network with cleanup, the VR should use the old service offering
        self.assertNotEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should be same as original offering before restart"
        )

        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart with cleanup, VR should use new service offering
        self.assertEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network1.id
        )

    def test_03_restart_network_with_cleanup(self):
        """
        1. set network.router.service.offering to new value
        2. Restart the network with cleanup option
        3. Ensure that the vr is using the new service offering
        """
        # Update service offering
        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value=self.service_offering_multiple_cores.id,
            networkid=self.network2.id
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network2.id,
            listall=True
        )

        # Before restarting network with cleanup, the VR should use the old service offering
        self.assertNotEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should be same as original offering before restart"
        )

        self.network2.restart(
            self.apiclient,
            cleanup=True
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network2.id,
            listall=True
        )

        # After network restart with cleanup, VR should use new service offering
        self.assertEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

    def test_04_account_routers_service_offering(self):
        """
        1. Update router.service.offering under account to new service offering
        2. Restart the network with cleanup option
        3. Ensure that the vr is using the new service offering
        """

        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network2.id
        )

        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network2.id
        )

        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        self.network2.restart(
            self.apiclient,
            cleanup=True
        )

        # Update service offering
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering_multiple_cores.id,
            accountid=self.account1.id
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # Before restarting network with cleanup, the VR should use the old service offering
        self.assertNotEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should be same as original offering before restart"
        )

        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        network_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart with cleanup, VR should use new
        self.assertEqual(
            network_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

    def test_05_different_account_routers_service_offering(self):
        """
        1. Update router.service.offering to new service offering for account1
        2. Restart the network of account2 with cleanup option
        3. Ensure that vr of another account is still using the old service offering
        """
        # Update service offering
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering_multiple_cores.id,
            accountid=self.account1.id
        )

        network2_details = Router.list(
            self.apiclient,
            networkid=self.network2.id,
            listall=True
        )

        # After network restart with cleanup, VR should use new
        self.assertNotEqual(
            network2_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

        # Restart network2 with cleanup
        self.network2.restart(
            self.apiclient,
            cleanup=True
        )

        network2_details = Router.list(
            self.apiclient,
            networkid=self.network2.id,
            listall=True
        )

        # After network restart with cleanup, VR should NOT use new service offering
        self.assertNotEqual(
            network2_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

    def test_06_domain_routers_service_offering(self):
        """
        1. Enable the domain settings
        2. Reset the account and the network settings
        3. Restart the network with cleanup so that vr uses the old service offering
        4. set the global setting to new service offering value
        5. Restart the network with cleanup so that vr will use the new service offering
        """

        # 1. Enable domain settings
        Configurations.update(
            self.apiclient,
            name="enable.account.settings.for.domain",
            value="true"
        )

        # 2. set account setting to null
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            accountid=self.account1.id
        )

        # set network setting to null
        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network1.id
        )

        # 3. restart network with cleanup so that VR uses original offering
        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        network1_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart with cleanup, VR should NOT use new service offering
        self.assertNotEqual(
            network1_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should not point to new service offering after restart"
        )

        # 4. set domain setting to proper value
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering_multiple_cores.id,
            domainid=self.user_domain.id
        )

        # 5. restart the network with cleanup so that it uses the new offering
        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        network1_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart with cleanup, VR should use new service offering
        self.assertNotEqual(
            network1_details[0].serviceofferingid,
            self.service_offering.id,
            "Router service offering should point to new service offering after restart"
        )

    def test_07_different_domain_router_offering(self):
        """
        1. set domain1 service offering to new value
        2. Restart the network of second domain
        3. Ensure that the vr of newly created domain uses the original service offering and not the new service offering

        Since router.service.offering is set for different domain, it should not affect the newly
        created domain
        """
        network3_details = Router.list(
            self.apiclient,
            networkid=self.network3.id,
            listall=True
        )

        self.assertNotEqual(
            network3_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

        # 2. set domain setting
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering_multiple_cores.id,
            domainid=self.user_domain.id
        )

        # 3. Restart network of new domain
        self.network3.restart(
            self.apiclient,
            cleanup=True
        )

        network3_details = Router.list(
            self.apiclient,
            networkid=self.network3.id,
            listall=True
        )

        # After network restart with cleanup, VR should NOT use new service offering
        self.assertNotEqual(
            network3_details[0].serviceofferingid,
            self.service_offering_multiple_cores.id,
            "Router service offering should point to new service offering after restart"
        )

    def test_08_global_router_service_offering(self):
        """
        1. set router.service.offering under global setting to new service offering
        2. Restart network of domain1 and domain2 with cleanup
        3. Ensure that both network vr's are using the new service offerings
        """

        # set account/domain/network service offering to null
        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network1.id
        )

        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network2.id
        )

        Configurations.update(
            self.apiclient,
            name="network.router.service.offering",
            value='NULL',
            networkid=self.network3.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            accountid=self.account1.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            accountid=self.account2.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            accountid=self.account3.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            domainid=self.user_domain.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL',
            domainid=self.second_domain.id
        )

        # Set the global setting to new service offering value
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering_multiple_cores.id
        )

        # 3. Restart the networks with cleanup option
        self.network1.restart(
            self.apiclient,
            cleanup=True
        )

        network1_details = Router.list(
            self.apiclient,
            networkid=self.network1.id,
            listall=True
        )

        # After network restart with cleanup, VR should NOT use new service offering
        self.assertNotEqual(
            network1_details[0].serviceofferingid,
            self.service_offering.id,
            "Router service offering should point to new service offering after restart"
        )

        self.network3.restart(
            self.apiclient,
            cleanup=True
        )

        network3_details = Router.list(
            self.apiclient,
            networkid=self.network3.id,
            listall=True
        )

        # After network restart with cleanup, VR should NOT use new service offering
        self.assertNotEqual(
            network3_details[0].serviceofferingid,
            self.service_offering.id,
            "Router service offering should point to new service offering after restart"
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value='NULL'
        )
