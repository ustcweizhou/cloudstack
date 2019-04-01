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
""" tests for VPC router offering in 4.11.2-leaseweb

    JIRA ticket: https://jira.ocom.com/browse/CLSTACK-4603

"""

import logging
# Import Local Modules
from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import cloudstackTestCase, unittest
from marvin.lib.utils import (validateList, cleanup_resources)
from marvin.lib.base import (Account,
                             Configurations,
                             Domain,
                             Network,
                             VPC,
                             VpcOffering,
                             VirtualMachine,
                             Router,
                             ServiceOffering)
from marvin.lib.common import (get_domain,
                               get_zone)

class TestVpcRouterOfferingSettings(cloudstackTestCase):
    @classmethod
    def setUpClass(self):
        self.logger = logging.getLogger('TestVpcRouterOfferingSettings')
        self.testClient = super(TestVpcRouterOfferingSettings, self).getClsTestClient()
        self.apiclient = self.testClient.getApiClient()
        self.testdata = self.testClient.getParsedTestDataConfig()
        self._cleanup = []

        # Get Zone, Domain
        self.domain = get_domain(self.apiclient)
        self.zone = get_zone(self.apiclient, self.testClient.getZoneForTests())

        try:
            # Create small service offering
            self.service_offering1 = ServiceOffering.create(
                self.apiclient,
                self.testdata["service_offerings"]["small"]
            )
            self.service_offering2 = ServiceOffering.create(
                self.apiclient,
                self.testdata["service_offerings"]["small"]
            )
            self.service_offering3 = ServiceOffering.create(
                self.apiclient,
                self.testdata["service_offerings"]["small"]
            )
            self.service_offering4 = ServiceOffering.create(
                self.apiclient,
                self.testdata["service_offerings"]["small"]
            )
            self.service_offering5 = ServiceOffering.create(
                self.apiclient,
                self.testdata["service_offerings"]["small"]
            )

            self._cleanup.append(self.service_offering1)
            self._cleanup.append(self.service_offering2)
            self._cleanup.append(self.service_offering3)
            self._cleanup.append(self.service_offering4)
            self._cleanup.append(self.service_offering5)

            self.debug("Creating a VPC offering..")
            self.vpc_off = VpcOffering.create(
                                     self.apiclient,
                                     self.testdata["vpc_offering"]
                                     )
            self.vpc_off.update(self.apiclient, state='Enabled')
            self._cleanup.append(self.vpc_off)

        except Exception as e:
            self.tearDownClass()
            raise unittest.SkipTest(e)

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
        self.cleanup = []

        # Create new domain, account, network and VM
        self.user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)

        # Create account
        self.account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            admin=True,
            domainid=self.user_domain.id
        )

        self.cleanup.append(self.account)
        self.cleanup.append(self.user_domain)

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering1.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering2.id,
            domainid=self.user_domain.id
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value=self.service_offering3.id,
            accountid=self.account.id
        )

        Configurations.update(
            self.apiclient,
            name="vpc.router.service.offering",
            value=self.service_offering4.id
        )

        return

    def tearDown(self):
        try:
            Configurations.update(
                self.apiclient,
                name="router.service.offering",
                value=""
            )
            Configurations.update(
                self.apiclient,
                name="vpc.router.service.offering",
                value=""
            )

            # Clean up
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(tags=["advanced"], required_hardware="false")
    def test_1_vpc_router_use_vpc_router_service_offering(self):

        self.testdata["vpc"]["cidr"] = '10.1.1.1/16'
        vpc = VPC.create(
                         self.apiclient,
                         self.testdata["vpc"],
                         vpcofferingid=self.vpc_off.id,
                         zoneid=self.zone.id,
                         account=self.account.name,
                         domainid=self.account.domainid
                         )

        vpc_routers = Router.list(
            self.apiclient,
            vpcid=vpc.id,
            listall=True
        )

        self.assertIsNotNone(vpc_routers, "Failed to get vpc routers")

        # Before restarting network with cleanup, the VR should use the old service offering
        self.assertEqual(
            vpc_routers[0].serviceofferingid,
            self.service_offering4.id,
            "Router service offering should be same as global/vpc.router.service.offering before restart"
        )

        Configurations.update(
            self.apiclient,
            name="vpc.router.service.offering",
            value=self.service_offering5.id,
            vpcid=vpc.id
        )

        vpc.restart(
            self.apiclient,
            cleanup=True
        )

        vpc_routers = Router.list(
            self.apiclient,
            vpcid=vpc.id,
            listall=True
        )

        self.assertIsNotNone(vpc_routers, "Failed to get vpc routers")

        # After restarting network with cleanup, the VR should use the vpc/vpc.router.service.offering
        self.assertEqual(
            vpc_routers[0].serviceofferingid,
            self.service_offering5.id,
            "Router service offering should be same as vpc/vpc.router.service.offering after restart"
        )

        return

    @attr(tags=["advanced"], required_hardware="false")
    def test2_vpc_router_use_router_service_offering(self):

        Configurations.update(
            self.apiclient,
            name="vpc.router.service.offering",
            value=""
        )
    
        self.testdata["vpc"]["cidr"] = '10.1.1.1/16'
        vpc = VPC.create(
                         self.apiclient,
                         self.testdata["vpc"],
                         vpcofferingid=self.vpc_off.id,
                         zoneid=self.zone.id,
                         account=self.account.name,
                         domainid=self.account.domainid
                         )

        vpc_routers = Router.list(
            self.apiclient,
            vpcid=vpc.id,
            listall=True
        )

        self.assertIsNotNone(vpc_routers, "Failed to get vpc routers")

        # Before restarting network with cleanup, the VR should use the account/router.service.offering
        self.assertEqual(
            vpc_routers[0].serviceofferingid,
            self.service_offering3.id,
            "Router service offering should be same as account/router.service.offering before restart"
        )

        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value="",
            accountid=self.account.id
        )

        vpc.restart(
            self.apiclient,
            cleanup=True
        )

        vpc_routers = Router.list(
            self.apiclient,
            vpcid=vpc.id,
            listall=True
        )

        self.assertIsNotNone(vpc_routers, "Failed to get vpc routers")

        # After restarting network with cleanup, the VR should use the domain/router.service.offering
        self.assertEqual(
            vpc_routers[0].serviceofferingid,
            self.service_offering2.id,
            "Router service offering should be same as domain/router.service.offering after restart"
        )
        Configurations.update(
            self.apiclient,
            name="router.service.offering",
            value="",
            domainid=self.account.domainid
        )

        vpc.restart(
            self.apiclient,
            cleanup=True
        )

        vpc_routers = Router.list(
            self.apiclient,
            vpcid=vpc.id,
            listall=True
        )

        self.assertIsNotNone(vpc_routers, "Failed to get vpc routers")

        # After restarting network with cleanup, the VR should use the global/router.service.offering
        self.assertEqual(
            vpc_routers[0].serviceofferingid,
            self.service_offering1.id,
            "Router service offering should be same as glonbal/router.service.offering after restart"
        )
        
        return
