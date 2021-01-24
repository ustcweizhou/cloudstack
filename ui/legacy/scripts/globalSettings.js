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

(function(cloudStack) {
    cloudStack.sections['global-settings'] = {
        title: 'label.menu.global.settings',
        id: 'global-settings',
        sectionSelect: {
            label: 'label.select-view'
        },
        sections: {
            globalSettings: {
                type: 'select',
                title: 'label.menu.global.settings',
                listView: {
                    label: 'label.menu.global.settings',
                    actions: {
                        edit: {
                            label: 'label.change.value',
                            action: function(args) {
                                var data = {
                                    name: args.data.jsonObj.name,
                                    value: args.data.value
                                };
                                $.ajax({
                                    url: createURL('updateConfiguration'),
                                    data: data,
                                    success: function(json) {
                                        var item = json.updateconfigurationresponse.configuration;
                                        if (item.category == "Usage" && item.isdynamic == false)
                                            cloudStack.dialog.notice({
                                                message: _l('message.restart.mgmt.usage.server')
                                            });
                                        else if (item.isdynamic == false)
                                            cloudStack.dialog.notice({
                                                message: _l('message.restart.mgmt.server')
                                            });
                                        args.response.success({
                                            data: item
                                        });
                                    },
                                    error: function(json) {
                                        args.response.error(parseXMLHttpResponse(json));
                                    }
                                });
                            }
                        }
                    },
                    fields: {
                        name: {
                            label: 'label.name',
                            id: true,
                            truncate: true
                        },
                        description: {
                            label: 'label.description'
                        },
                        value: {
                            label: 'label.value',
                            editable: true,
                            truncate: true
                        }
                    },
                    dataProvider: function(args) {
                        var data = {
                            page: args.page,
                            pagesize: pageSize
                        };

                        if (args.filterBy.search.value) {
                            data.name = args.filterBy.search.value;
                        }

                        $.ajax({
                            url: createURL('listConfigurations'),
                            data: data,
                            dataType: "json",
                            async: true,
                            success: function(json) {
                                var items = json.listconfigurationsresponse.configuration;
                                args.response.success({
                                    data: items
                                });
                            }
                        });
                    }
                }
            },
            ldapConfiguration: {
                type: 'select',
                title: 'label.ldap.configuration',
                listView: {
                    id: 'ldap',
                    label: 'label.ldap.configuration',
                    fields: {
                        hostname: {
                            label: 'label.host.name'
                        },
                        port: {
                            label: 'label.ldap.port'
                        }
                    },
                    dataProvider: function(args) {
                        var data = {};
                        listViewDataProvider(args, data);
                        $.ajax({
                            url: createURL('listLdapConfigurations'),
                            data: data,
                            success: function(json) {
                                var items = json.ldapconfigurationresponse.LdapConfiguration;
                                args.response.success({
                                    data: items
                                });
                            },
                            error: function(data) {
                                args.response.error(parseXMLHttpResponse(data));
                            }
                        });
                    },
                    detailView: {
                        name: 'label.details',
                        actions: {
                            remove: {
                                label: 'label.remove.ldap',
                                messages: {
                                    notification: function(args) {
                                        return 'label.remove.ldap';
                                    },
                                    confirm: function() {
                                        return 'message.remove.ldap';
                                    }
                                },
                                action: function(args) {
                                    $.ajax({
                                        url: createURL("deleteLdapConfiguration&hostname=" + args.context.ldapConfiguration[0].hostname),
                                        success: function(json) {
                                            args.response.success();
                                        }
                                    });
                                    $(window).trigger('cloudStack.fullRefresh');
                                }
                            }
                        },
                        tabs: {
                            details: {
                                title: 'label.ldap.configuration',
                                fields: [{
                                    hostname: {
                                        label: 'label.host.name'
                                    },
                                    port: {
                                        label: 'label.port'
                                    }
                                }],
                                dataProvider: function(args) {
                                    var items = [];
                                    $.ajax({
                                        url: createURL("listLdapConfigurations&hostname=" + args.context.ldapConfiguration[0].hostname),
                                        dataType: "json",
                                        async: true,
                                        success: function(json) {
                                            var item = json.ldapconfigurationresponse.LdapConfiguration;
                                            args.response.success({
                                                data: item[0]
                                            });
                                        }
                                    });
                                }
                            }
                        }
                    },
                    actions: {
                        add: {
                            label: 'label.configure.ldap',
                            messages: {
                                confirm: function(args) {
                                    return 'message.configure.ldap';
                                },
                                notification: function(args) {
                                    return 'label.configure.ldap';
                                }
                            },
                            createForm: {
                                title: 'label.configure.ldap',
                                fields: {
                                    hostname: {
                                        label: 'label.host.name',
                                        validation: {
                                            required: true
                                        }
                                    },
                                    port: {
                                        label: 'label.port',
                                        validation: {
                                            required: true
                                        }
                                    }
                                }
                            },
                            action: function(args) {
                                var array = [];
                                array.push("&hostname=" + encodeURIComponent(args.data.hostname));
                                array.push("&port=" + encodeURIComponent(args.data.port));
                                $.ajax({
                                    url: createURL("addLdapConfiguration" + array.join("")),
                                    dataType: "json",
                                    async: true,
                                    success: function(json) {
                                        var items = json.ldapconfigurationresponse.LdapAddConfiguration;
                                        args.response.success({
                                            data: items
                                        });
                                    },
                                    error: function(json) {
                                        args.response.error(parseXMLHttpResponse(json));
                                    }
                                });
                            }
                        }
                    }
                }
            },
            baremetalRct: {
                type: 'select',
                title: 'label.baremetal.rack.configuration',
                listView: {
                    id: 'baremetalRct',
                    label: 'label.baremetal.rack.configuration',
                    fields: {
                        id: {
                            label: 'label.id'
                        },
                        url: {
                            label: 'label.url'
                        }
                    },
                    dataProvider: function(args) {
                        var data = {};
                        listViewDataProvider(args, data);

                        $.ajax({
                            url: createURL("listBaremetalRct"),
                            data: data,
                            success: function(json) {
                                args.response.success({ data: json.listbaremetalrctresponse.baremetalrct });
                            }
                        });
                    },
                    actions: {
                        add: {
                            label: 'label.add.baremetal.rack.configuration',
                            messages: {
                                notification: function(args) {
                                    return 'label.add.baremetal.rack.configuration';
                                }
                            },
                            createForm: {
                                title: 'label.add.baremetal.rack.configuration',
                                fields: {
                                    url: {
                                        label: 'label.url',
                                        validation: {
                                            required: true
                                        }
                                    }
                                }
                            },
                            action: function(args) {
                                $.ajax({
                                    url: createURL("addBaremetalRct"),
                                    data: {
                                        baremetalrcturl: args.data.url
                                    },
                                    success: function(json) {
                                        var jid = json.addbaremetalrctresponse.jobid
                                        args.response.success({
                                            _custom: {
                                                jobId: jid,
                                                getUpdatedItem: function(json) {
                                                    return json.queryasyncjobresultresponse.jobresult.baremetalrct;
                                                }
                                            }
                                        });
                                    }
                                });
                            },
                            notification: {
                                poll: pollAsyncJobResult
                            }
                        }
                    },

                    detailView: {
                        name: "details",
                        actions: {
                            remove: {
                                label: 'label.delete.baremetal.rack.configuration',
                                messages: {
                                    confirm: function(args) {
                                        return 'message.confirm.delete.baremetal.rack.configuration';
                                    },
                                    notification: function(args) {
                                        return 'label.delete.baremetal.rack.configuration';
                                    }
                                },
                                action: function(args) {
                                    var data = {
                                        id: args.context.baremetalRct[0].id
                                    };
                                    $.ajax({
                                        url: createURL('deleteBaremetalRct'),
                                        data: data,
                                        success: function(json) {
                                            var jid = json.deletebaremetalrctresponse.jobid;
                                            args.response.success({
                                                _custom: {
                                                    jobId: jid
                                                }
                                            });
                                        }
                                    });
                                },
                                notification: {
                                    poll: pollAsyncJobResult
                                }
                            }
                        },
                        tabs: {
                            details: {
                                title: 'label.details',
                                fields: [{
                                    id: {
                                        label: 'label.id'
                                    },
                                    url: {
                                        label: 'label.url'
                                    }
                                }],
                                dataProvider: function(args) {
                                    var data = {
                                        id: args.context.baremetalRct[0].id
                                    };
                                    $.ajax({
                                        url: createURL("listBaremetalRct"),
                                        data: data,
                                        success: function(json) {
                                            args.response.success({ data: json.listbaremetalrctresponse.baremetalrct[0] });
                                        }
                                    });
                                }
                            }
                        }
                    }
                }
            },
            hypervisorCapabilities: {
                type: 'select',
                title: 'label.hypervisor.capabilities',
                listView: {
                    id: 'hypervisorCapabilities',
                    label: 'label.hypervisor.capabilities',
                    actions: {
                        add: {
                            label: 'Add hypervisor capabilities',
                            createForm: {
                                title: 'Add hypervisor capabilities',
                                fields: {
                                    hypervisor: {
                                        label: 'Hypervisor type',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'VMware',
                                                description: 'VMware'
                                            });
                                            items.push({
                                                id: 'XenServer',
                                                description: 'XenServer'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        validation: {
                                            required: true
                                        },
                                    },
                                    version: {
                                        label: 'Hypervisor version',
                                        validation: {
                                            required: true
                                        },
                                    },
                                    source: {
                                        label: 'Source hypervisor version',
                                        validation: {
                                            required: true
                                        },
                                    }
                                }
                            },
                            action: function(args) {
                            },
                            messages: {
                                notification: function() {
                                    return 'Added hypervisor capabilities';
                                }
                            }
                        },
                    },
                    fields: {
                        hypervisor: {
                            label: 'label.hypervisor'
                        },
                        hypervisorversion: {
                            label: 'label.hypervisor.version'
                        },
                        maxguestslimit: {
                            label: 'label.max.guest.limit'
                        }
                    },
                    dataProvider: function(args) {
                        var data = {};
                        listViewDataProvider(args, data);

                        $.ajax({
                            url: createURL('listHypervisorCapabilities'),
                            data: data,
                            success: function(json) {
                                var items = json.listhypervisorcapabilitiesresponse.hypervisorCapabilities;
                                args.response.success({
                                    data: items
                                });
                            },
                            error: function(data) {
                                args.response.error(parseXMLHttpResponse(data));
                            }
                        });
                    },

                    detailView: {
                        name: 'label.details',
                        actions: {
                            remove: {
                                label: 'Remove hypervisor capabilities',
                                messages: {
                                    notification: function(args) {
                                        return 'Remove hypervisor capabilities';
                                    },
                                    confirm: function() {
                                        return 'Remove hypervisor capabilities';
                                    }
                                },
                                action: function(args) {
                                    $.ajax({
                                        success: function(json) {
                                            args.response.success();
                                        }
                                    });
                                    $(window).trigger('cloudStack.fullRefresh');
                                }
                            },
                            edit: {
                                label: 'label.edit',
                                action: function(args) {
                                    var data = {
                                        id: args.context.hypervisorCapabilities[0].id,
                                        maxguestslimit: args.data.maxguestslimit
                                    };

                                    $.ajax({
                                        url: createURL('updateHypervisorCapabilities'),
                                        data: data,
                                        success: function(json) {
                                            var item = json.updatehypervisorcapabilitiesresponse['null'];
                                            args.response.success({
                                                data: item
                                            });
                                        },
                                        error: function(data) {
                                            args.response.error(parseXMLHttpResponse(data));
                                        }
                                    });
                                }
                            }
                        },

                        tabs: {
                            details: {
                                title: 'label.details',
                                fields: [{
                                    id: {
                                        label: 'label.id'
                                    },
                                    hypervisor: {
                                        label: 'label.hypervisor'
                                    },
                                    hypervisorversion: {
                                        label: 'label.hypervisor.version'
                                    },
                                    maxguestslimit: {
                                        label: 'label.max.guest.limit',
                                        isEditable: true
                                    }
                                }],
                                dataProvider: function(args) {
                                    args.response.success({
                                        data: args.context.hypervisorCapabilities[0]
                                    });
                                }
                            }
                        }
                    }
                }
            },
            ostype: {
                type: 'select',
                title: 'Guest OS type',
                listView: {
                    id: 'guestostype',
                    label: 'Guest OS type',
                    actions: {
                        add: {
                            label: 'Add Guest OS type',
                            createForm: {
                                title: 'Add Guest OS type',
                                desc: 'Add a Guest OS type. The details will be copied from Source Guest OS.',
                                fields: {
                                    oscategoryid: {
                                        label: 'Guest OS Category',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'CentOS',
                                                description: 'CentOS'
                                            });
                                            items.push({
                                                id: 'Debian',
                                                description: 'Debian'
                                            });
                                            items.push({
                                                id: 'RedHat',
                                                description: 'RedHat'
                                            });
                                            items.push({
                                                id: 'Ubuntu',
                                                description: 'Ubuntu'
                                            });
                                            items.push({
                                                id: 'Windows',
                                                description: 'Windows'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        validation: {
                                            required: true
                                        },
                                    },
                                    name: {
                                        label: 'Guest OS name',
                                        validation: {
                                            required: true
                                        },
                                    },
                                    source: {
                                        label: 'Source guest OS name',
                                        validation: {
                                            required: true
                                        },
                                    }
                                }
                            },
                            action: function(args) {
                            },
                            messages: {
                                notification: function() {
                                    return 'Added Guest OS';
                                }
                            }
                        },
                    },
                    fields: {
                        description: {
                            label: 'label.name'
                        },
                        isuserdefined: {
                            label: 'User defined',
                            converter: cloudStack.converters.toBooleanText
                        },
                        oscategoryname: {
                            label: 'Guest OS Category'
                        }
                    },
                    advSearchFields: {
                        keyword: {
                            label: 'label.name'
                        }
                    },
                    dataProvider: function(args) {
                        var data = {};
                        listViewDataProvider(args, data);

                        $.ajax({
                            url: createURL('listOsTypes'),
                            data: data,
                            success: function(json) {
                                var items = json.listostypesresponse.ostype;
                                args.response.success({
                                    data: items
                                });
                            },
                            error: function(data) {
                                args.response.error(parseXMLHttpResponse(data));
                            }
                        });
                    },

                    detailView: {
                        name: 'label.details',
                        actions: {
                            remove: {
                                label: 'Remove Guest OS',
                                messages: {
                                    notification: function(args) {
                                        return 'Remove Guest OS';
                                    },
                                    confirm: function() {
                                        return 'Remove Guest OS';
                                    }
                                },
                                action: function(args) {
                                    $.ajax({
                                        success: function(json) {
                                            args.response.success();
                                        }
                                    });
                                    $(window).trigger('cloudStack.fullRefresh');
                                }
                            },
                            edit: {
                                label: 'label.edit',
                                action: function(args) {
                                    var data = {
                                        id: args.context.ostype[0].id,
                                        osdisplayname: args.data.description
                                    };

                                    $.ajax({
                                        url: createURL('updateGuestOs'),
                                        data: data,
                                        success: function(json) {
                                            var item = json.updateguestosresponse['null'];
                                            args.response.success({
                                                data: item
                                            });
                                        },
                                        error: function(data) {
                                            args.response.error(parseXMLHttpResponse(data));
                                        }
                                    });
                                }
                            }
                        },

                        tabs: {
                            details: {
                                title: 'label.details',
                                fields: [{
                                    id: {
                                        label: 'label.id'
                                    },
                                    description: {
                                        label: 'label.name',
                                        isEditable: true
                                    },
                                    isuserdefined: {
                                        label: 'User defined',
                                        converter: cloudStack.converters.toBooleanText
                                    },
                                    oscategoryname: {
                                        label: 'Guest OS Category'
                                    }
                                }],
                                dataProvider: function(args) {
                                    args.response.success({
                                        data: args.context.ostype[0]
                                    });
                                }
                            }
                        }
                    }
                }
            },
            guestosmapping: {
                type: 'select',
                title: 'Guest OS - Hypervisor mapping',
                listView: {
                    id: 'guestosmapping',
                    label: 'Guest OS - Hypervisor mapping',
                    filters: {
                        display: {
                            label: 'Visible to end user'
                        },
                        hidden: {
                            label: 'Not visible to end user'
                        }
                    },
                    actions: {
                        add: {
                            label: 'Add mapping',
                            createForm: {
                                title: 'Add Guest OS mapping',
                                desc: 'Add a guest OS name to hypervisor OS name mapping. Please input correct Guest OS identifier for hypervisor.',
                                fields: {
                                    hypervisor: {
                                        label: 'Hypervisor type',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'VMware',
                                                description: 'VMware'
                                            });
                                            items.push({
                                                id: 'XenServer',
                                                description: 'XenServer'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        validation: {
                                            required: true
                                        },
                                    },
                                    version: {
                                        label: 'Hypervisor version',
                                        validation: {
                                            required: true
                                        },
                                    },
                                    osdisplayname: {
                                        label: 'Guest OS',
                                        validation: {
                                            required: true
                                        },
                                    },
                                    osnameforhypervisor: {
                                        label: 'Guest OS identifier',
                                        validation: {
                                            required: true
                                        },
                                    }
                                }
                            },
                            action: function(args) {
                            },
                            messages: {
                                notification: function() {
                                    return 'Added Guest OS mapping';
                                }
                            }
                        },
                        // Copy multiple mappings from guest os or hypervisor version
                        copy: {
                            label: 'Copy mappings',
                            isHeader: true,
                            addRow: false,
                            messages: {
                                confirm: function(args) {
                                    return 'Copy Guest OS mapping';
                                },
                                notification: function(args) {
                                    return 'Copy Guest OS mapping';
                                }
                            },
                            createForm: {
                                title: 'Copy Guest OS mapping',
                                desc: 'Copy all guest OS mapping from specific hypervisor version or guest OS. Please input one of source hypervisor version and source guest os.',
                                fields: {
                                    hypervisor: {
                                        label: 'Hypervisor type',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'VMware',
                                                description: 'VMware'
                                            });
                                            items.push({
                                                id: 'XenServer',
                                                description: 'XenServer'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        validation: {
                                            required: true
                                        },
                                    },
                                    hypervisorversion: {
                                        label: 'Hypervisor version',
                                        validation: {
                                            required: true
                                        }
                                    },
                                    sourcehypervisorversion: {
                                        label: 'Source hypervisor version'
                                    },
                                    osdisplayname: {
                                        label: 'Guest OS',
                                        validation: {
                                            required: true
                                        }
                                    },
                                    sourceguestos: {
                                        label: 'Source guest OS'
                                    }
                                }
                            },
                            action: function(args) {
                            }
                        },
                        // update multiple mappings from guest os or hypervisor version
                        update: {
                            label: 'Update mappings',
                            isHeader: true,
                            addRow: false,
                            messages: {
                                confirm: function(args) {
                                    return 'Update Guest OS mappings';
                                },
                                notification: function(args) {
                                    return 'Update Guest OS mappings';
                                }
                            },
                            createForm: {
                                title: 'Update Guest OS mappings',
                                desc: 'Update guest OS mappings by specific hypervisor version and/or guest OS type.',
                                fields: {
                                    hypervisor: {
                                        label: 'Hypervisor type',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'VMware',
                                                description: 'VMware'
                                            });
                                            items.push({
                                                id: 'XenServer',
                                                description: 'XenServer'
                                            });
                                            items.push({
                                                id: 'KVM',
                                                description: 'KVM'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        validation: {
                                            required: true
                                        }
                                    },
                                    hypervisorversion: {
                                        label: 'Hypervisor version',
                                        validation: {
                                            required: true
                                        }
                                    },
                                    osdisplayname: {
                                        label: 'Guest OS',
                                        validation: {
                                            required: true
                                        }
                                    },
                                    fordisplay: {
                                        label: 'Visible to end user',
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'true',
                                                description: 'Yes'
                                            });
                                            items.push({
                                                id: 'false',
                                                description: 'No'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                    }
                                }
                            },
                            action: function(args) {
                            }
                        }
                    },

                    fields: {
                        hypervisor: {
                            label: 'label.hypervisor'
                        },
                        hypervisorversion: {
                            label: 'Hypervisor version'
                        },
                        osdisplayname: {
                            label: 'Guest OS'
                        },
                        osnameforhypervisor: {
                            label: 'Guest OS identifier'
                        },
                        isuserdefined: {
                            label: 'User defined',
                            converter: function(booleanValue) {
                                if (booleanValue == "true")
                                    return "Yes"
                                else if (booleanValue == "false")
                                    return "No";
                            }
                        }
                    },
                    advSearchFields: {
                        hypervisor: {
                            label: 'label.hypervisor',
                            select: function(args) {
                                var items = [];
                                items.push({
                                    id: 'VMware',
                                    description: 'VMware'
                                });
                                items.push({
                                    id: 'XenServer',
                                    description: 'XenServer'
                                });
                                items.push({
                                    id: 'KVM',
                                    description: 'KVM'
                                });
                                args.response.success({
                                    data: items
                                });
                            }
                        },
                        hypervisorversion: {
                            label: 'Version'
                        },
                        keyword: {
                            label: 'label.name'
                        }
                    },
                    dataProvider: function(args) {
                        var data = {};
                        listViewDataProvider(args, data);

                        if (args.filterBy != null) { //filter dropdown
                            if (args.filterBy.kind != null) {
                                switch (args.filterBy.kind) {
                                    case "display":
                                        $.extend(data, {
                                            fordisplay: 'true'
                                        });
                                        break;
                                    case "hidden":
                                        $.extend(data, {
                                            fordisplay: 'false'
                                        });
                                        break;
                                }
                            }
                        }

                        $.ajax({
                            url: createURL('listGuestOsMapping'),
                            data: data,
                            success: function(json) {
                                var items = json.listguestosmappingresponse.guestosmapping;
                                args.response.success({
                                    data: items
                                });
                            },
                            error: function(data) {
                                args.response.error(parseXMLHttpResponse(data));
                            }
                        });
                    },

                    detailView: {
                        name: 'label.details',
                        actions: {
                            remove: {
                                label: 'Remove Guest OS mapping',
                                messages: {
                                    notification: function(args) {
                                        return 'Remove Guest OS mapping';
                                    },
                                    confirm: function() {
                                        return 'Remove Guest OS mapping';
                                    }
                                },
                                action: function(args) {
                                    $.ajax({
                                        success: function(json) {
                                            args.response.success();
                                        }
                                    });
                                    $(window).trigger('cloudStack.fullRefresh');
                                }
                            },
                            edit: {
                                label: 'label.edit',
                                action: function(args) {
                                    var data = {
                                        id: args.context.ostype[0].id,
                                        osnameforhypervisor: args.data.osnameforhypervisor
                                    };

                                    $.ajax({
                                        url: createURL('updateGuestOsMapping'),
                                        data: data,
                                        success: function(json) {
                                            var item = json.updateguestosmappingresponse['null'];
                                            args.response.success({
                                                data: item
                                            });
                                        },
                                        error: function(data) {
                                            args.response.error(parseXMLHttpResponse(data));
                                        }
                                    });
                                }
                            }
                        },

                        tabs: {
                            details: {
                                title: 'label.details',
                                fields: [{
                                    id: {
                                        label: 'label.id'
                                    },
                                    hypervisor: {
                                        label: 'label.hypervisor'
                                    },
                                    hypervisorversion: {
                                        label: 'Hypervisor version'
                                    },
                                    osdisplayname: {
                                        label: 'Guest OS'
                                    },
                                    osnameforhypervisor: {
                                        label: 'Guest OS identifier',
                                        isEditable: true
                                    },
                                    fordisplay: {
                                        label: 'Visible to end user',
                                        isEditable: true,
                                        select: function(args) {
                                            var items = [];
                                            items.push({
                                                id: 'true',
                                                description: 'Yes'
                                            });
                                            items.push({
                                                id: 'false',
                                                description: 'No'
                                            });
                                            args.response.success({
                                                data: items
                                            });
                                        },
                                        converter: cloudStack.converters.toBooleanText
                                    },
                                    isuserdefined: {
                                        label: 'User defined',
                                        converter: function(booleanValue) {
                                            if (booleanValue == "true")
                                                return "Yes"
                                            else if (booleanValue == "false")
                                                return "No";
                                        }
                                    }
                                }],
                                dataProvider: function(args) {
                                    args.response.success({
                                        data: args.context.guestosmapping[0]
                                    });
                                }
                            }
                        }
                    }
                }
            },
        }
    };
})(cloudStack);
