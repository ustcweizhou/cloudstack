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
package com.cloud.user;

import com.cloud.configuration.ConfigurationManager;
import com.cloud.user.dao.UserDao;
import com.cloud.utils.component.ManagerBase;
import com.cloud.utils.exception.CloudRuntimeException;
import com.warrenstrange.googleauth.ICredentialRepository;

import java.util.List;
import javax.annotation.PostConstruct;
import javax.inject.Inject;

import org.apache.log4j.Logger;

public class CloudStackCredentialRepository extends ManagerBase implements ICredentialRepository {
    public static final Logger s_logger = Logger.getLogger(CloudStackCredentialRepository.class);

    @Inject
    UserDao _userDao;
    @Inject
    ConfigurationManager _configMgr;

    static UserDao s_userDao;
    static ConfigurationManager s_configMgr;

    @PostConstruct
    void init() {
        s_userDao = _userDao;
        s_configMgr = _configMgr;
    }

    @Override
    public String getSecretKey(String userUuid) {
        UserVO user = s_userDao.getUser(userUuid);
        if (user == null) {
            s_logger.debug("Cannot find user " + userUuid);
            return null;
        }
        return TwoStepVerificationManagerImpl.TwoStepVerificationSecretKey.valueIn(user.getAccountId());
    }

    @Override
    public void saveUserCredentials(String userUuid, String secretKey, int validationCode, List<Integer> scratchCodes) {
        UserVO user = s_userDao.getUser(userUuid);
        if (user == null) {
            throw new CloudRuntimeException("Cannot find user " + userUuid);
        }
        final String updatedValue = s_configMgr.updateConfiguration(user.getId(),
                TwoStepVerificationManagerImpl.TwoStepVerificationSecretKey.key(),
                TwoStepVerificationManagerImpl.TwoStepVerificationSecretKey.category(),
                secretKey, TwoStepVerificationManagerImpl.TwoStepVerificationSecretKey.scope().toString(),
                user.getAccountId());
        if (secretKey == null && updatedValue == null || updatedValue.equalsIgnoreCase(secretKey)) {
            s_logger.debug("Saved secret key of Google Authenticator to database for account " + user.getAccountId());
        } else {
            throw new CloudRuntimeException("Unable to save secret key of Google Authenticator to database for account " + user.getAccountId());
        }
    }
}

