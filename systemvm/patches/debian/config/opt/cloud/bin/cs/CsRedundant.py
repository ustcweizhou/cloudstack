# -- coding: utf-8 --
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# -------------------------------------------------------------------- #
# Notes
# -------------------------------------------------------------------- #
# Vrouter
#
# eth0 router gateway IP for isolated network
# eth1 Control IP for hypervisor
# eth2 public ip(s)
#
# VPC Router
#
# eth0 control interface
# eth1 public ip
# eth2+ Guest networks
# -------------------------------------------------------------------- #
import os
import logging
import CsHelper
from CsFile import CsFile
from CsProcess import CsProcess
from CsApp import CsPasswdSvc
from CsAddress import CsDevice, VPC_PUBLIC_INTERFACE, NETWORK_PUBLIC_INTERFACE
from CsRoute import CsRoute
from CsStaticRoutes import CsStaticRoutes
import socket
from time import sleep

class CsRedundant(object):

    CS_RAMDISK_DIR = "/ramdisk"
    CS_PRIO_UP = 1
    CS_PRIO_DOWN = -1
    CS_ROUTER_DIR = "%s/rrouter" % CS_RAMDISK_DIR
    CS_TEMPLATES = [
        "heartbeat.sh.templ", "check_heartbeat.sh.templ",
        "arping_gateways.sh.templ"
    ]
    CS_TEMPLATES_DIR = "/opt/cloud/templates"
    CONNTRACKD_BIN = "/usr/sbin/conntrackd"
    CONNTRACKD_KEEPALIVED_CONFLOCK = "/var/lock/conntrack.lock"
    CONNTRACKD_CONF = "/etc/conntrackd/conntrackd.conf"
    RROUTER_LOG = "/var/log/cloud.log"
    KEEPALIVED_CONF = "/etc/keepalived/keepalived.conf"

    def __init__(self, config):
        self.cl = config.cmdline()
        self.address = config.address()
        self.config = config

    def set(self):
        logging.debug("Router redundancy status is %s", self.cl.is_redundant())
        if self.cl.is_redundant():
            self._redundant_on()
        else:
            self._redundant_off()

    def _redundant_off(self):
        CsHelper.service("conntrackd", "stop")
        CsHelper.service("keepalived", "stop")
        CsHelper.umount_tmpfs(self.CS_RAMDISK_DIR)
        CsHelper.rmdir(self.CS_RAMDISK_DIR)
        CsHelper.rm(self.CONNTRACKD_CONF)
        CsHelper.rm(self.KEEPALIVED_CONF)

    def _redundant_on(self):
        guest = self.address.get_guest_if()

        # No redundancy if there is no guest network
        if guest is None:
            self.set_backup()
            self._redundant_off()
            return

        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_guest()]
        isDeviceReady = False
        dev = ''
        for interface in interfaces:
            if dev == interface.get_device():
                continue
            dev = interface.get_device()
            logging.info("Wait for devices to be configured so we can start keepalived")
            devConfigured = CsDevice(dev, self.config).waitfordevice()
            if devConfigured:
                command = "ip link show %s | grep 'state UP'" % dev
                devUp = CsHelper.execute(command)
                if devUp:
                    logging.info("Device %s is present, let's start keepalive now." % dev)
                    isDeviceReady = True
        
        if not isDeviceReady:
            logging.info("Guest network not configured yet, let's stop router redundancy for now.")
            CsHelper.service("conntrackd", "stop")
            CsHelper.service("keepalived", "stop")
            return

        CsHelper.mkdir(self.CS_RAMDISK_DIR, 0755, False)
        CsHelper.mount_tmpfs(self.CS_RAMDISK_DIR)
        CsHelper.mkdir(self.CS_ROUTER_DIR, 0755, False)
        for s in self.CS_TEMPLATES:
            d = s
            if s.endswith(".templ"):
                d = s.replace(".templ", "")
            CsHelper.copy_if_needed(
                "%s/%s" % (self.CS_TEMPLATES_DIR, s), "%s/%s" % (self.CS_ROUTER_DIR, d))

        CsHelper.copy_if_needed(
            "%s/%s" % (self.CS_TEMPLATES_DIR, "keepalived.conf.templ"), self.KEEPALIVED_CONF)
        CsHelper.copy_if_needed(
            "%s/%s" % (self.CS_TEMPLATES_DIR, "checkrouter.sh.templ"), "/opt/cloud/bin/checkrouter.sh")

        CsHelper.execute(
            'sed -i "s/--exec\ \$DAEMON;/--exec\ \$DAEMON\ --\ --vrrp;/g" /etc/init.d/keepalived')
        # checkrouter.sh configuration
        check_router = CsFile("/opt/cloud/bin/checkrouter.sh")
        check_router.greplace("[RROUTER_LOG]", self.RROUTER_LOG)
        check_router.commit()

        # keepalived configuration
        keepalived_conf = CsFile(self.KEEPALIVED_CONF)
        keepalived_conf.search(
            " router_id ", "    router_id %s" % self.cl.get_name())
        keepalived_conf.search(
            " interface ", "    interface %s" % guest.get_device())
        keepalived_conf.greplace("[RROUTER_BIN_PATH]", self.CS_ROUTER_DIR)
        keepalived_conf.section("authentication {", "}", [
                                "        auth_type AH \n", "        auth_pass %s\n" % self.cl.get_router_password()])
        keepalived_conf.section(
            "virtual_ipaddress {", "}", self._collect_ips())

        # conntrackd configuration
        conntrackd_template_conf = "%s/%s" % (self.CS_TEMPLATES_DIR, "conntrackd.conf.templ")
        conntrackd_temp_bkp = "%s/%s" % (self.CS_TEMPLATES_DIR, "conntrackd.conf.templ.bkp")
        
        CsHelper.copy(conntrackd_template_conf, conntrackd_temp_bkp)

        conntrackd_tmpl = CsFile(conntrackd_template_conf)
        conntrackd_tmpl.section("Multicast {", "}", [
                      "IPv4_address 225.0.0.50\n",
                      "Group 3780\n",
                      "IPv4_interface %s\n" % guest.get_ip(),
                      "Interface %s\n" % guest.get_device(),
                      "SndSocketBuffer 1249280\n",
                      "RcvSocketBuffer 1249280\n",
                      "Checksum on\n"])
        conntrackd_tmpl.section("Address Ignore {", "}", self._collect_ignore_ips())
        conntrackd_tmpl.commit()

        conntrackd_conf = CsFile(self.CONNTRACKD_CONF)

        is_equals = conntrackd_tmpl.compare(conntrackd_conf)

        force_keepalived_restart = False
        proc = CsProcess(['/etc/conntrackd/conntrackd.conf'])

        if not proc.find() and not is_equals:
            CsHelper.copy(conntrackd_template_conf, self.CONNTRACKD_CONF)
            CsHelper.service("conntrackd", "restart")
            force_keepalived_restart = True

        # Restore the template file and remove the backup.
        CsHelper.copy(conntrackd_temp_bkp, conntrackd_template_conf)
        CsHelper.execute("rm -rf %s" % conntrackd_temp_bkp)

        # Configure heartbeat cron job - runs every 30 seconds
        heartbeat_cron = CsFile("/etc/cron.d/heartbeat")
        heartbeat_cron.add("SHELL=/bin/bash", 0)
        heartbeat_cron.add(
            "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin", 1)
        heartbeat_cron.add(
            "* * * * * root $SHELL %s/check_heartbeat.sh 2>&1 > /dev/null" % self.CS_ROUTER_DIR, -1)
        heartbeat_cron.add(
            "* * * * * root sleep 30; $SHELL %s/check_heartbeat.sh 2>&1 > /dev/null" % self.CS_ROUTER_DIR, -1)
        heartbeat_cron.commit()

        proc = CsProcess(['/usr/sbin/keepalived'])
        if not proc.find() or keepalived_conf.is_changed() or force_keepalived_restart:
            keepalived_conf.commit()
            CsHelper.service("keepalived", "restart")

    def release_lock(self):
        try:
            os.remove("/tmp/master_lock")
        except OSError:
            pass

    def set_lock(self):
        """
        Make sure that master state changes happen sequentially
        """
        iterations = 10
        time_between = 1

        for iter in range(0, iterations):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.bind('/tmp/master_lock')
                return s
            except socket.error, e:
                error_code = e.args[0]
                error_string = e.args[1]
                print "Process already running (%d:%s). Exiting" % (error_code, error_string)
                logging.info("Master is already running, waiting")
                sleep(time_between)

    def set_fault(self):
        """ Set fault mode on this router """
        if not self.cl.is_redundant():
            logging.error("Set fault called on non-redundant router")
            return

        self.set_lock()
        logging.info("Router switched to fault mode")

        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_public()]
        for interface in interfaces:
            CsHelper.execute("ifconfig %s down" % interface.get_device())

        cmd = "%s -C %s" % (self.CONNTRACKD_BIN, self.CONNTRACKD_CONF)
        CsHelper.execute("%s -s" % cmd)
        CsHelper.service("ipsec", "stop")
        CsHelper.service("xl2tpd", "stop")
        CsHelper.service("dnsmasq", "stop")

        self._restart_password_server()

        self.cl.set_fault_state()
        self.cl.save()
        self.release_lock()
        logging.info("Router switched to fault mode")

        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_public()]
        CsHelper.reconfigure_interfaces(self.cl, interfaces)

    def set_backup(self):
        """ Set the current router to backup """
        if not self.cl.is_redundant():
            logging.error("Set backup called on non-redundant router")
            return

        self.set_lock()
        logging.debug("Setting router to backup")

        dev = ''
        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_public()]
        for interface in interfaces:
            if dev == interface.get_device():
                continue
            logging.info("Bringing public interface %s down" % interface.get_device())
            cmd2 = "ip link set %s down" % interface.get_device()
            CsHelper.execute(cmd2)
            dev = interface.get_device()

        cmd = "%s -C %s" % (self.CONNTRACKD_BIN, self.CONNTRACKD_CONF)
        CsHelper.execute("%s -d" % cmd)
        CsHelper.service("ipsec", "stop")
        CsHelper.service("xl2tpd", "stop")
        CsHelper.service("dnsmasq", "stop")

        self._restart_password_server()

        self.cl.set_master_state(False)
        self.cl.save()
        self.release_lock()

        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_public()]
        CsHelper.reconfigure_interfaces(self.cl, interfaces)
        logging.info("Router switched to backup mode")

    def set_master(self):
        """ Set the current router to master """
        if not self.cl.is_redundant():
            logging.error("Set master called on non-redundant router")
            return

        self.set_lock()
        logging.debug("Setting router to master")

        self._bring_public_interfaces_up()

        logging.debug("Configuring static routes")
        static_routes = CsStaticRoutes("staticroutes", self.config)
        static_routes.process()

        cmd = "%s -C %s" % (self.CONNTRACKD_BIN, self.CONNTRACKD_CONF)
        CsHelper.execute("%s -c" % cmd)
        CsHelper.execute("%s -f" % cmd)
        CsHelper.execute("%s -R" % cmd)
        CsHelper.execute("%s -B" % cmd)
        CsHelper.service("ipsec", "restart")
        CsHelper.service("xl2tpd", "restart")
        CsHelper.service("dnsmasq", "restart")

        self._restart_password_server()

        self.cl.set_master_state(True)
        self.cl.save()
        self.release_lock()

        interfaces = [interface for interface in self.address.get_interfaces() if interface.is_public()]
        CsHelper.reconfigure_interfaces(self.cl, interfaces)
        logging.info("Router switched to master mode")


    def _bring_public_interfaces_up(self):
        '''Brings up all public interfaces and adds routes to the
        relevant routing tables.
        '''

        up = []         # devices we've already brought up
        routes = []     # routes to be added

        is_link_up = "ip link show %s | grep 'state UP'"
        set_link_up = "ip link set %s up"
        add_route = "ip route add %s"
        arping = "arping -c 1 -U %s -I %s"

        guestIps = [ip for ip in self.address.get_interfaces() if ip.is_guest()]
        guestDevs = []
        for guestIp in guestIps:
            guestDevs.append(guestIp.get_device())
        route = CsRoute()

        if self.config.is_vpc():
            default_gateway = VPC_PUBLIC_INTERFACE
        else:
            default_gateway = NETWORK_PUBLIC_INTERFACE

        public_ips = [ip for ip in self.address.get_interfaces() if ip.is_public()]

        for ip in public_ips:
            address = ip.get_ip()
            device = ip.get_device()
            gateway = ip.get_gateway()

            logging.debug("Configuring device %s for IP %s" % (device, address))

            if device in up:
                logging.debug("Device %s already configured. Skipping..." % device)
                continue

            if not CsDevice(device, self.config).waitfordevice():
                logging.error("Device %s was not ready could not bring it up." % device)
                continue

            if CsHelper.execute(is_link_up % device):
                logging.warn("Device %s was found already up. Assuming routes need configuring.")
                up.append(device)
            else:
                logging.info("Bringing public interface %s up" % device)
                CsHelper.execute(set_link_up % device)

            logging.debug("Collecting routes for interface %s" % device)
            routes.append("default via %s dev %s table Table_%s" % (gateway, device, device))

            if device in default_gateway:
                logging.debug("Determined that the gateway for %s should be in the main routing table." % device)
                routes.insert(0, "default via %s dev %s" % (gateway, device))

            up.append(device)

        logging.info("Adding all collected routes.")
        for route in routes:
            CsHelper.execute(add_route % route)

        logging.info("Sending gratuitous ARP for each Public IP...")
        for ip in public_ips:
            address = ip.get_ip()
            device = ip.get_device()
            # copy ip router for guest devs to all public devs
            route.copy_routes_from_main([device], guestDevs)
            CsHelper.execute(arping % (address, device))





    def _restart_password_server(self):
        '''
        CLOUDSTACK-9385
        Redundant virtual routers should have the password server running.
        '''
        if self.config.is_vpc():
            vrrp_addresses = [address for address in self.address.get_interfaces() if address.needs_vrrp()]

            for address in vrrp_addresses:
                CsPasswdSvc(address.get_gateway()).restart()
                CsPasswdSvc(address.get_ip()).restart()
        else:
            guest_addresses = [address for address in self.address.get_interfaces() if address.is_guest()]

            for address in guest_addresses:
                CsPasswdSvc(address.get_ip()).restart()


    def _collect_ignore_ips(self):
        """
        This returns a list of ip objects that should be ignored
        by conntrackd
        """
        lines = []
        lines.append("\t\t\tIPv4_address %s\n" % "127.0.0.1")
        lines.append("\t\t\tIPv4_address %s\n" %
                     self.address.get_control_if().get_ip())
        # FIXME - Do we need to also add any internal network gateways?
        return lines

    def _collect_ips(self):
        """
        Construct a list containing all the ips that need to be looked afer by vrrp
        This is based upon the address_needs_vrrp method in CsAddress which looks at
        the network type and decides if it is an internal address or an external one

        In a DomR there will only ever be one address in a VPC there can be many
        The new code also gives the possibility to cloudstack to have a hybrid device
        that could function as a router and VPC router at the same time
        """
        lines = []
        for interface in self.address.get_interfaces():
            if interface.needs_vrrp():
                cmdline=self.config.get_cmdline_instance()
                if not interface.is_added():
                    continue
                if(cmdline.get_type()=='router'):
                    str = "        %s brd %s dev %s\n" % (cmdline.get_guest_gw(), interface.get_broadcast(), interface.get_device())
                else:
                    str = "        %s brd %s dev %s\n" % (interface.get_gateway_cidr(), interface.get_broadcast(), interface.get_device())
                lines.append(str)
        return lines
