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
package org.apache.cloudstack.resourcedetail.dao;


import org.springframework.stereotype.Component;

import org.apache.cloudstack.resourcedetail.ResourceDetailsDaoBase;
import org.apache.cloudstack.resourcedetail.VpcDetailVO;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.cloudstack.framework.config.ConfigKey;
import org.apache.cloudstack.framework.config.ConfigKey.Scope;
import org.apache.cloudstack.framework.config.ScopedConfigStorage;

import com.cloud.utils.db.QueryBuilder;
import com.cloud.utils.db.SearchBuilder;
import com.cloud.utils.db.SearchCriteria;
import com.cloud.utils.db.SearchCriteria.Op;
import com.cloud.utils.db.TransactionLegacy;

@Component
public class VpcDetailsDaoImpl extends ResourceDetailsDaoBase<VpcDetailVO> implements VpcDetailsDao, ScopedConfigStorage {
    protected final SearchBuilder<VpcDetailVO> vpcSearch;

    @Override
    public void addDetail(long resourceId, String key, String value, boolean display) {
        super.addDetail(new VpcDetailVO(resourceId, key, value, display));
    }

    protected VpcDetailsDaoImpl() {
        vpcSearch = createSearchBuilder();
        vpcSearch.and("vpcId", vpcSearch.entity().getResourceId(), Op.EQ);
        vpcSearch.done();
    }

    @Override
    public Map<String, String> findDetails(long vpcId) {
        QueryBuilder<VpcDetailVO> sc = QueryBuilder.create(VpcDetailVO.class);
        sc.and(sc.entity().getResourceId(), Op.EQ, vpcId);
        List<VpcDetailVO> results = sc.list();
        Map<String, String> details = new HashMap<String, String>(results.size());
        for (VpcDetailVO r : results) {
            details.put(r.getName(), r.getValue());
        }
        return details;
    }

    @Override
    public void persist(long vpcId, Map<String, String> details) {
        TransactionLegacy txn = TransactionLegacy.currentTxn();
        txn.start();
        SearchCriteria<VpcDetailVO> sc = vpcSearch.create();
        sc.setParameters("vpcId", vpcId);
        expunge(sc);
        for (Map.Entry<String, String> detail : details.entrySet()) {
            VpcDetailVO vo = new VpcDetailVO(vpcId, detail.getKey(), detail.getValue(), true);
            persist(vo);
        }
        txn.commit();
    }

    @Override
    public VpcDetailVO findDetail(long vpcId, String name) {
        QueryBuilder<VpcDetailVO> sc = QueryBuilder.create(VpcDetailVO.class);
        sc.and(sc.entity().getResourceId(), Op.EQ, vpcId);
        sc.and(sc.entity().getName(), Op.EQ, name);
        return sc.find();
    }

    @Override
    public List<VpcDetailVO> listDetailsByName(String name) {
        QueryBuilder<VpcDetailVO> sc = QueryBuilder.create(VpcDetailVO.class);
        sc.and(sc.entity().getName(), Op.EQ, name);
        return sc.list();
    }

    @Override
    public void deleteDetails(long vpcId) {
        SearchCriteria<VpcDetailVO> sc = vpcSearch.create();
        sc.setParameters("vpcId", vpcId);
        List<VpcDetailVO> results = search(sc, null);
        for (VpcDetailVO result : results) {
            remove(result.getId());
        }
    }

    @Override
    public void update(long vpcId, Map<String, String> details) {
        Map<String, String> oldDetails = findDetails(vpcId);
        oldDetails.putAll(details);
        persist(vpcId, oldDetails);
    }

    @Override
    public Scope getScope() {
        return ConfigKey.Scope.Vpc;
    }

    @Override
    public String getConfigValue(long id, ConfigKey<?> key) {
        VpcDetailVO vo = findDetail(id, key.key());
        return vo == null ? null : vo.getValue();
    }
}
