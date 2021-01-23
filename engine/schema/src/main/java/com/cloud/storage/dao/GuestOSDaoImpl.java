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
package com.cloud.storage.dao;

import java.util.List;

import javax.annotation.PostConstruct;
import javax.inject.Inject;

import org.springframework.stereotype.Component;

import com.cloud.storage.GuestOSHypervisorVO;
import com.cloud.storage.GuestOSVO;
import com.cloud.utils.db.JoinBuilder.JoinType;
import com.cloud.utils.db.GenericDaoBase;
import com.cloud.utils.db.SearchBuilder;
import com.cloud.utils.db.SearchCriteria;

@Component
public class GuestOSDaoImpl extends GenericDaoBase<GuestOSVO, Long> implements GuestOSDao {

    @Inject
    private GuestOSHypervisorDao guestOSHypervisorDao;

    protected SearchBuilder<GuestOSVO> Search;
    private SearchBuilder<GuestOSVO> ListByIdsAndHypervisors;

    protected GuestOSDaoImpl() {
    }

    @PostConstruct
    protected void init() {
        Search = createSearchBuilder();
        Search.and("display_name", Search.entity().getDisplayName(), SearchCriteria.Op.EQ);
        Search.done();

        SearchBuilder<GuestOSHypervisorVO> guestOsMapping = guestOSHypervisorDao.createSearchBuilder();
        guestOsMapping.and("display", guestOsMapping.entity().isDisplay(), SearchCriteria.Op.EQ);
        guestOsMapping.and("hypervisor", guestOsMapping.entity().getHypervisorType(), SearchCriteria.Op.IN);

        ListByIdsAndHypervisors = createSearchBuilder();
        ListByIdsAndHypervisors.groupBy(ListByIdsAndHypervisors.entity().getId());
        ListByIdsAndHypervisors.and("ids", ListByIdsAndHypervisors.entity().getId(), SearchCriteria.Op.IN);
        ListByIdsAndHypervisors.join("guestOsMapping", guestOsMapping, ListByIdsAndHypervisors.entity().getId(), guestOsMapping.entity().getGuestOsId(), JoinType.INNER);
        ListByIdsAndHypervisors.done();
    }

    @Override
    public GuestOSVO listByDisplayName(String displayName) {
        SearchCriteria<GuestOSVO> sc = Search.create();
        sc.setParameters("display_name", displayName);
        return findOneBy(sc);
    }

    @Override
    public List<GuestOSVO> listByIdsAndHypervisors(List<Long> guestOSIds, List<String> hypervisors) {
        SearchCriteria<GuestOSVO> sc = ListByIdsAndHypervisors.create();
        sc.setParameters("ids", guestOSIds.toArray(new Object[guestOSIds.size()]));
        sc.setJoinParameters("guestOsMapping", "hypervisor", hypervisors.toArray(new Object[hypervisors.size()]));
        sc.setJoinParameters("guestOsMapping", "display", 1);
        return listBy(sc);
    }
}
