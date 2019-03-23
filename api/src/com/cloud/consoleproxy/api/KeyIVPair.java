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
package com.cloud.consoleproxy.api;

import org.apache.commons.codec.binary.Base64;

public class KeyIVPair {
    String base64EncodedKeyBytes;
    String base64EncodedIvBytes;

    public KeyIVPair() {
    }

    public KeyIVPair(String base64EncodedKeyBytes, String base64EncodedIvBytes) {
        this.base64EncodedKeyBytes = base64EncodedKeyBytes;
        this.base64EncodedIvBytes = base64EncodedIvBytes;
    }

    public String getKey() {
        return this.base64EncodedKeyBytes;
    }

    public byte[] getKeyBytes() {
        return Base64.decodeBase64(base64EncodedKeyBytes);
    }

    public void setKeyBytes(byte[] keyBytes) {
        base64EncodedKeyBytes = Base64.encodeBase64URLSafeString(keyBytes);
    }

    public String getIV() {
        return this.base64EncodedIvBytes;
    }

    public byte[] getIvBytes() {
        return Base64.decodeBase64(base64EncodedIvBytes);
    }

    public void setIvBytes(byte[] ivBytes) {
        base64EncodedIvBytes = Base64.encodeBase64URLSafeString(ivBytes);
    }
}
