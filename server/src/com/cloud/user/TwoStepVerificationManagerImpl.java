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

import com.twilio.Twilio;
import com.twilio.rest.api.v2010.account.Message;
import com.twilio.type.PhoneNumber;

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;

import java.util.Map;
import javax.inject.Inject;
import javax.naming.ConfigurationException;

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

    @Override
    public ConfigKey<?>[] getConfigKeys() {
        return new ConfigKey<?>[] { TwoStepVerificationEnabled, TwoStepVerificationTwilioSid,
                TwoStepVerificationTwilioToken, TwoStepVerificationTwilioFromPhoneNumber,
                TwoStepVerificationTwilioToPhoneNumber, TwoStepVerificationSecretKey };
    }

    @Override
    public String getConfigComponentName() {
        return TwoStepVerificationManagerImpl.class.getSimpleName();
    }

    @Override
    public boolean configure(final String name, final Map<String, Object> params) throws ConfigurationException {
        s_logger.debug("Creating verification code for user w.zhou");
        int code = generateVerificationCode("fed57d09-c3ae-40b2-abce-4072dd8a7089");
        s_logger.debug("Geneated verification code for user w.zhou : " + code);
        return true;
    }

    public boolean sendSMS(String sid, String token, String fromNumber, String toNumber, String body) {
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

    public int generateVerificationCode(String userUuid) {
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        final GoogleAuthenticatorKey key = gAuth.createCredentials(userUuid);
        return key.getVerificationCode();
    }

    public boolean authorizeUser(String userUuid, int verificationCode) {
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        boolean isCodeValid = gAuth.authorizeUser(userUuid, verificationCode);
        if (isCodeValid) {
            s_logger.debug("Two step verification passed for user " + userUuid);
        } else {
            s_logger.debug("Two step verification did not pass for user " + userUuid);
        }
        return isCodeValid;
    }

    public int generateAndSendVerificationCode(String userUuid) {
        UserVO user =  _userDao.findByUuid(userUuid);
        if (user == null) {
            s_logger.debug("Cannot find user " + userUuid);
            return -1;
        }
        if (! TwoStepVerificationEnabled.valueIn(user.getAccountId())) {
            return 0;
        }

        int code = generateVerificationCode(userUuid);
        String toNumber = TwoStepVerificationTwilioToPhoneNumber.valueIn(user.getAccountId());
        if (StringUtils.isEmpty(toNumber)) {
            return 0;
        }
        boolean result = sendSMS(TwoStepVerificationTwilioSid.value(), TwoStepVerificationTwilioToken.value(),
                TwoStepVerificationTwilioFromPhoneNumber.value(), toNumber, String.valueOf(code));
        if (result) {
            return 1;
        } else {
            return -1;
        }
    }
}
