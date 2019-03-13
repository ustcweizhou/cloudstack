-- Licensed to the Apache Software Foundation (ASF) under one
-- or more contributor license agreements.  See the NOTICE file
-- distributed with this work for additional information
-- regarding copyright ownership.  The ASF licenses this file
-- to you under the Apache License, Version 2.0 (the
-- "License"); you may not use this file except in compliance
-- with the License.  You may obtain a copy of the License at
--
--   http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing,
-- software distributed under the License is distributed on an
-- "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
-- KIND, either express or implied.  See the License for the
-- specific language governing permissions and limitations
-- under the License.

UPDATE `cloud`.`configuration` SET name='account.default.storage.tag',description='The service/disk offerings without storage tag will use this storage tag in vm/volume allocation.' WHERE name='domain.storage.tag';
DELETE FROM `cloud`.`configuration` WHERE name='general.storage.tag';
INSERT INTO `cloud`.`storage_pool_tags` (pool_id,tag) SELECT pool_id,name FROM storage_pool_details WHERE name !='vmware.create.full.clone' AND value='true';
DELETE FROM `cloud`.`storage_pool_details` WHERE name !='vmware.create.full.clone' AND value='true';
UPDATE `cloud`.`domain_details` SET name='account.default.storage.tag' WHERE name='domain.storage.tag';

