//
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
//

package com.cloud.hypervisor.kvm.resource.wrapper;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;
import java.util.Map;

import org.apache.cloudstack.storage.to.VolumeObjectTO;
import org.apache.log4j.Logger;
import org.libvirt.Connect;
import org.libvirt.Domain;
import org.libvirt.LibvirtException;

import com.cloud.agent.api.Answer;
import com.cloud.agent.api.RestoreVMSnapshotAnswer;
import com.cloud.agent.api.RestoreVMSnapshotCommand;
import com.cloud.agent.api.VMSnapshotTO;
import com.cloud.hypervisor.kvm.resource.LibvirtComputingResource;
import com.cloud.resource.CommandWrapper;
import com.cloud.resource.ResourceWrapper;
import com.cloud.utils.script.Script;
import com.cloud.vm.VirtualMachine;

@ResourceWrapper(handles =  RestoreVMSnapshotCommand.class)
public final class LibvirtRestoreVMSnapshotCommandWrapper extends CommandWrapper<RestoreVMSnapshotCommand, Answer, LibvirtComputingResource> {

    private static final Logger s_logger = Logger.getLogger(LibvirtRestoreVMSnapshotCommandWrapper.class);

    @Override
    public Answer execute(final RestoreVMSnapshotCommand cmd, final LibvirtComputingResource libvirtComputingResource) {
        String vmName = cmd.getVmName();
        List<VolumeObjectTO> listVolumeTo = cmd.getVolumeTOs();
        VirtualMachine.PowerState vmState = VirtualMachine.PowerState.PowerOn;

        Domain dm = null;
        try {
            final LibvirtUtilitiesHelper libvirtUtilitiesHelper = libvirtComputingResource.getLibvirtUtilitiesHelper();
            Connect conn = libvirtUtilitiesHelper.getConnection();
            dm = libvirtComputingResource.getDomain(conn, vmName);

            if (dm == null) {
                return new RestoreVMSnapshotAnswer(cmd, false,
                        "Restore VM Snapshot Failed due to can not find vm: " + vmName);
            }
            String xmlDesc = dm.getXMLDesc(0);

            List<VMSnapshotTO> snapshots = cmd.getSnapshots();
            Map<Long, VMSnapshotTO> snapshotAndParents = cmd.getSnapshotAndParents();
            for (VMSnapshotTO snapshot: snapshots) {
                VMSnapshotTO parent = snapshotAndParents.get(snapshot.getId());
                String vmSnapshotXML = libvirtUtilitiesHelper.generateVMSnapshotXML(snapshot, parent, xmlDesc);
                s_logger.debug("Restoring vm snapshot " + snapshot.getSnapshotName() + " on " + vmName + " with XML:\n " + vmSnapshotXML);
                File tmpCfgFile = null;
                try {
                    tmpCfgFile = File.createTempFile(vmName + "-", "cfg");
                    final PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter(tmpCfgFile)));
                    out.println(vmSnapshotXML);
                    out.close();
                    String cfgFilePath = tmpCfgFile.getAbsolutePath();
                    String cmdvirsh = "virsh snapshot-create --redefine " + vmName + (snapshot.getCurrent()? " --current ":" ") + cfgFilePath;
                    int cmdout = Script.runSimpleBashScriptForExitValue(cmdvirsh);
                    String result = null;
                    if (cmdout != 0) {
                        result = "Failed to migrate domain with exit value:" + cmdout;
                        return new RestoreVMSnapshotAnswer(cmd, false, result);
                    }
                } catch (IOException e) {
                    s_logger.debug("Failed to restore vm snapshot " + snapshot.getSnapshotName() + " on " + vmName);
                    return new RestoreVMSnapshotAnswer(cmd, false, e.toString());
                } finally {
                    if (tmpCfgFile != null) {
                        tmpCfgFile.delete();
                    }
                }
            }

            return new RestoreVMSnapshotAnswer(cmd, listVolumeTo, vmState);
        } catch (LibvirtException e) {
            String msg = " Restore snapshot failed due to " + e.toString();
            s_logger.warn(msg, e);
            return new RestoreVMSnapshotAnswer(cmd, false, msg);
        } finally {
            if (dm != null) {
                try {
                    dm.free();
                } catch (LibvirtException l) {
                    s_logger.trace("Ignoring libvirt error.", l);
                };
            }
        }
    }
}
