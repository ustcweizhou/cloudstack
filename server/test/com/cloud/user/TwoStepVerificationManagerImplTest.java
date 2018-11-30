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

import com.warrenstrange.googleauth.GoogleAuthenticator;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;

import org.junit.Test;

public class TwoStepVerificationManagerImplTest {
    @Test
    public void generateAndVerifyCode() {
        // mvn -P developer,systemvm -pl server -Dtest=com.cloud.user.TwoStepVerificationManagerImplTest
        GoogleAuthenticator gAuth = new GoogleAuthenticator();
        GoogleAuthenticatorKey key = gAuth.createCredentials();
        String secretKey = key.getKey();
        int code = gAuth.getTotpPassword(secretKey);
        System.out.println("secret key is " + secretKey + ", verification code is " + code);

        for (int i = 0; i < 120; i++) {
            boolean isCodeValid = gAuth.authorize(secretKey, code);
            if (isCodeValid) {
                System.out.println("Two step verification passed after " + i + "s");
            } else {
                System.out.println("Two step verification did not pass after " + i + "s");
                break;
            }
            try {
                Thread.sleep(1000);
            } catch (Exception e) {
            }
        }
    }
}
