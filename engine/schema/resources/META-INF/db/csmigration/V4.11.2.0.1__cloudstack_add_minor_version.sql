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

DROP PROCEDURE IF EXISTS `cloud`.`add_minor_version_to_version`;
DELIMITER $$
CREATE PROCEDURE `cloud`.`add_minor_version_to_version`()
BEGIN
DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END;

ALTER TABLE `cloud`.`version` ADD COLUMN `minor_version` varchar(100) COMMENT 'minor version' AFTER `version`;
ALTER TABLE `cloud`.`version` DROP KEY `version`;
ALTER TABLE `cloud`.`version` DROP INDEX `i_version__version`;
ALTER TABLE `cloud`.`version` ADD UNIQUE `i_version__minor_version`(`version`, `minor_version`);

END $$
DELIMITER ;
CALL `cloud`.`add_minor_version_to_version`();
DROP PROCEDURE `cloud`.`add_minor_version_to_version`;

