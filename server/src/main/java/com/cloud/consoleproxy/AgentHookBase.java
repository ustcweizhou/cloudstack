// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

package com.cloud.consoleproxy;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Date;

import org.apache.commons.codec.binary.Base64;
import org.apache.log4j.Logger;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import org.apache.cloudstack.framework.config.dao.ConfigurationDao;
import org.apache.cloudstack.framework.security.keys.KeysManager;
import org.apache.cloudstack.framework.security.keystore.KeystoreManager;
import org.apache.cloudstack.vm.VmConsoleTicketVO;
import org.apache.cloudstack.vm.dao.VmConsoleTicketDao;

import com.cloud.agent.AgentManager;
import com.cloud.agent.api.AgentControlAnswer;
import com.cloud.agent.api.Answer;
import com.cloud.agent.api.ConsoleAccessAuthenticationAnswer;
import com.cloud.agent.api.ConsoleAccessAuthenticationCommand;
import com.cloud.agent.api.ConsoleProxyLoadReportCommand;
import com.cloud.agent.api.GetVncPortAnswer;
import com.cloud.agent.api.GetVncPortCommand;
import com.cloud.agent.api.StartupCommand;
import com.cloud.agent.api.StartupProxyCommand;
import com.cloud.agent.api.proxy.StartConsoleProxyAgentHttpHandlerCommand;
import com.cloud.configuration.Config;
import com.cloud.exception.AgentUnavailableException;
import com.cloud.exception.OperationTimedoutException;
import com.cloud.host.Host;
import com.cloud.host.HostVO;
import com.cloud.host.Status;
import com.cloud.host.dao.HostDao;
import com.cloud.servlet.ConsoleProxyPasswordBasedEncryptor;
import com.cloud.servlet.ConsoleProxyServlet;
import com.cloud.utils.Ternary;
import com.cloud.vm.VirtualMachine;
import com.cloud.vm.dao.VMInstanceDao;

/**
 * Utility class to manage interactions with agent-based console access
 * Extracted from ConsoleProxyManagerImpl so that other console proxy managers
 * can reuse
 */
public abstract class AgentHookBase implements AgentHook {
    private static final Logger s_logger = Logger.getLogger(AgentHookBase.class);

    VMInstanceDao _instanceDao;
    HostDao _hostDao;
    ConfigurationDao _configDao;
    AgentManager _agentMgr;
    KeystoreManager _ksMgr;
    KeysManager _keysMgr;
    VmConsoleTicketDao _ticketDao;

    public AgentHookBase(VMInstanceDao instanceDao, HostDao hostDao, ConfigurationDao cfgDao, KeystoreManager ksMgr, AgentManager agentMgr, KeysManager keysMgr, VmConsoleTicketDao ticketDao) {
        _instanceDao = instanceDao;
        _hostDao = hostDao;
        _agentMgr = agentMgr;
        _configDao = cfgDao;
        _ksMgr = ksMgr;
        _keysMgr = keysMgr;
        _ticketDao = ticketDao;
    }

