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
import com.cloud.utils.component.Manager;
import com.cloud.utils.component.ManagerBase;
import com.cloud.utils.exception.CloudRuntimeException;

import com.twilio.Twilio;
import com.twilio.rest.api.v2010.account.Message;
import com.twilio.type.PhoneNumber;

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;

import javax.inject.Inject;

import org.apache.cloudstack.framework.config.ConfigKey;
import org.apache.cloudstack.framework.config.Configurable;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;

public class TwoStepVerificationManagerImpl extends ManagerBase implements Manager, Configurable {
    public static final Logger s_logger = Logger.getLogger(TwoStepVerificationManagerImpl.class);

    @Inject
    UserDao _userDao;
    @Inject
    ConfigurationManager _configMgr;

    public static final ConfigKey<Boolean> TwoStepVerificationEnabled = new ConfigKey<Boolean>("Advanced", Boolean.class, "two.step.verification.enabled", "true", "If true, two step verification will be enabled for all users except admin", true, ConfigKey.Scope.Account);

    public static final ConfigKey<String> TwoStepVerificationTwilioSid = new ConfigKey<String>(String.class, "two.step.verification.twilio.sid", "Advanced", "", "SID of twilio account used in two step verification.", true, ConfigKey.Scope.Global, null);

    public static final ConfigKey<String> TwoStepVerificationTwilioToken = new ConfigKey<String>(String.class, "two.step.verification.twilio.token", "Advanced", "", "token of twilio account used in two step verification.", true, ConfigKey.Scope.Global, null);

    public static final ConfigKey<String> TwoStepVerificationTwilioFromPhoneNumber = new ConfigKey<String>(String.class, "two.step.verification.twilio.from.phone.number", "Advanced", "", "phone number where twilio SMS sent from in two step verification.", true, ConfigKey.Scope.Global, null);

    public static final ConfigKey<String> TwoStepVerificationTwilioToPhoneNumber = new ConfigKey<String>(String.class, "two.step.verification.twilio.to.phone.number", "Advanced", "", "phone number to receive twilio SMS in two step verification. This is used for testing", true, ConfigKey.Scope.Account, null);

    public static final ConfigKey<String> TwoStepVerificationSecretKey = new ConfigKey<String>(String.class, "two.step.verification.secret.key", "Advanced", "", "secret key of Google Authenticator in two step verification.", true, ConfigKey.Scope.Account, null);

    public static final ConfigKey<String> TwoStepVerificationClientAddress = new ConfigKey<String>(String.class, "two.step.verification.client.address", "Advanced", "", "client address in two step verification.", true, ConfigKey.Scope.Account, null);

    @Override
    public ConfigKey<?>[] getConfigKeys() {
        return new ConfigKey<?>[] { TwoStepVerificationEnabled, TwoStepVerificationTwilioSid,
                TwoStepVerificationTwilioToken, TwoStepVerificationTwilioFromPhoneNumber,
                TwoStepVerificationTwilioToPhoneNumber, TwoStepVerificationSecretKey,
                TwoStepVerificationClientAddress };
    }

    @Override
    public String getConfigComponentName() {
        return TwoStepVerificationManagerImpl.class.getSimpleName();
    }

    public boolean sendSMS(String sid, String token, String fromNumber, String toNumber, String body) {
        //TODO: remove it
        if (1==1)
            return true;
        Twilio.init(sid, token);
        Message message = Message.creator(new PhoneNumber(toNumber), new PhoneNumber(fromNumber), body).create();
        if (! StringUtils.isEmpty(message.getSid())){
            s_logger.debug("Message sent, sid is " + message.getSid());
            return true;
        } else {
            s_logger.debug("Message sent, sid is empty, return false");
            return false;
        }
    }

    public int generateVerificationCode(UserVO user) {
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        GoogleAuthenticatorKey key = gAuth.createCredentials();
        String secretKey = key.getKey();
        final String updatedValue = _configMgr.updateConfiguration(user.getId(),
                TwoStepVerificationSecretKey.key(), TwoStepVerificationSecretKey.category(),
                secretKey, TwoStepVerificationSecretKey.scope().toString(), user.getAccountId());
        if (secretKey == null && updatedValue == null || updatedValue.equalsIgnoreCase(secretKey)) {
            s_logger.debug("Saved secret key of Google Authenticator to database for account " + user.getAccountId());
        } else {
            throw new CloudRuntimeException("Unable to save secret key of Google Authenticator to database for account " + user.getAccountId());
        }
        int code = gAuth.getTotpPassword(secretKey);
        s_logger.debug("Generated verification code: " + code);
        return code;
    }

    public String getSecretKey(UserVO user) {
        String secretKey = TwoStepVerificationSecretKey.valueIn(user.getAccountId());
        if (StringUtils.isEmpty(secretKey)) {
            throw new CloudRuntimeException("Secret key of Google Authenticator is empty for account " + user.getAccountId());
        }
        return secretKey;
    }

    public boolean authorizeUser(String userUuid, int verificationCode, String clientAddress) {
        UserVO user = _userDao.findByUuid(userUuid);
        if (user == null) {
            s_logger.debug("Cannot find user " + userUuid);
            throw new CloudRuntimeException("Cannot find user " + userUuid);
        }
        String clientAddressInDB = TwoStepVerificationClientAddress.valueIn(user.getAccountId());
        if (! clientAddressInDB.equals(clientAddress)) {
            throw new CloudRuntimeException("client address " + clientAddress + " is different from last request");
        }
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        String secretKey = getSecretKey(user);
        boolean isCodeValid = gAuth.authorize(secretKey, verificationCode);
        if (isCodeValid) {
            s_logger.debug("Two step verification passed for user " + userUuid);
        } else {
            s_logger.debug("Two step verification did not pass for user " + userUuid);
        }
        return isCodeValid;
    }

    public int generateAndSendVerificationCode(String userUuid, String clientAddress) {
        UserVO user = _userDao.findByUuid(userUuid);
        if (user == null) {
            s_logger.debug("Cannot find user " + userUuid);
            throw new CloudRuntimeException("Cannot find user " + userUuid);
        }
        if (! TwoStepVerificationEnabled.valueIn(user.getAccountId())) {
            return 0;
        }

        // save client address
        final String updatedClientAddress = _configMgr.updateConfiguration(user.getId(),
                TwoStepVerificationClientAddress.key(), TwoStepVerificationClientAddress.category(),
                clientAddress, TwoStepVerificationClientAddress.scope().toString(), user.getAccountId());
        if (clientAddress == null && updatedClientAddress == null || updatedClientAddress.equalsIgnoreCase(clientAddress)) {
            s_logger.debug("Saved client address to database for account " + user.getAccountId());
        } else {
            throw new CloudRuntimeException("Unable to save client address to database for account " + user.getAccountId());
        }

        int code = generateVerificationCode(user);
        // TODO: get toNumber from user details
        String toNumber = TwoStepVerificationTwilioToPhoneNumber.valueIn(user.getAccountId());
        if (StringUtils.isEmpty(toNumber)) {
            return 0;
        }
        boolean result = sendSMS(TwoStepVerificationTwilioSid.value(), TwoStepVerificationTwilioToken.value(),
                TwoStepVerificationTwilioFromPhoneNumber.value(), toNumber, String.valueOf(code));
        if (result) {
            return code;
        } else {
            return -1;
        }
    }
}
