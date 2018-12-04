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
import com.cloud.utils.concurrency.NamedThreadFactory;
import com.cloud.utils.exception.CloudRuntimeException;

import com.twilio.Twilio;
import com.twilio.rest.api.v2010.account.Message;
import com.twilio.type.PhoneNumber;

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;

import javax.inject.Inject;
import javax.mail.Authenticator;
import javax.mail.Message.RecipientType;
import javax.mail.MessagingException;
import javax.mail.PasswordAuthentication;
import javax.mail.SendFailedException;
import javax.mail.Session;
import javax.mail.URLName;
import javax.mail.internet.InternetAddress;
import javax.naming.ConfigurationException;

import com.sun.mail.smtp.SMTPMessage;
import com.sun.mail.smtp.SMTPSSLTransport;
import com.sun.mail.smtp.SMTPTransport;

import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.apache.cloudstack.framework.config.ConfigKey;
import org.apache.cloudstack.framework.config.Configurable;
import org.apache.commons.lang.StringUtils;
import org.apache.log4j.Logger;

public class TwoStepVerificationManagerImpl extends ManagerBase implements Manager, Configurable {
    public static final Logger s_logger = Logger.getLogger(TwoStepVerificationManagerImpl.class);

    private static EmailManager emailManager;

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

    @Override
    public boolean configure(String name, Map<String, Object> params) throws ConfigurationException {
        emailManager = new EmailManager("smtp.gmail.com", 465, 30000, 30000, true, true,
                "leasewebcloud@gmail.com", "cloudstack", "leasewebcloud@gmail.com", false);

        return true;
    }

    static class EmailManager {
        private Session _smtpSession;
        private InternetAddress[] _recipientList;
        private final String _smtpHost;
        private int _smtpPort = -1;
        private boolean _smtpUseAuth = false;
        private boolean _smtpSslAuth = false;
        private final String _smtpUsername;
        private final String _smtpPassword;
        private final String _emailSender;
        private int _smtpTimeout;
        private int _smtpConnectionTimeout;

        private ExecutorService _executor;

        public Session getSession() {
            return _smtpSession;
        }

        public EmailManager(final String smtpHost, final int smtpPort, final int smtpConnectionTimeout,
                final int smtpTimeout, final boolean smtpUseAuth, final boolean smtpSslAuth, final String smtpUsername,
                final String smtpPassword, String emailSender, boolean smtpDebug) {

            _smtpHost = smtpHost;
            _smtpPort = smtpPort;
            _smtpUseAuth = smtpUseAuth;
            _smtpSslAuth = smtpSslAuth;
            _smtpUsername = smtpUsername;
            _smtpPassword = smtpPassword;
            _emailSender = emailSender;
            _smtpTimeout = smtpTimeout;
            _smtpConnectionTimeout = smtpConnectionTimeout;

            if (_smtpHost != null) {
                Properties smtpProps = new Properties();
                smtpProps.put("mail.smtp.host", smtpHost);
                smtpProps.put("mail.smtp.port", smtpPort);
                smtpProps.put("mail.smtp.auth", "" + smtpUseAuth);
                smtpProps.put("mail.smtp.timeout", _smtpTimeout);
                smtpProps.put("mail.smtp.connectiontimeout", _smtpConnectionTimeout);

                if (smtpUsername != null) {
                    smtpProps.put("mail.smtp.user", smtpUsername);
                }

                smtpProps.put("mail.smtps.host", smtpHost);
                smtpProps.put("mail.smtps.port", smtpPort);
                smtpProps.put("mail.smtps.auth", "" + smtpUseAuth);
                smtpProps.put("mail.smtps.timeout", _smtpTimeout);
                smtpProps.put("mail.smtps.connectiontimeout", _smtpConnectionTimeout);

                if (smtpUsername != null) {
                    smtpProps.put("mail.smtps.user", smtpUsername);
                }

                if (("smtp.gmail.com").equals(smtpHost)) {
                    smtpProps.put("mail.smtp.starttls.enable","true");
                    smtpProps.put("mail.smtp.socketFactory.port",String.valueOf(smtpPort));
                    smtpProps.put("mail.smtp.socketFactory.class","javax.net.ssl.SSLSocketFactory");
                    smtpProps.put("mail.smtp.socketFactory.fallback","false");
                }

                if ((smtpUsername != null) && (smtpPassword != null)) {
                    _smtpSession = Session.getInstance(smtpProps, new Authenticator() {
                        @Override
                        protected PasswordAuthentication getPasswordAuthentication() {
                            return new PasswordAuthentication(smtpUsername, smtpPassword);
                        }
                    });
                } else {
                    _smtpSession = Session.getInstance(smtpProps);
                }
                _smtpSession.setDebug(smtpDebug);
            } else {
                _smtpSession = null;
            }

            _executor = Executors.newCachedThreadPool(new NamedThreadFactory("Email-Sender"));
        }

