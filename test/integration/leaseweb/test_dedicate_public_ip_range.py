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
""" tests for Dedicating Public IP addresses in 4.11.2-leaseweb

    JIRA ticket: https://jira.ocom.com/browse/CLSTACK-4040    

"""
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
                             NetworkOffering,
                             PublicIPAddress,
                             FireWallRule,
                             VPC,
                             VpcOffering,
                             LoadBalancerRule,
                             Resources,
                             updateResourceCount)
from marvin.lib.common import (get_domain,
                               get_zone,
                               get_free_vlan,
                               matchResourceCount)
from marvin.codes import (PASS,
                          FAIL,
                          RESOURCE_PUBLIC_IP)
from netaddr import IPAddress
import random


class TestDedicatePublicIPRange(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.testClient = super(
            TestDedicatePublicIPRange,
            cls).getClsTestClient()
        cls.apiclient = cls.testClient.getApiClient()
        cls.testdata = cls.testClient.getParsedTestDataConfig()
        cls.hypervisor = cls.testClient.getHypervisorInfo()
        # Get Zone, Domain
        cls.domain = get_domain(cls.apiclient)
        cls.zone = get_zone(cls.apiclient, cls.testClient.getZoneForTests())
        cls.testdata["isolated_network"]["zoneid"] = cls.zone.id
        cls.testdata["publiciprange"]["zoneid"] = cls.zone.id
        cls._cleanup = []
        try:
            cls.isolated_network_offering = NetworkOffering.create(
                cls.apiclient,
                cls.testdata["isolated_network_offering"])
            cls._cleanup.append(cls.isolated_network_offering)
            cls.isolated_network_offering.update(
                cls.apiclient,
                state='Enabled')

            cls.vpc_network_offering = NetworkOffering.create(
                cls.apiclient,
                cls.testdata["nw_offering_isolated_vpc"],
                conservemode=False)
            cls._cleanup.append(cls.vpc_network_offering)
            cls.vpc_network_offering.update(cls.apiclient, state='Enabled')

            cls.vpc_off = VpcOffering.create(
                cls.apiclient,
                cls.testdata["vpc_offering"]
            )
            cls.vpc_off.update(cls.apiclient, state='Enabled')
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
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []

        # Setting up random public ip range
        self.testdata["publiciprange"]["vlan"] = get_free_vlan(
            self.apiclient,
            self.zone.id)[1]
        random_subnet_number = random.randrange(1, 254)
        self.testdata["publiciprange"]["gateway"] = "172.16." + \
            str(random_subnet_number) + ".1"
        self.testdata["publiciprange"]["startip"] = "172.16." + \
            str(random_subnet_number) + ".10"
        self.testdata["publiciprange"]["endip"] = "172.16." + \
            str(random_subnet_number) + ".20"
        self.testdata["publiciprange"]["netmask"] = "255.255.255.0"
        return

    def tearDown(self):
        try:
            # Clean up
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(tags=["advanced"], required_hardware="false")
    def test_01_keep_dedicate_public_ip_range_in_domain_account_removal(self):
        """Keep dedicated ip ranges in account/domain removal

        # Validate the following:
        # 0. set global setting delete.dedicated.ip.ranges.in.domain.account.removal to false
        # 1. Create a Public IP range, verify with listVlanIpRanges
        # 2. Create domain test2, and account test2/test2
        # 3. Dedicate ip range to account test2/test2
        # 4. Remove account test2/test2, ip range should be released
        # 5. Dedicate ip range to domain test2,
        # 6. Remove domain test2, ip range should be released
        """

        # 0. set global setting delete.dedicated.ip.ranges.in.domain.account.removal to false
        Configurations.update(
            self.apiclient,
            name="delete.dedicated.ip.ranges.in.domain.account.removal",
            value="false"
        )

        # 1. Create a Public IP range, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        self.cleanup.append(public_ip_range)
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 2. Create domain
        user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        # Create account
        account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=user_domain.id
        )

        # 3. Dedicate ip range to account test2/test2
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            account=account.name,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].account,
            account.name,
            "Check account name is in listVlanIpRanges\
               as the account public ip range is dedicated to")

        # 4. Remove account test2/test2, ip range should be released
        account.delete(self.apiclient)
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            str(public_ip_ranges[0].domain).lower(),
            "root",
            "Check domain name is root")
        self.assertEqual(
            str(public_ip_ranges[0].account).lower(),
            "system",
            "Check account name is system")

        # 5. Dedicate ip range to domain test2,
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].domain,
            user_domain.name,
            "Check domain name is " + user_domain.name)

        # 6. Remove domain test2, ip range should be released
        user_domain.delete(self.apiclient)
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            str(public_ip_ranges[0].domain).lower(),
            "root",
            "Check domain name is root")
        self.assertEqual(
            str(public_ip_ranges[0].account).lower(),
            "system",
            "Check account name is system")

        return

    @attr(tags=["advanced"], required_hardware="false")
    def test_02_remove_dedicate_public_ip_range_in_domain_account_removal(self):
        """Remove dedicated ip ranges in account/domain removal

        # Validate the following:
        # 0. set global setting delete.dedicated.ip.ranges.in.domain.account.removal to true
        # 1. Create a Public IP range, verify with listVlanIpRanges
        # 2. Create domain test2, and account test2/test2
        # 3. Dedicate ip range to account test2/test2
        # 4. Remove account test2/test2, ip range should be removed
        # 5. Create the ip range again, verify with listVlanIpRanges
        # 5. Dedicate ip range to domain test2,
        # 6. Remove domain test2, ip range should be removed
        """

        # 0. set global setting delete.dedicated.ip.ranges.in.domain.account.removal to true
        Configurations.update(
            self.apiclient,
            name="delete.dedicated.ip.ranges.in.domain.account.removal",
            value="true"
        )

        # 1. Create a Public IP range, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 2. Create domain test2, and account test2/test2
        user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        # Create account
        account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=user_domain.id
        )

        # 3. Dedicate ip range to account test2/test2
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            account=account.name,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].account,
            account.name,
            "Check account name is in listVlanIpRanges\
               as the account public ip range is dedicated to")

        # 4. Remove account test2/test2, ip range should be removed
        account.delete(self.apiclient)
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertIsNone(public_ip_ranges, "public ip range should be removed")

        # 5. Create the ip range again, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 5. Dedicate ip range to domain test2,
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].domain,
            user_domain.name,
            "Check domain name is " + user_domain.name)

        # 6. Remove domain test2, ip range should be removed
        user_domain.delete(self.apiclient)
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertIsNone(public_ip_ranges, "public ip range should be removed")

        return

    @attr(tags=["advanced"], required_hardware="false")
    def test_03_dedicate_ip_range_domain_or_account_when_ip_is_used_by_account(self):
        """Dedicate public IP range to an account during its creation only

        # Validate the following:
        # 1. Create a Public IP range, verify with listVlanIpRanges
        # 2. Create domain test2, and account test2/test2
        # 3. change test2/test2 account setting use.system.public.ips to false
        # 4. Assign public ip range to domain test2
        # 5. Create a vm in an isolated network for account test2/test2
        # 6. Acquire a IP in network, and add firewall rules
        # 7. Acquire a IP in network, not add rule
        # 8. Release ip range from domain test2, ip acquired in #7 should be released
        # 9. Dedicate ip range to account test2/test2, operation should succeed
        # 10. Acquire a IP in network, not add rule
        # 11. Release ip range from account test2/test2, ip acquired in #10 should be released
        # 12. Dedicate ip range to domain test2, operation should succeed
        # 13. Remove firewall rules from ip #6, Remove public ip range
        """

        # 1. Create a Public IP range, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 2. Create domain test2, and account test2/test2
        user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        # Create account
        account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=user_domain.id
        )
        self.cleanup.append(account)
        self.cleanup.append(user_domain)

        # 3. change test2/test2 account setting use.system.public.ips to false
        Configurations.update(
            self.apiclient,
            name="use.system.public.ips",
            value="false",
            accountid=account.id
        )

        # 4. Dedicate public ip range to domain test2
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].domain,
            user_domain.name,
            "Check domain name is " + user_domain.name)

        # 5. Create an isolated network for account test2/test2
        isolated_network = Network.create(
            self.apiclient,
            self.testdata["isolated_network"],
            account.name,
            account.domainid,
            networkofferingid=self.isolated_network_offering.id)

        # 6. Acquire a IP in network, and add firewall rules
        public_ip6 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip6.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        fw_rule = FireWallRule.create(
            self.apiclient,
            ipaddressid=public_ip6.ipaddress.id,
            protocol=self.testdata["natrule"]["protocol"],
            cidrlist=['0.0.0.0/0'],
            startport=self.testdata["natrule"]["publicport"],
            endport=self.testdata["natrule"]["publicport"]
        )

        # 7. Acquire a IP in network, not add rule
        public_ip7 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip7.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        # 8. Release ip range from domain test2, ip acquired in #7 should be released
        public_ip_range.release(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip7.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #7 should be Free"
                         )

        # 9. Dedicate up range to account test2/test2, operation should succeed
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            account=account.name,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].account,
            account.name,
            "Check account name is in listVlanIpRanges\
               as the account public ip range is dedicated to")

        # 10. Acquire a IP in network, not add rule
        public_ip10 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip10.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        # 11. Release ip range from account test2/test2, ip acquired in #10 should be released
        public_ip_range.release(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip10.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #10 should be Free"
                         )

        # 12. Dedicate ip range to domain test2, operation should succeed
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].domain,
            user_domain.name,
            "Check domain name is " + user_domain.name)

        # 13. Remove firewall rules from ip #6, Remove network, Remove public ip range
        fw_rule.delete(self.apiclient)
        isolated_network.delete(self.apiclient)
        public_ip_range.delete(self.apiclient)

        return


    @attr(tags=["advanced"], required_hardware="false")
    def test_04_resource_count_all_dedicated_ips_for_account(self):
        """Resource count takes all dedicated ips into calculation of account

        # Validate the following:
        # 1. set global setting resource.count.all.dedicated.ips to true, Update resource count of ROOT domain
        # 2. Create domain test2, and account test2/test2
        # 3. Create a Public IP range, verify with listVlanIpRanges
        # 4. dedicate ip range to account test2/test2, Get resource count of account. count = number of all ips
        # 5. Create an isolated network for account test2/test2
        # 6. Acquire public ip and add firewall rules, Get resource count of account. count = number of all ips
        # 7. Acquire public ip, Get resource count of account. count = number of all ips
        # 8. Release ip #7, Get resource count of account. count = number of all ips
        # 9. Acquire public ip, Get resource count of account. count = number of all ips
        # 10. Release ip range, Get resource count of account. count = 1, ip #9 is released
        # 11. Acquire public ip, Get resource count of account. count = 2
        # 12. Remove network #5, Get resource count of account. count = 0
        """

        # 1. set global setting resource.count.all.dedicated.ips to true, Update resource count of ROOT domain
        Configurations.update(
            self.apiclient,
            name="resource.count.all.dedicated.ips",
            value="true"
        )

        cmd = updateResourceCount.updateResourceCountCmd()
        cmd.domainid = self.domain.id
        response=self.apiclient.updateResourceCount(cmd)

        # 2. Create domain test2, and account test2/test2
        user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        # Create account
        account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=user_domain.id
        )
        self.cleanup.append(account)
        self.cleanup.append(user_domain)

        # 3. Create a Public IP range, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 4. dedicate ip range to account test2/test2, Get resource count of account. count = number of all ips
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            account=account.name,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].account,
            account.name,
            "Check account name is in listVlanIpRanges\
               as the account public ip range is dedicated to")

        expectedCount = 11 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 5. Create an isolated network for account test2/test2
        isolated_network = Network.create(
            self.apiclient,
            self.testdata["isolated_network"],
            account.name,
            account.domainid,
            networkofferingid=self.isolated_network_offering.id)

        # 6. Acquire public ip and add firewall rules, Get resource count of account. count = number of all ips
        public_ip6 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip6.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        fw_rule = FireWallRule.create(
            self.apiclient,
            ipaddressid=public_ip6.ipaddress.id,
            protocol=self.testdata["natrule"]["protocol"],
            cidrlist=['0.0.0.0/0'],
            startport=self.testdata["natrule"]["publicport"],
            endport=self.testdata["natrule"]["publicport"]
        )

        expectedCount = 11 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 7. Acquire public ip, Get resource count of account. count = number of all ips
        public_ip7 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip7.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        expectedCount = 11 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 8. Release ip #7, Get resource count of account. count = number of all ips
        public_ip7.delete(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip7.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #7 should be Free"
                         )

        expectedCount = 11 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 9. Acquire public ip, Get resource count of account. count = number of all ips
        public_ip9 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip9.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        expectedCount = 11 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 10. Release ip range, Get resource count of account. count = 2, ip #9 is released
        public_ip_range.release(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip9.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #9 should be Free"
                         )

        expectedCount = 1 # only the source nat ip. startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 11. Acquire public ip, Get resource count of account. count = 2
        public_ip11 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        expectedCount = 2 # only the source nat ip #6 and ip #11. startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 12. Remove network #5, Get resource count of account. count = 0
        isolated_network.delete(self.apiclient)
        isolated_networks = Network.list(
                          self.apiclient,
                          id=isolated_network.id)
        self.assertIsNone(isolated_networks, "isolated network should be removed")

        expectedCount = 0 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        public_ip_range.delete(self.apiclient)
        return

    @attr(tags=["advanced"], required_hardware="false")
    def test_05_resource_count_used_dedicated_ip_for_account(self):
        """Resource count takes only used dedicated ips into calculation of account

        # Validate the following:
        # 1. set global setting resource.count.all.dedicated.ips to false, Update resource count of ROOT domain
        # 2. Create domain test2, and account test2/test2
        # 3. Create a Public IP range, verify with listVlanIpRanges
        # 4. dedicate ip range to account test2/test2, Get resource count of account. count = 0
        # 5. Create an isolated network for account test2/test2, Get resource count of account. count = 0
        # 6. Acquire public ip and add firewall rules, Get resource count of account. count = 1
        # 7. Acquire public ip, Get resource count of account. count = 2
        # 8. Release ip #7, Get resource count of account. count = 1
        # 9. Acquire public ip , Get resource count of account. count = 2
        # 10. Release ip range, Get resource count of account. count = 1, ip #9 is released
        # 11. Remove network #5, Get resource count of account. count = 0, ip #6 is released
        """

        # 1. set global setting resource.count.all.dedicated.ips to false, Update resource count of ROOT domain
        Configurations.update(
            self.apiclient,
            name="resource.count.all.dedicated.ips",
            value="false"
        )

        cmd = updateResourceCount.updateResourceCountCmd()
        cmd.domainid = self.domain.id
        response=self.apiclient.updateResourceCount(cmd)

        # 2. Create domain test2, and account test2/test2
        user_domain = Domain.create(
            self.apiclient,
            services=self.testdata["acl"]["domain2"],
            parentdomainid=self.domain.id)
        # Create account
        account = Account.create(
            self.apiclient,
            self.testdata["acl"]["accountD2"],
            domainid=user_domain.id
        )
        self.cleanup.append(account)
        self.cleanup.append(user_domain)

        # 3. Create a Public IP range, verify with listVlanIpRanges
        public_ip_range = PublicIpRange.create(
            self.apiclient,
            self.testdata["publiciprange"]
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(
            validateList(public_ip_ranges)[0],
            PASS,
            "public ip ranges list validation failed"
        )
        self.assertEqual(
            public_ip_ranges[0].id,
            public_ip_range.vlan.id,
            "Check public ip range response id is in listVlanIpRanges"
        )

        # 4. dedicate ip range to account test2/test2, Get resource count of account. count = 0
        PublicIpRange.dedicate(
            self.apiclient,
            public_ip_range.vlan.id,
            account=account.name,
            domainid=account.domainid
        )
        public_ip_ranges = PublicIpRange.list(
            self.apiclient,
            id=public_ip_range.vlan.id
        )
        self.assertEqual(validateList(public_ip_ranges)[0], PASS,
                         "public ip ranges list validation failed")
        self.assertEqual(
            public_ip_ranges[0].account,
            account.name,
            "Check account name is in listVlanIpRanges\
               as the account public ip range is dedicated to")

        expectedCount = 0 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 5. Create an isolated network for account test2/test2, Get resource count of account. count = 0
        isolated_network = Network.create(
            self.apiclient,
            self.testdata["isolated_network"],
            account.name,
            account.domainid,
            networkofferingid=self.isolated_network_offering.id)

        # 6. Acquire public ip and add firewall rules, Get resource count of account. count = 1
        public_ip6 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip6.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        fw_rule = FireWallRule.create(
            self.apiclient,
            ipaddressid=public_ip6.ipaddress.id,
            protocol=self.testdata["natrule"]["protocol"],
            cidrlist=['0.0.0.0/0'],
            startport=self.testdata["natrule"]["publicport"],
            endport=self.testdata["natrule"]["publicport"]
        )

        expectedCount = 1 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 7. Acquire public ip, Get resource count of account. count = 2
        public_ip7 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip7.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        expectedCount = 2 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 8. Release ip #7, Get resource count of account. count = 1
        public_ip7.delete(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip7.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #7 should be Free"
                         )

        expectedCount = 1 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 9. Acquire public ip , Get resource count of account. count = 2
        public_ip9 = PublicIPAddress.create(
            self.apiclient,
            accountid=account.name,
            zoneid=self.zone.id,
            domainid=account.domainid,
            networkid=isolated_network.id)

        formatted_startip = IPAddress(
            self.testdata["publiciprange"]["startip"])
        formatted_endip = IPAddress(self.testdata["publiciprange"]["endip"])
        formatted_publicip = IPAddress(public_ip9.ipaddress.ipaddress)

        self.assertTrue(int(formatted_startip) <=
                        int(formatted_publicip) <= int(formatted_endip),
                        "publicip should be from the dedicated range")

        expectedCount = 2 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 10. Release ip range, Get resource count of account. count = 2, ip #7 is released
        public_ip_range.release(self.apiclient)
        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip9.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #9 should be Free"
                         )

        expectedCount = 1 # only the source nat ip . startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        # 11. Remove network #5, Get resource count of account. count = 0, ip #6 is released
        isolated_network.delete(self.apiclient)
        isolated_networks = Network.list(
                          self.apiclient,
                          id=isolated_network.id)
        self.assertIsNone(isolated_networks, "isolated network should be removed")

        expectedCount = 0 # startip=172.16.X.10, endip=172.16.X.20
        response = matchResourceCount(
            self.apiclient, expectedCount,
            RESOURCE_PUBLIC_IP,
            accountid=account.id)
        if response[0] == FAIL:
            raise Exception(response[1])

        public_ips = PublicIPAddress.list(
                          self.apiclient,
                          forvirtualnetwork=True,
                          allocatedonly=False,
                          listall=True,
                          ipaddress=public_ip6.ipaddress.ipaddress
                          )
        self.assertEqual(
                         isinstance(public_ips, list),
                         True,
                         "List public Ip for network should list the Ip addr"
                         )
        self.assertEqual(
                         public_ips[0].state,
                         "Free",
                         "public Ip in #6 should be Free"
                         )

        public_ip_range.delete(self.apiclient)
        return

