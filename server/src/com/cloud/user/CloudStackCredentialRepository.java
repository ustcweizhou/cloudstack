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
import com.cloud.utils.exception.CloudRuntimeException;

import com.warrenstrange.googleauth.ICredentialRepository;

import java.util.List;
import javax.inject.Inject;

import org.apache.log4j.Logger;

public class CloudStackCredentialRepository implements ICredentialRepository {
    public static final Logger s_logger = Logger.getLogger(CloudStackCredentialRepository.class);

    @Inject
    UserDao _userDao;
    @Inject
    ConfigurationManager _configMgr;

    @Override
    public String getSecretKey(String userUuid) {
        UserVO user =  _userDao.findByUuid(userUuid);
        if (user == null) {
            s_logger.debug("Cannot find user " + userUuid);
            return null;
        }
        return TwoStepVerificationSecretKey.valueIn(user.getAccountId());
    }

    @Override
    public void saveUserCredentials(String userUuid, String secretKey, int validationCode, List<Integer> scratchCodes) {
        UserVO user = _userDao.findByUuid(userUuid);
        if (user == null) {
            throw new CloudRuntimeException("Cannot find user " + userUuid);
        }
        final String updatedValue =_configMgr.updateConfiguration(user.getId(),
                TwoStepVerificationSecretKey.key(), TwoStepVerificationSecretKey.category(),
                secretKey, TwoStepVerificationSecretKey.scope().toString(), user.getAccountId());
        if (secretKey == null && updatedValue == null || updatedValue.equalsIgnoreCase(secretKey)) {
            s_logger.debug("Saved secret key of Google Authenticator to database for account " + user.getAccountId());
        } else {
            throw new CloudRuntimeException("Unable to save secret key of Google Authenticator to database for account " + user.getAccountId());
        }
    }
}