        public void sendEmail(List<String> recipientList, String subject, String content) throws UnsupportedEncodingException, MessagingException {
            s_logger.warn("Sending email to " + recipientList);
            InternetAddress[] recipient = null;
            if (recipientList != null) {
                recipient = new InternetAddress[recipientList.size()];
                int cnt = 0;
                for (String recipientInList: recipientList) {
                    try {
                        recipient[cnt++] = new InternetAddress(recipientInList, recipientInList);
                    } catch (Exception ex) {
                        s_logger.error("Exception creating address for: " + recipientInList, ex);
                    }
                }
            }
            if (_smtpSession != null) {
                SMTPMessage msg = new SMTPMessage(_smtpSession);
                msg.setSender(new InternetAddress(_emailSender, _emailSender));
                msg.setFrom(new InternetAddress(_emailSender, _emailSender));
                for (InternetAddress address : recipient) {
                    msg.addRecipient(RecipientType.TO, address);
                }
                msg.setSubject(subject);
                msg.setSentDate(new Date());
                msg.setContent(content, "text/html");
                msg.saveChanges();

                SMTPTransport smtpTrans = null;
                if (_smtpSslAuth) {
                    smtpTrans = new SMTPSSLTransport(_smtpSession, new URLName("smtps", _smtpHost, _smtpPort, null, _smtpUsername, _smtpPassword));
                } else {
                    smtpTrans = new SMTPTransport(_smtpSession, new URLName("smtp", _smtpHost, _smtpPort, null, _smtpUsername, _smtpPassword));
                }
                sendMessage(smtpTrans, msg);
                s_logger.debug("Done sending email to " + recipientList);
            }
        }

        private void sendMessage(final SMTPTransport smtpTrans, final SMTPMessage msg) {
            _executor.execute(new Runnable() {
                @Override
                public void run() {
                    try {
                        smtpTrans.connect();
                        smtpTrans.sendMessage(msg, msg.getAllRecipients());
                        smtpTrans.close();
                    } catch (SendFailedException e) {
                        s_logger.error(" Failed to send email due to " + e);
                    } catch (MessagingException e) {
                        s_logger.error(" Failed to send email due to " + e);
                    }
                }
            });
        }
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
        String body = "Verification code of Leaseweb Private Cloud : " + code;
        boolean result = sendSMS(TwoStepVerificationTwilioSid.value(), TwoStepVerificationTwilioToken.value(),
                TwoStepVerificationTwilioFromPhoneNumber.value(), toNumber, body);

        // TODO: get email address from user details
        List<String> recipientList = new ArrayList<String>();
        recipientList.add("w.zhou@global.leaseweb.com");
        String subject = "Verification code of Leaseweb Private Cloud";
        try {
            emailManager.sendEmail(recipientList, subject, body);
        } catch (UnsupportedEncodingException e1) {
            s_logger.debug("Failed to sent email to " + recipientList);
        } catch (MessagingException e2) {
            s_logger.debug("Failed to sent email to " + recipientList);
        }
        if (result) {
            return code;
        } else {
            return -1;
        }
    }
}
