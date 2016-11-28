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
package com.cloud.agent.api.to;

import com.cloud.server.ResourceTag;
import com.cloud.server.ResourceTag.ResourceObjectType;

public class ResourceTagTO {
    private String uuid;
    private String key;
    private String value;
    private String resourceUuid;
    private ResourceObjectType resourceType;

    public ResourceTagTO(String uuid, String key, String value, ResourceObjectType resourceType, String resourceUuid) {
        this.uuid = uuid;
        this.key = key;
        this.value = value;
        this.resourceType = resourceType;
        this.resourceUuid = resourceUuid;
    }

    public ResourceTagTO(ResourceTag resourceTag) {
        this.uuid = resourceTag.getUuid();
        this.key = resourceTag.getKey();
        this.value = resourceTag.getValue();
        this.resourceType = resourceTag.getResourceType();
        this.resourceUuid = resourceTag.getResourceUuid();
    }

    protected ResourceTagTO() {
    }

    public String getUuid() {
        return uuid;
    }

    public String getKey() {
        return key;
    }

    public String getValue() {
        return value;
    }

    public ResourceObjectType getResourceType() {
        return resourceType;
    }

    public String getResourceUuid() {
        return resourceUuid;
    }
}
