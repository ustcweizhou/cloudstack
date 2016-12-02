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

(function($, cloudStack) {

    cloudStack.uiCustom.sslCertificate = function(args) {

        // Place outer args here as local variables
        // i.e, -- var dataProvider = args.dataProvider

        return function(args) {
            if (args.context.multiRules == undefined) { //LB rule is not created yet
                cloudStack.dialog.notice({
                    message: _l('SSL Certificate only be configured on a created LB rule')
                });
                return;
            }

            var formData = args.formData;
            var forms = $.extend(true, {}, args.forms);
            var topFieldForm, $topFieldForm;
            var topfields = forms.topFields;

            var $sslCertConfigTitle = $('<div>' + _l('Please select a SSL Certificate to be assigned to the load balancer. <br>Please go to Accounts (left panel)->(choose account)->"SSL Certificate" to get more details of the SSL certificates.') + '</div>').addClass('ssl-certificate-description');

            var $sslCertDialog = $('<div>').addClass('ssl-certificate');
            var $loadingOnDialog = $('<div>').addClass('loading-overlay');

            var sslCertObj = null;

            $.ajax({
                url: createURL('listSslCerts'),
                data: {
                    lbruleid: args.context.multiRules[0].id
                },
                async: false,
                success: function(json) {
                    if (json.listsslcertsresponse.sslcert != null && json.listsslcertsresponse.sslcert.length > 0) {
                        sslCertObj = json.listsslcertsresponse.sslcert[0];
                    }
                }
            });

            topFieldForm = cloudStack.dialog.createForm({
                context: args.context,
                noDialog: true, // Don't render a dialog, just return $formContainer
                form: {
                    title: '',
                    fields: {
                        certid: {
                            label: 'label.ssl.certificate',
                            validation: {
                                required: false
                            },
                            select: function(args) {
                                var data = {};
                                $.ajax({
                                    url: createURL("listLoadBalancerRules&id=" + args.context.multiRules[0].id),
                                    dataType: "json",
                                    async: false,
                                    success: function(json) {
                                        var projectid = json.listloadbalancerrulesresponse.loadbalancerrule[0].projectid;
                                        if (projectid != null) {
                                            $.extend(data, {
                                                projectid: projectid
                                            });
                                        } else {
                                            var domainid = json.listloadbalancerrulesresponse.loadbalancerrule[0].domainid;
                                            var accountName = json.listloadbalancerrulesresponse.loadbalancerrule[0].account;
                                            $.ajax({
                                                url: createURL("listAccounts&domainid=" + domainid + "&name=" + accountName),
                                                dataType: "json",
                                                async: false,
                                                success: function(json) {
                                                    $.extend(data, {
                                                        accountid: json.listaccountsresponse.account[0].id
                                                    });
                                                }
                                            });
                                        }
                                    }
                                });

                                $.ajax({
                                    url: createURL("listSslCerts"),
                                    dataType: "json",
                                    data: data,
                                    async: false,
                                    success: function(json) {
                                        if (json.listsslcertsresponse.sslcert != null) {
                                            sslSertObjs = json.listsslcertsresponse.sslcert;
                                            var items = [];
                                            $(sslSertObjs).each(function() {
                                                items.push({
                                                    id: this.id,
                                                    description: this.id
                                                });
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        } else {
                                            cloudStack.dialog.notice({
                                                message: _l('No SSL Certificates are avaialble')
                                            });
                                        }
                                    }
                                });
                            }
                        }
                    }
                }
            });

            $topFieldForm = topFieldForm.$formContainer;

            var $loadbalancerrule = $('<br><br><div>'+ _l('label.load.balancer.rule') + ': ' + _l(args.context.multiRules[0].id) + '</div>').addClass('ssl-certificate-content');
            if (sslCertObj == null) { //ssl certificate is not configured yet
                $sslCertDialog.append($sslCertConfigTitle).append($loadbalancerrule);
                $topFieldForm.appendTo($sslCertDialog);
            } else {
                var $sslCertConfigRemove = $('<div>' + _l('Please confirm that you will remove this certificate from load balancer rule.') + '</div>').addClass('ssl-certificate-description');
                var $sslCertificate = $('<div>'+ _l('label.ssl.certificate') + ': ' + _l(sslCertObj.id) + '</div>').addClass('ssl-certificate-content');
                $sslCertDialog.append($sslCertConfigRemove).append($loadbalancerrule).append($sslCertificate);
            }

            var buttons = [{
                text: _l('label.cancel'),
                'class': 'cancel',
                click: function() {
                    $sslCertDialog.dialog('destroy');
                    $('.overlay').remove();
                }
            }];

            if (sslCertObj == null) { //ssl certificate is not configured yet
                buttons.push({
                    text: _l('Assign'),
                    'class': 'ok',
                    click: function() {
                        $loadingOnDialog.appendTo($sslCertDialog);
                        var formData = cloudStack.serializeForm($sslCertDialog.find('form'));
                        var data = {
                            lbruleid: args.context.multiRules[0].id,
                            certid: formData.certid
                        };

                        $.ajax({
                            url: createURL('assignCertToLoadBalancer'),
                            data: data,
                            success: function(json) {
                                var jobId = json.assigncerttoloadbalancerresponse.jobid;
                                var assignCertToLoadBalancerIntervalId = setInterval(function() {
                                    $.ajax({
                                        url: createURL('queryAsyncJobResult'),
                                        data: {
                                            jobid: jobId
                                        },
                                        success: function(json) {
                                            var result = json.queryasyncjobresultresponse;
                                            if (result.jobstatus == 0) {
                                                return; //Job has not completed
                                            } else {
                                                clearInterval(assignCertToLoadBalancerIntervalId);

                                                if (result.jobstatus == 1) {
                                                    isHidden: 2,
                                                    cloudStack.dialog.notice({
                                                        message: _l('SSL Certificate has been assigned to load balancer')
                                                    });
                                                    $loadingOnDialog.remove();
                                                    $sslCertDialog.dialog('destroy');
                                                    $('.overlay').remove();
                                                } else if (result.jobstatus == 2) {
                                                    cloudStack.dialog.notice({
                                                        message: _s(result.jobresult.errortext)
                                                    });
                                                    $loadingOnDialog.remove();
                                                    $sslCertDialog.dialog('destroy');
                                                    $('.overlay').remove();
                                                }
                                            }
                                        }
                                    });
                                }, g_queryAsyncJobResultInterval);
                            },

                            error: function(json) {

                                cloudStack.dialog.notice({
                                    message: parseXMLHttpResponse(json)
                                }); //Error message in the API needs to be improved
                                $sslCertDialog.dialog('close');
                                $('.overlay').remove();
                            }

                        });
                    }
                });
            } else { // ssl certificate has been already assigned
                buttons.push(
                    //Delete Button (begin) - call delete API
                    {
                        text: _l('Remove'),
                        'class': 'delete',
                        click: function() {
                            $loadingOnDialog.appendTo($sslCertDialog);

                            $.ajax({
                                url: createURL('removeCertFromLoadBalancer'),
                                data: {
                                    lbruleid: args.context.multiRules[0].id
                                },
                                success: function(json) {
                                    var jobId = json.removecertfromloadbalancerresponse.jobid;
                                    var removeCertFromLoadBalancerIntervalId = setInterval(function() {
                                        $.ajax({
                                            url: createURL('queryAsyncJobResult'),
                                            data: {
                                                jobid: jobId
                                            },
                                            success: function(json) {
                                                var result = json.queryasyncjobresultresponse;
                                                if (result.jobstatus == 0) {
                                                    return; //Job has not completed
                                                } else {
                                                    clearInterval(removeCertFromLoadBalancerIntervalId);

                                                    if (result.jobstatus == 1) {
                                                        cloudStack.dialog.notice({
                                                            message: _l('SSL Certificate has been removed from load balancer')
                                                        });
                                                        $loadingOnDialog.remove();
                                                        $sslCertDialog.dialog('destroy');
                                                        $('.overlay').remove();
                                                    } else if (result.jobstatus == 2) {
                                                        cloudStack.dialog.notice({
                                                            message: _s(result.jobresult.errortext)
                                                        });
                                                        $loadingOnDialog.remove();
                                                        $sslCertDialog.dialog('destroy');
                                                        $('.overlay').remove();
                                                    }
                                                }
                                            }
                                        });
                                    }, g_queryAsyncJobResultInterval);
                                }
                            });
                        }
                    }
                    //Delete Button (end)
                );
            }

            $sslCertDialog.dialog({
                title: _l('label.ssl.certificate'),
                width: 500,
                height: 250,
                draggable: true,
                closeonEscape: false,
                overflow: 'auto',
                open: function() {
                    $("button").each(function() {
                        $(this).attr("style", "left: 150px; position: relative; margin-right: 5px; ");
                    });

                    $('.ui-dialog .delete').css('left', '150px');

                },
                buttons: buttons
            }).closest('.ui-dialog').overlay();

        }
    }
}(jQuery, cloudStack));
