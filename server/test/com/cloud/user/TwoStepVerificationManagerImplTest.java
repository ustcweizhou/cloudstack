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

import com.twilio.Twilio;
import com.twilio.rest.api.v2010.account.Message;
import com.twilio.type.PhoneNumber;

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorConfig;
import com.warrenstrange.googleauth.GoogleAuthenticatorConfig.GoogleAuthenticatorConfigBuilder;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;

import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.TimeUnit;
import javax.mail.Authenticator;
import javax.mail.MessagingException;
import javax.mail.PasswordAuthentication;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.URLName;
import javax.mail.internet.AddressException;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;

import com.sun.mail.smtp.SMTPMessage;
import com.sun.mail.smtp.SMTPSSLTransport;
import com.sun.mail.smtp.SMTPTransport;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import com.cloud.user.TwoStepVerificationManagerImpl.EmailManager;

public class TwoStepVerificationManagerImplTest {

    EmailManager emailManager;

    @Before
    public void setUp() {
        emailManager = new EmailManager("smtp.gmail.com", 465, 30000, 30000, true, true,
                "leasewebcloud@gmail.com", "cloudstack", "leasewebcloud@gmail.com", true);
    }

    @After
    public void tearDown() {
        try {
            Thread.sleep(5000);
        } catch (Exception e) {
        }
    }

    @Test
    public void generateAndVerifyCode1() {
        // mvn -P developer,systemvm -pl server -Dtest=com.cloud.user.TwoStepVerificationManagerImplTest
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        GoogleAuthenticatorKey key = gAuth.createCredentials();
        String secretKey = key.getKey();
        int code = gAuth.getTotpPassword(secretKey);
        System.out.println("Test 1: secret key is " + secretKey + ", verification code is " + code);

        long now = new Date().getTime();

        for (int i = 0; i < 120; i++) {
            boolean isCodeValid = gAuth.authorize(secretKey, code, now + i * 1000);
            if (isCodeValid) {
                System.out.println("Test 1: Two step verification passed after " + i + "s");
            } else {
                System.out.println("Test 1: Two step verification did not pass after " + i + "s");
                break;
            }
        }
    }

    @Test
    public void generateAndVerifyCode2() {
        // mvn -P developer,systemvm -pl server -Dtest=com.cloud.user.TwoStepVerificationManagerImplTest
        GoogleAuthenticatorConfigBuilder builder = new GoogleAuthenticatorConfigBuilder();
        builder.setCodeDigits(8);
        builder.setTimeStepSizeInMillis(TimeUnit.SECONDS.toMillis(60));
        GoogleAuthenticatorConfig config = builder.build();
        GoogleAuthenticator gAuth = new GoogleAuthenticator(config);
        GoogleAuthenticatorKey key = gAuth.createCredentials();
        String secretKey = key.getKey();
        int code = gAuth.getTotpPassword(secretKey);
        System.out.println("Test 2: secret key is " + secretKey + ", verification code is " + code);

        long now = new Date().getTime();

        for (int i = 0; i < 120; i++) {
            boolean isCodeValid = gAuth.authorize(secretKey, code, now + i * 1000);
            if (isCodeValid) {
                System.out.println("Test 2: Two step verification passed after " + i + "s");
            } else {
                System.out.println("Test 2: Two step verification did not pass after " + i + "s");
                break;
            }
        }
    }

    @Test
    public void generateAndSentCode3() {
        GoogleAuthenticatorConfigBuilder builder = new GoogleAuthenticatorConfigBuilder();
        builder.setCodeDigits(8);
        builder.setTimeStepSizeInMillis(TimeUnit.SECONDS.toMillis(60));
        GoogleAuthenticatorConfig config = builder.build();
        GoogleAuthenticator gAuth = new GoogleAuthenticator(config);
        GoogleAuthenticatorKey key = gAuth.createCredentials();
        String secretKey = key.getKey();
        int code = gAuth.getTotpPassword(secretKey);
        System.out.println("Test 3: secret key is " + secretKey + ", verification code is " + code);

        String sid = "AC8e90ade0e3240e50fc9ce2dc9f50a54e";
        String token = "0a9170c914a8876f01765368080b3ac9";
        String toNumber = "+31615855099";
        String fromNumber = "+18102029336";
        String body = "verfication code is " + code;

        Twilio.init(sid, token);
        Message message = Message.creator(new PhoneNumber(toNumber), new PhoneNumber(fromNumber), body).create();
        System.out.println("Message sent, sid is " + message.getSid());
    }