    @Override
    public AgentControlAnswer onConsoleAccessAuthentication(ConsoleAccessAuthenticationCommand cmd) {
        String ticketInUrl = cmd.getTicket();
        if (ticketInUrl == null) {
            s_logger.error("Access ticket could not be found, you could be running an old version of console proxy. vmId: " + cmd.getVmId());
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        if (s_logger.isDebugEnabled()) {
            s_logger.debug("Console authentication. Ticket in url for " + cmd.getHost() + ":" + cmd.getPort() + "-" + cmd.getVmId() + " is " + ticketInUrl);
        }

        if (cmd.getVmId() != null && cmd.getVmId().isEmpty()) {
            if (s_logger.isDebugEnabled()) {
                s_logger.debug("Invalid vm id sent from proxy(happens when proxy session has terminated)");
            }
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        VirtualMachine vm = _instanceDao.findByUuid(cmd.getVmId());
        if (vm == null) {
            vm = _instanceDao.findById(Long.parseLong(cmd.getVmId()));
        }
        if (vm == null) {
            s_logger.error("Invalid vm id " + cmd.getVmId() + " sent from console access authentication");
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        Long vmId = vm.getId();
        if (!cmd.isReauthenticating()) {
            VmConsoleTicketVO ticket = _ticketDao.findByVmIdAndTicket(vmId, ticketInUrl);
            if (ticket == null) {
                s_logger.error("Access ticket does not exist or expired. vmId: " + cmd.getVmId() + "ticket in URL: " + ticketInUrl);
                return new ConsoleAccessAuthenticationAnswer(cmd, false);
            } else if (ticket.getTakenAt() != null) {
                s_logger.error("Access ticket has been used so it cannot be used any more. vmId: " + cmd.getVmId() + "ticket in URL: " + ticketInUrl);
                return new ConsoleAccessAuthenticationAnswer(cmd, false);
            }
            ticket.setTakenAt(new Date());
            _ticketDao.update(ticket.getId(), ticket);
        }

        if (vm.getHostId() == null) {
            s_logger.warn("VM " + vmId + " lost host info, failed authentication request");
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        HostVO host = _hostDao.findById(vm.getHostId());
        if (host == null) {
            s_logger.warn("VM " + vmId + "'s host does not exist, fail authentication request");
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        String sid = cmd.getSid();
        if (sid == null || !sid.equals(vm.getVncPassword())) {
            s_logger.warn("sid " + sid + " in url does not match stored sid.");
            return new ConsoleAccessAuthenticationAnswer(cmd, false);
        }

        if (cmd.isReauthenticating()) {
            ConsoleAccessAuthenticationAnswer authenticationAnswer = new ConsoleAccessAuthenticationAnswer(cmd, true);
            authenticationAnswer.setReauthenticating(true);

            s_logger.info("Re-authentication request, ask host " + vm.getHostId() + " for new console info");
            GetVncPortAnswer answer = (GetVncPortAnswer)_agentMgr.easySend(vm.getHostId(), new GetVncPortCommand(vm.getId(), vm.getInstanceName()));

            if (answer != null && answer.getResult()) {
                Ternary<String, String, String> parsedHostInfo = ConsoleProxyServlet.parseHostInfo(answer.getAddress());

                if (parsedHostInfo.second() != null && parsedHostInfo.third() != null) {

                    s_logger.info("Re-authentication result. vm: " + vm.getId() + ", tunnel url: " + parsedHostInfo.second() + ", tunnel session: " +
                        parsedHostInfo.third());

                    authenticationAnswer.setTunnelUrl(parsedHostInfo.second());
                    authenticationAnswer.setTunnelSession(parsedHostInfo.third());
                } else {
                    s_logger.info("Re-authentication result. vm: " + vm.getId() + ", host address: " + parsedHostInfo.first() + ", port: " + answer.getPort());

                    authenticationAnswer.setHost(parsedHostInfo.first());
                    authenticationAnswer.setPort(answer.getPort());
                }
            } else {
                s_logger.warn("Re-authentication request failed");

                authenticationAnswer.setSuccess(false);
            }

            return authenticationAnswer;
        }

        return new ConsoleAccessAuthenticationAnswer(cmd, true);
    }

    @Override
    public void startAgentHttpHandlerInVM(StartupProxyCommand startupCmd) {
        StartConsoleProxyAgentHttpHandlerCommand cmd = null;

        try {
            SecureRandom random = SecureRandom.getInstance("SHA1PRNG");

            byte[] randomBytes = new byte[16];
            random.nextBytes(randomBytes);
            String storePassword = Base64.encodeBase64String(randomBytes);

            byte[] ksBits = null;
            String consoleProxyUrlDomain = _configDao.getValue(Config.ConsoleProxyUrlDomain.key());
            if (consoleProxyUrlDomain == null || consoleProxyUrlDomain.isEmpty()) {
                s_logger.debug("SSL is disabled for console proxy based on global config, skip loading certificates");
            } else {
                ksBits = _ksMgr.getKeystoreBits(ConsoleProxyManager.CERTIFICATE_NAME, ConsoleProxyManager.CERTIFICATE_NAME, storePassword);
                //ks manager raises exception if ksBits are null, hence no need to explicltly handle the condition
            }

            cmd = new StartConsoleProxyAgentHttpHandlerCommand(ksBits, storePassword);
            cmd.setEncryptorPassword(getEncryptorPassword());

            HostVO consoleProxyHost = findConsoleProxyHost(startupCmd);

            assert (consoleProxyHost != null);
            if (consoleProxyHost != null) {
                Answer answer = _agentMgr.send(consoleProxyHost.getId(), cmd);
                if (answer == null || !answer.getResult()) {
                    s_logger.error("Console proxy agent reported that it failed to execute http handling startup command");
                } else {
                    s_logger.info("Successfully sent out command to start HTTP handling in console proxy agent");
                }
            }
        }catch (NoSuchAlgorithmException e) {
            s_logger.error("Unexpected exception in SecureRandom Algorithm selection ", e);
        } catch (AgentUnavailableException e) {
            s_logger.error("Unable to send http handling startup command to the console proxy resource for proxy:" + startupCmd.getProxyVmId(), e);
        } catch (OperationTimedoutException e) {
            s_logger.error("Unable to send http handling startup command(time out) to the console proxy resource for proxy:" + startupCmd.getProxyVmId(), e);
        } catch (OutOfMemoryError e) {
            s_logger.error("Unrecoverable OutOfMemory Error, exit and let it be re-launched");
            System.exit(1);
        } catch (Exception e) {
            s_logger.error(
                "Unexpected exception when sending http handling startup command(time out) to the console proxy resource for proxy:" + startupCmd.getProxyVmId(), e);
        }
    }

    private String getEncryptorPassword() {
        String key;
        String iv;
        ConsoleProxyPasswordBasedEncryptor.KeyIVPair keyIvPair = null;

        // if we failed after reset, something is definitely wrong
        for (int i = 0; i < 2; i++) {
            key = _keysMgr.getEncryptionKey();
            iv = _keysMgr.getEncryptionIV();

            keyIvPair = new ConsoleProxyPasswordBasedEncryptor.KeyIVPair(key, iv);

            if (keyIvPair.getIvBytes() == null || keyIvPair.getIvBytes().length != 16 || keyIvPair.getKeyBytes() == null || keyIvPair.getKeyBytes().length != 16) {

                s_logger.warn("Console access AES KeyIV sanity check failed, reset and regenerate");
                _keysMgr.resetEncryptionKeyIV();
            } else {
                break;
            }
        }

        Gson gson = new GsonBuilder().create();
        return gson.toJson(keyIvPair);
    }

    protected abstract HostVO findConsoleProxyHost(StartupProxyCommand cmd);

    @Override
    public void onLoadReport(ConsoleProxyLoadReportCommand cmd) {
        // no-op since we do not auto-scale
    }

    @Override
    public void onAgentConnect(Host host, StartupCommand cmd) {
        // no-op
    }

    @Override
    public void onAgentDisconnect(long agentId, Status state) {
        // no-op since we do not autoscale
    }
}
