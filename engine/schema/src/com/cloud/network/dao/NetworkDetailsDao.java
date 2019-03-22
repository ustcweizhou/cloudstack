// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// the License.  You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.
package com.cloud.network.dao;

import com.cloud.utils.db.GenericDao;
import org.apache.cloudstack.resourcedetail.ResourceDetailsDao;

import java.util.List;
import java.util.Map;

public interface NetworkDetailsDao extends GenericDao<NetworkDetailVO, Long>, ResourceDetailsDao<NetworkDetailVO> {

    Map<String, String> findDetails(long networkId);

    void persist(long networkId, Map<String, String> details);

    NetworkDetailVO findDetail(long networkId, String name);

    List<NetworkDetailVO> listDetailsByName(String name);

    void deleteDetails(long networkId);

    void update(long networkId, Map<String, String> details);

}
