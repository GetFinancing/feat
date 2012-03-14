# F3AT - Flumotion Asynchronous Autonomous Agent Toolkit
# Copyright (C) 2010,2011 Flumotion Services, S.A.
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# See "LICENSE.GPL" in the source distribution for more information.

# Headers in this file shall remain intact.
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
from zope.interface import implements

from feat.agents.base import replay, poster, contractor
from feat.agencies import recipient, message
from feat.common import serialization, annotate, container, formatable
from feat.agents.application import feat

from feat.interface.alert import IAlertFactory, Severity, IAlert
from feat.interface.protocols import InterestType


def may_raise(factory):
    annotate.injectClassCallback("alert", 3, "_register_alert_factory",
                                 factory)


@feat.register_restorator
class AlertingAgentEntry(formatable.Formatable):

    formatable.field('hostname', None)
    formatable.field('agent_id', None)
    formatable.field('alerts', []) #[IAlertFactory]


class AlertsDiscoveryContractor(contractor.BaseContractor):

    protocol_id = 'discover-alerts'
    interest_type = InterestType.public

    @replay.journaled
    def announced(self, state, announcement):
        payload = AlertingAgentEntry(
            hostname=state.agent.get_hostname(),
            agent_id=state.agent.get_agent_id(),
            alerts=type(state.agent)._alert_factories.values())
        state.medium.bid(message.Bid(payload=payload))


class MetaAlert(type(serialization.Serializable)):
    implements(IAlertFactory)


class BaseAlert(serialization.Serializable):
    __metaclass__ = MetaAlert

    implements(IAlert)

    name = None
    severity = None

    def __init__(self, hostname, agent_id, status_info=None):
        self.name = type(self).name
        self.severity = type(self).severity
        self.hostname = hostname
        self.agent_id = agent_id
        self.status_info = status_info

        assert self.name is not None, \
               "Class %r should have name attribute set" % (type(self), )
        assert isinstance(self.severity, Severity), \
               "Class %r should have severity attribute set" % (type(self), )


class AgentMixin(object):

    _alert_factories = container.MroDict("_mro_alert_factories")

    ### anotations ###

    @classmethod
    def _register_alert_factory(cls, factory):
        f = IAlertFactory(factory)
        cls._alert_factories[f.name] = f

    ### public ###

    @replay.mutable
    def initiate(self, state):
        state.medium.register_interest(AlertsDiscoveryContractor)
        recp = recipient.Broadcast(AlertPoster.protocol_id,
                                   self.get_shard_id())
        state.alerter = self.initiate_protocol(AlertPoster, recp)

    @replay.mutable
    def raise_alert(self, state, service_name, status_info=None):
        alert = self._generate_alert(service_name, status_info)
        state.alerter.notify('raised', alert)

    @replay.mutable
    def resolve_alert(self, state, service_name, status_info=None):
        alert = self._generate_alert(service_name, status_info)
        state.alerter.notify('resolved', alert)

    ### private ###

    @replay.immutable
    def _generate_alert(self, state, service_name, status_info):
        alert_factory = type(self)._alert_factories.get(service_name, None)
        assert alert_factory is not None, \
               "Unknown service name %r" % (service_name, )
        return alert_factory(hostname=state.medium.get_hostname(),
                             status_info=status_info,
                             agent_id=self.get_agent_id())


class AlertPoster(poster.BasePoster):

    protocol_id = 'alert'

    def pack_payload(self, action, alert):
        return action, alert
