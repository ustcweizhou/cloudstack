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
package org.apache.cloudstack.vm.dao;

import java.util.Date;
import java.util.List;

import org.apache.cloudstack.vm.VmConsoleTicketVO;
import org.springframework.stereotype.Component;

import com.cloud.utils.db.GenericDaoBase;
import com.cloud.utils.db.SearchBuilder;
import com.cloud.utils.db.SearchCriteria;

@Component
public class VmConsoleTicketDaoImpl extends GenericDaoBase<VmConsoleTicketVO, Long> implements VmConsoleTicketDao {
    private SearchBuilder<VmConsoleTicketVO> AllFieldsSearch;

    public VmConsoleTicketDaoImpl() {
        AllFieldsSearch = createSearchBuilder();
        AllFieldsSearch.and("vmId", AllFieldsSearch.entity().getVmId(), SearchCriteria.Op.EQ);
        AllFieldsSearch.and("ticket", AllFieldsSearch.entity().getTicket(), SearchCriteria.Op.EQ);
        AllFieldsSearch.and("created", AllFieldsSearch.entity().getCreated(), SearchCriteria.Op.LT);
        AllFieldsSearch.and("removed", AllFieldsSearch.entity().getRemoved(), SearchCriteria.Op.NULL);
        AllFieldsSearch.done();
    }

    @Override
    public List<VmConsoleTicketVO> listByVmId(Long vmId) {
        SearchCriteria<VmConsoleTicketVO> sc = AllFieldsSearch.create();
        sc.setParameters("vmId", vmId);
        return listBy(sc);
    }

    @Override
    public VmConsoleTicketVO findByVmIdAndTicket(Long vmId, String ticket) {
        SearchCriteria<VmConsoleTicketVO> sc = AllFieldsSearch.create();
        sc.setParameters("vmId", vmId);
        sc.setParameters("ticket", ticket);
        return findOneBy(sc);
    }

    @Override
    public void removeExpiredTicket(Date expiredDate) {
        SearchCriteria<VmConsoleTicketVO> sc = AllFieldsSearch.create();
        sc.setParameters("created", expiredDate);
        remove(sc);
    }
}