    @Test
    public void sendEmailviaGmail() {
        final String d_email = "leasewebcloud@gmail.com";
        final String d_uname = "leasewebcloud@gmail.com";
        final String d_password = "cloudstack";
        final String d_host = "smtp.gmail.com";
        final int d_port  = 465;
        final String m_to = "w.zhou@global.leaseweb.com";
        final String m_subject = "send Email via Gmail";
        final String m_text = "This message is from Leaseweb Cloud";
        Properties props = new Properties();
        props.put("mail.smtp.user", d_email);
        props.put("mail.smtp.host", d_host);
        props.put("mail.smtp.port", d_port);
        props.put("mail.smtp.starttls.enable","true");
        props.put("mail.smtp.debug", "true");
        props.put("mail.smtp.auth", "true");
        props.put("mail.smtp.socketFactory.port", d_port);
        props.put("mail.smtp.socketFactory.class", "javax.net.ssl.SSLSocketFactory");
        props.put("mail.smtp.socketFactory.fallback", "false");

        Session session = Session.getInstance(props, new Authenticator() {
            @Override
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(d_uname, d_password);
            }
        });

        session.setDebug(true);

        MimeMessage msg = new MimeMessage(session);
        try {
            msg.setSubject(m_subject);
            msg.setFrom(new InternetAddress(d_email));
            msg.addRecipient(javax.mail.Message.RecipientType.TO, new InternetAddress(m_to));
            msg.setText("test email via gmail");

            Transport transport = session.getTransport("smtps");
//            transport.connect(d_host, d_port, d_uname, d_password);
//            transport.sendMessage(msg, msg.getAllRecipients());
//            transport.close();

        } catch (AddressException e) {
            e.printStackTrace();
        } catch (MessagingException e) {
            e.printStackTrace();
        }
    }

    @Test
    public void sendEmailviaEmailManagerSession() throws UnsupportedEncodingException, MessagingException {
        List<String> recipientList = new ArrayList<String>();
        recipientList.add("w.zhou@global.leaseweb.com");

        final String d_email = "leasewebcloud@gmail.com";
        final String d_uname = "leasewebcloud@gmail.com";
        final String d_password = "cloudstack";
        final String d_host = "smtp.gmail.com";
        final int d_port  = 465;
        final String m_to = "w.zhou@global.leaseweb.com";
        final String m_subject = "send Email via email manager session";
        final String m_text = "This message is from Leaseweb Cloud";

        Session session = emailManager.getSession();
        SMTPMessage msg = new SMTPMessage(session);
        msg.setSender(new InternetAddress(d_email, d_email));
        msg.setFrom(new InternetAddress(d_email, d_email));
        msg.addRecipient(javax.mail.Message.RecipientType.TO, new InternetAddress(m_to));

        msg.setSubject(m_subject);
        msg.setSentDate(new Date());
        msg.setContent(m_text, "text/html");
        msg.saveChanges();

        SMTPTransport smtpTrans = null;
        boolean _smtpSslAuth = true;
        if (_smtpSslAuth) {
            smtpTrans = new SMTPSSLTransport(session, new URLName("smtps", d_host, d_port, null, d_uname, d_password));
        } else {
            smtpTrans = new SMTPTransport(session, new URLName("smtp", d_host, d_port, null, d_uname, d_password));
        }
//        smtpTrans.connect();
//        smtpTrans.sendMessage(msg, msg.getAllRecipients());
//        smtpTrans.close();
    }

    @Test
    public void sendEmailviaEmailManager() throws UnsupportedEncodingException, MessagingException {
        List<String> recipientList = new ArrayList<String>();
        recipientList.add("w.zhou@global.leaseweb.com");

        emailManager.sendEmail(recipientList, "send Email via email manager", "this is content<br><hr>second part<hr>third part<li>aa</li><li>bb</li>");
    }
}
